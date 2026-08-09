from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_SCHEMA_VERSION = "3.0.0-draft.10"
ContractSchemaVersion = Literal["3.0.0-draft.10"]


class StrictModel(BaseModel):
    """Strict base model for v3 data contracts.

    Unknown fields are rejected so accidental schema drift is detected at API and
    engine boundaries rather than silently entering analytical calculations.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class VersionedContract(StrictModel):
    schema_version: ContractSchemaVersion = CONTRACT_SCHEMA_VERSION


class TimeStampedContract(VersionedContract):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value


def require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")
    return value
