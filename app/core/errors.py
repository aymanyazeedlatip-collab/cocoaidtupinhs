from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    APPLICATION_ERROR = "application_error"
    VALIDATION_ERROR = "validation_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    INVALID_FARM_STATE = "invalid_farm_state"
    MODEL_ARTIFACT_ERROR = "model_artifact_error"
    CONTRACT_NOT_FOUND = "contract_not_found"
    ENGINE_NOT_FOUND = "engine_not_found"
    ENGINE_EXECUTION_FAILED = "engine_execution_failed"
    MIGRATION_ERROR = "migration_error"
    CONFIGURATION_ERROR = "configuration_error"


class CocoAidError(Exception):
    """Base exception for expected, user-safe application failures."""

    error_code = ErrorCode.APPLICATION_ERROR
    status_code = 400

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        error_code: ErrorCode | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code


class ProviderUnavailableError(CocoAidError):
    error_code = ErrorCode.PROVIDER_UNAVAILABLE
    status_code = 503


class ProviderRateLimitError(CocoAidError):
    error_code = ErrorCode.PROVIDER_RATE_LIMITED
    status_code = 429


class InvalidFarmStateError(CocoAidError):
    error_code = ErrorCode.INVALID_FARM_STATE
    status_code = 422


class ModelArtifactError(CocoAidError):
    error_code = ErrorCode.MODEL_ARTIFACT_ERROR
    status_code = 500


class ContractNotFoundError(CocoAidError):
    error_code = ErrorCode.CONTRACT_NOT_FOUND
    status_code = 404


class EngineNotFoundError(CocoAidError):
    error_code = ErrorCode.ENGINE_NOT_FOUND
    status_code = 404


class EngineExecutionError(CocoAidError):
    error_code = ErrorCode.ENGINE_EXECUTION_FAILED
    status_code = 500


class MigrationError(CocoAidError):
    error_code = ErrorCode.MIGRATION_ERROR
    status_code = 500
