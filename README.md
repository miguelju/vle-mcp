# vle-mcp

![vle-mcp architecture: an AI question passes through a typed MCP gateway to water and steam calculations and returns a structured result](assets/vle-mcp-hero.png)

*Hero image generated with ChatGPT Images via OpenAI Codex (GPT-5.6 Sol).*

An educational Model Context Protocol server for the
[`vle`](https://github.com/miguelju/vle) scientific library (published on PyPI
as [`vle-thermo`](https://pypi.org/project/vle-thermo/)).

It exposes 14 read-only tools: water and steam properties (IAPWS-IF97), a
bundled pure-component database, multicomponent vapor-liquid equilibrium with
cubic equations of state, and petroleum-fraction characterization. The chatbot
interprets and explains the request; tested scientific software supplies the
number.

> **Development:** this repository is currently being developed using
> [Claude Code](https://claude.com/claude-code), under Miguel Jackson's
> direction. See [Authorship](#authorship).

## Status

M0 through M3 are implemented and locally verified. The tool catalogue exposes
a reviewed selection of the `vle-thermo` 0.18 public API (see [Tools](#tools)).
The project supports local stdio and an OAuth-protected Streamable HTTP ASGI
application factory for remote deployment. Verification includes protocol round trips over both
transports, a real stdio subprocess handshake, RFC 9728 metadata, bearer scope
and resource binding, and remote resource limits. See [PLAN.md](PLAN.md),
[TODO.md](TODO.md), [the M2 verification record](docs/m2-client-verification.md),
and [the M3 remote guide](docs/remote-http.md).

## Why MCP?

MCP gives AI clients a standard way to discover and call typed tools. It
separates natural-language reasoning from authoritative programs and data:

- the model determines intent;
- the MCP client controls connections and tool use;
- this server validates a typed request;
- `vle` performs the scientific calculation.

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

For remote clients, integrate the ASGI factory with a maintained OAuth token
verifier and HTTPS ingress. The remote endpoint deliberately cannot start
without those operator-owned security inputs. See
[docs/remote-http.md](docs/remote-http.md).

## Tools

Every tool is read-only, deterministic, and annotated as such. Pressures are
always absolute. Temperatures accept `K`, `degC`, `degF`, or `degR`; pressures
accept `Pa`, `kPa`, `MPa`, `bar`, or `atm`. Every result carries its units and
a `calculation` block naming the library, method, and installed `vle-thermo`
version.

| Tool | Answers | Backed by |
|---|---|---|
| `water_saturation_temperature` | Boiling temperature of water at a pressure | `vle.steam.tsat` |
| `water_saturation_properties` | Saturation-table row at T or P: vapor pressure, h/s/v/u of both phases, latent heat, viscosity, conductivity, surface tension | `vle.steam.saturation` |
| `water_state` | Full state from T+P, T+quality, P+quality, P+h, or P+s: density, h, s, cp, cv, speed of sound, transport properties | `vle.steam.Water` |
| `list_components` | Names, formulas, and CAS numbers the mixture tools accept | `vle.components` |
| `component_properties` | Molar mass, critical point, acentric factor, normal boiling point | `vle.components.get` |
| `mixture_flash` | Isothermal (PT) flash: vapor fraction, phase compositions, K-values | `vle.System.flash_pt` |
| `mixture_bubble_point` | Bubble temperature at P, or bubble pressure at T, and the first vapor | `vle.System.bubble_*` |
| `mixture_dew_point` | Dew temperature at P, or dew pressure at T, and the first liquid | `vle.System.dew_*` |
| `mixture_critical_point` | Mixture Tc, Pc, Vc (Heidemann-Khalil) | `vle.System.critical_point` |
| `mixture_phase_envelope` | P-T phase envelope points | `vle.System.phase_envelope` |
| `mixture_phase_properties` | Z, density, H, S, Cp, and fugacity coefficients of one phase | `vle.System` property methods |
| `petroleum_fraction_properties` | Watson K, molar mass, critical properties, and acentric factor from boiling point and gravity | `vle.petroleum.estimate` |
| `petroleum_boiling_point_at_pressure` | Boiling point of a fraction at another pressure (Maxwell-Bonnell) | `vle.petroleum` |
| `petroleum_normal_boiling_point` | Atmospheric equivalent temperature from vacuum distillation data | `vle.petroleum` |

Mixture tools take 1 to 10 components from `list_components`, with mole
fractions greater than zero that sum to one (within 0.001; the normalized
composition is echoed back). The model is one cubic equation of state for both
phases (`PR`, `SRK`, `RK`, `PRSV`, `VdW`, `Schmidt-Wenzel`, or `Patel-Teja`)
with classical mixing and zero binary interaction parameters. Solver
iterations are capped. The [architecture guide](docs/architecture.md#tool-catalogue)
records which parts of the `vle` API are deliberately not exposed and why.

Example: boiling point of water at one atmosphere.

```json
{"pressure": 101.325, "pressure_unit": "kPa"}
```

`water_saturation_temperature` returns approximately `373.1243 K` or
`99.9743 °C`.

Example: flash of a light-hydrocarbon mixture at 250 K and 20 bar.

```json
{
  "component_names": ["methane", "ethane", "propane", "n-butane"],
  "mole_fractions": [0.4, 0.3, 0.2, 0.1],
  "temperature": 250,
  "pressure": 20,
  "pressure_unit": "bar"
}
```

With the default Peng-Robinson model, `mixture_flash` reports a two-phase split
with a vapor fraction of about `0.486`.

## Verification

```sh
.venv/bin/python scripts/check_public_data.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
.venv/bin/python scripts/verify_stdio_client.py --command .venv/bin/vle-mcp
```

## Security

The tools remain read-only and deterministic. Stdio requires no credentials;
Streamable HTTP requires a resource-bound bearer token with `vle:read`. Read
[SECURITY.md](SECURITY.md), [docs/security-model.md](docs/security-model.md),
and [docs/remote-http.md](docs/remote-http.md) before deployment or extension.

## Authorship

Miguel Jackson owns and directs the project. M0 through M3 were implemented
collaboratively by OpenAI Codex using the GPT-5.6 Sol model, following Miguel's
instructions and approved plan. Development now continues with
[Claude Code](https://claude.com/claude-code) (Claude Opus 5.5), which scoped
the project to `vle` alone and built the `vle-thermo` 0.18 tool catalogue. See
[AUTHORS.md](AUTHORS.md) for the precise human/AI attribution and limitations.

## License

MIT
