# vle-mcp project plan

## Authorship

This plan and the M0/M1 implementation were produced by OpenAI Codex using
GPT-5.6 Sol under Miguel Jackson's direction and approval. Miguel is the project
owner; Codex is recorded as an AI development collaborator. See `AUTHORS.md`.

## 1. Purpose

`vle-mcp` is a public learning repository that exposes selected capabilities
from [`vle`](https://github.com/miguelju/vle) and
[`stages-thermo`](https://github.com/miguelju/stages-thermo) through the Model
Context Protocol (MCP).

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
2. both upstream projects already provide Python bindings;
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
  -> vle.steam today; stages-thermo in later milestones
  -> structured result with units and provenance
  -> chatbot explanation
```

Layers:

- `server.py`: MCP registration and stdio lifecycle.
- `models.py`: public, structured tool result schemas.
- `tools/water.py`: unit validation and domain call.
- `vle.steam`: authoritative Python binding over `vle-steam`.
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
- M3: Streamable HTTP, HTTPS, OAuth 2.1 resource-server behavior, and limits.
- M4: the first bounded `stages-thermo` tool after an upstream API review.
- M5: generic homelab, single-host, and managed-container deployment guides.
- M6: release signing, SBOM, checksums, and public-repository hardening.

## 8. Completion rule

Documentation is a claim and code is the fact. A milestone may be marked
complete only after its implementation can be located, a test asserts the
behavior, and the verification command has run successfully in the same work
session.
