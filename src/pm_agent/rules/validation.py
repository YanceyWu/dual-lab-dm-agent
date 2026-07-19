"""
domain/validation.py — Input validation with graceful degradation.

Principle: warn and use a safe default, never crash the recommendation.
Raise only when the data is so broken it would produce a meaningless result.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    valid: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False


def validate_member(m: dict) -> ValidationResult:
    r = ValidationResult()

    if not m.get("id"):
        r.add_error("Employee missing 'id'")
        return r

    if not m.get("name"):
        r.add_error(f"Employee {m['id']} missing 'name'")

    load = m.get("current_load", 0.0)
    if not isinstance(load, (int, float)):
        r.add_warning(f"{m['id']}: current_load is not a number, defaulting to 0")
        m["current_load"] = 0.0
    elif load > 1.0:
        r.add_warning(
            f"{m['id']}: current_load={load:.2f} exceeds 1.0 — check assignments table"
        )
        m["current_load"] = min(load, 1.0)

    skills = m.get("skills", {})
    if not isinstance(skills, dict):
        r.add_warning(f"{m['id']}: skills is not a dict, resetting to empty")
        m["skills"] = {}
    else:
        for skill, score in list(skills.items()):
            if not isinstance(score, (int, float)):
                r.add_warning(f"{m['id']}.skills.{skill}: invalid value, defaulting to 0")
                skills[skill] = 0.0
            elif not 0.0 <= score <= 1.0:
                r.add_warning(
                    f"{m['id']}.skills.{skill}={score} out of [0,1], clamping"
                )
                skills[skill] = max(0.0, min(score, 1.0))

    return r


def validate_project(p: dict) -> ValidationResult:
    r = ValidationResult()

    if not p.get("id"):
        r.add_error("Project missing 'id'")
        return r
    if not p.get("name"):
        r.add_error(f"Project {p['id']} missing 'name'")

    return r


def validate_allocation_request(req: dict) -> ValidationResult:
    r = ValidationResult()

    if not req.get("project_id"):
        r.add_error("Allocation request missing 'project_id'")
    if not req.get("role"):
        r.add_warning("No role specified — skipping team_fit scoring")
    if req.get("count", 1) < 1:
        r.add_error("count must be >= 1")

    required = req.get("required_skills", [])
    if not required:
        r.add_warning("No required_skills specified — skill scoring will be neutral (0.5)")

    return r


def validate_action_item(data: dict) -> ValidationResult:
    r = ValidationResult()

    if not data.get("title", "").strip():
        r.add_error("Action item must have a title")

    priority = data.get("priority", "medium")
    if priority not in {"high", "medium", "low"}:
        r.add_warning(f"Unknown priority '{priority}', defaulting to 'medium'")
        data["priority"] = "medium"

    return r
