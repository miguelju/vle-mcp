"""Hardened Streamable HTTP application factory for remote MCP clients."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import anyio
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from vle_mcp.server import create_mcp

READ_SCOPE = "vle:read"


@dataclass(frozen=True)
class RemoteLimits:
    """Per-process safeguards; ingress should enforce equivalent outer limits."""

    max_request_body_bytes: int = 64 * 1024
    requests_per_window: int = 60
    rate_window_seconds: float = 60.0
    max_concurrent_requests: int = 8
    request_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        values = (
            self.max_request_body_bytes,
            self.requests_per_window,
            self.rate_window_seconds,
            self.max_concurrent_requests,
            self.request_timeout_seconds,
        )
        if any(value <= 0 for value in values):
            raise ValueError("all remote limits must be positive")


class ResourceBoundTokenVerifier:
    """Require the delegate's verified token to target this issuer and resource.

    The delegate remains responsible for cryptographic signature, audience,
    expiry, and issuer validation against the authorization server. This wrapper
    rejects incomplete verifier results and prevents tokens for another MCP
    resource from being accepted.
    """

    def __init__(
        self,
        delegate: TokenVerifier,
        *,
        issuer_url: str,
        resource_server_url: str,
    ) -> None:
        self._delegate = delegate
        self._issuer_url = issuer_url.rstrip("/")
        self._resource_server_url = resource_server_url

    async def verify_token(self, token: str) -> AccessToken | None:
        verified = await self._delegate.verify_token(token)
        if verified is None or verified.expires_at is None:
            return None
        if verified.resource != self._resource_server_url:
            return None
        issuer = (verified.claims or {}).get("iss")
        if not isinstance(issuer, str) or issuer.rstrip("/") != self._issuer_url:
            return None
        return verified


class RemoteLimitMiddleware:
    """Apply global rate, concurrency, and wall-clock limits to HTTP requests."""

    def __init__(
        self,
        app: ASGIApp,
        limits: RemoteLimits,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self._limits = limits
        self._clock = clock
        self._recent_requests: deque[float] = deque()
        self._rate_lock = anyio.Lock()
        self._capacity = anyio.CapacityLimiter(limits.max_concurrent_requests)

    async def _rate_limited(self) -> bool:
        now = self._clock()
        cutoff = now - self._limits.rate_window_seconds
        async with self._rate_lock:
            while self._recent_requests and self._recent_requests[0] <= cutoff:
                self._recent_requests.popleft()
            if len(self._recent_requests) >= self._limits.requests_per_window:
                return True
            self._recent_requests.append(now)
            return False

    @staticmethod
    async def _error(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        message: str,
    ) -> None:
        response = JSONResponse({"error": message}, status_code=status_code)
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if await self._rate_limited():
            await self._error(scope, receive, send, 429, "rate limit exceeded")
            return
        try:
            self._capacity.acquire_nowait()
        except anyio.WouldBlock:
            await self._error(scope, receive, send, 503, "concurrency limit exceeded")
            return
        try:
            pending: list[Message] = []

            async def capture(message: Message) -> None:
                pending.append(message)

            with anyio.fail_after(self._limits.request_timeout_seconds):
                await self.app(scope, receive, capture)
        except TimeoutError:
            await self._error(scope, receive, send, 504, "request timed out")
        else:
            for message in pending:
                await send(message)
        finally:
            self._capacity.release()


def create_remote_app(
    *,
    token_verifier: TokenVerifier,
    issuer_url: str,
    resource_server_url: str,
    allowed_hosts: list[str],
    allowed_origins: list[str],
    limits: RemoteLimits | None = None,
) -> ASGIApp:
    """Create an OAuth-protected, stateless Streamable HTTP ASGI application.

    ``resource_server_url`` is the externally visible HTTPS MCP endpoint and is
    both the OAuth resource identifier and the audience/resource binding.
    """

    if not resource_server_url.startswith("https://"):
        raise ValueError("resource_server_url must use HTTPS")
    if not issuer_url.startswith("https://"):
        raise ValueError("issuer_url must use HTTPS")
    if not allowed_hosts:
        raise ValueError("allowed_hosts must not be empty")

    effective_limits = limits or RemoteLimits()
    verifier = ResourceBoundTokenVerifier(
        token_verifier,
        issuer_url=issuer_url,
        resource_server_url=resource_server_url,
    )
    server = create_mcp(
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=issuer_url,
            resource_server_url=resource_server_url,
            required_scopes=[READ_SCOPE],
        ),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        ),
        stateless_http=True,
        json_response=True,
        max_request_body_size=effective_limits.max_request_body_bytes,
    )
    return RemoteLimitMiddleware(server.streamable_http_app(), effective_limits)
