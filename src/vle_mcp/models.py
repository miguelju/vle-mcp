# Created by OpenAI Codex using GPT-5.6 Sol, under Miguel Jackson's direction.
"""Structured public models returned by MCP tools."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TemperatureResult(BaseModel):
    """A temperature represented in absolute and user-friendly units."""

    model_config = ConfigDict(extra="forbid")

    kelvin: float = Field(description="Saturation temperature in K.")
    celsius: float = Field(description="Saturation temperature in degC.")


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
