import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_readme_commands_and_required_assets_match_cli(self):
        readme = (REPO / "README.md").read_text()
        cli = (REPO / "tools" / "cli.py").read_text()
        for command in ("onboard", "save", "rebuild", "search", "migrate", "doctor", "rollback"):
            self.assertIn(f'"{command}"', cli)
            self.assertIn(f"mogoj {command}", readme)
        self.assertTrue((REPO / "docs" / "assets" / "terminal-demo.gif").is_file())
        self.assertTrue((REPO / "examples" / "fictional-store" / ".mogoj" / "store.json").is_file())
        self.assertIn("not a generic vector database", readme)
        self.assertIn("Honest beta limitations", readme)


if __name__ == "__main__":
    unittest.main()
