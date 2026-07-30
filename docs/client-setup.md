# Client setup

M1 provides a local stdio server. Client interfaces change over time, so verify
the current vendor documentation before publishing product-specific screenshots
or menu paths.

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

The client launches the server. The process should remain silent on stdout
except for MCP messages. No API key is needed for M1.

## Claude Desktop

Claude Desktop supports local MCP servers and desktop extensions. M2 will
verify the current configuration and package format against the released
desktop application before claiming support.

## ChatGPT

A hosted client cannot start a process on a user's computer or connect to its
loopback interface. M2 will verify whether the current desktop/plugin surface
can run this local server directly. M3 will provide the Streamable HTTP endpoint
needed by hosted integrations.

## General chatbot

Any client implementing MCP stdio can use M1. A chatbot that supports only
provider-specific function calling needs an MCP client bridge; that bridge is
client infrastructure, not part of the thermodynamic server.
