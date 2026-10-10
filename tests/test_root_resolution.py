import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SEARCH = REPO / "tools" / "search.py"
INGEST = REPO / "tools" / "ingest.py"


class RootResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def store(self, name):
        root = self.base / name
        (root / ".mogoj").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / ".mogoj" / "store.json").write_text('{"version": 1}\n')
        return root

    def run_tool(self, tool, *args, cwd=None, root_env=None):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env.pop("MOGOJ_ROOT", None)
        if root_env is not None:
            env["MOGOJ_ROOT"] = str(root_env)
        return subprocess.run(
            [sys.executable, str(tool), *map(str, args)],
            cwd=str(cwd or REPO), env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_explicit_root_precedes_environment(self):
        explicit = self.store("explicit")
        configured = self.store("configured")
        result = self.run_tool(
            SEARCH, "--root", explicit, "--verbose", "anything",
            root_env=configured,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Mogoj root: {explicit.resolve()}", result.stderr)

    def test_marker_resolves_from_store_and_subdirectory(self):
        store = self.store("memory")
        nested = store / "docs" / "projects"
        nested.mkdir(parents=True)
        for cwd in (store, nested):
            result = self.run_tool(SEARCH, "--verbose", "anything", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(store.resolve()), result.stderr)

    def test_symlink_is_normalized(self):
        store = self.store("real")
        link = self.base / "linked"
        try:
            link.symlink_to(store, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        result = self.run_tool(SEARCH, "--verbose", "anything", cwd=link)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Mogoj root: {store.resolve()}", result.stderr)

    def test_unrelated_and_engine_repositories_fail_closed(self):
        unrelated = self.base / "unrelated"
        unrelated.mkdir()
        (unrelated / ".git").mkdir()
        (unrelated / "CLAUDE.md").write_text("not a Mogoj store\n")
        for cwd in (unrelated, REPO):
            result = self.run_tool(SEARCH, "anything", cwd=cwd)
            self.assertEqual(result.returncode, 4)
            self.assertIn("No initialized Mogoj store found", result.stderr)

    def test_unset_environment_does_not_guess(self):
        result = self.run_tool(SEARCH, "anything", cwd=self.base)
        self.assertEqual(result.returncode, 4)

    def test_traversal_write_is_rejected(self):
        store = self.store("safe")
        source = self.base / "source.md"
        source.write_text("# source\n")
        result = self.run_tool(
            INGEST, "--root", store, "import", source,
            "--dest", "../escaped.md",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((self.base / "escaped.md").exists())


if __name__ == "__main__":
    unittest.main()
