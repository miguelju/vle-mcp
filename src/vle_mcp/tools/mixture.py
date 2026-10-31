# Created by Claude Code (Claude Opus 5.5), under Miguel Jackson's direction.
"""Multicomponent vapor-liquid equilibrium tools backed by ``vle.System``.

Scope is deliberately bounded: components come only from the bundled
database, the model is a single cubic equation of state with classical mixing
and zero binary interaction parameters, and solver iterations are capped.
Arbitrary user-supplied critical constants, interaction matrices, activity
models, and batch (array) calls are not exposed.
"""

import math
from typing import Annotated, Literal

from pydantic import Field
from vle import System

from vle_mcp.models import (
    ComponentFugacity,
    ComponentSplit,
    EnvelopePoint,
    IncipientComponent,
    MixtureCriticalPointResult,
    MixtureFlashResult,
    MixtureModel,
    MixturePhasePropertiesResult,
    PhaseEnvelopeResult,
    PressureResult,
    SaturationPointResult,
    TemperatureResult,
)
from vle_mcp.tools.common import (
    PressureUnit,
    TemperatureUnit,
    ToolInputError,
    call_domain,
    exactly_one,
    floats,
    provenance,
    require_finite,
    require_range,
    to_kelvin,
    to_kpa,
)
from vle_mcp.tools.components import resolve_component_name

MAX_COMPONENTS = 10
COMPOSITION_TOLERANCE = 1e-3
MAX_TEMPERATURE_K = 2_000.0
MAX_PRESSURE_KPA = 100_000.0
SOLVER_MAX_ITER = 200
MAX_ENVELOPE_POINTS = 120

EquationOfState = Literal["PR", "SRK", "RK", "PRSV", "VdW", "Schmidt-Wenzel", "Patel-Teja"]
# vle-thermo 0.18 computes mixture critical points only for two-parameter
# cubics. Schmidt-Wenzel and Patel-Teja raise "unsupported"; van der Waals
# panics inside the Rust engine (critical.rs, unwrap on None), so it is
# excluded here until upstream fixes it:
# https://github.com/miguelju/vle/issues/4
CriticalPointEquationOfState = Literal["PR", "SRK", "RK", "PRSV"]
Phase = Literal["liquid", "vapor"]

_EOS_DESCRIPTIONS: dict[str, str] = {
    "PR": "Peng-Robinson (1976)",
    "SRK": "Soave-Redlich-Kwong (1972)",
    "RK": "Redlich-Kwong (1949)",
    "PRSV": "Peng-Robinson-Stryjek-Vera (1986)",
    "VdW": "van der Waals (1870)",
    "Schmidt-Wenzel": "Schmidt-Wenzel",
    "Patel-Teja": "Patel-Teja",
}
_CRITICAL_POINT_EOS = ("PR", "SRK", "RK", "PRSV")
# vle-thermo defines no Peneloux volume shift for these, so density is null.
_NO_PENELOUX_EOS = ("VdW", "Schmidt-Wenzel", "Patel-Teja")
_LIBRARY = "vle-thermo"

ComponentNames = Annotated[
    list[str],
    Field(
        min_length=1,
        max_length=MAX_COMPONENTS,
        description="Component names from list_components, in the same order as the fractions.",
    ),
]
MoleFractions = Annotated[
    list[float],
    Field(
        min_length=1,
        max_length=MAX_COMPONENTS,
        description="Mole fractions, each greater than zero, summing to 1.",
    ),
]
Eos = Annotated[EquationOfState, Field(description="Cubic equation of state for both phases.")]


def _temperature(kelvin: float) -> TemperatureResult:
    return TemperatureResult(kelvin=kelvin, celsius=kelvin - 273.15)


def mixture_temperature(value: float, unit: str, name: str = "temperature") -> float:
    return require_range(
        to_kelvin(value, unit, name=name),
        1.0,
        MAX_TEMPERATURE_K,
        f"{name} must be between 1 and {MAX_TEMPERATURE_K:g} K",
    )


def mixture_pressure(value: float, unit: str, name: str = "pressure") -> float:
    return require_range(
        to_kpa(value, unit, name=name),
        1e-3,
        MAX_PRESSURE_KPA,
        f"{name} must be between 0.001 and {MAX_PRESSURE_KPA:g} kPa absolute",
    )


def validate_mixture(
    component_names: list[str], mole_fractions: list[float], *, min_components: int = 1
) -> tuple[list[str], list[float]]:
    """Resolve names and return a composition normalized to sum exactly to one.

    vle does not reject a composition that fails to sum to one, so a sum
    outside ``1 ± COMPOSITION_TOLERANCE`` is an error rather than a silent
    renormalization. Within tolerance, rounding (for example 0.33/0.33/0.34)
    is normalized and the normalized values are echoed in the result.
    Upstream validation is tracked in https://github.com/miguelju/vle/issues/5.
    """

    if not min_components <= len(component_names) <= MAX_COMPONENTS:
        raise ToolInputError(f"provide between {min_components} and {MAX_COMPONENTS} components")
    if len(component_names) != len(mole_fractions):
        raise ToolInputError("component_names and mole_fractions must have the same length")
    names = [resolve_component_name(n) for n in component_names]
    if len(set(names)) != len(names):
        raise ToolInputError("component_names must not repeat a component")
    fractions = [require_finite(f, "mole fraction") for f in mole_fractions]
    if any(f <= 0.0 for f in fractions):
        raise ToolInputError("every mole fraction must be greater than zero")
    total = math.fsum(fractions)
    if abs(total - 1.0) > COMPOSITION_TOLERANCE:
        raise ToolInputError(f"mole fractions must sum to 1 (got {total:.6g})")
    return names, [f / total for f in fractions]


def _system(names: list[str], eos: str) -> System:
    if eos not in _EOS_DESCRIPTIONS:
        raise ToolInputError(f"equation_of_state must be one of: {', '.join(_EOS_DESCRIPTIONS)}")
    return call_domain(
        lambda: System(names, eos=eos.lower()),
        "vle-thermo could not build this mixture model",
    )


def _model(eos: str) -> MixtureModel:
    return MixtureModel(equation_of_state=_EOS_DESCRIPTIONS[eos])


def _method(eos: str, algorithm: str) -> str:
    return f"{algorithm}; {_EOS_DESCRIPTIONS[eos]} EOS with classical mixing, kij = 0"


# --- MCP tools ----------------------------------------------------------------


def mixture_flash(
    component_names: ComponentNames,
    mole_fractions: MoleFractions,
    temperature: float,
    pressure: float,
    temperature_unit: TemperatureUnit = "K",
    pressure_unit: PressureUnit = "kPa",
    equation_of_state: Eos = "PR",
) -> MixtureFlashResult:
    """Isothermal (PT) flash: split a feed into liquid and vapor at fixed T and P.

    Returns whether the feed is two-phase, the vapor fraction, and each
    component's liquid and vapor mole fractions and K-value. Use for "how much
    of this mixture vaporizes at T and P?" questions. Pressure is absolute.
    """

    names, z = validate_mixture(component_names, mole_fractions)
    t_k = mixture_temperature(temperature, temperature_unit)
    p_kpa = mixture_pressure(pressure, pressure_unit)
    system = _system(names, equation_of_state)
    result = call_domain(
        lambda: system.flash_pt(t_k, p_kpa, z, max_iter=SOLVER_MAX_ITER),
        "the flash did not converge for these conditions",
    )
    return MixtureFlashResult(
        model=_model(equation_of_state),
        temperature=_temperature(t_k),
        pressure=PressureResult(value=p_kpa),
        two_phase=bool(result.two_phase),
        vapor_fraction=float(result.beta),
        components=[
            ComponentSplit(
                component=name,
                feed_mole_fraction=zi,
                liquid_mole_fraction=xi,
                vapor_mole_fraction=yi,
                k_value=ki,
            )
            for name, zi, xi, yi, ki in zip(
                names, z, floats(result.x), floats(result.y), floats(result.k), strict=True
            )
        ],
        iterations=int(result.iterations),
        calculation=provenance(_LIBRARY, _method(equation_of_state, "isothermal (PT) flash")),
    )


def _saturation_point(
    point: Literal["bubble", "dew"],
    component_names: list[str],
    mole_fractions: list[float],
    temperature: float | None,
    temperature_unit: str,
    pressure: float | None,
    pressure_unit: str,
    equation_of_state: str,
) -> SaturationPointResult:
    exactly_one("temperature", temperature, "pressure", pressure)
    names, composition = validate_mixture(component_names, mole_fractions)
    system = _system(names, equation_of_state)
    failure = f"the {point}-point calculation did not converge for these conditions"

    if pressure is not None:
        p_kpa = mixture_pressure(pressure, pressure_unit)
        solve = system.bubble_temperature if point == "bubble" else system.dew_temperature
        result = call_domain(lambda: solve(composition, p_kpa, max_iter=SOLVER_MAX_ITER), failure)
        t_k, solved_for = float(result.value), "temperature"
    else:
        assert temperature is not None
        t_k = mixture_temperature(temperature, temperature_unit)
        solve = system.bubble_pressure if point == "bubble" else system.dew_pressure
        result = call_domain(lambda: solve(composition, t_k, max_iter=SOLVER_MAX_ITER), failure)
        p_kpa, solved_for = float(result.value), "pressure"

    if not (math.isfinite(t_k) and math.isfinite(p_kpa) and t_k > 0 and p_kpa > 0):
        raise ToolInputError(failure)

    incipient = floats(result.y if point == "bubble" else result.x)
    return SaturationPointResult(
        model=_model(equation_of_state),
        point=point,
        solved_for=solved_for,
        temperature=_temperature(t_k),
        pressure=PressureResult(value=p_kpa),
        specified_phase="liquid" if point == "bubble" else "vapor",
        incipient_phase="vapor" if point == "bubble" else "liquid",
        components=[
            IncipientComponent(
                component=name,
                specified_mole_fraction=c,
                incipient_mole_fraction=i,
                k_value=k,
            )
            for name, c, i, k in zip(names, composition, incipient, floats(result.k), strict=True)
        ],
        calculation=provenance(
            _LIBRARY, _method(equation_of_state, f"{point}-point {solved_for} solver")
        ),
    )


def mixture_bubble_point(
    component_names: ComponentNames,
    mole_fractions: Annotated[
        list[float],
        Field(
            min_length=1,
            max_length=MAX_COMPONENTS,
            description="Liquid mole fractions, each greater than zero, summing to 1.",
        ),
    ],
    temperature: Annotated[
        float | None, Field(description="Give to solve for bubble pressure.")
    ] = None,
    pressure: Annotated[
        float | None, Field(description="Absolute; give to solve for bubble temperature.")
    ] = None,
    temperature_unit: TemperatureUnit = "K",
    pressure_unit: PressureUnit = "kPa",
    equation_of_state: Eos = "PR",
) -> SaturationPointResult:
    """Bubble point of a liquid mixture: where the first vapor bubble forms.

    Give exactly one of temperature (solves for bubble pressure) or pressure
    (solves for bubble temperature). Returns the solved value and the
    composition of the first vapor.
    """

    return _saturation_point(
        "bubble",
        component_names,
        mole_fractions,
        temperature,
        temperature_unit,
        pressure,
        pressure_unit,
        equation_of_state,
    )


def mixture_dew_point(
    component_names: ComponentNames,
    mole_fractions: Annotated[
        list[float],
        Field(
            min_length=1,
            max_length=MAX_COMPONENTS,
            description="Vapor mole fractions, each greater than zero, summing to 1.",
        ),
    ],
    temperature: Annotated[float | None, Field(description="Give to solve for dew pressure.")] = (
        None
    ),
    pressure: Annotated[
        float | None, Field(description="Absolute; give to solve for dew temperature.")
    ] = None,
    temperature_unit: TemperatureUnit = "K",
    pressure_unit: PressureUnit = "kPa",
    equation_of_state: Eos = "PR",
) -> SaturationPointResult:
    """Dew point of a vapor mixture: where the first liquid drop condenses.

    Give exactly one of temperature (solves for dew pressure) or pressure
    (solves for dew temperature). Returns the solved value and the composition
    of the first liquid.
    """

    return _saturation_point(
        "dew",
        component_names,
        mole_fractions,
        temperature,
        temperature_unit,
        pressure,
        pressure_unit,
        equation_of_state,
    )


def mixture_critical_point(
    component_names: ComponentNames,
    mole_fractions: MoleFractions,
    equation_of_state: Annotated[
        CriticalPointEquationOfState,
        Field(description="Two-parameter cubic equation of state."),
    ] = "PR",
) -> MixtureCriticalPointResult:
    """True critical point (Tc, Pc, Vc) of a mixture of two or more components by
    the Heidemann-Khalil method. For a pure component use component_properties."""

    names, z = validate_mixture(component_names, mole_fractions, min_components=2)
    if equation_of_state not in _CRITICAL_POINT_EOS:
        raise ToolInputError(f"equation_of_state must be one of: {', '.join(_CRITICAL_POINT_EOS)}")
    system = _system(names, equation_of_state)
    result = call_domain(
        lambda: system.critical_point(z, max_iter=SOLVER_MAX_ITER),
        "the critical-point calculation did not converge for this mixture",
    )
    tc, pc = float(result.tc), float(result.pc)
    if not (math.isfinite(tc) and math.isfinite(pc) and tc > 0 and pc > 0):
        raise ToolInputError("the critical-point calculation did not converge for this mixture")
    return MixtureCriticalPointResult(
        model=_model(equation_of_state),
        composition=dict(zip(names, z, strict=True)),
        critical_temperature=_temperature(tc),
        critical_pressure=PressureResult(value=pc),
        critical_molar_volume=float(result.vc),
        calculation=provenance(
            _LIBRARY, _method(equation_of_state, "Heidemann-Khalil critical point")
        ),
    )


def mixture_phase_envelope(
    component_names: ComponentNames,
    mole_fractions: MoleFractions,
    equation_of_state: Eos = "PR",
    max_points: Annotated[
        int, Field(ge=10, le=MAX_ENVELOPE_POINTS, description="Upper bound on traced points.")
    ] = 60,
) -> PhaseEnvelopeResult:
    """Trace the pressure-temperature phase envelope (bubble and dew curves) of a
    mixture of two or more components at fixed overall composition, starting
    from 100 kPa."""

    names, z = validate_mixture(component_names, mole_fractions, min_components=2)
    if not 10 <= max_points <= MAX_ENVELOPE_POINTS:
        raise ToolInputError(f"max_points must be between 10 and {MAX_ENVELOPE_POINTS}")
    system = _system(names, equation_of_state)
    points = call_domain(
        lambda: system.phase_envelope(z, max_points=max_points),
        "the phase envelope could not be traced for this mixture",
    )
    traced = [
        EnvelopePoint(temperature_k=float(t), pressure_kpa=float(p))
        for t, p in points
        if math.isfinite(t) and math.isfinite(p)
    ]
    if not traced:
        raise ToolInputError("the phase envelope could not be traced for this mixture")
    return PhaseEnvelopeResult(
        model=_model(equation_of_state),
        composition=dict(zip(names, z, strict=True)),
        point_count=len(traced),
        points=traced,
        calculation=provenance(_LIBRARY, _method(equation_of_state, "phase-envelope tracing")),
    )


def mixture_phase_properties(
    component_names: ComponentNames,
    mole_fractions: MoleFractions,
    temperature: float,
    pressure: float,
    phase: Annotated[Phase, Field(description="Which EOS root to evaluate.")],
    temperature_unit: TemperatureUnit = "K",
    pressure_unit: PressureUnit = "kPa",
    equation_of_state: Eos = "PR",
) -> MixturePhasePropertiesResult:
    """Thermodynamic properties of one phase of known composition at T and P.

    Returns compressibility factor Z, volume-translated mass density (null for
    VdW, Schmidt-Wenzel, and Patel-Teja, which have no Peneloux shift), molar
    enthalpy and entropy (relative to the ideal gas at 298.15 K and 101.325
    kPa), Cp, and each component's fugacity coefficient. This does not decide
    whether the phase is stable; use mixture_flash for that.
    """

    names, x = validate_mixture(component_names, mole_fractions)
    t_k = mixture_temperature(temperature, temperature_unit)
    p_kpa = mixture_pressure(pressure, pressure_unit)
    system = _system(names, equation_of_state)
    failure = "vle-thermo could not evaluate this phase at these conditions"

    z_factor = call_domain(lambda: float(system.z_factor(t_k, p_kpa, x, phase)), failure)
    density = (
        None
        if equation_of_state in _NO_PENELOUX_EOS
        else call_domain(lambda: float(system.translated_density(t_k, p_kpa, x, phase)), failure)
    )
    enthalpy, entropy = call_domain(
        lambda: tuple(float(v) for v in system.enthalpy_entropy(t_k, p_kpa, x, phase)), failure
    )
    cp = call_domain(lambda: float(system.phase_cp(t_k, p_kpa, x, phase)), failure)
    ln_phi = call_domain(lambda: floats(system.ln_phi(t_k, p_kpa, x, phase)), failure)

    values = [z_factor, enthalpy, entropy, cp, *ln_phi]
    if density is not None:
        values.append(density)
    # exp(ln_phi) must also be representable as a float.
    if not all(math.isfinite(v) for v in values) or any(abs(v) > 700.0 for v in ln_phi):
        raise ToolInputError(failure)

    return MixturePhasePropertiesResult(
        model=_model(equation_of_state),
        phase=phase,
        temperature=_temperature(t_k),
        pressure=PressureResult(value=p_kpa),
        compressibility_factor=z_factor,
        mass_density=density,
        molar_enthalpy=enthalpy,
        molar_entropy=entropy,
        isobaric_heat_capacity=cp,
        components=[
            ComponentFugacity(
                component=name,
                mole_fraction=xi,
                ln_fugacity_coefficient=lp,
                fugacity_coefficient=math.exp(lp),
            )
            for name, xi, lp in zip(names, x, ln_phi, strict=True)
        ],
        calculation=provenance(
            _LIBRARY,
            _method(equation_of_state, "cubic EOS residual properties with Peneloux translation"),
        ),
    )


TOOLS = (
    mixture_flash,
    mixture_bubble_point,
    mixture_dew_point,
    mixture_critical_point,
    mixture_phase_envelope,
    mixture_phase_properties,
)
