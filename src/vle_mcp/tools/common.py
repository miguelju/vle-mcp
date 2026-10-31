# Created by Claude Code (Claude Opus 5.5), under Miguel Jackson's direction.
"""Shared validation, unit normalization, and error handling for MCP tools.

Unit conversion is delegated to ``vle.units``; this module only restricts the
accepted unit names and enforces finite, physical bounds before any domain
call. vle itself does not reject a non-physical temperature or a composition
that does not sum to one, so those checks must happen here.
"""

import asyncio
import math
from collections.abc import Callable, Sequence
from importlib.metadata import version
from typing import Literal, TypeVar

from vle import units

from vle_mcp.models import Provenance

PressureUnit = Literal["Pa", "kPa", "MPa", "bar", "atm"]
TemperatureUnit = Literal["K", "degC", "degF", "degR"]

PRESSURE_UNITS: tuple[str, ...] = ("Pa", "kPa", "MPa", "bar", "atm")
TEMPERATURE_UNITS: tuple[str, ...] = ("K", "degC", "degF", "degR")

VLE_VERSION = version("vle-thermo")

T = TypeVar("T")


class ToolInputError(ValueError):
    """A stable, public validation error safe to return through MCP."""


def require_finite(value: float, name: str) -> float:
    """Reject NaN and infinities with a public message."""

    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ToolInputError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ToolInputError(f"{name} must be finite")
    return float(value)


def to_kpa(pressure: float, pressure_unit: str, *, name: str = "pressure") -> float:
    """Normalize a finite, positive, absolute pressure to kPa."""

    require_finite(pressure, name)
    if pressure <= 0.0:
        raise ToolInputError(f"{name} must be greater than zero")
    if pressure_unit not in PRESSURE_UNITS:
        raise ToolInputError(f"{name}_unit must be one of: {', '.join(PRESSURE_UNITS)}")
    return units.to_canonical(float(pressure), pressure_unit, "pressure")


def to_kelvin(temperature: float, temperature_unit: str, *, name: str = "temperature") -> float:
    """Normalize a finite temperature to K and require it to be above absolute zero."""

    require_finite(temperature, name)
    if temperature_unit not in TEMPERATURE_UNITS:
        raise ToolInputError(f"{name}_unit must be one of: {', '.join(TEMPERATURE_UNITS)}")
    kelvin = units.to_canonical(float(temperature), temperature_unit, "temperature")
    if kelvin <= 0.0:
        raise ToolInputError(f"{name} must be above absolute zero")
    return kelvin


def require_range(value: float, low: float, high: float, message: str) -> float:
    """Require ``low <= value <= high``."""

    if not low <= value <= high:
        raise ToolInputError(message)
    return value


def exactly_one(name_a: str, a: object | None, name_b: str, b: object | None) -> None:
    """Require exactly one of two mutually exclusive specifications."""

    if (a is None) == (b is None):
        raise ToolInputError(f"provide exactly one of {name_a} or {name_b}")


def finite_or_none(value: float | None) -> float | None:
    """Map None or NaN (vle's "not defined in this phase") to JSON null."""

    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def floats(values: Sequence[float]) -> list[float]:
    """Convert a numeric sequence from the engine into plain floats."""

    return [float(v) for v in values]


# Interpreter-control and cancellation signals must keep propagating.
_NEVER_SWALLOW = (KeyboardInterrupt, SystemExit, GeneratorExit, asyncio.CancelledError)


def call_domain(fn: Callable[[], T], failure: str) -> T:
    """Run a vle call and replace any dependency error with a fixed message.

    Dependency exception text may contain implementation details or paths, so
    it never reaches the client.
    """

    try:
        return fn()
    except ToolInputError:
        raise
    except _NEVER_SWALLOW:
        raise
    except BaseException as exc:
        # BaseException, not Exception: a Rust panic inside vle's engine reaches
        # Python as pyo3's PanicException, which derives from BaseException.
        # Left uncaught it would bypass the MCP SDK's tool-error handling.
        raise ToolInputError(failure) from exc


def provenance(library: str, method: str) -> Provenance:
    """Describe which installed implementation produced a result."""

    return Provenance(library=library, method=method, vle_thermo_version=VLE_VERSION)
