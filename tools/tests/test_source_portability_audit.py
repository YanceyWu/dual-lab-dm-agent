from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.audit_source_portability import audit, inspect_text


class SourcePortabilityAuditTests(unittest.TestCase):
    def test_reports_categories_without_match_values(self) -> None:
        findings = inspect_text(
            'url = "https://internal.example.test"\nemail = "person@example.test"\nid = "1234567"',
            "module.py",
        )
        categories = {finding.category for finding in findings}
        self.assertEqual(
            categories,
            {
                "concrete-url-in-portable-source",
                "non-synthetic-email-domain",
                "hard-coded-numeric-identifier",
            },
        )
        self.assertTrue(all(finding.path == "module.py" for finding in findings))

    def test_accepts_reserved_synthetic_values(self) -> None:
        findings = inspect_text(
            'url = "https://jira.example.invalid"\nemail = "person@example.invalid"\nid = "9901001"',
            "module.py",
        )
        self.assertEqual(findings, set())

    def test_accepts_template_urls_without_treating_them_as_concrete(self) -> None:
        findings = inspect_text('url = "https://[template-host]/path"', "module.py")
        self.assertEqual(findings, set())

    def test_accepts_public_vendor_protocol_urls_and_zero_color_values(self) -> None:
        findings = inspect_text(
            'oauth = "https://auth.atlassian.com/oauth/token"\ncolor = "000000"',
            "module.py",
        )
        self.assertEqual(findings, set())

    def test_classifies_company_config_and_history_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            company = root / "configs" / "company" / "baseline.yaml"
            history = root / "docs" / "history" / "old.md"
            uat = root / "docs" / "current" / "PM_AGENT_UAT_RESULTS.md"
            company.parent.mkdir(parents=True)
            history.parent.mkdir(parents=True)
            uat.parent.mkdir(parents=True)
            company.write_text("enabled: false", encoding="utf-8")
            history.write_text("historical", encoding="utf-8")
            uat.write_text("internal validation", encoding="utf-8")

            findings = audit(root)

        categories = {(finding.path, finding.category) for finding in findings}
        self.assertIn(("configs/company/baseline.yaml", "company-configuration-unit"), categories)
        self.assertIn(("docs/history/old.md", "historical-documentation-unit"), categories)
        self.assertIn(
            ("docs/current/PM_AGENT_UAT_RESULTS.md", "internal-validation-artifact"),
            categories,
        )

    def test_portable_only_audit_skips_internal_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            internal = root / "configs" / "company" / "baseline.yaml"
            portable = root / "module.py"
            internal.parent.mkdir(parents=True)
            internal.write_text('url: "https://internal.example.test"', encoding="utf-8")
            portable.write_text(
                'url = "https://api.atlassian.com/ex/jira/990001"',
                encoding="utf-8",
            )

            findings = audit(root, include_internal=False)

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
