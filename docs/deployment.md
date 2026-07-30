# Generic deployment guidance

Remote deployment is planned for M3 and is not implemented in M1.

## Homelab

- Run the service as an unprivileged account or rootless container.
- Terminate TLS at a maintained reverse proxy.
- Expose only the MCP HTTPS route and health endpoints.
- Keep the application on an isolated network segment.
- Inject credentials from a secret store or protected runtime file.
- Restrict inbound and outbound traffic to required destinations.
- Back up configuration without tokens and test restoration.

## Single hosted machine

- Use an immutable image or reproducible container.
- Place HTTPS ingress in front of the application.
- Use workload identity or a secret manager where available.
- Apply automatic security updates with staged rollout and rollback.
- Export sanitized metrics and audit events, not request bodies or tokens.

## Managed container platform

- Use a non-root, read-only container with dropped capabilities.
- Configure readiness/liveness probes and graceful shutdown.
- Bound instance concurrency, request size, duration, and scaling.
- Use workload identity and private downstream connectivity.
- Keep authorization state in a suitable shared service if sessions require it.

All public examples use `mcp.example.com` and `${VARIABLE}` placeholders.
Never commit a real address, hostname, access policy, or network diagram.
