import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "mogoj"


class CodexPluginTests(unittest.TestCase):
    def test_portable_manifest_assets_and_marketplace(self):
        manifest = json.loads((PLUGIN / "plugin.json").read_text())
        fallback = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
        marketplace = json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text())
        self.assertEqual(manifest, fallback)
        self.assertEqual(manifest["name"], "mogoj")
        self.assertEqual(manifest["version"], "0.1.0-beta.1")
        for key in ("composerIcon", "logo"):
            asset = PLUGIN / manifest["interface"][key]
            self.assertTrue(asset.is_file(), asset)
            self.assertGreater(asset.stat().st_size, 1000)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_skills_use_bounded_cli_without_remote_dependencies(self):
        manifest = json.loads((PLUGIN / "plugin.json").read_text())
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("hooks", manifest)
        search = (PLUGIN / "skills" / "mogoj-search" / "SKILL.md").read_text()
        self.assertIn("mogoj --json search", search)
        self.assertIn("bounded", search.lower())
        self.assertIn("path:Lx-Ly", search)


if __name__ == "__main__":
    unittest.main()
