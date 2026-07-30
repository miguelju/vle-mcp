# M3 remote Streamable HTTP

M3 exposes the same read-only tool over stateless MCP Streamable HTTP. The
application is an ASGI factory rather than a public unauthenticated executable:

```python
from vle_mcp.remote import create_remote_app

app = create_remote_app(
    token_verifier=verified_oauth_tokens,
    issuer_url="https://auth.example.com",
    resource_server_url="https://mcp.example.com/mcp",
    allowed_hosts=["mcp.example.com"],
    allowed_origins=["https://client.example.com"],
)
```

`verified_oauth_tokens` is an operator-supplied implementation of the MCP
SDK's `TokenVerifier` protocol. It must use a maintained authorization-server
integration to verify the token cryptographically before returning an
`AccessToken`. Do not implement token parsing by decoding unverified JWT claims.

The externally visible MCP endpoint is:

```text
https://mcp.example.com/mcp
```

The OAuth Protected Resource Metadata endpoint is:

```text
https://mcp.example.com/.well-known/oauth-protected-resource/mcp
```

## OAuth 2.1 resource-server contract

The authorization server and verifier must:

- require authorization code with PKCE for public clients;
- validate token signature against trusted, rotation-aware keys;
- validate exact issuer, audience, expiration, and not-before claims;
- bind the token to `https://mcp.example.com/mcp` using the OAuth resource
  indicator;
- return the exact resource in `AccessToken.resource`;
- return the verified issuer in `AccessToken.claims["iss"]`;
- return a finite `AccessToken.expires_at`;
- grant the narrow `vle:read` scope.

The application rejects missing, expired, wrong-issuer, wrong-resource, and
insufficient-scope tokens. It publishes RFC 9728 metadata and includes its URL
in `WWW-Authenticate`. MCP session IDs are never treated as authentication.
Tokens are not logged, placed in URLs, or passed to `vle-steam`.

## HTTPS

Terminate TLS at a maintained reverse proxy, load balancer, or managed
container ingress. Store certificates and keys in the platform's secret
facility, not this repository. Forward only sanitized proxy metadata and keep
the ASGI service on a non-public listener. Redirecting cleartext requests is
not sufficient; do not expose the cleartext listener publicly.

The factory requires `https://` issuer and resource URLs. `allowed_hosts` is
mandatory, and browser origins should be enumerated exactly. An absent Origin
is valid for non-browser MCP clients.

## Default limits

| Limit | Default | Enforcement |
|---|---:|---|
| Request body | 64 KiB | MCP SDK request-body middleware |
| Rate | 60 requests / 60 s | Per application process |
| Concurrency | 8 active requests | Per application process |
| Wall-clock time | 10 s | Per HTTP request |

These defaults are deliberately conservative for the single bounded IF97
operation. Production ingress must repeat the body and timeout limits and add
per-principal rate limits. A multi-instance deployment needs shared rate-limit
state. Reject overload; do not queue requests without a bound.

The timeout layer buffers the bounded response until completion so a timeout
can return one valid HTTP response instead of corrupting a partially streamed
message. Revisit this design before adding tools that intentionally stream
large or long-running results.

## Verification

`tests/test_remote.py` uses an in-process ASGI client and a fake verifier. It
asserts authentication challenges, Protected Resource Metadata, an authorized
MCP tool round trip, resource binding, body size, rate, concurrency, timeout,
and HTTPS configuration. The fake token exists only in tests and is not an
authorization-server example.
