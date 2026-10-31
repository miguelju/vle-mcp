# Created by Claude Code (Claude Opus 5.5), under Miguel Jackson's direction.
"""Read-only access to vle-thermo's bundled pure-component database."""

from typing import Annotated

from pydantic import Field
from vle import components

from vle_mcp.models import (
    ComponentListResult,
    ComponentPropertiesResult,
    ComponentSummary,
    PressureResult,
    TemperatureResult,
)
from vle_mcp.tools.common import ToolInputError

MAX_NAME_LENGTH = 64


def resolve_component_name(name: str) -> str:
    """Return the database's canonical spelling of ``name`` or raise a public error."""

    if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME_LENGTH:
        raise ToolInputError(f"component names must be 1 to {MAX_NAME_LENGTH} characters")
    available = components.available()
    by_lower = {candidate.lower(): candidate for candidate in available}
    try:
        return by_lower[name.strip().lower()]
    except KeyError:
        raise ToolInputError(
            f"unknown component {name.strip()!r}; call list_components for the supported names"
        ) from None


def list_components() -> ComponentListResult:
    """List every pure component available to the mixture tools.

    Call this before a mixture calculation to find the exact component names
    the server accepts (for example "n-butane", "carbon dioxide", "water").
    """

    rows = [
        ComponentSummary(name=c.name, formula=c.formula, cas=c.cas)
        for c in components.all_components()
    ]
    return ComponentListResult(count=len(rows), components=rows)


def component_properties(
    name: Annotated[str, Field(description="Component name from list_components.")],
) -> ComponentPropertiesResult:
    """Return a pure component's constants: molar mass, critical point, acentric
    factor, and normal boiling point, from vle-thermo's bundled database."""

    c = components.get(resolve_component_name(name))
    return ComponentPropertiesResult(
        name=c.name,
        formula=c.formula,
        cas=c.cas,
        molar_mass=c.mw,
        critical_temperature=TemperatureResult(kelvin=c.tc, celsius=c.tc - 273.15),
        critical_pressure=PressureResult(value=c.pc),
        critical_molar_volume=c.vc,
        critical_compressibility=c.zc,
        acentric_factor=c.omega,
        normal_boiling_point=TemperatureResult(kelvin=c.tb, celsius=c.tb - 273.15),
    )


TOOLS = (list_components, component_properties)
