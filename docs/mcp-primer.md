# MCP primer

## Why MCP exists

Before MCP, connecting an AI application to a program generally required a
client-specific function-calling adapter. MCP standardizes discovery,
invocation, results, lifecycle, and transports so one server can work with
multiple conforming clients.

MCP does not move scientific correctness into the language model. It provides a
typed boundary through which a model can request that an authoritative program
perform an operation.

## Core primitives

- **Tools** perform bounded computations or actions.
- **Resources** expose addressable context, similar to read-oriented data.
- **Prompts** publish reusable interaction templates.

M1 needs one tool and no resources or prompts.

## Example message path

For “What is the boiling temperature of water at atmospheric pressure?”:

1. The client initializes an MCP session.
2. It calls `tools/list` and receives the generated schema.
3. The model selects `water_saturation_temperature`.
4. The client calls it with `101.325 kPa`.
5. The server validates and normalizes the request.
6. The adapter calls `vle.steam.tsat(101.325)`.
7. `vle-steam` evaluates the IAPWS-IF97 Region 4 inverse saturation relation.
8. The server returns structured temperature, pressure, and provenance.
9. The model explains the tool result.

The model does not calculate or “correct” the returned value.

See [architecture.md](architecture.md) for the full component diagram, trust
boundaries, typed result contract, and extension path for further `vle`
tools.

## Transport

M1 uses stdio: a client starts the server as a child process and exchanges MCP
messages over stdin/stdout. This is appropriate for a local learning server.
Streamable HTTP is a later milestone for hosted clients.

## References

- [MCP specification](https://modelcontextprotocol.io/specification/)
- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [IAPWS](https://www.iapws.org/)
