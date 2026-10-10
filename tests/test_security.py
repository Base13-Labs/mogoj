import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "bin" / "mogoj"


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"
        self.env = os.environ.copy()
        self.env["HOME"] = str(Path(self.temp.name) / "home")
        subprocess.run([sys.executable, str(CLI), "--root", str(self.root), "init"], env=self.env, check=True,
                       stdout=subprocess.PIPE, text=True)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "--root", str(self.root), *args], env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_secret_is_not_saved_or_leaked_in_error(self):
        secret = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"
        result = self.run_cli("save", f"token={secret}")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret, result.stderr)
        self.assertEqual(list((self.root / "docs" / "notes").glob("*.md")), [])

    def test_redaction_replaces_secret(self):
        secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
        result = self.run_cli("save", f"credential {secret}", "--title", "safe", "--redact")
        self.assertEqual(result.returncode, 0, result.stderr)
        content = next((self.root / "docs" / "notes").glob("*.md")).read_text()
        self.assertNotIn(secret, content)
        self.assertIn("REDACTED", content)

    def test_symlink_overwrite_is_refused(self):
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("private\n")
        day = __import__("datetime").date.today().isoformat()
        destination = self.root / "docs" / "notes" / f"{day}-linked.md"
        try:
            destination.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        result = self.run_cli("save", "new", "--title", "linked", "--force")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(outside.read_text(), "private\n")

    def test_new_files_and_backups_are_private(self):
        saved = self.run_cli("save", "private memory", "--title", "permissions")
        self.assertEqual(saved.returncode, 0, saved.stderr)
        memory = next((self.root / "docs" / "notes").glob("*.md"))
        if os.name != "nt":
            self.assertEqual(memory.stat().st_mode & 0o777, 0o600)
        backup = self.run_cli("backup")
        self.assertEqual(backup.returncode, 0, backup.stderr)
        archive = next((self.root / ".mogoj" / "backups").glob("*.zip"))
        if os.name != "nt":
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
