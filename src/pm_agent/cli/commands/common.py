"""Shared CLI helpers."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def spin(message: str) -> Progress:
    return Progress(SpinnerColumn(), TextColumn(message), transient=True)


def format_age_hours(age_hours: Optional[float]) -> str:
    if age_hours is None:
        return "-"
    if age_hours >= 48:
        return f"{age_hours / 24:.1f}d"
    return f"{age_hours:.1f}h"
