from __future__ import annotations

from pathlib import Path

from pm_agent.connectors.servicenow import browser_client


def test_default_edge_profile_uses_macos_layout() -> None:
    profile = browser_client._default_edge_profile(
        "darwin",
        Path("/Users/example"),
        None,
    )

    assert profile == Path("/Users/example/Library/Application Support/Microsoft Edge")


def test_default_edge_profile_uses_windows_layout() -> None:
    profile = browser_client._default_edge_profile(
        "win32",
        Path("C:/Users/Example"),
        "C:/Users/Example/AppData/Local",
    )

    assert profile == Path("C:/Users/Example/AppData/Local/Microsoft/Edge/User Data")


def test_default_edge_profile_uses_linux_layout() -> None:
    profile = browser_client._default_edge_profile(
        "linux",
        Path("/home/example"),
        None,
    )

    assert profile == Path("/home/example/.config/microsoft-edge")
