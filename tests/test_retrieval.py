import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MIGRATE = REPO / "tools" / "migrate.py"
FIXTURE = REPO / "tests" / "fixtures" / "base13-brain"


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"
        shutil.copytree(FIXTURE, self.root)
        env = os.environ.copy()
        env["MOGOJ_ROOT"] = str(self.root)
        subprocess.run(
            [sys.executable, str(MIGRATE), "migrate"], env=env,
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.old_root = os.environ.get("MOGOJ_ROOT")
        os.environ["MOGOJ_ROOT"] = str(self.root)
        sys.path.insert(0, str(REPO / "tools"))

    def tearDown(self):
        if self.old_root is None:
            os.environ.pop("MOGOJ_ROOT", None)
        else:
            os.environ["MOGOJ_ROOT"] = self.old_root
        self.temp.cleanup()

    def _load_retrieve(self):
        for module in ("common", "config", "retrieve"):
            sys.modules.pop(module, None)
        import retrieve
        return retrieve

    def test_configured_character_budget_is_never_exceeded(self):
        retrieve = self._load_retrieve()
        for budget in (40, 120, 315, 800):
            result = retrieve.retrieve("migration", char_budget=budget)
            self.assertLessEqual(result["context_chars"], budget)
            self.assertTrue(result["within_budget"])

    def test_results_are_diverse_cited_and_full_content_is_opt_in(self):
        retrieve = self._load_retrieve()
        result = retrieve.retrieve("existing", token_budget=300)
        paths = [item["path"] for item in result["results"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn(":L", result["context"])
        self.assertNotIn("Full documents (explicitly requested)", result["context"])

    def test_no_result_behavior_is_clear_and_bounded(self):
        retrieve = self._load_retrieve()
        result = retrieve.retrieve("wordthatcannotpossiblyexist", char_budget=100)
        self.assertIn("No result met", result["context"])
        self.assertLessEqual(result["context_chars"], 100)


if __name__ == "__main__":
    unittest.main()
