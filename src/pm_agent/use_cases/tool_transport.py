"""Structured, local tool transport for Copilot and command-line clients."""

from __future__ import annotations

from typing import Any

from pm_agent.use_cases.execution import UseCaseExecutor
from pm_agent.use_cases.service import UseCaseRequest, UseCaseResult, new_execution_metadata


class ToolTransport:
    """Expose safe list, describe, and query operations over one executor."""

    def __init__(self, executor: UseCaseExecutor) -> None:
        self._executor = executor

    def handle(self, request: UseCaseRequest) -> UseCaseResult:
        if request.operation == "list":
            return UseCaseResult(
                status="success",
                data={"use_cases": [self._descriptor_data(item) for item in self._executor.list_descriptors()]},
                execution_metadata=new_execution_metadata(request),
            )
        if request.operation == "describe":
            descriptor = self._executor.describe(request.use_case_id)
            if descriptor is None:
                return self._unavailable(request)
            return UseCaseResult(
                status="success",
                data={"use_case": self._descriptor_data(descriptor)},
                execution_metadata=new_execution_metadata(request),
            )
        if request.operation == "query":
            if not request.use_case_id:
                return self._invalid(request, "A use_case_id is required for query.")
            return self._executor.execute(request)
        return self._invalid(request, f"Unknown tool operation: {request.operation}")

    @staticmethod
    def _descriptor_data(descriptor: Any) -> dict[str, object]:
        return {
            "use_case_id": descriptor.use_case_id,
            "contract_version": descriptor.contract_version,
            "purpose": descriptor.purpose,
            "parameter_schema": descriptor.parameter_schema,
            "supported_operations": list(descriptor.supported_operations),
            "read_only": descriptor.read_only,
            "known_statuses": list(descriptor.known_statuses),
        }

    @staticmethod
    def _invalid(request: UseCaseRequest, warning: str) -> UseCaseResult:
        return UseCaseResult(
            status="invalid",
            warnings=[{"code": "TOOL_REQUEST_INVALID", "message": warning}],
            execution_metadata=new_execution_metadata(request),
        )

    @staticmethod
    def _unavailable(request: UseCaseRequest) -> UseCaseResult:
        return UseCaseResult(
            status="unavailable",
            warnings=[{"code": "USE_CASE_NOT_FOUND", "field": "use_case_id"}],
            execution_metadata=new_execution_metadata(request),
        )
