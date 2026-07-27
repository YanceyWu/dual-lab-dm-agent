from __future__ import annotations

from collections.abc import Callable

import pytest

from pm_agent.use_cases.execution import UseCaseDescriptor, UseCaseExecutor
from pm_agent.use_cases.service import (
    IntelligenceFact,
    IntelligenceRecommendation,
    IntelligenceSignal,
    IntelligenceSubject,
    UseCaseRequest,
    UseCaseResult,
)


def _execute(
    isolated_db,
    handler: Callable[[UseCaseRequest], UseCaseResult],
) -> UseCaseResult:
    executor = UseCaseExecutor()
    executor.register(
        UseCaseDescriptor(
            use_case_id="synthetic-intelligence",
            purpose="Validate synthetic intelligence output.",
            parameter_schema={},
        ),
        handler,
    )
    return executor.execute(UseCaseRequest(use_case_id="synthetic-intelligence"))


def _subject() -> IntelligenceSubject:
    return IntelligenceSubject(kind="project", id="project-001")


def _fact(
    *,
    fact_id: str = "fact-001",
    value: object = "amber",
    value_state: str = "known",
    evidence_refs: list[str] | None = None,
    freshness_refs: list[str] | None = None,
    fact_kind: str = "observed",
    rule_version: str | None = None,
) -> IntelligenceFact:
    return IntelligenceFact(
        fact_id=fact_id,
        fact_type="project_health_state",
        fact_kind=fact_kind,
        subject=_subject(),
        value=value,
        value_state=value_state,
        evidence_refs=evidence_refs or [],
        freshness_refs=freshness_refs or [],
        rule_version=rule_version,
    )


def _signal(
    *,
    signal_id: str = "signal-001",
    fact_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
) -> IntelligenceSignal:
    return IntelligenceSignal(
        signal_id=signal_id,
        signal_type="project_health_attention",
        subject=_subject(),
        state="active",
        severity="medium",
        reason_codes=["project_health_amber"],
        fact_refs=fact_refs or [],
        evidence_refs=evidence_refs or [],
        rule_version="health-attention-v1",
    )


def _recommendation(
    *,
    recommendation_id: str = "recommendation-001",
    signal_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    write_mode: str = "advisory",
    confirmation_required: bool = False,
) -> IntelligenceRecommendation:
    return IntelligenceRecommendation(
        recommendation_id=recommendation_id,
        recommendation_type="review_project_health",
        subject=_subject(),
        state="available",
        rationale_codes=["health_attention_active"],
        signal_refs=signal_refs or [],
        evidence_refs=evidence_refs or [],
        write_mode=write_mode,
        confirmation_required=confirmation_required,
    )


def _valid_result() -> UseCaseResult:
    return UseCaseResult(
        status="success",
        evidence=[{"evidence_id": "evidence-001", "source_kind": "synthetic"}],
        freshness=[{"source_id": "source-001", "state": "fresh"}],
        facts=[
            _fact(
                evidence_refs=["evidence-001"],
                freshness_refs=["source-001"],
                fact_kind="derived",
                rule_version="health-state-v1",
            )
        ],
        signals=[
            _signal(
                fact_refs=["fact-001"],
                evidence_refs=["evidence-001"],
            )
        ],
        recommendations=[
            _recommendation(
                signal_refs=["signal-001"],
                evidence_refs=["evidence-001"],
            )
        ],
    )


def _assert_contract_invalid(result: UseCaseResult) -> None:
    assert result.status == "failed"
    assert result.warnings == [{"code": "RESULT_CONTRACT_INVALID"}]
    assert result.data == {}
    assert result.facts == []
    assert result.signals == []
    assert result.recommendations == []


def test_use_case_result_adds_empty_intelligence_defaults() -> None:
    result = UseCaseResult(status="success", data={"legacy": True})

    assert result.contract_version == "1.0"
    assert result.data == {"legacy": True}
    assert result.facts == []
    assert result.signals == []
    assert result.recommendations == []


def test_executor_accepts_valid_and_empty_intelligence_output(isolated_db) -> None:
    valid = _execute(isolated_db, lambda request: _valid_result())
    empty = _execute(
        isolated_db,
        lambda request: UseCaseResult(status="success", data={"legacy": True}),
    )

    assert valid.status == empty.status == "success"
    assert valid.facts[0].fact_id == "fact-001"
    assert valid.signals[0].fact_refs == ["fact-001"]
    assert valid.recommendations[0].signal_refs == ["signal-001"]
    assert empty.facts == empty.signals == empty.recommendations == []


@pytest.mark.parametrize("value_state", ["unknown", "unavailable", "conflicting"])
def test_executor_accepts_non_known_fact_with_null_value(
    isolated_db,
    value_state: str,
) -> None:
    result = _execute(
        isolated_db,
        lambda request: UseCaseResult(
            status="success",
            facts=[_fact(value=None, value_state=value_state)],
        ),
    )

    assert result.status == "success"
    assert result.facts[0].value is None
    assert result.facts[0].value_state == value_state


@pytest.mark.parametrize(
    "facts,signals,recommendations",
    [
        ([_fact(), _fact()], [], []),
        ([_fact()], [_signal(), _signal()], []),
        (
            [_fact()],
            [_signal()],
            [_recommendation(), _recommendation()],
        ),
    ],
)
def test_executor_rejects_duplicate_intelligence_ids(
    isolated_db,
    facts: list[IntelligenceFact],
    signals: list[IntelligenceSignal],
    recommendations: list[IntelligenceRecommendation],
) -> None:
    result = _execute(
        isolated_db,
        lambda request: UseCaseResult(
            status="success",
            facts=facts,
            signals=signals,
            recommendations=recommendations,
        ),
    )

    _assert_contract_invalid(result)


@pytest.mark.parametrize(
    "build_result",
    [
        lambda: UseCaseResult(
            status="success",
            facts=[_fact(evidence_refs=["missing-evidence"])],
        ),
        lambda: UseCaseResult(
            status="success",
            facts=[_fact(freshness_refs=["missing-freshness"])],
        ),
        lambda: UseCaseResult(
            status="success",
            signals=[_signal(fact_refs=["missing-fact"])],
        ),
        lambda: UseCaseResult(
            status="success",
            signals=[_signal(evidence_refs=["missing-evidence"])],
        ),
        lambda: UseCaseResult(
            status="success",
            recommendations=[_recommendation(signal_refs=["missing-signal"])],
        ),
        lambda: UseCaseResult(
            status="success",
            recommendations=[
                _recommendation(evidence_refs=["missing-evidence"])
            ],
        ),
    ],
)
def test_executor_rejects_missing_intelligence_references(
    isolated_db,
    build_result: Callable[[], UseCaseResult],
) -> None:
    result = _execute(isolated_db, lambda request: build_result())

    _assert_contract_invalid(result)
    assert "missing-" not in str(result.model_dump())


@pytest.mark.parametrize(
    "build_result",
    [
        lambda: UseCaseResult(
            status="success",
            facts=[
                _fact(
                    value="must-not-survive",
                    value_state="unknown",
                )
            ],
        ),
        lambda: UseCaseResult(
            status="success",
            facts=[_fact(fact_kind="derived", rule_version=None)],
        ),
        lambda: UseCaseResult(
            status="success",
            recommendations=[
                _recommendation(
                    write_mode="proposal_required",
                    confirmation_required=False,
                )
            ],
        ),
    ],
)
def test_executor_rejects_illegal_intelligence_semantics(
    isolated_db,
    build_result: Callable[[], UseCaseResult],
) -> None:
    result = _execute(isolated_db, lambda request: build_result())

    _assert_contract_invalid(result)
    assert "must-not-survive" not in str(result.model_dump())


@pytest.mark.parametrize("invalid_id", ["", "x" * 129])
def test_executor_rejects_empty_or_overlong_intelligence_id(
    isolated_db,
    invalid_id: str,
) -> None:
    result = _execute(
        isolated_db,
        lambda request: UseCaseResult(
            status="success",
            facts=[_fact(fact_id=invalid_id)],
        ),
    )

    _assert_contract_invalid(result)


def test_executor_revalidates_mutated_handler_result_without_exposing_payload(
    isolated_db,
) -> None:
    damaged = UseCaseResult(status="success")
    damaged.facts.append(
        {
            "fact_id": "fact-secret",
            "fact_type": "project_health_state",
            "fact_kind": "observed",
            "subject": {"kind": "project", "id": "project-secret"},
            "value": "private-config-value",
            "value_state": "not-a-valid-state",
        }
    )

    result = _execute(isolated_db, lambda request: damaged)

    _assert_contract_invalid(result)
    serialized = str(result.model_dump())
    assert "fact-secret" not in serialized
    assert "private-config-value" not in serialized
