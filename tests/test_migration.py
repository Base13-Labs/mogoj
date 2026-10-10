import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MIGRATE = REPO / "tools" / "migrate.py"
FIXTURES = REPO / "tests" / "fixtures"


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, name):
        destination = self.base / name
        shutil.copytree(FIXTURES / name, destination)
        return destination

    def run_mogoj(self, root, *args):
        env = os.environ.copy()
        env["HOME"] = str(self.base / "home")
        return subprocess.run(
            [sys.executable, str(MIGRATE), "--root", str(root), *args],
            env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_public_template_migration_is_idempotent_and_preserves_markdown(self):
        root = self.fixture("public-template")
        source = root / "docs" / "sample.md"
        original = source.read_bytes()
        for _ in range(2):
            result = self.run_mogoj(root, "migrate")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), original)
        database = root / "data" / "db" / "mogoj.db"
        connection = sqlite3.connect(str(database))
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("SELECT count(*) FROM docs").fetchone()[0], 1)
        finally:
            connection.close()
        self.assertTrue((root / ".mogoj" / "store.json").is_file())
        self.assertEqual(len(list((root / ".mogoj" / "backups").glob("*.zip"))), 2)

    def test_base13_layout_dry_run_and_interrupted_recovery(self):
        root = self.fixture("base13-brain")
        dry_run = self.run_mogoj(root, "--dry-run", "migrate")
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertIn("Would build database", dry_run.stdout)
        self.assertFalse((root / "data" / "db" / "mogoj.db").exists())

        stage = root / "data" / "db" / "mogoj.db.migrating"
        stage.parent.mkdir(parents=True)
        stage.write_text("interrupted")
        result = self.run_mogoj(root, "migrate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Recovered interrupted migration", result.stdout)
        self.assertFalse(stage.exists())
        state = json.loads((root / ".mogoj" / "migration-state.json").read_text())
        self.assertEqual(state["status"], "complete")

    def test_rollback_restores_generated_state_only(self):
        root = self.fixture("public-template")
        self.assertEqual(self.run_mogoj(root, "migrate").returncode, 0)
        self.assertEqual(self.run_mogoj(root, "backup").returncode, 0)
        database = root / "data" / "db" / "mogoj.db"
        database.write_bytes(b"broken")
        source = root / "docs" / "sample.md"
        source.write_text("# changed after backup\n")
        result = self.run_mogoj(root, "rollback")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Restored: data/db/mogoj.db", result.stdout.replace("\\", "/"))
        self.assertEqual(source.read_text(), "# changed after backup\n")
        connection = sqlite3.connect(str(database))
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
