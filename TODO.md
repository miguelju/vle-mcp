# TODO

Checked items are verified claims, not estimates.

M0 through M3 were implemented by OpenAI Codex using GPT-5.6 Sol under Miguel
Jackson's direction and approved plan. Later work is done with Claude Code.

## M0 — Repository foundation

- [x] Initialize the Git repository and Python package.
- [x] Add `README.md`, `PLAN.md`, `TODO.md`, `SECURITY.md`, `CONTRIBUTING.md`,
      and `AGENTS.md`.
- [x] Document why MCP exists, why Python is used, and why domain API
      granularity matters.
- [x] Add generic client and deployment documentation without private topology.
- [x] Add the public-data and secret-scanning gate.
- [x] Add least-privilege CI with SHA-pinned actions.
- [x] Run the M0 verification commands.

## M1 — First `vle-steam` MCP tool

- [x] Pin a compatible official MCP Python SDK range.
- [x] Implement the stdio server lifecycle and tool registration.
- [x] Define the typed `water_saturation_temperature` result.
- [x] Validate finite, positive, absolute pressure and supported units.
- [x] Delegate the calculation to `vle.steam.tsat`.
- [x] Return units and calculation provenance.
- [x] Add domain unit tests.
- [x] Add an in-memory MCP discovery and invocation test.
- [x] Pin the `101.325 kPa` acceptance result.
- [x] Verify stdout is reserved for MCP protocol messages with a real subprocess
      handshake.
- [x] Run the M1 verification commands.

## M2 — Local clients

- [x] Verify a general stdio client configuration.
- [x] Verify Claude Desktop configuration.
- [x] Evaluate desktop extension packaging.
- [x] Verify the current ChatGPT desktop/plugin path.

## M3 — Remote clients

- [x] Add Streamable HTTP.
- [x] Add HTTPS and OAuth 2.1 resource-server guidance.
- [x] Add request-size, rate, concurrency, and timeout limits.

## Tool catalogue — `vle-thermo` 0.18

Implemented by Claude Code (Claude Opus 5.5) under Miguel Jackson's direction.
Tests: `tests/test_catalogue.py`.

- [x] Pin `vle-thermo>=0.18,<0.19` and review its public API.
- [x] Water: `water_saturation_properties`, `water_state` (`tools/water.py`).
- [x] Components: `list_components`, `component_properties`
      (`tools/components.py`).
- [x] Mixtures: `mixture_flash`, `mixture_bubble_point`, `mixture_dew_point`,
      `mixture_critical_point`, `mixture_phase_envelope`,
      `mixture_phase_properties` (`tools/mixture.py`).
- [x] Petroleum: `petroleum_fraction_properties`,
      `petroleum_boiling_point_at_pressure`, `petroleum_normal_boiling_point`
      (`tools/petroleum.py`).
- [x] Validate inputs that vle silently accepts: compositions that do not
      sum to one, and non-physical temperatures.
- [x] Sanitize Rust engine panics (`BaseException`) as well as ordinary errors.
- [x] Publish every tool with read-only annotations; assert it over MCP.
- [x] Record excluded APIs and upstream defects in `docs/architecture.md`.

## M5/M6 — Deployment and releases

- [ ] Complete generic deployment guides.
- [ ] Add SBOM, checksums, signed releases, and branch protections.
