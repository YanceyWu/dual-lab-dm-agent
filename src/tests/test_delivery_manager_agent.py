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


def test_delivery_manager_agent_rejects_legacy_rag_configuration() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")
    normalized = " ".join(content.split())

    assert "`rag-config-preview`" not in content
    assert "RAG configuration is unavailable" in normalized
    assert "never invoke a legacy mapping configuration path" in normalized
    assert "attempt to confirm a legacy configuration operation" in normalized


def test_delivery_manager_agent_reads_interaction_memory_before_routing() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")
    normalized = " ".join(content.split())

    assert content.index("## Interaction-memory pre-read") < content.index(
        "## Direct routing"
    )
    assert "For every natural-language user request, first run" in content
    assert "`tool query interaction-memory-context` through a shell-safe transport." in content
    assert "--param-stdin message" in content
    assert "`working_context.answer_preferences`" in content
    assert "`working_context.routing_hints`" in content
    assert "`working_context.follow_up_hints`" in content
    assert "`working_context.strategy_flags`" in content
    assert '--param message="<current user turn>"' not in content
    assert "interaction-memory-context --param-stdin message" in content
    assert "override a clear business intent with a different use case" in normalized


def test_delivery_manager_agent_uses_local_pm_and_fails_open_without_memory() -> None:
    content = AGENT_FILE.read_text(encoding="utf-8")
    normalized = " ".join(content.split())

    assert (
        "prefer `src/.venv/bin/pm` if that workspace-relative executable exists; "
        "otherwise use `pm`." in normalized
    )
    assert "Do not splice raw user text directly into a shell-quoted" in normalized
    assert (
        "If the interaction-memory result state is `empty`, `disabled`, "
        "`scope_unknown`, `unknown`, `unavailable`, `invalid`, or `failed`, "
        "continue with the baseline routing and answer flow." in normalized
    )
    assert "Briefly say that local interaction memory was not used only when" in normalized
