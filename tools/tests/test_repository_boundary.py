from __future__ import annotations

import unittest

from tools.check_repository_boundary import (
    normalize_path,
    private_reason,
    repository_reason,
    scan_paths,
)


class RepositoryBoundaryTests(unittest.TestCase):
    def test_normalizes_common_relative_path_shapes(self) -> None:
        self.assertEqual(normalize_path(r".\src\data\pm.db"), "src/data/pm.db")

    def test_blocks_private_runtime_directories(self) -> None:
        blocked = (
            "src/data/pm.db",
            "src/data-feed/latest.csv",
            "src/.auth/session.json",
            "src/exports/report.csv",
            "src/configs/company/baseline.yaml",
            "src/docs/history/legacy-reference.md",
            "src/docs/current/PM_AGENT_UAT_RESULTS.md",
            "company-data/snapshot.json",
            "raw-exports/issues.csv",
        )
        for path in blocked:
            with self.subTest(path=path):
                self.assertIsNotNone(private_reason(path))

    def test_blocks_credentials_logs_and_databases_by_default(self) -> None:
        blocked = (".env", ".env.local", "runtime.log", "tmp/team.sqlite3", "backup.db-wal")
        for path in blocked:
            with self.subTest(path=path):
                self.assertIsNotNone(private_reason(path))

    def test_allows_sanitized_sample_data_and_source_code(self) -> None:
        allowed = (
            "src/sample-data/demo/sample_pm.db",
            "src/sample-data/csv/people.csv",
            "src/pm_agent/services/resource_planning.py",
            "src/.env.example",
            "architecture/04_COPILOT_LOCAL_AGENT_ARCHITECTURE.md",
        )
        for path in allowed:
            with self.subTest(path=path):
                self.assertIsNone(private_reason(path))

    def test_scan_reports_source_without_reading_files(self) -> None:
        violations = scan_paths(("src/data/pm.db", "architecture/README.md"), "tracked")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, "src/data/pm.db")
        self.assertEqual(violations[0].source, "tracked")

    def test_approved_runtime_source_is_transferable(self) -> None:
        runtime_path = "src/pm_agent/use_cases/service.py"
        self.assertIsNone(repository_reason(runtime_path, "staged"))
        self.assertIsNone(repository_reason(runtime_path, "tracked"))
        self.assertIsNone(repository_reason(runtime_path, "untracked-and-not-ignored"))

    def test_approved_synthetic_sample_path_is_transferable(self) -> None:
        sample_path = "src/sample-data/demo/sample_pm.db"
        self.assertIsNone(repository_reason(sample_path, "staged"))


if __name__ == "__main__":
    unittest.main()
