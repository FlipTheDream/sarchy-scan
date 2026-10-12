import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scan_agent  # noqa: E402


class VerdictTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(scan_agent.verdict_for(0), ("✅ CLEAN", scan_agent.EXIT_CLEAN))

    def test_infected(self):
        self.assertEqual(scan_agent.verdict_for(1), ("⚠️ INFECTED / VERIFY", scan_agent.EXIT_INFECTED))

    def test_error(self):
        self.assertEqual(scan_agent.verdict_for(2), ("❌ SCAN ERROR", scan_agent.EXIT_ERROR))


class ReportTests(unittest.TestCase):
    def test_report_strips_workdir_paths(self):
        assets = "/tmp/scan_agent_abc/assets"
        logs = f"{assets}/app.zip: OK\n{assets}/evil.exe: Win.Test FOUND\n"
        report = scan_agent.build_report("owner/repo", "v1.0.0", "✅ CLEAN", logs, assets)

        self.assertIn("- **Repository:** owner/repo", report)
        self.assertIn("- **Target Release:** `v1.0.0`", report)
        self.assertIn("assets:/app.zip: OK", report)
        self.assertIn("assets:/evil.exe: Win.Test FOUND", report)
        self.assertNotIn("/tmp/scan_agent_abc", report)
        self.assertIn("*Report generated autonomously by Sarchy-Scan execution.*", report)


if __name__ == "__main__":
    unittest.main()
