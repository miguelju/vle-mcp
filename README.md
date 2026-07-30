# vle-mcp

![vle-mcp architecture: an AI question passes through a typed MCP gateway to water and steam calculations and returns a structured result](assets/vle-mcp-hero.png)

An educational Model Context Protocol server for the
[`vle`](https://github.com/miguelju/vle) and
[`stages-thermo`](https://github.com/miguelju/stages-thermo) scientific
libraries.

The first tool calculates the boiling temperature of water at an absolute
pressure using `vle-steam`'s IAPWS-IF97 implementation. The chatbot interprets
and explains the request; tested scientific software supplies the number.

## Status

M0 (repository foundation) and M1 (minimum stdio server) are implemented and
locally verified. The suite contains 19 tests, including an in-memory MCP
round trip, a real stdio subprocess handshake, and the `vle-steam` standard
atmosphere acceptance case. See [PLAN.md](PLAN.md) for architecture and
[TODO.md](TODO.md) for verified status.

## Why MCP?

MCP gives AI clients a standard way to discover and call typed tools. It
separates natural-language reasoning from authoritative programs and data:

- the model determines intent;
- the MCP client controls connections and tool use;
- this server validates a typed request;
- `vle-steam` performs the scientific calculation.

See [docs/mcp-primer.md](docs/mcp-primer.md) for the protocol path and
[docs/architecture.md](docs/architecture.md) for the component architecture.
[PLAN.md](PLAN.md) records the Python and API-granularity decisions.

## Development setup

Python 3.11 or newer is required.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/vle-mcp
```

The last command starts a stdio MCP server and waits for a client. It is not an
interactive shell; use an MCP client or the protocol tests.

For development against a local `vle` checkout, install its Python package into
the virtual environment according to that repository's build instructions.
Do not commit a machine-specific path.

## Tool

### `water_saturation_temperature`

Inputs:

- `pressure`: positive finite number;
- `pressure_unit`: `Pa`, `kPa`, `MPa`, `bar`, or `atm`;
- all pressure is absolute.

Example arguments:

```json
{"pressure": 101.325, "pressure_unit": "kPa"}
```

The result is approximately `373.1243 K` or `99.9743 °C`. It includes the
normalized pressure and IAPWS-IF97 provenance.

## Verification

```sh
.venv/bin/python scripts/check_public_data.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```

## Security

M1 is local, read-only, deterministic, and uses stdio. No credentials are
required. Read [SECURITY.md](SECURITY.md) and
[docs/security-model.md](docs/security-model.md) before adding a tool or remote
transport.

## Authorship

Miguel Jackson owns and directs the project. M0 and M1 were implemented
collaboratively by OpenAI Codex using the GPT-5.6 Sol model, following Miguel's
instructions and approved plan. See [AUTHORS.md](AUTHORS.md) for the precise
human/AI attribution and limitations.

## License

MIT
