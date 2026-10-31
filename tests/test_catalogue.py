# Created by Claude Code (Claude Opus 5.5), under Miguel Jackson's direction.
"""Adapter and protocol tests for the vle-thermo 0.18 tool catalogue.

Each domain test compares the adapter's output with a direct call to the same
vle function, so it proves delegation and unit handling without re-deriving
any thermodynamics here. Validation tests cover inputs vle itself accepts
silently (non-normalized compositions, non-physical temperatures).
"""

import math

import pytest
import vle
from mcp.shared.memory import create_connected_server_and_client_session
from vle import petroleum, steam

from vle_mcp.server import TOOLS, mcp
from vle_mcp.tools.common import ToolInputError, call_domain
from vle_mcp.tools.components import component_properties, list_components
from vle_mcp.tools.mixture import (
    MAX_COMPONENTS,
    mixture_bubble_point,
    mixture_critical_point,
    mixture_dew_point,
    mixture_flash,
    mixture_phase_envelope,
    mixture_phase_properties,
    validate_mixture,
)
from vle_mcp.tools.petroleum import (
    petroleum_boiling_point_at_pressure,
    petroleum_fraction_properties,
    petroleum_normal_boiling_point,
)
from vle_mcp.tools.water import water_saturation_properties, water_state

NAMES = ["methane", "ethane", "propane", "n-butane"]
Z = [0.4, 0.3, 0.2, 0.1]


# --- water -------------------------------------------------------------------


def test_saturation_properties_by_temperature_matches_vle_steam() -> None:
    result = water_saturation_properties(temperature=100.0, temperature_unit="degC")
    row = steam.saturation(T=373.15)

    assert result.pressure.value == pytest.approx(row.p)
    assert result.enthalpy_of_vaporization == pytest.approx(row.h_fg)
    assert result.saturated_liquid.specific_enthalpy == pytest.approx(row.h_f)
    assert result.saturated_vapor.specific_volume == pytest.approx(row.v_g)
    assert result.surface_tension == pytest.approx(row.sigma)
    assert result.calculation.library == "vle-steam"
    assert result.calculation.vle_thermo_version == vle.__version__


def test_saturation_properties_by_pressure_matches_tsat() -> None:
    result = water_saturation_properties(pressure=1.0, pressure_unit="atm")
    assert result.temperature.kelvin == pytest.approx(steam.tsat(101.325))


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"temperature": 300.0, "pressure": 3.5}, {"temperature": 700.0}, {"pressure": 0.1}],
)
def test_saturation_properties_rejects_bad_specifications(kwargs: dict) -> None:
    with pytest.raises(ToolInputError):
        water_saturation_properties(**kwargs)


def test_water_state_superheated_steam_matches_vle_steam() -> None:
    result = water_state(temperature=500.0, pressure=1.0, pressure_unit="MPa")
    state = steam.Water(T=500.0, P=1000.0)

    assert result.phase == state.phase == "vapor"
    assert result.density == pytest.approx(state.rho)
    assert result.specific_enthalpy == pytest.approx(state.h)
    assert result.dynamic_viscosity == pytest.approx(state.mu)
    assert result.vapor_quality is None


def test_water_state_wet_steam_reports_null_for_undefined_properties() -> None:
    result = water_state(pressure=101.325, vapor_quality=0.5)

    assert result.vapor_quality == pytest.approx(0.5)
    assert result.temperature.kelvin == pytest.approx(steam.tsat(101.325))
    assert result.isobaric_heat_capacity is None
    assert result.dynamic_viscosity is None


def test_water_state_ph_flash_round_trips() -> None:
    h = steam.Water(T=500.0, P=1000.0).h
    result = water_state(pressure=1000.0, specific_enthalpy=h)
    assert result.temperature.kelvin == pytest.approx(500.0, rel=1e-6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature": 300.0},
        {"temperature": 300.0, "specific_enthalpy": 100.0},
        {"pressure": 100.0, "vapor_quality": 1.5},
        {"temperature": 5000.0, "pressure": 100.0},
        {"temperature": -300.0, "temperature_unit": "degC", "pressure": 100.0},
    ],
)
def test_water_state_rejects_bad_specifications(kwargs: dict) -> None:
    with pytest.raises(ToolInputError):
        water_state(**kwargs)


def test_water_state_dependency_error_is_sanitized() -> None:
    with pytest.raises(ToolInputError) as captured:
        water_state(temperature=5000.0, pressure=100.0)
    assert "IAPWS-IF97 validity range" in str(captured.value)
    assert "5000" not in str(captured.value)


# --- components ----------------------------------------------------------------


def test_list_components_mirrors_bundled_database() -> None:
    result = list_components()
    assert result.count == len(vle.components.available())
    assert [c.name for c in result.components] == vle.components.available()


def test_component_properties_is_case_insensitive_and_matches_database() -> None:
    result = component_properties("Methane")
    record = vle.components.get("methane")

    assert result.name == "methane"
    assert result.critical_temperature.kelvin == pytest.approx(record.tc)
    assert result.critical_pressure.value == pytest.approx(record.pc)
    assert result.acentric_factor == pytest.approx(record.omega)


@pytest.mark.parametrize("name", ["unobtainium", "", "x" * 65])
def test_unknown_component_is_rejected(name: str) -> None:
    with pytest.raises(ToolInputError):
        component_properties(name)


# --- mixture validation --------------------------------------------------------


def test_composition_within_tolerance_is_normalized() -> None:
    names, z = validate_mixture(["methane", "ethane", "propane"], [0.333, 0.333, 0.333])
    assert names == ["methane", "ethane", "propane"]
    assert math.fsum(z) == pytest.approx(1.0, abs=1e-15)


@pytest.mark.parametrize(
    ("names", "fractions", "match"),
    [
        (NAMES, [0.5, 0.5, 0.1, 0.1], "sum to 1"),
        (NAMES, [0.4, 0.3, 0.3], "same length"),
        (["methane", "methane"], [0.5, 0.5], "repeat"),
        (["methane", "ethane"], [1.0, 0.0], "greater than zero"),
        (["methane", "ethane"], [math.nan, 0.5], "finite"),
        (["methane"] * (MAX_COMPONENTS + 1), [0.1] * (MAX_COMPONENTS + 1), "between 1 and"),
    ],
)
def test_invalid_mixtures_are_rejected(names: list, fractions: list, match: str) -> None:
    with pytest.raises(ToolInputError, match=match):
        validate_mixture(names, fractions)


def test_non_physical_temperature_is_rejected_before_vle() -> None:
    # vle.System.flash_pt accepts T = -5 K and returns a result; the adapter must not.
    with pytest.raises(ToolInputError, match="absolute zero"):
        mixture_flash(NAMES, Z, temperature=-5.0, pressure=2000.0)


# --- mixture calculations ------------------------------------------------------


def test_flash_matches_vle_system() -> None:
    result = mixture_flash(
        NAMES, Z, temperature=-23.15, temperature_unit="degC", pressure=20.0, pressure_unit="bar"
    )
    expected = vle.System(NAMES, eos="pr").flash_pt(250.0, 2000.0, Z)

    assert result.two_phase is True
    assert result.vapor_fraction == pytest.approx(expected.beta)
    assert [c.vapor_mole_fraction for c in result.components] == pytest.approx(expected.y)
    assert [c.k_value for c in result.components] == pytest.approx(expected.k)
    assert result.model.equation_of_state == "Peng-Robinson (1976)"


def test_flash_equation_of_state_selection_reaches_vle() -> None:
    result = mixture_flash(NAMES, Z, 250.0, 2000.0, equation_of_state="SRK")
    expected = vle.System(NAMES, eos="srk").flash_pt(250.0, 2000.0, Z)
    assert result.vapor_fraction == pytest.approx(expected.beta)


def test_bubble_and_dew_points_match_vle_and_bracket_the_flash() -> None:
    bubble = mixture_bubble_point(NAMES, Z, pressure=2000.0)
    dew = mixture_dew_point(NAMES, Z, pressure=2000.0)
    system = vle.System(NAMES, eos="pr")

    assert bubble.solved_for == "temperature"
    assert bubble.temperature.kelvin == pytest.approx(system.bubble_temperature(Z, 2000.0).value)
    assert dew.temperature.kelvin == pytest.approx(system.dew_temperature(Z, 2000.0).value)
    # The two-phase flash at 250 K must lie between the bubble and dew temperatures.
    assert bubble.temperature.kelvin < 250.0 < dew.temperature.kelvin


def test_bubble_pressure_at_temperature_matches_vle() -> None:
    result = mixture_bubble_point(NAMES, Z, temperature=250.0)
    expected = vle.System(NAMES, eos="pr").bubble_pressure(Z, 250.0)

    assert result.solved_for == "pressure"
    assert result.pressure.value == pytest.approx(expected.value)
    assert [c.incipient_mole_fraction for c in result.components] == pytest.approx(expected.y)


def test_saturation_point_requires_exactly_one_specification() -> None:
    with pytest.raises(ToolInputError, match="exactly one"):
        mixture_bubble_point(NAMES, Z, temperature=250.0, pressure=2000.0)
    with pytest.raises(ToolInputError, match="exactly one"):
        mixture_dew_point(NAMES, Z)


def test_non_convergence_is_sanitized() -> None:
    with pytest.raises(ToolInputError) as captured:
        mixture_bubble_point(NAMES, Z, pressure=99_000.0)
    assert (
        str(captured.value) == "the bubble-point calculation did not converge for these conditions"
    )


def test_critical_point_matches_vle() -> None:
    result = mixture_critical_point(NAMES, Z)
    expected = vle.System(NAMES, eos="pr").critical_point(Z)

    assert result.critical_temperature.kelvin == pytest.approx(expected.tc)
    assert result.critical_pressure.value == pytest.approx(expected.pc)


def test_phase_envelope_is_bounded_and_matches_vle() -> None:
    result = mixture_phase_envelope(NAMES, Z, max_points=30)
    expected = vle.System(NAMES, eos="pr").phase_envelope(Z, max_points=30)

    assert 0 < result.point_count <= 30
    assert result.points[0].temperature_k == pytest.approx(expected[0][0])
    assert result.points[0].pressure_kpa == pytest.approx(expected[0][1])


def test_phase_properties_match_vle() -> None:
    result = mixture_phase_properties(NAMES, Z, 250.0, 2000.0, phase="vapor")
    system = vle.System(NAMES, eos="pr")
    h, s = system.enthalpy_entropy(250.0, 2000.0, Z, "vapor")

    assert result.compressibility_factor == pytest.approx(
        system.z_factor(250.0, 2000.0, Z, "vapor")
    )
    assert result.molar_enthalpy == pytest.approx(h)
    assert result.molar_entropy == pytest.approx(s)
    assert [c.ln_fugacity_coefficient for c in result.components] == pytest.approx(
        system.ln_phi(250.0, 2000.0, Z, "vapor")
    )


# --- petroleum -----------------------------------------------------------------


def test_fraction_properties_match_vle_and_accept_api_gravity() -> None:
    by_sg = petroleum_fraction_properties(500.0, specific_gravity=0.8)
    by_api = petroleum_fraction_properties(500.0, api_gravity=petroleum.api_from_sg(0.8))
    expected = petroleum.estimate(500.0, 0.8)

    assert by_sg.watson_k == pytest.approx(expected["watson_k"])
    assert by_sg.molar_mass == pytest.approx(expected["mw"])
    assert by_sg.critical_temperature.kelvin == pytest.approx(expected["tc"])
    assert by_api.molar_mass == pytest.approx(by_sg.molar_mass)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"normal_boiling_point": 500.0},
        {"normal_boiling_point": 500.0, "specific_gravity": 0.8, "api_gravity": 45.0},
        {"normal_boiling_point": 500.0, "specific_gravity": 3.0},
        {"normal_boiling_point": 50.0, "specific_gravity": 0.8},
    ],
)
def test_fraction_properties_reject_bad_input(kwargs: dict) -> None:
    with pytest.raises(ToolInputError):
        petroleum_fraction_properties(**kwargs)


def test_maxwell_bonnell_directions_match_vle() -> None:
    down = petroleum_boiling_point_at_pressure(500.0, 10.0)
    up = petroleum_normal_boiling_point(400.0, 10.0)

    assert down.boiling_point_at_pressure.kelvin == pytest.approx(
        petroleum.boiling_point_at_pressure(500.0, 10.0)
    )
    assert up.normal_boiling_point.kelvin == pytest.approx(
        petroleum.normal_boiling_point(400.0, 10.0)
    )


# --- protocol ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_tool_is_published_read_only() -> None:
    async with create_connected_server_and_client_session(mcp) as session:
        tools = (await session.list_tools()).tools

    assert {t.name for t in tools} == {fn.__name__ for fn in TOOLS}
    for tool in tools:
        assert tool.description, tool.name
        assert tool.outputSchema is not None, tool.name
        assert tool.annotations is not None and tool.annotations.readOnlyHint is True, tool.name


@pytest.mark.asyncio
async def test_mixture_flash_over_mcp() -> None:
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool(
            "mixture_flash",
            {
                "component_names": NAMES,
                "mole_fractions": Z,
                "temperature": 250.0,
                "pressure": 2000.0,
            },
        )
    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["two_phase"] is True


@pytest.mark.asyncio
async def test_invalid_input_becomes_a_tool_error_over_mcp() -> None:
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool(
            "mixture_flash",
            {
                "component_names": ["methane", "ethane"],
                "mole_fractions": [0.9, 0.9],
                "temperature": 250.0,
                "pressure": 2000.0,
            },
        )
    assert result.isError is True
    assert "sum to 1" in result.content[0].text


@pytest.mark.asyncio
async def test_oversized_mixture_is_rejected_by_schema_over_mcp() -> None:
    names = vle.components.available()[: MAX_COMPONENTS + 1]
    async with create_connected_server_and_client_session(mcp) as session:
        result = await session.call_tool(
            "mixture_critical_point",
            {"component_names": names, "mole_fractions": [1 / len(names)] * len(names)},
        )
    assert result.isError is True


# --- hardening found while building the catalogue -----------------------------


class _FakePanic(BaseException):
    """Stands in for pyo3's PanicException, which derives from BaseException."""


def test_engine_panics_are_sanitized() -> None:
    def panic() -> None:
        raise _FakePanic("called `Option::unwrap()` on a `None` value")

    with pytest.raises(ToolInputError, match=r"^fixed message$"):
        call_domain(panic, "fixed message")


def test_cancellation_is_not_swallowed() -> None:
    def interrupted() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        call_domain(interrupted, "fixed message")


@pytest.mark.parametrize("eos", ["VdW", "Schmidt-Wenzel", "Patel-Teja"])
def test_critical_point_rejects_eos_vle_cannot_handle(eos: str) -> None:
    # VdW panics inside vle-thermo 0.18's engine; the other two are unsupported.
    with pytest.raises(ToolInputError, match="equation_of_state"):
        mixture_critical_point(NAMES, Z, equation_of_state=eos)


@pytest.mark.parametrize("eos", ["PR", "SRK", "RK", "PRSV"])
def test_critical_point_supported_eos(eos: str) -> None:
    result = mixture_critical_point(NAMES, Z, equation_of_state=eos)
    assert result.critical_pressure.value > 0


@pytest.mark.parametrize("tool", [mixture_critical_point, mixture_phase_envelope])
def test_pure_component_is_rejected_where_meaningless(tool) -> None:
    with pytest.raises(ToolInputError, match="between 2 and"):
        tool(["methane"], [1.0])


@pytest.mark.parametrize(
    ("eos", "has_density"),
    [
        ("PR", True),
        ("SRK", True),
        ("RK", True),
        ("PRSV", True),
        ("VdW", False),
        ("Schmidt-Wenzel", False),
        ("Patel-Teja", False),
    ],
)
def test_phase_properties_for_every_eos(eos: str, has_density: bool) -> None:
    result = mixture_phase_properties(NAMES, Z, 250.0, 2000.0, "liquid", equation_of_state=eos)
    assert (result.mass_density is not None) is has_density
    assert result.compressibility_factor > 0
