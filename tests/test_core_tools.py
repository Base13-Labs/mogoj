import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "bin" / "mogoj"
TOOLS = REPO / "tools"


class CoreToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "Store with space মগজ"
        self.env = os.environ.copy()
        self.env["HOME"] = str(Path(self.temp.name) / "offline-home")
        self.env["HTTP_PROXY"] = "http://127.0.0.1:1"
        self.env["HTTPS_PROXY"] = "http://127.0.0.1:1"
        self.run_cli("init")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(self.root), *args],
            env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if check and result.returncode:
            self.fail(result.stderr or result.stdout)
        return result

    def run_tool(self, name, *args, check=True):
        result = subprocess.run(
            [sys.executable, str(TOOLS / name), "--root", str(self.root), *args],
            env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if check and result.returncode:
            self.fail(result.stderr or result.stdout)
        return result

    def test_index_graph_ram_and_ingestion_lifecycle(self):
        external = Path(self.temp.name) / "import me.md"
        external.write_text("# Linked project\n\n**shared-topic** decision\n")
        self.run_tool("ingest.py", "import", external, "--type", "project")
        self.run_cli("save", "shared-topic context", "--title", "Second", "--type", "decision")
        self.run_tool("index.py", "build", "--sync")
        queried = self.run_tool("index.py", "query", "shared-topic")
        self.assertIn("doc(s)", queried.stdout)
        self.run_tool("graph.py", "build")
        clusters = self.run_tool("graph.py", "clusters")
        self.assertIn("cluster", clusters.stdout.lower())
        self.run_tool("ram.py", "clear", "--force")
        self.run_tool("ram.py", "archive", "test-session", "--clear")
        archives = self.run_tool("ram.py", "list")
        self.assertIn("test-session", archives.stdout)

    def test_corrupt_index_fails_cleanly_and_backup_survives(self):
        index = self.root / "data" / "index" / "context-index.json"
        index.write_text("{not json")
        result = self.run_cli("rebuild", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(list((self.root / ".mogoj" / "backups").glob("*.zip")))

    def test_concurrent_saves_and_reads(self):
        self.run_cli("save", "concurrency seed", "--title", "Seed")
        self.run_cli("rebuild")

        def save(index):
            return self.run_cli("save", f"parallel memory {index}", "--title", f"Parallel {index}", check=False)

        with ThreadPoolExecutor(max_workers=4) as pool:
            writes = list(pool.map(save, range(4)))
        self.assertTrue(all(result.returncode == 0 for result in writes), [r.stderr for r in writes])
        found = self.run_cli("--json", "search", "parallel memory")
        self.assertGreaterEqual(len(json.loads(found.stdout)["results"]), 1)

    @unittest.skipIf(os.name == "nt", "POSIX permissions are not enforced by chmod on Windows")
    def test_read_only_store_has_actionable_failure(self):
        notes = self.root / "docs" / "notes"
        notes.chmod(0o500)
        try:
            result = self.run_cli("save", "cannot write", "--title", "readonly", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("could not continue", result.stderr.lower())
        finally:
            notes.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
