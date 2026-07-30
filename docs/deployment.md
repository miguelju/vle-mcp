# Generic deployment guidance

M3 provides the OAuth-protected Streamable HTTP ASGI application factory.
See [remote-http.md](remote-http.md) for its integration contract. This guide
describes deployment shapes without prescribing private infrastructure.

## Homelab

- Run the service as an unprivileged account or rootless container.
- Terminate TLS at a maintained reverse proxy.
- Expose only the MCP HTTPS route and health endpoints.
- Supply a maintained OAuth token verifier to `create_remote_app`.
- Keep the application on an isolated network segment.
- Inject credentials from a secret store or protected runtime file.
- Restrict inbound and outbound traffic to required destinations.
- Back up configuration without tokens and test restoration.

## Single hosted machine

- Use an immutable image or reproducible container.
- Place HTTPS ingress in front of the application.
- Apply per-principal rate limits at ingress in addition to process limits.
- Use workload identity or a secret manager where available.
- Apply automatic security updates with staged rollout and rollback.
- Export sanitized metrics and audit events, not request bodies or tokens.

## Managed container platform

- Use a non-root, read-only container with dropped capabilities.
- Configure readiness/liveness probes and graceful shutdown.
- Bound instance concurrency, request size, duration, and scaling.
- Use shared rate-limit state when traffic spans multiple instances.
- Use workload identity and private downstream connectivity.
- Keep authorization state in a suitable shared service if sessions require it.

All public examples use `mcp.example.com` and `${VARIABLE}` placeholders.
Never commit a real address, hostname, access policy, or network diagram.
