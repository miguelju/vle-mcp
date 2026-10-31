# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
# Tool catalogue expanded by Claude Code (Claude Opus 5.5).
"""MCP construction and the local stdio entry point."""

from collections.abc import Callable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from vle_mcp.tools import components, mixture, petroleum, water

# Every tool is a deterministic, read-only calculation with no external access.
_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

TOOLS: tuple[Callable[..., object], ...] = (
    *water.TOOLS,
    *components.TOOLS,
    *mixture.TOOLS,
    *petroleum.TOOLS,
)

# Kept importable from this module for backward compatibility.
water_saturation_temperature = water.water_saturation_temperature


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
        "vle",
        instructions=(
            "Read-only thermodynamic calculations backed by the vle library: water and "
            "steam properties (IAPWS-IF97), a bundled pure-component database, "
            "multicomponent vapor-liquid equilibrium with cubic equations of state, and "
            "petroleum-fraction characterization. Do not estimate a value when a matching "
            "tool is available. All pressure arguments are absolute. Call list_components "
            "to find valid component names before a mixture calculation."
        ),
        token_verifier=token_verifier,
        auth=auth,
        transport_security=transport_security,
        stateless_http=stateless_http,
        json_response=json_response,
        max_request_body_size=max_request_body_size,
    )
    for tool in TOOLS:
        server.tool(annotations=_READ_ONLY)(tool)
    return server


mcp = create_mcp()


def main() -> None:
    """Run the local server; stdout is reserved for MCP protocol messages."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
