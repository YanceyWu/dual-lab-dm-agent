from __future__ import annotations

import unittest

from tools.check_synthetic_samples import MARKER, validate_text


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


if __name__ == "__main__":
    unittest.main()
