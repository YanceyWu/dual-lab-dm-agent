"""Application-level use-case execution and registration."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from pydantic import ValidationError

from pm_agent.database import repository
from pm_agent.use_cases.service import (
    UseCaseRequest,
    UseCaseResult,
    new_execution_metadata,
)

UseCaseHandler = Callable[[UseCaseRequest], UseCaseResult]


@dataclass(frozen=True)
class UseCaseDescriptor:
    """Public metadata needed for safe tool discovery and description."""

    use_case_id: str
    purpose: str
    parameter_schema: dict[str, object]
    contract_version: str = "1.0"
    supported_operations: tuple[str, ...] = ("query",)
    read_only: bool = True
    known_statuses: tuple[str, ...] = ("success", "unavailable", "invalid", "failed")


class UseCaseExecutor:
    """Routes stable requests to registered application use cases.

    Interfaces provide a ``UseCaseRequest`` and render the resulting neutral
    contract; business routing remains here rather than in every interface.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, UseCaseHandler] = {}
        self._descriptors: dict[str, UseCaseDescriptor] = {}

    def register(self, descriptor: UseCaseDescriptor, handler: UseCaseHandler) -> None:
        use_case_id = descriptor.use_case_id
        if use_case_id in self._handlers:
            raise ValueError(f"Use case '{use_case_id}' is already registered.")
        self._handlers[use_case_id] = handler
        self._descriptors[use_case_id] = descriptor

    def list_descriptors(self) -> list[UseCaseDescriptor]:
        return [self._descriptors[key] for key in sorted(self._descriptors)]

    def describe(self, use_case_id: str) -> UseCaseDescriptor | None:
        return self._descriptors.get(use_case_id)

    def execute(self, request: UseCaseRequest) -> UseCaseResult:
        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        handler = self._handlers.get(request.use_case_id)
        if handler is None:
            return self._finalize(UseCaseResult(
                status="unavailable",
                warnings=[{"code": "USE_CASE_NOT_FOUND", "field": "use_case_id"}],
                execution_metadata=new_execution_metadata(request),
            ), request, started_at, started_clock, read_only=True)
        descriptor = self._descriptors[request.use_case_id]
        validation_warnings = self._validate_request(request, descriptor)
        if validation_warnings:
            return self._finalize(
                UseCaseResult(
                    status="invalid",
                    warnings=validation_warnings,
                    execution_metadata=new_execution_metadata(request),
                ),
                request,
                started_at,
                started_clock,
                read_only=descriptor.read_only,
            )
        if request.operation not in descriptor.supported_operations:
            return self._finalize(UseCaseResult(
                status="invalid",
                warnings=[{"code": "OPERATION_NOT_SUPPORTED", "field": "operation"}],
                execution_metadata=new_execution_metadata(request),
            ), request, started_at, started_clock, read_only=descriptor.read_only)
        try:
            handler_result = handler(request)
        except ValidationError as exc:
            result = UseCaseResult(
                status="failed",
                warnings=[
                    {
                        "code": (
                            "RESULT_CONTRACT_INVALID"
                            if self._is_result_contract_validation_error(exc)
                            else self._safe_exception_code(exc)
                        )
                    }
                ],
                execution_metadata=new_execution_metadata(request),
            )
        except Exception as exc:
            result = UseCaseResult(
                status="failed",
                warnings=[{"code": self._safe_exception_code(exc)}],
                execution_metadata=new_execution_metadata(request),
            )
        else:
            try:
                raw_result = (
                    handler_result.model_dump(warnings=False)
                    if isinstance(handler_result, UseCaseResult)
                    else handler_result
                )
                result = UseCaseResult.model_validate(raw_result)
                if not self._intelligence_output_is_valid(result):
                    raise ResultContractInvalidError
            except Exception:
                result = UseCaseResult(
                    status="failed",
                    warnings=[{"code": "RESULT_CONTRACT_INVALID"}],
                    execution_metadata=new_execution_metadata(request),
                )
        return self._finalize(
            result,
            request,
            started_at,
            started_clock,
            read_only=descriptor.read_only,
        )

    @staticmethod
    def _validate_request(
        request: UseCaseRequest,
        descriptor: UseCaseDescriptor,
    ) -> list[dict[str, object]]:
        warnings: list[dict[str, object]] = []
        if request.contract_version != descriptor.contract_version:
            warnings.append(
                {
                    "code": "CONTRACT_VERSION_UNSUPPORTED",
                    "field": "contract_version",
                    "supported": [descriptor.contract_version],
                }
            )
        if request.correlation_id is not None and (
            len(request.correlation_id) > 128
            or re.fullmatch(r"[A-Za-z0-9._:-]+", request.correlation_id) is None
        ):
            warnings.append({"code": "CORRELATION_ID_INVALID", "field": "correlation_id"})

        schema = descriptor.parameter_schema
        unknown = sorted(set(request.parameters) - set(schema))
        warnings.extend(
            {"code": "UNKNOWN_PARAMETER", "field": field} for field in unknown
        )
        for field, raw_rules in schema.items():
            rules = raw_rules if isinstance(raw_rules, dict) else {}
            present = field in request.parameters
            if rules.get("required") and not present:
                warnings.append({"code": "REQUIRED_PARAMETER_MISSING", "field": field})
                continue
            if not present:
                continue
            value = request.parameters[field]
            expected = rules.get("type")
            valid_type = {
                "string": isinstance(value, str),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "number": isinstance(value, (int, float)) and not isinstance(value, bool),
                "boolean": isinstance(value, bool),
                "array": isinstance(value, list),
                "object": isinstance(value, dict),
            }.get(str(expected), True)
            if not valid_type:
                warnings.append(
                    {
                        "code": "PARAMETER_TYPE_INVALID",
                        "field": field,
                        "expected": expected,
                    }
                )
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                minimum = rules.get("minimum")
                maximum = rules.get("maximum")
                if minimum is not None and value < minimum:
                    warnings.append(
                        {
                            "code": "PARAMETER_OUT_OF_RANGE",
                            "field": field,
                            "minimum": minimum,
                            "maximum": maximum,
                        }
                    )
                elif maximum is not None and value > maximum:
                    warnings.append(
                        {
                            "code": "PARAMETER_OUT_OF_RANGE",
                            "field": field,
                            "minimum": minimum,
                            "maximum": maximum,
                        }
                    )
            if isinstance(value, str):
                if not value.strip() and rules.get("allow_empty") is not True:
                    warnings.append({"code": "PARAMETER_EMPTY", "field": field})
                maximum_length = rules.get("maximum_length")
                if maximum_length is not None and len(value) > maximum_length:
                    warnings.append(
                        {
                            "code": "PARAMETER_TOO_LONG",
                            "field": field,
                            "maximum_length": maximum_length,
                        }
                    )
            allowed = rules.get("enum")
            if allowed is not None and value not in allowed:
                warnings.append(
                    {
                        "code": "PARAMETER_NOT_ALLOWED",
                        "field": field,
                        "allowed": allowed,
                    }
                )
        return warnings

    @staticmethod
    def _is_result_contract_validation_error(exc: ValidationError) -> bool:
        return exc.title in {
            "UseCaseResult",
            "IntelligenceSubject",
            "IntelligenceFact",
            "IntelligenceSignal",
            "IntelligenceRecommendation",
        }

    @staticmethod
    def _intelligence_output_is_valid(result: UseCaseResult) -> bool:
        """Validate intelligence IDs, semantics, and result-local references."""

        def valid_identifier(value: object) -> bool:
            return (
                isinstance(value, str)
                and bool(value.strip())
                and len(value) <= 128
            )

        def valid_unique_ids(values: list[object]) -> bool:
            return (
                all(valid_identifier(value) for value in values)
                and len(values) == len(set(values))
            )

        fact_ids = [fact.fact_id for fact in result.facts]
        signal_ids = [signal.signal_id for signal in result.signals]
        recommendation_ids = [
            recommendation.recommendation_id
            for recommendation in result.recommendations
        ]
        if not all(
            (
                valid_unique_ids(fact_ids),
                valid_unique_ids(signal_ids),
                valid_unique_ids(recommendation_ids),
            )
        ):
            return False

        subjects = [
            item.subject
            for collection in (
                result.facts,
                result.signals,
                result.recommendations,
            )
            for item in collection
        ]
        if any(
            not valid_identifier(subject.kind) or not valid_identifier(subject.id)
            for subject in subjects
        ):
            return False

        evidence_ids = {
            item.get("evidence_id")
            for item in result.evidence
            if valid_identifier(item.get("evidence_id"))
        }
        freshness_ids = {
            item.get("source_id")
            for item in result.freshness
            if valid_identifier(item.get("source_id"))
        }
        fact_id_set = set(fact_ids)
        signal_id_set = set(signal_ids)

        for fact in result.facts:
            if fact.fact_kind == "derived" and fact.rule_version is None:
                return False
            if fact.value_state != "known" and fact.value is not None:
                return False
            if not set(fact.evidence_refs).issubset(evidence_ids):
                return False
            if not set(fact.freshness_refs).issubset(freshness_ids):
                return False

        for signal in result.signals:
            if not set(signal.fact_refs).issubset(fact_id_set):
                return False
            if not set(signal.evidence_refs).issubset(evidence_ids):
                return False

        for recommendation in result.recommendations:
            if not set(recommendation.signal_refs).issubset(signal_id_set):
                return False
            if not set(recommendation.evidence_refs).issubset(evidence_ids):
                return False
            if (
                recommendation.write_mode == "proposal_required"
                and not recommendation.confirmation_required
            ):
                return False

        return True

    @staticmethod
    def _safe_exception_code(exc: Exception) -> str:
        if isinstance(exc, sqlite3.Error):
            return "DATA_ACCESS_FAILED"
        if isinstance(exc, (TypeError, ValueError)):
            return "DOMAIN_VALIDATION_FAILED"
        return "USE_CASE_EXECUTION_FAILED"

    def get_result(self, execution_id: str) -> UseCaseResult | None:
        trace = repository.get_execution_trace(execution_id)
        if trace is None:
            return None
        return UseCaseResult(
            status=trace["status"],
            evidence=trace["evidence_summary"],
            freshness=trace["freshness_summary"],
            warnings=trace["warning_codes"],
            proposed_writes=[{}] * trace["proposed_write_count"],
            execution_metadata={
                "execution_id": trace["execution_id"],
                "use_case_id": trace["use_case_id"],
                "operation": trace["operation"],
                "actor": trace["actor"],
                "correlation_id": trace["correlation_id"] or None,
                "started_at": trace["started_at"],
                "finished_at": trace["finished_at"],
                "duration_ms": trace["duration_ms"],
                "outcome": trace["status"],
                "trace_summary": True,
            },
        )

    @staticmethod
    def _finalize(
        result: UseCaseResult,
        request: UseCaseRequest,
        started_at: datetime,
        started_clock: float,
        *,
        read_only: bool,
    ) -> UseCaseResult:
        finished_at = datetime.now(timezone.utc)
        metadata = dict(result.execution_metadata) or new_execution_metadata(request)
        metadata.update(
            {
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": round((perf_counter() - started_clock) * 1000),
                "outcome": result.status,
                "read_only": read_only,
            }
        )
        result.execution_metadata = metadata
        repository.save_execution_trace(
            {
                "execution_id": metadata["execution_id"],
                "use_case_id": request.use_case_id,
                "operation": request.operation,
                "actor": request.actor,
                "correlation_id": request.correlation_id,
                "status": result.status,
                "started_at": metadata["started_at"],
                "finished_at": metadata["finished_at"],
                "duration_ms": metadata["duration_ms"],
                "evidence_summary": [
                    {key: item.get(key) for key in ("evidence_id", "source_kind", "entity_kind", "record_count", "applied_filters")}
                    for item in result.evidence
                ],
                "freshness_summary": result.freshness,
                "warning_codes": [
                    item.get("code", "WARNING") if isinstance(item, dict) else item
                    for item in result.warnings
                ],
                "proposed_write_count": len(result.proposed_writes),
            }
        )
        return result


class ResultContractInvalidError(Exception):
    """Internal sentinel for a handler result that must fail closed."""
