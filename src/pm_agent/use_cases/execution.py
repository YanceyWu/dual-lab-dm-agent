"""Application-level use-case execution and registration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

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
                warnings=[f"Unknown use case: {request.use_case_id}"],
                execution_metadata=new_execution_metadata(request),
            ), request, started_at, started_clock)
        descriptor = self._descriptors[request.use_case_id]
        if request.operation not in descriptor.supported_operations:
            return self._finalize(UseCaseResult(
                status="invalid",
                warnings=[
                    f"Operation '{request.operation}' is not supported for "
                    f"use case: {request.use_case_id}"
                ],
                execution_metadata=new_execution_metadata(request),
            ), request, started_at, started_clock)
        try:
            result = handler(request)
        except Exception:
            result = UseCaseResult(
                status="failed",
                warnings=["The local use case could not complete."],
                execution_metadata=new_execution_metadata(request),
            )
        return self._finalize(result, request, started_at, started_clock)

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
    ) -> UseCaseResult:
        finished_at = datetime.now(timezone.utc)
        metadata = dict(result.execution_metadata) or new_execution_metadata(request)
        metadata.update(
            {
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": round((perf_counter() - started_clock) * 1000),
                "outcome": result.status,
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
                "warning_codes": result.warnings,
                "proposed_write_count": len(result.proposed_writes),
            }
        )
        return result
