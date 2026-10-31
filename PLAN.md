# vle-mcp project plan

## Authorship

This plan and the M0/M1 implementation were produced by OpenAI Codex using
GPT-5.6 Sol under Miguel Jackson's direction and approval. The `vle`-only
scoping and the tool catalogue (section 9) were produced with Claude Code
(Claude Opus 5.5). Miguel is the project owner; the AI tools are recorded as
development collaborators. See `AUTHORS.md`.

## 1. Purpose

`vle-mcp` is a public learning repository that exposes selected capabilities
from [`vle`](https://github.com/miguelju/vle) through the Model Context
Protocol (MCP).

The first vertical slice answers a narrow question: the saturation (boiling)
temperature of water at a specified absolute pressure. The number must come
from `vle-steam`'s IAPWS-IF97 implementation, not from model memory.

## 2. Why Python

Python is often called the **lingua franca of AI and machine learning**: it is
the common integration language across model SDKs, scientific computing,
notebooks, evaluation frameworks, and automation. It is not the only good MCP
language, and the thermodynamic engines remain in Rust, but it is the best
teaching and integration layer here because:

1. the official MCP Python SDK offers a compact, typed `FastMCP` server API;
2. `vle` already provides Python bindings;
3. examples and tests are readable to the broadest AI/engineering audience;
4. Python keeps protocol orchestration separate from high-performance Rust
   calculations.

The trade-off is an additional runtime and packaging layer. Type annotations,
Pydantic models, strict validation, dependency bounds, and tests prevent the
Python boundary from becoming an untyped scripting layer.

M1 targets the official MCP Python SDK 1.x (`mcp>=1.27,<2`). A major-version
upgrade requires an explicit compatibility review.

## 3. Why domain API granularity determines MCP quality

An MCP server is an adapter, not a substitute for a well-designed program.
Useful tools require underlying APIs that expose cohesive operations with:

- explicit inputs and outputs;
- documented physical units and reference bases;
- deterministic error behavior;
- bounded computational cost;
- no hidden global state;
- enough granularity to compose safely, but not so much that a model must
  orchestrate internal numerical steps.

An API that only exposes a monolithic “run simulation” operation forces an MCP
tool to accept large, ambiguous payloads and makes validation, authorization,
recovery, and explanation difficult. At the other extreme, exposing internal
solver iterations as tools makes the model responsible for numerical
algorithms it should not control.

The preferred boundary is a **domain operation** such as
`saturation_temperature(pressure_absolute)`. The program owns IF97, convergence,
and numerical correctness; the MCP layer owns schema validation, unit
normalization, provenance, and protocol errors; the model owns intent
recognition and explanation.

Before adding a tool, review the upstream API. If a cohesive function is
missing, improve the domain library first rather than embedding business or
scientific logic in the MCP adapter.

## 4. Architecture

```text
user
  -> MCP-capable chatbot
  -> MCP tools/list and tools/call
  -> vle-mcp protocol layer
  -> typed tool model and validation
  -> domain adapter
  -> vle.steam, vle.components, vle.System, or vle.petroleum
  -> structured result with units and provenance
  -> chatbot explanation
```

Layers:

- `server.py`: MCP registration and stdio lifecycle.
- `models.py`: public, structured tool result schemas.
- `tools/common.py`: shared unit normalization, validation, and error sanitizing.
- `tools/water.py`, `tools/components.py`, `tools/mixture.py`,
  `tools/petroleum.py`: per-domain validation and domain calls.
- `vle` (`vle-thermo`): the authoritative Python binding over the Rust engine.
- tests: domain behavior and an in-memory MCP protocol round trip.

## 5. M0 — repository foundation

Deliverables:

- public-repository governance and contributor guidance;
- an educational MCP primer and threat model;
- generic configuration and deployment documentation;
- Python packaging, linting, tests, CI, and a public-data gate;
- no client secrets or environment-specific infrastructure.

## 6. M1 — minimum useful MCP server

Expose one read-only tool:

`water_saturation_temperature(pressure, pressure_unit="kPa")`

Contract:

- `pressure` must be finite and positive;
- pressure is always absolute;
- supported units are `Pa`, `kPa`, `MPa`, `bar`, and `atm`;
- the normalized pressure must be inside IF97's saturation range;
- the domain call is `vle.steam.tsat(pressure_kpa)`;
- output contains Kelvin, Celsius, normalized pressure, method, and library
  provenance;
- invalid input becomes a concise tool error without secrets or local paths.

Acceptance case:

```text
input:  101.325 kPa absolute
engine: vle.steam.tsat(101.325)
output: approximately 373.1243 K / 99.9743 °C
```

The stdio server is the M1 transport. Streamable HTTP, authentication, and
deployment belong to later milestones because they introduce a materially
larger attack surface.

## 7. Later milestones

- M2: verified general stdio and Claude Desktop interoperability, current
  ChatGPT connection requirements, and a documented MCP Bundle packaging
  decision.
- M5: generic homelab, single-host, and managed-container deployment guides.
- M6: release signing, SBOM, checksums, and public-repository hardening.

## 8. M3 — remote clients

M3 adds a production-oriented ASGI application factory, not an embedded
authorization server:

- stateless Streamable HTTP with JSON responses at `/mcp`;
- HTTPS-only external issuer and resource identifiers;
- an operator-supplied `TokenVerifier` backed by a maintained OAuth 2.1
  authorization server integration;
- bearer-token enforcement with the `vle:read` scope;
- exact issuer, resource, and expiry binding after cryptographic verification;
- RFC 9728 Protected Resource Metadata;
- host/origin validation and DNS-rebinding protection;
- 64 KiB request bodies, 60 requests per 60 seconds, 8 concurrent requests,
  and a 10-second request timeout by default.

TLS certificates and private keys terminate at maintained HTTPS ingress and
never enter this repository. The application-level rate limit protects one
process; production ingress must additionally enforce per-principal and
distributed limits. See [docs/remote-http.md](docs/remote-http.md).

## 9. Tool catalogue — `vle-thermo` 0.18

The single-tool M1 scope was widened to the parts of the `vle-thermo` 0.18
public API that are complete, bounded domain operations: water and steam
(IAPWS-IF97), the bundled component database, multicomponent VLE through
`vle.System` with an enumerated set of cubic equations of state, and
petroleum-fraction characterization. Fourteen tools in total.

Design rules:

- one complete domain operation per tool; no batch/array calls, no solver
  internals;
- components only from the bundled database, at most 10 per call;
- validate in the adapter whatever vle does not (composition sums, absolute
  zero) and report the normalized input back;
- every dependency failure, including a Rust panic, becomes a fixed public
  message.

The excluded APIs, the reason for each, and the upstream defects found during
the review are listed in `docs/architecture.md` ("Tool catalogue").

## 10. Completion rule

Documentation is a claim and code is the fact. A milestone may be marked
complete only after its implementation can be located, a test asserts the
behavior, and the verification command has run successfully in the same work
session.
