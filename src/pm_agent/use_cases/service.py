"""Shared contracts for PM use-case services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Shared I/O contracts
# ──────────────────────────────────────────────

class ServiceRequest(BaseModel):
    """Base request passed to a use-case service."""

    query: str = ""
    context: dict[str, Any] = {}
    project_id: str | None = None
    member_ids: list[str] = []


class ScoreBreakdown(BaseModel):
    """Per-dimension scores returned with allocation recommendations."""

    skill: float = 0.0
    availability: float = 0.0
    track_record: float = 0.0
    team_fit: float = 0.0
    total: float = 0.0
    blocked: bool = False
    blocked_reason: str = ""


class ServiceResponse(BaseModel):
    """Common response returned by a use-case service."""

    success: bool
    data: dict[str, Any] = {}
    message: str = ""
    decision_id: int | None = None   # set when a Decision Log entry was created


class UseCaseRequest(BaseModel):
    """Stable application-level request accepted by every registered use case."""

    contract_version: str = "1.0"
    use_case_id: str = ""
    operation: str = "query"
    actor: str = "local-user"
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_output: str = "default"
    confirmation_token: str | None = None
    correlation_id: str | None = None


class UseCaseResult(BaseModel):
    """Stable, renderer-neutral result returned by the use-case executor."""

    contract_version: str = "1.0"
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    freshness: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    proposed_writes: list[dict[str, Any]] = Field(default_factory=list)
    execution_metadata: dict[str, Any] = Field(default_factory=dict)


def new_execution_metadata(request: UseCaseRequest) -> dict[str, Any]:
    """Create the trace fields that are common to all use-case executions."""

    return {
        "execution_id": str(uuid4()),
        "contract_version": request.contract_version,
        "use_case_id": request.use_case_id,
        "operation": request.operation,
        "actor": request.actor,
        "requested_output": request.requested_output,
        "correlation_id": request.correlation_id,
        "read_only": request.confirmation_token is None,
    }


# ──────────────────────────────────────────────
# Base class
# ──────────────────────────────────────────────

class BaseService(ABC):
    """
    Minimal contract shared by service classes.

    CLI commands usually call service-specific methods directly.
    ``run()`` exists for generic routing or future automation layers.
    """

    supported_requests: list[str] = []   # filled by each subclass

    @abstractmethod
    def run(self, inp: ServiceRequest) -> ServiceResponse:
        ...

    def supports(self, request_name: str) -> bool:
        return request_name in self.supported_requests
