# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Structured public models returned by MCP tools."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TemperatureResult(BaseModel):
    """A temperature represented in absolute and user-friendly units."""

    model_config = ConfigDict(extra="forbid")

    kelvin: float = Field(description="Temperature in K.")
    celsius: float = Field(description="Temperature in degC.")


class PressureResult(BaseModel):
    """The pressure normalized to the vle repository's canonical unit."""

    model_config = ConfigDict(extra="forbid")

    value: float = Field(description="Pressure in kPa absolute.")
    unit: Literal["kPa"] = "kPa"
    basis: Literal["absolute"] = "absolute"


class CalculationProvenance(BaseModel):
    """Identifies the numerical implementation used for the answer."""

    model_config = ConfigDict(extra="forbid")

    library: Literal["vle-steam"] = "vle-steam"
    method: Literal["IAPWS-IF97 Region 4 saturation equation"] = (
        "IAPWS-IF97 Region 4 saturation equation"
    )


class WaterSaturationTemperatureResult(BaseModel):
    """Structured result for a water saturation-temperature query."""

    model_config = ConfigDict(extra="forbid")

    substance: Literal["water"] = "water"
    temperature: TemperatureResult
    pressure: PressureResult
    calculation: CalculationProvenance = Field(default_factory=CalculationProvenance)


# ---------------------------------------------------------------------------
# Models below were added by Claude Code (Claude Opus 5.5) for the vle-thermo
# 0.18 tool catalogue, under Miguel Jackson's direction.
# ---------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(_Strict):
    """Identifies the numerical implementation and installed version."""

    library: str = Field(description="Python package that produced the number.")
    method: str = Field(description="Correlation, equation of state, or algorithm used.")
    vle_thermo_version: str = Field(description="Installed vle-thermo distribution version.")


# --- Water and steam (IAPWS-IF97) -------------------------------------------


class SaturatedPhaseProperties(_Strict):
    """Mass-basis properties of one saturated phase."""

    specific_volume: float = Field(description="Specific volume in m3/kg.")
    specific_enthalpy: float = Field(description="Specific enthalpy in kJ/kg.")
    specific_entropy: float = Field(description="Specific entropy in kJ/(kg*K).")
    specific_internal_energy: float = Field(description="Specific internal energy in kJ/kg.")
    dynamic_viscosity: float | None = Field(description="Dynamic viscosity in Pa*s.")
    thermal_conductivity: float | None = Field(description="Thermal conductivity in W/(m*K).")


class WaterSaturationPropertiesResult(_Strict):
    """One row of the water/steam saturation table."""

    substance: Literal["water"] = "water"
    temperature: TemperatureResult
    pressure: PressureResult
    saturated_liquid: SaturatedPhaseProperties
    saturated_vapor: SaturatedPhaseProperties
    enthalpy_of_vaporization: float = Field(description="Latent heat h_fg in kJ/kg.")
    entropy_of_vaporization: float = Field(description="s_fg in kJ/(kg*K).")
    surface_tension: float | None = Field(description="Liquid-vapor surface tension in N/m.")
    calculation: Provenance


class WaterStateResult(_Strict):
    """A single resolved water/steam state. Null means not defined for this phase."""

    substance: Literal["water"] = "water"
    phase: str = Field(description="Phase reported by IF97, for example liquid or vapor.")
    if97_region: str = Field(description="IAPWS-IF97 region used for the state.")
    temperature: TemperatureResult
    pressure: PressureResult
    vapor_quality: float | None = Field(description="Vapor mass fraction; null if single-phase.")
    density: float = Field(description="Density in kg/m3.")
    specific_volume: float = Field(description="Specific volume in m3/kg.")
    specific_enthalpy: float = Field(description="Specific enthalpy in kJ/kg.")
    specific_entropy: float = Field(description="Specific entropy in kJ/(kg*K).")
    specific_internal_energy: float = Field(description="Specific internal energy in kJ/kg.")
    isobaric_heat_capacity: float | None = Field(description="cp in kJ/(kg*K).")
    isochoric_heat_capacity: float | None = Field(description="cv in kJ/(kg*K).")
    speed_of_sound: float | None = Field(description="Speed of sound in m/s.")
    dynamic_viscosity: float | None = Field(description="Dynamic viscosity in Pa*s.")
    kinematic_viscosity: float | None = Field(description="Kinematic viscosity in m2/s.")
    thermal_conductivity: float | None = Field(description="Thermal conductivity in W/(m*K).")
    thermal_diffusivity: float | None = Field(description="Thermal diffusivity in m2/s.")
    prandtl_number: float | None = Field(description="Prandtl number, dimensionless.")
    calculation: Provenance


# --- Bundled component database ---------------------------------------------


class ComponentSummary(_Strict):
    name: str
    formula: str
    cas: str = Field(description="CAS registry number.")


class ComponentListResult(_Strict):
    count: int
    components: list[ComponentSummary]
    source: Literal["vle-thermo bundled component database"] = (
        "vle-thermo bundled component database"
    )


class ComponentPropertiesResult(_Strict):
    """Pure-component constants from the bundled database."""

    name: str
    formula: str
    cas: str = Field(description="CAS registry number.")
    molar_mass: float = Field(description="Molar mass in kg/kmol (g/mol).")
    critical_temperature: TemperatureResult
    critical_pressure: PressureResult
    critical_molar_volume: float = Field(description="Critical molar volume in cm3/mol.")
    critical_compressibility: float = Field(description="Critical compressibility Zc.")
    acentric_factor: float = Field(description="Pitzer acentric factor, dimensionless.")
    normal_boiling_point: TemperatureResult
    source: Literal["vle-thermo bundled component database"] = (
        "vle-thermo bundled component database"
    )


# --- Multicomponent mixtures (vle.System) -----------------------------------


class MixtureModel(_Strict):
    equation_of_state: str = Field(description="Cubic EOS applied to both phases.")
    mixing_rule: Literal["classical (kij = 0)"] = "classical (kij = 0)"


class ComponentSplit(_Strict):
    component: str
    feed_mole_fraction: float
    liquid_mole_fraction: float
    vapor_mole_fraction: float
    k_value: float = Field(description="Equilibrium ratio K = y/x.")


class MixtureFlashResult(_Strict):
    """Isothermal (PT) flash of a feed."""

    model: MixtureModel
    temperature: TemperatureResult
    pressure: PressureResult
    two_phase: bool = Field(description="Whether the feed splits into liquid and vapor.")
    vapor_fraction: float = Field(
        description="Vapor mole fraction V/F. With two_phase false, 0 means all liquid "
        "and 1 means all vapor; liquid and vapor compositions then equal the feed."
    )
    components: list[ComponentSplit]
    iterations: int
    calculation: Provenance


class IncipientComponent(_Strict):
    component: str
    specified_mole_fraction: float = Field(description="The fixed phase composition.")
    incipient_mole_fraction: float = Field(description="Composition of the first new phase.")
    k_value: float = Field(description="Equilibrium ratio K = y/x.")


class SaturationPointResult(_Strict):
    """A bubble or dew point of a mixture."""

    model: MixtureModel
    point: Literal["bubble", "dew"]
    solved_for: Literal["temperature", "pressure"]
    temperature: TemperatureResult
    pressure: PressureResult
    specified_phase: Literal["liquid", "vapor"]
    incipient_phase: Literal["liquid", "vapor"]
    components: list[IncipientComponent]
    calculation: Provenance


class MixtureCriticalPointResult(_Strict):
    model: MixtureModel
    composition: dict[str, float]
    critical_temperature: TemperatureResult
    critical_pressure: PressureResult
    critical_molar_volume: float = Field(description="Critical molar volume in m3/kmol.")
    calculation: Provenance


class EnvelopePoint(_Strict):
    temperature_k: float
    pressure_kpa: float = Field(description="Absolute pressure in kPa.")


class PhaseEnvelopeResult(_Strict):
    model: MixtureModel
    composition: dict[str, float]
    point_count: int
    points: list[EnvelopePoint] = Field(
        description="Traced saturation boundary points in tracing order."
    )
    calculation: Provenance


class ComponentFugacity(_Strict):
    component: str
    mole_fraction: float
    ln_fugacity_coefficient: float
    fugacity_coefficient: float


class MixturePhasePropertiesResult(_Strict):
    """Properties of one phase at a fixed temperature, pressure, and composition."""

    model: MixtureModel
    phase: Literal["liquid", "vapor"]
    temperature: TemperatureResult
    pressure: PressureResult
    compressibility_factor: float = Field(description="Z = PV/(RT), dimensionless.")
    mass_density: float | None = Field(
        description="Peneloux volume-translated density in kg/m3; null where the EOS "
        "has no Peneloux shift (VdW, Schmidt-Wenzel, Patel-Teja)."
    )
    molar_enthalpy: float = Field(description="H in kJ/kmol relative to the reference state.")
    molar_entropy: float = Field(description="S in kJ/(kmol*K) relative to the reference state.")
    isobaric_heat_capacity: float = Field(description="Cp in kJ/(kmol*K).")
    reference_state: Literal["ideal gas at 298.15 K and 101.325 kPa"] = (
        "ideal gas at 298.15 K and 101.325 kPa"
    )
    components: list[ComponentFugacity]
    calculation: Provenance


# --- Petroleum characterization ---------------------------------------------


class PetroleumFractionResult(_Strict):
    """Estimated pseudocomponent properties of a petroleum fraction."""

    normal_boiling_point: TemperatureResult
    specific_gravity: float = Field(description="Specific gravity at 60/60 degF.")
    api_gravity: float = Field(description="API gravity in degAPI.")
    watson_k: float = Field(description="Watson (UOP) characterization factor.")
    molar_mass: float = Field(description="Molar mass in kg/kmol.")
    critical_temperature: TemperatureResult
    critical_pressure: PressureResult
    critical_molar_volume: float = Field(description="Critical molar volume in cm3/mol.")
    critical_compressibility: float
    acentric_factor: float
    calculation: Provenance


class PetroleumBoilingPointResult(_Strict):
    """Maxwell-Bonnell conversion between a boiling point and pressure."""

    normal_boiling_point: TemperatureResult
    pressure: PressureResult
    boiling_point_at_pressure: TemperatureResult
    watson_k: float | None = Field(description="Watson K used for the correction, if any.")
    calculation: Provenance
