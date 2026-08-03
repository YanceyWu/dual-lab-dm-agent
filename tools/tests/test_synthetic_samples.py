from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.check_synthetic_samples import MARKER, validate_sqlite, validate_text


class SyntheticSampleTests(unittest.TestCase):
    def test_accepts_reserved_synthetic_values(self) -> None:
        text = (
            f"{MARKER} Alex Example 990001 Project Atlas 9901001 "
            "alex.example@example.invalid https://jira.example.invalid/boards/9901001"
        )
        self.assertEqual(validate_text(text, "sample.csv"), [])

    def test_requires_marker(self) -> None:
        findings = validate_text("Alex Example 990001", "sample.csv")
        self.assertTrue(any("marker" in item.reason for item in findings))

    def test_rejects_non_reserved_email_domain(self) -> None:
        findings = validate_text(f"{MARKER} person@corp.test", "sample.json")
        self.assertTrue(any("email domain" in item.reason for item in findings))

    def test_rejects_non_reserved_url_host(self) -> None:
        findings = validate_text(f"{MARKER} https://tracker.corp.test/item", "sample.csv")
        self.assertTrue(any("URL host" in item.reason for item in findings))

    def test_rejects_numeric_identifiers_outside_reserved_range(self) -> None:
        findings = validate_text(f"{MARKER} employee 450101", "sample.csv")
        self.assertTrue(any("numeric ID" in item.reason for item in findings))

    def test_sqlite_ignores_timestamp_microseconds_when_scanning_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo" / "sample_pm.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "CREATE TABLE employees (id TEXT, notes TEXT)"
                )
                connection.execute(
                    "CREATE TABLE execution_traces (started_at TEXT, finished_at TEXT)"
                )
                connection.execute(
                    "INSERT INTO employees (id, notes) VALUES (?, ?)",
                    ("member-synthetic-001", f"{MARKER} sample employee"),
                )
                connection.execute(
                    "INSERT INTO execution_traces (started_at, finished_at) VALUES (?, ?)",
                    (
                        "2026-08-03T08:37:43.931759+00:00",
                        "2026-08-03T08:37:43.945242+00:00",
                    ),
                )
                connection.commit()
            finally:
                connection.close()
            self.assertEqual(validate_sqlite(db_path, "demo/sample_pm.db"), [])

    def test_sqlite_rejects_non_reserved_numeric_identifier_in_id_like_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "demo" / "sample_pm.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(db_path)
            try:
                connection.execute(
                    "CREATE TABLE employees (wd_id TEXT, notes TEXT)"
                )
                connection.execute(
                    "INSERT INTO employees (wd_id, notes) VALUES (?, ?)",
                    ("450101", f"{MARKER} sample employee"),
                )
                connection.commit()
            finally:
                connection.close()
            findings = validate_sqlite(db_path, "demo/sample_pm.db")
            self.assertTrue(any("numeric ID" in item.reason for item in findings))


if __name__ == "__main__":
    unittest.main()
