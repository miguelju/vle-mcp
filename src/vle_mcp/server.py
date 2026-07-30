# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""MCP construction and the local stdio entry point."""

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from vle_mcp.models import WaterSaturationTemperatureResult
from vle_mcp.tools.water import PressureUnit, calculate_water_saturation_temperature


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


def create_mcp(
    *,
    token_verifier: TokenVerifier | None = None,
    auth: AuthSettings | None = None,
    transport_security: TransportSecuritySettings | None = None,
    stateless_http: bool = False,
    json_response: bool = False,
    max_request_body_size: int = 4 * 1024 * 1024,
) -> FastMCP:
    """Build one server so stdio and HTTP expose exactly the same tools."""

    server = FastMCP(
        "vle-steam",
        instructions=(
            "Use these read-only tools for water/steam thermodynamic calculations. "
            "Do not estimate a value when a matching tool is available. All pressure "
            "arguments are absolute."
        ),
        token_verifier=token_verifier,
        auth=auth,
        transport_security=transport_security,
        stateless_http=stateless_http,
        json_response=json_response,
        max_request_body_size=max_request_body_size,
    )
    server.tool()(water_saturation_temperature)
    return server


mcp = create_mcp()


def main() -> None:
    """Run the local server; stdout is reserved for MCP protocol messages."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
