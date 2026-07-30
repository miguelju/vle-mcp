#!/usr/bin/env python3
# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Verify discovery and invocation through a generic MCP stdio client."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TOOL_NAME = "water_saturation_temperature"
EXPECTED_KELVIN = 373.1243
EXPECTED_CELSIUS = 99.9743


def parse_args() -> argparse.Namespace:
    """Parse a server command without depending on a machine-specific path."""

    parser = argparse.ArgumentParser(
        description="Launch an MCP stdio server and verify the vle-steam tool."
    )
    parser.add_argument(
        "--command",
        default="vle-mcp",
        help="MCP server executable (default: vle-mcp from PATH)",
    )
    parser.add_argument(
        "--server-arg",
        action="append",
        default=[],
        help="Argument passed to the server; repeat for multiple arguments",
    )
    return parser.parse_args()


def validate_result(result: dict[str, Any]) -> None:
    """Reject a response that does not satisfy the public acceptance contract."""

    try:
        kelvin = float(result["temperature"]["kelvin"])
        celsius = float(result["temperature"]["celsius"])
        pressure = result["pressure"]
        calculation = result["calculation"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("tool returned an invalid structured result") from exc

    if not math.isclose(kelvin, EXPECTED_KELVIN, rel_tol=1e-5):
        raise RuntimeError(f"unexpected Kelvin result: {kelvin}")
    if not math.isclose(celsius, EXPECTED_CELSIUS, rel_tol=1e-5):
        raise RuntimeError(f"unexpected Celsius result: {celsius}")
    if pressure != {"value": 101.325, "unit": "kPa", "basis": "absolute"}:
        raise RuntimeError("tool returned unexpected normalized pressure")
    if calculation.get("library") != "vle-steam":
        raise RuntimeError("tool did not report vle-steam provenance")


async def verify(command: str, server_args: list[str]) -> dict[str, Any]:
    """Exercise the same protocol operations used by a general MCP client."""

    parameters = StdioServerParameters(command=command, args=server_args)
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            if TOOL_NAME not in tool_names:
                raise RuntimeError(f"required tool is not discoverable: {TOOL_NAME}")

            call = await session.call_tool(
                TOOL_NAME,
                {"pressure": 1.0, "pressure_unit": "atm"},
            )
            if call.isError:
                raise RuntimeError("tool call returned an MCP error")
            if call.structuredContent is None:
                raise RuntimeError("tool call did not return structured content")

            result = dict(call.structuredContent)
            validate_result(result)
            return {
                "status": "verified",
                "server": initialized.serverInfo.name,
                "tools": tool_names,
                "acceptance_case": result,
            }


def main() -> int:
    """Run the asynchronous verifier and emit one machine-readable report."""

    args = parse_args()
    command = str(Path(args.command)) if "/" in args.command else args.command
    report = asyncio.run(verify(command, args.server_arg))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
