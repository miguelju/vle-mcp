# Client setup

M2 verifies the local stdio interface and records the client paths current on
2026-07-29. Vendor interfaces can change; recheck the linked primary
documentation before relying on product-specific menu paths.

## Generic stdio configuration

Use the installed executable:

```json
{
  "mcpServers": {
    "vle-steam": {
      "command": "/path/to/venv/bin/vle-mcp",
      "args": []
    }
  }
}
```

`/path/to/venv` is a placeholder. Do not commit a personal home-directory path.
The same placeholder-only configuration is available in
`examples/clients/stdio.json`.

The client launches the server. The process should remain silent on stdout
except for MCP messages. No API key is needed.

Verify the complete protocol path independently of a chatbot:

```sh
.venv/bin/python scripts/verify_stdio_client.py \
  --command .venv/bin/vle-mcp
```

## Claude Desktop

Claude Desktop supports local MCP servers. Open its developer settings and edit
the desktop configuration, or add the following `mcpServers` member while
preserving existing settings:

```json
{
  "mcpServers": {
    "vle-steam": {
      "command": "/path/to/venv/bin/vle-mcp",
      "args": []
    }
  }
}
```

Use an absolute path in the private desktop configuration because the desktop
application may not inherit the shell's `PATH`. Restart Claude Desktop after
editing the file, then ask:

> Use the vle-steam tool to calculate the saturation temperature of water at
> 101.325 kPa absolute. State the returned Kelvin and Celsius values.

The tool result should be approximately `373.1243 K` and `99.9743 degC`.
Review the tool-call prompt before approval. The server is read-only and does
not require credentials.

See [Claude's current local-server instructions](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers).

### Desktop extension packaging

The current package name is MCP Bundle (`.mcpb`), formerly Desktop Extension
(`.dxt`). M2 evaluated but did not ship a bundle because this Python project
contains platform-specific compiled dependencies. See
[the M2 verification record](m2-client-verification.md) for the decision and
future packaging criteria.

## ChatGPT

ChatGPT does not directly launch a local stdio MCP process. Its custom apps use
remote MCP connections. The current private-local route is an
[OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels),
which can launch or reach this stdio server through an outbound encrypted
connection.

Creating a tunnel requires an OpenAI Platform tunnel identifier, an API key
with suitable tunnel permissions, and ChatGPT developer-mode access. Those are
private operator settings and must never be committed. Tunnel provisioning and
the repository's native Streamable HTTP transport belong to M3.

The current ChatGPT product workflow is documented in
[Developer mode, custom apps, and full MCP connectors](https://help.openai.com/en/articles/12584461-developer-mode-apps-and-full-mcp-connectors-in-chatgpt-beta).

## General chatbot

Any client implementing MCP stdio can use M1. A chatbot that supports only
provider-specific function calling needs an MCP client bridge; that bridge is
client infrastructure, not part of the thermodynamic server.

## Remote Streamable HTTP

M3 clients connect to the externally visible HTTPS resource:

```text
https://mcp.example.com/mcp
```

The client discovers the authorization server through RFC 9728 Protected
Resource Metadata, completes the authorization server's OAuth 2.1 flow, and
sends a resource-bound bearer token with `vle:read`. Client secrets, access
tokens, redirect URIs, and operator-specific settings must remain outside this
repository. See [remote-http.md](remote-http.md) for the server contract.
