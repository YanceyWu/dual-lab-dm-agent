from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest
from typer.testing import CliRunner

from pm_agent.cli.app import app
from scripts.import_from_excel import load_excel


def _write_distribution_workbook(path: Path, sheet_name: str) -> None:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(
        [
            "SYNTHETIC_DATASET_V1",
            "Source",
            "Team",
            "Staff",
            "Project",
            "Role",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
            "Location",
            "Manager",
            "Cost Centre",
            "Notes",
            "Status",
        ]
    )
    worksheet.append(
        [
            "SYNTHETIC_DATASET_V1",
            "fictional",
            "Sample Team",
            "Alex Example - 990001",
            "Project Atlas (9901001)",
            "Delivery Lead",
            *([0.5] * 12),
            "Example",
            "Manager Example",
            "SYN-001",
            "Fictional record",
            "Active",
        ]
    )
    workbook.save(path)


def test_distribution_import_uses_column_contract_not_team_sheet_name(tmp_path: Path) -> None:
    workbook_path = tmp_path / "distribution.xlsx"
    _write_distribution_workbook(workbook_path, "Any Team Export")

    records = load_excel(str(workbook_path))

    assert len(records) == 1
    assert records[0]["staff_raw"] == "Alex Example - 990001"
    assert records[0]["project_raw"] == "Project Atlas (9901001)"


def test_distribution_import_rejects_unknown_layout(tmp_path: Path) -> None:
    workbook_path = tmp_path / "unknown.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active.title = "Unknown"
    workbook.save(workbook_path)

    with pytest.raises(ValueError, match="No distribution worksheet"):
        load_excel(str(workbook_path))


def test_portable_connector_validation_is_redacted_and_offline() -> None:
    result = CliRunner().invoke(app, ["connector", "validate", "--portable"])

    assert result.exit_code == 0
    assert "runtime_configuration: not inspected" in result.stdout
    assert "network: disabled" in result.stdout
    assert "http://" not in result.stdout
    assert "https://" not in result.stdout
    assert "/" + "Users/" not in result.stdout
