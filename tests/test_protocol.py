# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Protocol-level discovery and invocation tests using the official SDK."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from vle_mcp.server import mcp


@pytest.mark.asyncio
async def test_tool_is_discoverable_and_callable_over_mcp() -> None:
    async with create_connected_server_and_client_session(mcp) as session:
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        assert "water_saturation_temperature" in names

        result = await session.call_tool(
            "water_saturation_temperature",
            {"pressure": 101.325, "pressure_unit": "kPa"},
        )

        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["temperature"]["kelvin"] == pytest.approx(
            373.1243, rel=1e-5
        )
        assert result.structuredContent["calculation"]["library"] == "vle-steam"
