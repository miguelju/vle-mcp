# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Local stdio MCP server for the vle scientific libraries."""

from mcp.server.fastmcp import FastMCP

from vle_mcp.models import WaterSaturationTemperatureResult
from vle_mcp.tools.water import PressureUnit, calculate_water_saturation_temperature

mcp = FastMCP(
    "vle-steam",
    instructions=(
        "Use these read-only tools for water/steam thermodynamic calculations. "
        "Do not estimate a value when a matching tool is available. All pressure "
        "arguments are absolute."
    ),
)


@mcp.tool()
def water_saturation_temperature(
    pressure: float,
    pressure_unit: PressureUnit = "kPa",
) -> WaterSaturationTemperatureResult:
    """Calculate water's boiling/saturation temperature at an absolute pressure.

    Use this for questions such as “What is the boiling temperature of water at
    atmospheric pressure?” One standard atmosphere is 1 atm or 101.325 kPa
    absolute. Do not use gauge pressure.
    """

    return calculate_water_saturation_temperature(pressure, pressure_unit)


def main() -> None:
    """Run the local server; stdout is reserved for MCP protocol messages."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
