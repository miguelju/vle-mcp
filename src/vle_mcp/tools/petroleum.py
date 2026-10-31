# Created by Claude Code (Claude Opus 5.5), under Miguel Jackson's direction.
"""Petroleum-fraction characterization tools backed by ``vle.petroleum``."""

from typing import Annotated, Literal

from pydantic import Field
from vle import petroleum

from vle_mcp.models import (
    PetroleumBoilingPointResult,
    PetroleumFractionResult,
    PressureResult,
    TemperatureResult,
)
from vle_mcp.tools.common import (
    PressureUnit,
    TemperatureUnit,
    ToolInputError,
    call_domain,
    exactly_one,
    provenance,
    require_finite,
    require_range,
    to_kelvin,
    to_kpa,
)

PropertyMethod = Literal["api", "riazi-daubert-1980", "kesler-lee", "twu"]

# Bounds of physically meaningful petroleum-fraction inputs. They stop absurd
# requests early; they are not claims about each correlation's validity range.
MIN_BOILING_POINT_K = 200.0
MAX_BOILING_POINT_K = 1_200.0
MIN_SPECIFIC_GRAVITY = 0.5
MAX_SPECIFIC_GRAVITY = 1.3
MIN_WATSON_K = 8.0
MAX_WATSON_K = 15.0
MIN_PRESSURE_KPA = 0.001
MAX_PRESSURE_KPA = 1_000.0

_LIBRARY = "vle-thermo (vle.petroleum)"


def _temperature(kelvin: float) -> TemperatureResult:
    return TemperatureResult(kelvin=kelvin, celsius=kelvin - 273.15)


def _boiling_point(value: float, unit: str, name: str) -> float:
    return require_range(
        to_kelvin(value, unit, name=name),
        MIN_BOILING_POINT_K,
        MAX_BOILING_POINT_K,
        f"{name} must be between {MIN_BOILING_POINT_K:g} and {MAX_BOILING_POINT_K:g} K",
    )


def _pressure(value: float, unit: str) -> float:
    return require_range(
        to_kpa(value, unit),
        MIN_PRESSURE_KPA,
        MAX_PRESSURE_KPA,
        f"pressure must be between {MIN_PRESSURE_KPA:g} and {MAX_PRESSURE_KPA:g} kPa absolute",
    )


def _watson_k(value: float | None) -> float | None:
    if value is None:
        return None
    return require_range(
        require_finite(value, "watson_k"),
        MIN_WATSON_K,
        MAX_WATSON_K,
        f"watson_k must be between {MIN_WATSON_K:g} and {MAX_WATSON_K:g}",
    )


def petroleum_fraction_properties(
    normal_boiling_point: Annotated[
        float, Field(description="Normal (atmospheric) boiling point of the cut.")
    ],
    temperature_unit: TemperatureUnit = "K",
    specific_gravity: Annotated[
        float | None, Field(description="Specific gravity at 60/60 degF. Omit if api_gravity.")
    ] = None,
    api_gravity: Annotated[
        float | None, Field(description="API gravity in degAPI. Omit if specific_gravity.")
    ] = None,
    method: Annotated[
        PropertyMethod, Field(description="Critical-property correlation set.")
    ] = "api",
) -> PetroleumFractionResult:
    """Characterize a petroleum fraction as a pseudocomponent.

    From its normal boiling point and gravity (give exactly one of specific
    gravity or API gravity), estimates Watson K, molar mass, critical
    temperature, pressure and volume, Zc, and acentric factor.
    """

    exactly_one("specific_gravity", specific_gravity, "api_gravity", api_gravity)
    tb = _boiling_point(normal_boiling_point, temperature_unit, "normal_boiling_point")
    if api_gravity is not None:
        api = require_finite(api_gravity, "api_gravity")
        sg = call_domain(lambda: float(petroleum.sg_from_api(api)), "invalid api_gravity")
    else:
        assert specific_gravity is not None
        sg = require_finite(specific_gravity, "specific_gravity")
    sg = require_range(
        sg,
        MIN_SPECIFIC_GRAVITY,
        MAX_SPECIFIC_GRAVITY,
        f"specific gravity must be between {MIN_SPECIFIC_GRAVITY:g} and {MAX_SPECIFIC_GRAVITY:g}",
    )
    if method not in petroleum.PROPERTY_METHODS:
        raise ToolInputError(f"method must be one of: {', '.join(petroleum.PROPERTY_METHODS)}")

    est = call_domain(
        lambda: petroleum.estimate(tb, sg, method=method),
        "vle-thermo could not characterize this fraction",
    )
    api_value = call_domain(lambda: float(petroleum.api_from_sg(sg)), "invalid specific gravity")
    return PetroleumFractionResult(
        normal_boiling_point=_temperature(float(est["tb"])),
        specific_gravity=float(est["sg"]),
        api_gravity=api_value,
        watson_k=float(est["watson_k"]),
        molar_mass=float(est["mw"]),
        critical_temperature=_temperature(float(est["tc"])),
        critical_pressure=PressureResult(value=float(est["pc"])),
        critical_molar_volume=float(est["vc"]),
        critical_compressibility=float(est["zc"]),
        acentric_factor=float(est["omega"]),
        calculation=provenance(
            _LIBRARY,
            f"pseudocomponent estimate, '{method}' critical-property method, "
            "Lee-Kesler critical compressibility",
        ),
    )


def petroleum_boiling_point_at_pressure(
    normal_boiling_point: Annotated[float, Field(description="Normal boiling point.")],
    pressure: Annotated[float, Field(description="Absolute pressure of interest.")],
    temperature_unit: TemperatureUnit = "K",
    pressure_unit: PressureUnit = "kPa",
    watson_k: Annotated[
        float | None, Field(description="Watson K for the correction; omit to use none.")
    ] = None,
) -> PetroleumBoilingPointResult:
    """Boiling temperature of a petroleum fraction at a sub- or super-atmospheric
    pressure, from its normal boiling point (Maxwell-Bonnell)."""

    tb = _boiling_point(normal_boiling_point, temperature_unit, "normal_boiling_point")
    p_kpa = _pressure(pressure, pressure_unit)
    kw = _watson_k(watson_k)
    t = call_domain(
        lambda: float(petroleum.boiling_point_at_pressure(tb, p_kpa, watson_k_value=kw)),
        "vle-thermo could not evaluate this boiling point",
    )
    return PetroleumBoilingPointResult(
        normal_boiling_point=_temperature(tb),
        pressure=PressureResult(value=p_kpa),
        boiling_point_at_pressure=_temperature(t),
        watson_k=kw,
        calculation=provenance(_LIBRARY, "Maxwell-Bonnell vapor-pressure correlation"),
    )


def petroleum_normal_boiling_point(
    observed_boiling_point: Annotated[
        float, Field(description="Boiling temperature observed at the given pressure.")
    ],
    pressure: Annotated[float, Field(description="Absolute pressure of the observation.")],
    temperature_unit: TemperatureUnit = "K",
    pressure_unit: PressureUnit = "kPa",
    watson_k: Annotated[
        float | None, Field(description="Watson K for the correction; omit to use none.")
    ] = None,
) -> PetroleumBoilingPointResult:
    """Atmospheric equivalent temperature (normal boiling point) of a petroleum
    fraction from a boiling point observed under vacuum, e.g. ASTM D1160 data
    (Maxwell-Bonnell)."""

    t_obs = _boiling_point(observed_boiling_point, temperature_unit, "observed_boiling_point")
    p_kpa = _pressure(pressure, pressure_unit)
    kw = _watson_k(watson_k)
    tb = call_domain(
        lambda: float(petroleum.normal_boiling_point(t_obs, p_kpa, watson_k_value=kw)),
        "vle-thermo could not evaluate this boiling point",
    )
    return PetroleumBoilingPointResult(
        normal_boiling_point=_temperature(tb),
        pressure=PressureResult(value=p_kpa),
        boiling_point_at_pressure=_temperature(t_obs),
        watson_k=kw,
        calculation=provenance(_LIBRARY, "Maxwell-Bonnell vapor-pressure correlation"),
    )


TOOLS = (
    petroleum_fraction_properties,
    petroleum_boiling_point_at_pressure,
    petroleum_normal_boiling_point,
)
