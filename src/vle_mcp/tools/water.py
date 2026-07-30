# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Water saturation tools backed by the granular ``vle.steam`` API."""

import math
from collections.abc import Callable
from typing import Literal

from vle import steam

from vle_mcp.models import (
    PressureResult,
    TemperatureResult,
    WaterSaturationTemperatureResult,
)

PressureUnit = Literal["Pa", "kPa", "MPa", "bar", "atm"]

_KPA_PER_UNIT: dict[str, float] = {
    "Pa": 0.001,
    "kPa": 1.0,
    "MPa": 1000.0,
    "bar": 100.0,
    "atm": 101.325,
}

# IF97 Region 4 is valid from the triple point to the critical point. Keeping
# the bound here makes the public contract explicit; vle-steam remains the
# authoritative calculator and performs its own range check too.
_MIN_SATURATION_PRESSURE_KPA = 0.611_212_677
_MAX_SATURATION_PRESSURE_KPA = 22_064.0


class ToolInputError(ValueError):
    """A stable, public validation error safe to return through MCP."""


def to_kpa_absolute(pressure: float, pressure_unit: PressureUnit) -> float:
    """Normalize an absolute pressure to kPa.

    Args:
        pressure: Finite, positive pressure magnitude.
        pressure_unit: One of Pa, kPa, MPa, bar, or atm.

    Returns:
        Pressure in kPa absolute.
    """

    if not math.isfinite(pressure):
        raise ToolInputError("pressure must be finite")
    if pressure <= 0.0:
        raise ToolInputError("pressure must be greater than zero")

    try:
        scale = _KPA_PER_UNIT[pressure_unit]
    except KeyError as exc:
        raise ToolInputError("pressure_unit must be one of: Pa, kPa, MPa, bar, atm") from exc

    pressure_kpa = pressure * scale
    if not _MIN_SATURATION_PRESSURE_KPA <= pressure_kpa <= _MAX_SATURATION_PRESSURE_KPA:
        raise ToolInputError(
            "pressure is outside the IAPWS-IF97 saturation range "
            f"({_MIN_SATURATION_PRESSURE_KPA:g} to "
            f"{_MAX_SATURATION_PRESSURE_KPA:g} kPa absolute)"
        )
    return pressure_kpa


def calculate_water_saturation_temperature(
    pressure: float,
    pressure_unit: PressureUnit = "kPa",
    *,
    tsat: Callable[[float], float] = steam.tsat,
) -> WaterSaturationTemperatureResult:
    """Calculate water's saturation temperature at an absolute pressure.

    The MCP layer validates and normalizes input; ``vle.steam.tsat`` owns the
    IAPWS-IF97 calculation.
    """

    pressure_kpa = to_kpa_absolute(pressure, pressure_unit)
    try:
        temperature_k = float(tsat(pressure_kpa))
    except Exception as exc:
        # Do not expose dependency exception details, stack traces, or paths.
        raise ToolInputError("vle-steam could not evaluate this pressure") from exc

    return WaterSaturationTemperatureResult(
        temperature=TemperatureResult(
            kelvin=temperature_k,
            celsius=temperature_k - 273.15,
        ),
        pressure=PressureResult(value=pressure_kpa),
    )
