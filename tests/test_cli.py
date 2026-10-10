import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "bin" / "mogoj"


class CliJourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "first-store"
        self.env = os.environ.copy()
        self.env["HOME"] = str(Path(self.temp.name) / "home")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(self.root), *args], env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if check and result.returncode:
            self.fail(result.stderr or result.stdout)
        return result

    def test_first_time_init_save_search_and_doctor(self):
        initialized = self.run_cli("--json", "init")
        self.assertTrue(json.loads(initialized.stdout)["ok"])
        saved = self.run_cli(
            "--json", "save", "SQLite keeps search local and private.",
            "--title", "Local search", "--type", "decision",
        )
        self.assertTrue(json.loads(saved.stdout)["path"].endswith("local-search.md"))
        self.run_cli("rebuild")
        searched = self.run_cli("--json", "search", "SQLite local")
        payload = json.loads(searched.stdout)
        self.assertTrue(payload["within_budget"])
        self.assertIn("docs/decisions", payload["context"])
        doctor = self.run_cli("--json", "doctor")
        self.assertTrue(json.loads(doctor.stdout)["ok"])

    def test_help_has_copy_paste_examples_and_version_is_json(self):
        help_result = subprocess.run([sys.executable, str(CLI), "--help"], text=True, stdout=subprocess.PIPE)
        self.assertIn("mogoj init", help_result.stdout)
        initialized = self.run_cli("init")
        self.assertIn("Mogoj is ready", initialized.stdout)
        version = self.run_cli("--json", "version")
        self.assertEqual(json.loads(version.stdout)["version"], "0.1.0-beta.1")

    def test_store_path_with_spaces_and_unicode(self):
        self.root = Path(self.temp.name) / "Memory Store মগজ space"
        self.run_cli("init")
        self.run_cli("save", "Unicode paths work", "--title", "বাংলা memory")
        self.run_cli("rebuild")
        result = self.run_cli("--json", "search", "Unicode")
        self.assertTrue(json.loads(result.stdout)["within_budget"])


if __name__ == "__main__":
    unittest.main()
