# Security policy

## Supported versions

This repository is pre-1.0. Security fixes apply to the current default branch
and the latest release only.

## Reporting

Do not open a public issue containing an unpatched vulnerability, credential,
private address, internal hostname, or network topology. Contact the maintainer
privately through the security-reporting mechanism configured on the public
repository.

## Security invariants

- Tools are read-only and deterministic.
- The server never executes shell commands or arbitrary code.
- The server accepts no file paths, URLs, credentials, or user-supplied Python.
- Pressure inputs are typed, finite, bounded, and normalized once.
- Scientific calculation is delegated to the tested upstream library.
- stdout carries MCP protocol traffic only.
- Exceptions returned to clients contain no stack traces or local paths.
- OAuth integration and TLS secrets are operator-supplied at runtime.
- Remote transport requires bearer authentication, `vle:read`, HTTPS external
  identifiers, host/origin checks, and bounded resource use.
- Tokens are bound to the configured issuer and MCP resource and are never
  forwarded to scientific libraries.

See [docs/security-model.md](docs/security-model.md) and
[docs/remote-http.md](docs/remote-http.md).
