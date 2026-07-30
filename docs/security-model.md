# Security model

## Why MCP security matters

An MCP tool converts model-selected arguments into program execution. Models
process untrusted natural language and can be influenced by prompt injection,
malicious tool output, misleading descriptions, or accidental ambiguity.
Consequently, every tool is a security boundary.

## M1 assets and trust boundaries

Protected assets:

- integrity of the scientific answer;
- integrity and availability of the local client;
- confidentiality of the local environment;
- the client/server protocol stream.

Untrusted:

- user text;
- model-selected tool arguments;
- MCP client metadata;
- exception text from dependencies.

Trusted but verified through tests:

- the pinned MCP SDK;
- the installed `vle-thermo` package;
- this repository's validation and adapter code.

## M1 threats and controls

| Threat | Control |
|---|---|
| Prompt injection selects a tool | Tool is read-only, bounded, and deterministic |
| NaN, infinity, negative, or extreme input | Explicit validation and IF97 range checks |
| Unit ambiguity | Enumerated units; pressure is always absolute |
| Scientific logic drifts into the adapter | One direct call to `vle.steam.tsat` |
| Protocol corruption | No stdout logging |
| Local path or stack-trace disclosure | Stable public exceptions and stderr diagnostics |
| Secret or topology disclosure | Repository scan plus review |
| Dependency compromise | Bounded dependencies, lockfile/release review, minimal CI permissions |

## Remote milestone requirements

Do not expose the server remotely by merely switching transports. M3 must add:

- HTTPS;
- OAuth 2.1-compatible authorization using maintained libraries;
- PKCE for public clients;
- Protected Resource Metadata;
- issuer, signature, audience, expiry, and scope validation;
- tokens bound to this MCP resource;
- no token passthrough to downstream services;
- short token lifetime and secure storage;
- body, rate, concurrency, and execution-time limits;
- origin/host validation, audit logs, and safe error handling.

MCP session IDs are routing state, not authentication.

## Tool review checklist

Before registering a tool:

1. Is the underlying domain operation cohesive and tested?
2. Can the schema be narrow, typed, and bounded?
3. Are units, reference states, side effects, and cost explicit?
4. Does authorization apply to the operation and the underlying object?
5. Can untrusted output influence another tool call?
6. Are errors stable and free of sensitive context?
7. Is there a protocol-level test?
