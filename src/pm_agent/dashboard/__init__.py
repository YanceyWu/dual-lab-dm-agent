"""Dashboard package for the PM agent."""

from __future__ import annotations

from typing import Any

__all__ = ["app", "serve"]


def __getattr__(name: str) -> Any:
    if name == "app":
        from pm_agent.dashboard.server import app

        return app
    if name == "serve":
        from pm_agent.dashboard.server import serve

        return serve
    raise AttributeError(name)
