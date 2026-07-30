# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Unit tests for the domain adapter."""

import math

import pytest

from vle_mcp.tools.water import (
    ToolInputError,
    calculate_water_saturation_temperature,
    to_kpa_absolute,
)


@pytest.mark.parametrize(
    ("value", "unit", "expected_kpa"),
    [
        (101_325.0, "Pa", 101.325),
        (101.325, "kPa", 101.325),
        (0.101325, "MPa", 101.325),
        (1.01325, "bar", 101.325),
        (1.0, "atm", 101.325),
    ],
)
def test_pressure_units_normalize_to_standard_atmosphere(
    value: float, unit: str, expected_kpa: float
) -> None:
    assert to_kpa_absolute(value, unit) == pytest.approx(expected_kpa)


@pytest.mark.parametrize("pressure", [math.nan, math.inf, -math.inf, 0.0, -1.0])
def test_invalid_pressure_is_rejected(pressure: float) -> None:
    with pytest.raises(ToolInputError):
        to_kpa_absolute(pressure, "kPa")


def test_unsupported_unit_is_rejected() -> None:
    with pytest.raises(ToolInputError, match="pressure_unit"):
        to_kpa_absolute(1.0, "psi")


@pytest.mark.parametrize("pressure", [0.61, 22_065.0])
def test_pressure_outside_if97_saturation_range_is_rejected(pressure: float) -> None:
    with pytest.raises(ToolInputError, match="outside"):
        to_kpa_absolute(pressure, "kPa")


def test_domain_call_receives_normalized_kpa_and_result_has_provenance() -> None:
    calls: list[float] = []

    def fake_tsat(pressure_kpa: float) -> float:
        calls.append(pressure_kpa)
        return 373.1243

    result = calculate_water_saturation_temperature(1.0, "atm", tsat=fake_tsat)

    assert calls == [pytest.approx(101.325)]
    assert result.temperature.kelvin == pytest.approx(373.1243)
    assert result.temperature.celsius == pytest.approx(99.9743)
    assert result.pressure.value == pytest.approx(101.325)
    assert result.pressure.basis == "absolute"
    assert result.calculation.library == "vle-steam"
    assert result.calculation.method == "IAPWS-IF97 Region 4 saturation equation"


def test_standard_atmosphere_uses_real_vle_steam() -> None:
    result = calculate_water_saturation_temperature(101.325, "kPa")

    assert result.temperature.kelvin == pytest.approx(373.1243, rel=1e-5)
    assert result.temperature.celsius == pytest.approx(99.9743, rel=1e-5)


def test_dependency_error_is_sanitized() -> None:
    def failing_tsat(_: float) -> float:
        raise RuntimeError("/private/path and implementation detail")

    with pytest.raises(ToolInputError) as captured:
        calculate_water_saturation_temperature(101.325, tsat=failing_tsat)

    assert str(captured.value) == "vle-steam could not evaluate this pressure"
    assert "/private/path" not in str(captured.value)
