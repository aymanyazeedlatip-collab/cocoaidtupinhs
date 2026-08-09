from __future__ import annotations

from enum import StrEnum

from app.domain.base import StrictModel


class UnitCode(StrEnum):
    FRACTION = "fraction"
    PERCENT = "percent"
    COUNT = "count"
    HECTARE = "ha"
    SQUARE_METER = "m2"
    KILOGRAM = "kg"
    TONNE = "t"
    KILOGRAM_PER_HECTARE = "kg/ha"
    TONNE_PER_HECTARE = "t/ha"
    MILLIMETER = "mm"
    MILLIMETER_PER_DAY = "mm/day"
    CELSIUS = "degC"
    KILOMETER_PER_HOUR = "km/h"
    METER_PER_SECOND = "m/s"
    WATT_PER_SQUARE_METER = "W/m2"
    MEGAJOULE_PER_SQUARE_METER_DAY = "MJ/m2/day"
    HECTOPASCAL = "hPa"
    KILOPASCAL = "kPa"
    CUBIC_METER_PER_CUBIC_METER = "m3/m3"
    METER = "m"
    DEGREE = "degree"
    PH = "pH"
    PHILIPPINE_PESO = "PHP"
    DAY = "day"
    YEAR = "year"
    INDEX_0_1 = "index_0_1"
    SCORE_0_100 = "score_0_100"
    PROBABILITY = "probability_0_1"


class UnitDefinition(StrictModel):
    code: UnitCode
    quantity: str
    symbol: str
    canonical: bool = True
    notes: str = ""


UNIT_CATALOG: dict[UnitCode, UnitDefinition] = {
    UnitCode.FRACTION: UnitDefinition(code=UnitCode.FRACTION, quantity="ratio", symbol="1"),
    UnitCode.PERCENT: UnitDefinition(code=UnitCode.PERCENT, quantity="percentage", symbol="%"),
    UnitCode.COUNT: UnitDefinition(code=UnitCode.COUNT, quantity="count", symbol="count"),
    UnitCode.HECTARE: UnitDefinition(code=UnitCode.HECTARE, quantity="area", symbol="ha"),
    UnitCode.SQUARE_METER: UnitDefinition(code=UnitCode.SQUARE_METER, quantity="area", symbol="m²", canonical=False),
    UnitCode.KILOGRAM: UnitDefinition(code=UnitCode.KILOGRAM, quantity="mass", symbol="kg"),
    UnitCode.TONNE: UnitDefinition(code=UnitCode.TONNE, quantity="mass", symbol="t"),
    UnitCode.KILOGRAM_PER_HECTARE: UnitDefinition(code=UnitCode.KILOGRAM_PER_HECTARE, quantity="yield", symbol="kg/ha"),
    UnitCode.TONNE_PER_HECTARE: UnitDefinition(code=UnitCode.TONNE_PER_HECTARE, quantity="yield", symbol="t/ha"),
    UnitCode.MILLIMETER: UnitDefinition(code=UnitCode.MILLIMETER, quantity="water depth", symbol="mm"),
    UnitCode.MILLIMETER_PER_DAY: UnitDefinition(code=UnitCode.MILLIMETER_PER_DAY, quantity="water flux", symbol="mm/day"),
    UnitCode.CELSIUS: UnitDefinition(code=UnitCode.CELSIUS, quantity="temperature", symbol="°C"),
    UnitCode.KILOMETER_PER_HOUR: UnitDefinition(code=UnitCode.KILOMETER_PER_HOUR, quantity="speed", symbol="km/h"),
    UnitCode.METER_PER_SECOND: UnitDefinition(code=UnitCode.METER_PER_SECOND, quantity="speed", symbol="m/s", canonical=False),
    UnitCode.WATT_PER_SQUARE_METER: UnitDefinition(code=UnitCode.WATT_PER_SQUARE_METER, quantity="irradiance", symbol="W/m²"),
    UnitCode.MEGAJOULE_PER_SQUARE_METER_DAY: UnitDefinition(code=UnitCode.MEGAJOULE_PER_SQUARE_METER_DAY, quantity="daily radiation", symbol="MJ/m²/day"),
    UnitCode.HECTOPASCAL: UnitDefinition(code=UnitCode.HECTOPASCAL, quantity="pressure", symbol="hPa"),
    UnitCode.KILOPASCAL: UnitDefinition(code=UnitCode.KILOPASCAL, quantity="pressure", symbol="kPa"),
    UnitCode.CUBIC_METER_PER_CUBIC_METER: UnitDefinition(code=UnitCode.CUBIC_METER_PER_CUBIC_METER, quantity="volumetric water content", symbol="m³/m³"),
    UnitCode.METER: UnitDefinition(code=UnitCode.METER, quantity="length/elevation", symbol="m"),
    UnitCode.DEGREE: UnitDefinition(code=UnitCode.DEGREE, quantity="angle", symbol="°"),
    UnitCode.PH: UnitDefinition(code=UnitCode.PH, quantity="soil reaction", symbol="pH"),
    UnitCode.PHILIPPINE_PESO: UnitDefinition(code=UnitCode.PHILIPPINE_PESO, quantity="currency", symbol="PHP"),
    UnitCode.DAY: UnitDefinition(code=UnitCode.DAY, quantity="duration", symbol="day"),
    UnitCode.YEAR: UnitDefinition(code=UnitCode.YEAR, quantity="duration", symbol="year"),
    UnitCode.INDEX_0_1: UnitDefinition(code=UnitCode.INDEX_0_1, quantity="normalized index", symbol="0–1"),
    UnitCode.SCORE_0_100: UnitDefinition(code=UnitCode.SCORE_0_100, quantity="score", symbol="0–100"),
    UnitCode.PROBABILITY: UnitDefinition(code=UnitCode.PROBABILITY, quantity="probability", symbol="0–1"),
}


_CONVERSIONS: dict[tuple[UnitCode, UnitCode], float] = {
    (UnitCode.FRACTION, UnitCode.PERCENT): 100.0,
    (UnitCode.PERCENT, UnitCode.FRACTION): 0.01,
    (UnitCode.HECTARE, UnitCode.SQUARE_METER): 10_000.0,
    (UnitCode.SQUARE_METER, UnitCode.HECTARE): 0.0001,
    (UnitCode.TONNE, UnitCode.KILOGRAM): 1000.0,
    (UnitCode.KILOGRAM, UnitCode.TONNE): 0.001,
    (UnitCode.TONNE_PER_HECTARE, UnitCode.KILOGRAM_PER_HECTARE): 1000.0,
    (UnitCode.KILOGRAM_PER_HECTARE, UnitCode.TONNE_PER_HECTARE): 0.001,
    (UnitCode.KILOMETER_PER_HOUR, UnitCode.METER_PER_SECOND): 1.0 / 3.6,
    (UnitCode.METER_PER_SECOND, UnitCode.KILOMETER_PER_HOUR): 3.6,
}


def convert_value(value: float, from_unit: UnitCode, to_unit: UnitCode) -> float:
    if from_unit == to_unit:
        return float(value)
    factor = _CONVERSIONS.get((from_unit, to_unit))
    if factor is None:
        raise ValueError(f"No supported conversion from {from_unit} to {to_unit}")
    return float(value) * factor


CANONICAL_VARIABLE_UNITS: dict[str, UnitCode] = {
    "farm_area": UnitCode.HECTARE,
    "production_mass": UnitCode.TONNE,
    "yield": UnitCode.TONNE_PER_HECTARE,
    "rainfall": UnitCode.MILLIMETER,
    "evapotranspiration": UnitCode.MILLIMETER_PER_DAY,
    "temperature": UnitCode.CELSIUS,
    "relative_humidity": UnitCode.PERCENT,
    "wind_speed": UnitCode.KILOMETER_PER_HOUR,
    "pressure": UnitCode.HECTOPASCAL,
    "vapor_pressure_deficit": UnitCode.KILOPASCAL,
    "soil_moisture": UnitCode.CUBIC_METER_PER_CUBIC_METER,
    "probability": UnitCode.PROBABILITY,
    "normalized_index": UnitCode.INDEX_0_1,
    "suitability_score": UnitCode.SCORE_0_100,
    "cost": UnitCode.PHILIPPINE_PESO,
}
