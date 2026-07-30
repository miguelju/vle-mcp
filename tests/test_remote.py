# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""M3 tests for OAuth-protected Streamable HTTP and instance limits."""

from __future__ import annotations

import time

import anyio
import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.auth.provider import AccessToken
from starlette.responses import PlainTextResponse

from vle_mcp.remote import (
    READ_SCOPE,
    RemoteLimitMiddleware,
    RemoteLimits,
    ResourceBoundTokenVerifier,
    create_remote_app,
)

ISSUER = "https://auth.example.com"
RESOURCE = "https://mcp.example.com/mcp"


class FakeVerifier:
    def __init__(self, access_token: AccessToken | None) -> None:
        self.access_token = access_token

    async def verify_token(self, token: str) -> AccessToken | None:
        return self.access_token if token == "test-token" else None


def valid_access_token(**changes: object) -> AccessToken:
    values = {
        "token": "test-token",
        "client_id": "example-client",
        "scopes": [READ_SCOPE],
        "expires_at": int(time.time()) + 300,
        "resource": RESOURCE,
        "subject": "example-user",
        "claims": {"iss": ISSUER},
    }
    values.update(changes)
    return AccessToken(**values)


def remote_app(
    verifier: FakeVerifier,
    *,
    limits: RemoteLimits | None = None,
):
    return create_remote_app(
        token_verifier=verifier,
        issuer_url=ISSUER,
        resource_server_url=RESOURCE,
        allowed_hosts=["mcp.example.com"],
        allowed_origins=["https://client.example.com"],
        limits=limits,
    )


@pytest.mark.asyncio
async def test_streamable_http_requires_bearer_token_and_advertises_metadata() -> None:
    app = remote_app(FakeVerifier(valid_access_token()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://mcp.example.com") as client:
        response = await client.post(
            "/mcp",
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )

    assert response.status_code == 401
    assert "oauth-protected-resource/mcp" in response.headers["www-authenticate"]


@pytest.mark.asyncio
async def test_protected_resource_metadata_names_issuer_resource_and_scope() -> None:
    app = remote_app(FakeVerifier(valid_access_token()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://mcp.example.com") as client:
        response = await client.get("/.well-known/oauth-protected-resource/mcp")

    assert response.status_code == 200
    assert response.json()["resource"] == RESOURCE
    assert response.json()["authorization_servers"] == [f"{ISSUER}/"]
    assert response.json()["scopes_supported"] == [READ_SCOPE]


@pytest.mark.asyncio
async def test_authenticated_streamable_http_round_trip() -> None:
    app = remote_app(FakeVerifier(valid_access_token()))
    transport = httpx.ASGITransport(app=app)
    headers = {
        "authorization": "Bearer test-token",
        "origin": "https://client.example.com",
    }
    async with app.app.router.lifespan_context(app.app):  # type: ignore[attr-defined]
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://mcp.example.com",
            headers=headers,
        ) as client:
            async with streamable_http_client(RESOURCE, http_client=client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "water_saturation_temperature",
                        {"pressure": 1.0, "pressure_unit": "atm"},
                    )

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["pressure"]["value"] == pytest.approx(101.325)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "access_token",
    [
        valid_access_token(resource="https://other.example.com/mcp"),
        valid_access_token(claims={"iss": "https://other.example.com"}),
        valid_access_token(expires_at=None),
    ],
)
async def test_resource_binding_rejects_incomplete_or_misdirected_token(
    access_token: AccessToken,
) -> None:
    verifier = ResourceBoundTokenVerifier(
        FakeVerifier(access_token),
        issuer_url=ISSUER,
        resource_server_url=RESOURCE,
    )
    assert await verifier.verify_token("test-token") is None


@pytest.mark.asyncio
async def test_request_body_limit_returns_413() -> None:
    app = remote_app(
        FakeVerifier(valid_access_token()),
        limits=RemoteLimits(max_request_body_bytes=64),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://mcp.example.com") as client:
        response = await client.post(
            "/mcp",
            headers={
                "authorization": "Bearer test-token",
                "content-type": "application/json",
            },
            content=b"x" * 65,
        )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_rate_limit_returns_429() -> None:
    async def ok(scope, receive, send):
        await PlainTextResponse("ok")(scope, receive, send)

    app = RemoteLimitMiddleware(
        ok,
        RemoteLimits(requests_per_window=1),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://mcp.example.com") as client:
        assert (await client.get("/first")).status_code == 200
        response = await client.get("/second")
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_concurrency_limit_returns_503() -> None:
    entered = anyio.Event()
    release = anyio.Event()

    async def blocked(scope, receive, send):
        entered.set()
        await release.wait()
        await PlainTextResponse("ok")(scope, receive, send)

    app = RemoteLimitMiddleware(
        blocked,
        RemoteLimits(max_concurrent_requests=1),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://mcp.example.com") as client:
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(client.get, "/first")
            await entered.wait()
            response = await client.get("/second")
            release.set()
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_timeout_returns_504() -> None:
    async def slow(scope, receive, send):
        await anyio.sleep(0.05)
        await PlainTextResponse("too late")(scope, receive, send)

    app = RemoteLimitMiddleware(
        slow,
        RemoteLimits(request_timeout_seconds=0.001),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://mcp.example.com") as client:
        response = await client.get("/")
    assert response.status_code == 504


def test_remote_configuration_requires_https_and_host_allowlist() -> None:
    verifier = FakeVerifier(valid_access_token())
    with pytest.raises(ValueError, match="HTTPS"):
        create_remote_app(
            token_verifier=verifier,
            issuer_url=ISSUER,
            resource_server_url="http://mcp.example.com/mcp",
            allowed_hosts=["mcp.example.com"],
            allowed_origins=[],
        )
    with pytest.raises(ValueError, match="allowed_hosts"):
        create_remote_app(
            token_verifier=verifier,
            issuer_url=ISSUER,
            resource_server_url=RESOURCE,
            allowed_hosts=[],
            allowed_origins=[],
        )
