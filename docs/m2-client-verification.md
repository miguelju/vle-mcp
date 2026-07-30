# M2 client verification

M2 was implemented by OpenAI Codex using GPT-5.6 Sol under Miguel Jackson's
direction. This record distinguishes verified interoperability from future
deployment work.

## Generic stdio client

The executable verifier in `scripts/verify_stdio_client.py` uses the official
Python MCP SDK as a client. It launches the configured command, completes MCP
initialization, lists tools, invokes `water_saturation_temperature`, and checks
the structured one-atmosphere result and `vle-steam` provenance.

Run it from an installed development environment:

```sh
.venv/bin/python scripts/verify_stdio_client.py \
  --command .venv/bin/vle-mcp
```

The M2 run completed successfully and reported `status: verified`, the
discovered tool, `373.12430000048056 K`, and `99.97430000048058 degC`. This is
client-independent protocol evidence; a compatible chatbot performs the same
discovery and call operations around its model interaction.

## Claude Desktop

Claude Desktop supports local stdio servers through `mcpServers`. M2 was
checked on 2026-07-29 with Claude Desktop `1.24012.9` using the configuration
in `docs/client-setup.md`. The check established all of the following:

1. Claude's MCP host launched the configured `vle-mcp` executable;
2. Claude discovered `water_saturation_temperature`;
3. a one-atmosphere question caused a tool call; and
4. Claude named `vle-steam:water_saturation_temperature` and returned
   `373.1243 K` and `99.9743 degC`.

The private desktop configuration is not repository data. It can contain an
absolute executable path, so it must remain outside Git.

## ChatGPT

The current supported ChatGPT path is not direct local stdio process launch.
ChatGPT custom apps connect to remote MCP servers. A private stdio server can
instead be reached through OpenAI's Secure MCP Tunnel, which makes an outbound
connection and does not require a public inbound endpoint.

Tunnel setup is intentionally deferred to M3 because it requires an OpenAI API
credential, account permissions, and a continuously running connector. M2
therefore verifies and documents the product path; it does not claim that
ChatGPT invoked the local server.

Primary references:

- [ChatGPT developer mode and full MCP apps](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta)
- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

## MCP Bundle evaluation

Desktop Extension (`.dxt`) packaging was renamed MCP Bundle (`.mcpb`). A bundle
is a ZIP archive containing a `manifest.json` and the server payload.

A portable bundle is not shipped in M2. This project depends on Python packages
with platform-specific compiled components, including `vle-thermo`; packaging
one traditional Python dependency tree would therefore produce a
platform-specific artifact rather than a trustworthy cross-platform bundle.
The bundle specification also supports a host-managed `uv` runtime, which is a
candidate for a later, separately tested distribution milestone.

The M2 decision is to retain the verified stdio installation and configuration
path. A future MCPB release must build and test per target platform, or prove a
host-managed environment strategy, before it is advertised as portable.

Primary references:

- [Claude local MCP server setup](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers)
- [MCP Bundle specification and tooling](https://github.com/modelcontextprotocol/mcpb)
