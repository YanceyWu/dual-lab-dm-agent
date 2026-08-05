"""
domain/scoring.py — Allocation scoring engine.

Design rules:
- Weights are injected, never hardcoded.
- Hard rules produce blocked=True (zero score, excluded from results).
- Each dimension is a separate function → easy to test and extend.
- No I/O here. All data arrives as plain dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pm_agent.config import HardRules, ScoringWeights


# ──────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────

@dataclass
class ScoringResult:
    member_id: str
    member_name: str
    score: float                          # 0.0 – 1.0
    breakdown: dict[str, float] = field(default_factory=dict)
    blocked: bool = False
    blocked_reason: str = ""
    reason_text: str = ""                 # human-readable explanation


@dataclass
class AllocationOption:
    """One recommended combination of N people."""
    label: str
    members: list[ScoringResult]
    combined_score: float


def calc_availability(current_load: float) -> float:
    """Simple complement: 100% load = 0 availability."""
    return max(0.0, 1.0 - current_load)


def calc_track_record(outcomes: list[str]) -> float:
    """
    outcomes: list of 'success'|'delayed'|'failed' strings from decision_log.
    < 3 records → neutral 0.5 (new member, no penalty).
    """
    if len(outcomes) < 3:
        return 0.5
    success_count = sum(1 for o in outcomes if o == "success")
    return success_count / len(outcomes)


def calc_team_fit(member_active_projects: list[str], target_project_id: str) -> float:
    """Already on the project = 1.0, not on it = 0.3."""
    return 1.0 if target_project_id in member_active_projects else 0.3


# ──────────────────────────────────────────────
# Hard rules
# ──────────────────────────────────────────────

def check_hard_rules(
    member: dict,
    active_projects: list[str],
    rules: HardRules,
) -> tuple[bool, str]:
    """
    Returns (is_blocked, reason).
    Checked in priority order; first match wins.
    """
    load = member.get("current_load", 0.0)
    if load > rules.max_load_threshold:
        return True, f"超负荷（负载 {load:.0%}）"

    proj_count = len(active_projects)
    if proj_count >= rules.max_concurrent_projects:
        return True, f"已有 {proj_count} 个并行项目（上限 {rules.max_concurrent_projects}）"

    if member.get("employee_status") == "on_leave":
        return True, "当前状态：请假"

    return False, ""


# ──────────────────────────────────────────────
# Main scoring entry point
# ──────────────────────────────────────────────

def score_member(
    member: dict,
    active_projects: list[str],
    target_project_id: str,
    task_type: str,
    historical_outcomes: list[str],       # from repository.get_decision_outcomes()
    weights: ScoringWeights,
    rules: HardRules,
) -> ScoringResult:

    # Hard rules first
    blocked, block_reason = check_hard_rules(member, active_projects, rules)
    if blocked:
        return ScoringResult(
            member_id=member["id"],
            member_name=member["name"],
            score=0.0,
            blocked=True,
            blocked_reason=block_reason,
        )

    # Dimension scores
    avail   = calc_availability(member.get("current_load", 0.0))
    track   = calc_track_record(historical_outcomes)
    fit     = calc_team_fit(active_projects, target_project_id)

    # Weighted total
    total = (
        avail * weights.availability_weight
        + track * weights.track_record_weight
        + fit   * weights.team_fit_weight
    )
    total = round(min(total, 1.0), 3)

    breakdown = {
        "availability": round(avail, 3),
        "track_record": round(track, 3),
        "team_fit":     round(fit, 3),
    }

    return ScoringResult(
        member_id=member["id"],
        member_name=member["name"],
        score=total,
        breakdown=breakdown,
        blocked=False,
        blocked_reason=block_reason,
        reason_text=_build_reason(breakdown, member),
    )


def _build_reason(bd: dict[str, float], member: dict) -> str:
    parts: list[str] = []
    avail_pct = bd["availability"]
    load_pct = 1.0 - avail_pct
    parts.append(f"当前负载{load_pct:.0%}")

    if bd["track_record"] >= 0.8:
        parts.append("历史表现优")
    elif bd["track_record"] == 0.5:
        parts.append("暂无历史记录")

    if bd["team_fit"] == 1.0:
        parts.append("已在该项目组")

    return "；".join(parts)


# ──────────────────────────────────────────────
# Combination builder
# ──────────────────────────────────────────────

def build_options(
    scored: list[ScoringResult],
    count: int,
    max_options: int = 3,
) -> list[AllocationOption]:
    """
    Build up to max_options combinations of `count` people from the eligible list.
    Simple greedy: take top N, then swap one person at a time.
    """
    eligible = [s for s in scored if not s.blocked and s.score > 0]
    if len(eligible) < count:
        return []

    options: list[AllocationOption] = []
    labels = ["方案A", "方案B", "方案C"]

    # Option A: top-N by score
    top = eligible[:count]
    options.append(AllocationOption(
        label=labels[0],
        members=top,
        combined_score=round(sum(m.score for m in top) / count, 3),
    ))

    # Option B / C: swap last pick with next candidates
    for i in range(1, min(max_options, len(eligible) - count + 1)):
        alt_members = eligible[: count - 1] + [eligible[count - 1 + i]]
        options.append(AllocationOption(
            label=labels[i],
            members=alt_members,
            combined_score=round(sum(m.score for m in alt_members) / count, 3),
        ))

    return options[:max_options]
