# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Guards for the stdio protocol channel."""

import ast
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_server_module_does_not_print_to_stdout() -> None:
    source = Path("src/vle_mcp/server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    print_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert print_calls == []


@pytest.mark.asyncio
async def test_server_completes_a_real_stdio_handshake() -> None:
    """A successful client call proves stdout remained valid MCP traffic."""

    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "vle_mcp.server"],
    )

    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {"water_saturation_temperature"}

            result = await session.call_tool(
                "water_saturation_temperature",
                {"pressure": 1.0, "pressure_unit": "atm"},
            )
            assert result.isError is False
            assert result.structuredContent is not None
            assert result.structuredContent["pressure"]["value"] == pytest.approx(101.325)
