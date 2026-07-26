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
