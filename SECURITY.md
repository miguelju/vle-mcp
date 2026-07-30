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

- M1 tools are read-only and deterministic.
- The server never executes shell commands or arbitrary code.
- The server accepts no file paths, URLs, credentials, or user-supplied Python.
- Pressure inputs are typed, finite, bounded, and normalized once.
- Scientific calculation is delegated to the tested upstream library.
- stdout carries MCP protocol traffic only.
- Exceptions returned to clients contain no stack traces or local paths.
- Secrets are injected at runtime if a future milestone needs them.
- Remote transport is not enabled until authentication, authorization, TLS,
  request limits, and threat tests are implemented together.

See [docs/security-model.md](docs/security-model.md).
