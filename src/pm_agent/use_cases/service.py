"""Shared contracts for PM use-case services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


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
