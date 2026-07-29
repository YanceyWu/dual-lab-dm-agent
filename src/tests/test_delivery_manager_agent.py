from pathlib import Path

from pm_agent.use_cases import use_case_executor


AGENT_FILE = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "agents"
    / "delivery-manager.agent.md"
)


def test_delivery_manager_agent_routes_every_registered_use_case() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")

    for descriptor in use_case_executor.list_descriptors():
        assert descriptor.use_case_id in content


def test_delivery_manager_agent_keeps_a_bounded_tool_surface() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")
    frontmatter = content.split("---", 2)[1]

    assert "  - execute/runInTerminal" in frontmatter
    assert "agents: []" in frontmatter
    assert "disable-model-invocation: true" in frontmatter
    assert "edit/" not in frontmatter


def test_delivery_manager_agent_preserves_intelligence_result_priority() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")

    facts_position = content.index("`facts` establish what is known")
    signals_position = content.index(
        "`signals` establish deterministic rule outcomes"
    )
    recommendations_position = content.index(
        "`recommendations` establish supported next actions"
    )
    qualification_position = content.index(
        "`evidence`, `freshness`, `assumptions`, and `warnings` qualify"
    )

    assert (
        facts_position
        < signals_position
        < recommendations_position
        < qualification_position
    )
    assert "an empty `recommendations` array remains empty" in content
    assert "Do not create a missing fact, signal, or recommendation." in content


def test_delivery_manager_agent_keeps_rag_configuration_explicit_and_separate() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")

    assert "`rag-config-preview`" in content
    assert "never infer labels, precedence, project IDs, or removal intent" in content
    assert "A confirmed RAG configuration creates only a new rule version" in content
    assert "separately previews and confirms a project-health reconciliation" in content
