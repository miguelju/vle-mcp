# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
# Saturation-table and state tools added by Claude Code (Claude Opus 5.5).
"""Water and steam tools backed by the granular ``vle.steam`` API (IAPWS-IF97)."""

from collections.abc import Callable
from typing import Annotated

from pydantic import Field
from vle import steam

from vle_mcp.models import (
    PressureResult,
    SaturatedPhaseProperties,
    TemperatureResult,
    WaterSaturationPropertiesResult,
    WaterSaturationTemperatureResult,
    WaterStateResult,
)
from vle_mcp.tools.common import (
    PressureUnit,
    TemperatureUnit,
    ToolInputError,
    call_domain,
    exactly_one,
    finite_or_none,
    provenance,
    require_finite,
    require_range,
    to_kelvin,
    to_kpa,
)

__all__ = [
    "PressureUnit",
    "ToolInputError",
    "calculate_water_saturation_temperature",
    "to_kpa_absolute",
    "water_saturation_properties",
    "water_saturation_temperature",
    "water_state",
]

# IF97 Region 4 is valid from the triple point to the critical point. Keeping
# the bound here makes the public contract explicit; vle-steam remains the
# authoritative calculator and performs its own range check too.
_MIN_SATURATION_PRESSURE_KPA = 0.611_212_677
_MAX_SATURATION_PRESSURE_KPA = 22_064.0
_MIN_SATURATION_TEMPERATURE_K = 273.15
_MAX_SATURATION_TEMPERATURE_K = 647.096

_STEAM_LIBRARY = "vle-steam"


def to_kpa_absolute(pressure: float, pressure_unit: PressureUnit) -> float:
    """Normalize an absolute pressure to kPa and require the IF97 saturation range.

    Args:
        pressure: Finite, positive pressure magnitude.
        pressure_unit: One of Pa, kPa, MPa, bar, or atm.

    Returns:
        Pressure in kPa absolute.
    """

    pressure_kpa = to_kpa(pressure, pressure_unit)
    return require_range(
        pressure_kpa,
        _MIN_SATURATION_PRESSURE_KPA,
        _MAX_SATURATION_PRESSURE_KPA,
        "pressure is outside the IAPWS-IF97 saturation range "
        f"({_MIN_SATURATION_PRESSURE_KPA:g} to "
        f"{_MAX_SATURATION_PRESSURE_KPA:g} kPa absolute)",
    )


def _temperature(kelvin: float) -> TemperatureResult:
    return TemperatureResult(kelvin=kelvin, celsius=kelvin - 273.15)


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
        temperature=_temperature(temperature_k),
        pressure=PressureResult(value=pressure_kpa),
    )


# --- MCP tools ----------------------------------------------------------------


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


def water_saturation_properties(
    temperature: Annotated[
        float | None, Field(description="Saturation temperature. Omit if pressure is given.")
    ] = None,
    temperature_unit: TemperatureUnit = "K",
    pressure: Annotated[
        float | None,
        Field(description="Absolute saturation pressure. Omit if temperature is given."),
    ] = None,
    pressure_unit: PressureUnit = "kPa",
) -> WaterSaturationPropertiesResult:
    """Look up one row of the water/steam saturation table (IAPWS-IF97).

    Give exactly one of temperature or pressure. Returns the saturation
    pressure or temperature, saturated-liquid and saturated-vapor properties,
    latent heat, and surface tension. Use this for vapor pressure of water,
    latent heat of vaporization, or steam-table saturation questions. Valid
    from the triple point (273.15 K) to the critical point (647.096 K).
    """

    exactly_one("temperature", temperature, "pressure", pressure)
    if temperature is not None:
        t_k = require_range(
            to_kelvin(temperature, temperature_unit),
            _MIN_SATURATION_TEMPERATURE_K,
            _MAX_SATURATION_TEMPERATURE_K,
            "temperature is outside the IAPWS-IF97 saturation range (273.15 to 647.096 K)",
        )
        row = call_domain(
            lambda: steam.saturation(T=t_k), "vle-steam could not evaluate this temperature"
        )
    else:
        assert pressure is not None
        p_kpa = to_kpa_absolute(pressure, pressure_unit)
        row = call_domain(
            lambda: steam.saturation(P=p_kpa), "vle-steam could not evaluate this pressure"
        )

    return WaterSaturationPropertiesResult(
        temperature=_temperature(float(row.t)),
        pressure=PressureResult(value=float(row.p)),
        saturated_liquid=SaturatedPhaseProperties(
            specific_volume=float(row.v_f),
            specific_enthalpy=float(row.h_f),
            specific_entropy=float(row.s_f),
            specific_internal_energy=float(row.u_f),
            dynamic_viscosity=finite_or_none(row.mu_f),
            thermal_conductivity=finite_or_none(row.k_f),
        ),
        saturated_vapor=SaturatedPhaseProperties(
            specific_volume=float(row.v_g),
            specific_enthalpy=float(row.h_g),
            specific_entropy=float(row.s_g),
            specific_internal_energy=float(row.u_g),
            dynamic_viscosity=finite_or_none(row.mu_g),
            thermal_conductivity=finite_or_none(row.k_g),
        ),
        enthalpy_of_vaporization=float(row.h_fg),
        entropy_of_vaporization=float(row.s_fg),
        surface_tension=finite_or_none(row.sigma),
        calculation=provenance(
            _STEAM_LIBRARY,
            "IAPWS-IF97 Region 4 with IAPWS R12-08 viscosity, R15-11 thermal "
            "conductivity, and R1-76(2014) surface tension",
        ),
    )


def water_state(
    temperature: Annotated[float | None, Field(description="Temperature.")] = None,
    temperature_unit: TemperatureUnit = "K",
    pressure: Annotated[float | None, Field(description="Absolute pressure.")] = None,
    pressure_unit: PressureUnit = "kPa",
    vapor_quality: Annotated[
        float | None,
        Field(description="Vapor mass fraction from 0 (saturated liquid) to 1 (saturated vapor)."),
    ] = None,
    specific_enthalpy: Annotated[float | None, Field(description="Specific enthalpy in kJ/kg.")] = (
        None
    ),
    specific_entropy: Annotated[
        float | None, Field(description="Specific entropy in kJ/(kg*K).")
    ] = None,
) -> WaterStateResult:
    """Resolve a water/steam state and return its full property set (IAPWS-IF97).

    Give exactly one supported pair:
    temperature + pressure (compressed liquid or superheated steam);
    temperature + vapor_quality or pressure + vapor_quality (wet steam);
    pressure + specific_enthalpy (throttling / PH flash);
    pressure + specific_entropy (isentropic expansion / PS flash).
    Returns density, enthalpy, entropy, heat capacities, speed of sound, and
    transport properties. Two-phase states report null where a property is
    undefined. Pressures are absolute; do not use gauge pressure.
    """

    given = {
        name
        for name, value in (
            ("temperature", temperature),
            ("pressure", pressure),
            ("vapor_quality", vapor_quality),
            ("specific_enthalpy", specific_enthalpy),
            ("specific_entropy", specific_entropy),
        )
        if value is not None
    }
    supported = (
        {"temperature", "pressure"},
        {"temperature", "vapor_quality"},
        {"pressure", "vapor_quality"},
        {"pressure", "specific_enthalpy"},
        {"pressure", "specific_entropy"},
    )
    if given not in supported:
        raise ToolInputError(
            "provide exactly one supported pair: temperature+pressure, "
            "temperature+vapor_quality, pressure+vapor_quality, "
            "pressure+specific_enthalpy, or pressure+specific_entropy"
        )

    kwargs: dict[str, float] = {}
    if temperature is not None:
        kwargs["T"] = to_kelvin(temperature, temperature_unit)
    if pressure is not None:
        kwargs["P"] = to_kpa(pressure, pressure_unit)
    if vapor_quality is not None:
        kwargs["x"] = require_range(
            require_finite(vapor_quality, "vapor_quality"),
            0.0,
            1.0,
            "vapor_quality must be between 0 and 1",
        )
    if specific_enthalpy is not None:
        kwargs["h"] = require_finite(specific_enthalpy, "specific_enthalpy")
    if specific_entropy is not None:
        kwargs["s"] = require_finite(specific_entropy, "specific_entropy")

    state = call_domain(
        lambda: steam.Water(**kwargs),
        "vle-steam could not resolve this state; it may be outside the IAPWS-IF97 "
        "validity range (273.15 to 1073.15 K up to 100 MPa; to 2273.15 K up to 50 MPa)",
    )
    quality = finite_or_none(getattr(state, "x", None))

    return WaterStateResult(
        phase=str(state.phase),
        if97_region=str(state.region),
        temperature=_temperature(float(state.t)),
        pressure=PressureResult(value=float(state.p)),
        vapor_quality=quality,
        density=float(state.rho),
        specific_volume=float(state.v),
        specific_enthalpy=float(state.h),
        specific_entropy=float(state.s),
        specific_internal_energy=float(state.u),
        isobaric_heat_capacity=finite_or_none(state.cp),
        isochoric_heat_capacity=finite_or_none(state.cv),
        speed_of_sound=finite_or_none(state.w),
        dynamic_viscosity=finite_or_none(state.mu),
        kinematic_viscosity=finite_or_none(state.nu),
        thermal_conductivity=finite_or_none(state.k),
        thermal_diffusivity=finite_or_none(state.alpha),
        prandtl_number=finite_or_none(state.pr),
        calculation=provenance(
            _STEAM_LIBRARY,
            "IAPWS-IF97 with IAPWS R12-08 viscosity and R15-11 thermal conductivity",
        ),
    )


TOOLS = (water_saturation_temperature, water_saturation_properties, water_state)
