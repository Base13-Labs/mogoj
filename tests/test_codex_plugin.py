import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
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
        self.assertLessEqual(len(manifest["interface"]["shortDescription"]), 30)
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
        self.assertIn("<plugin-root>/hooks/run.cjs", search)
        self.assertIn("Do not assume a globally installed", search)
        self.assertIn("bounded", search.lower())
        self.assertIn("path:Lx-Ly", search)

    def test_codex_hooks_use_plugin_root_and_bundled_runtime(self):
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
        commands = [
            hook["command"]
            for groups in hooks["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertTrue(all("${PLUGIN_ROOT}/hooks/run.cjs" in command for command in commands))
        self.assertTrue((PLUGIN / "tools" / "auto_memory.py").is_file())
        self.assertEqual(
            (PLUGIN / "tools" / "auto_memory.py").read_bytes(),
            (REPO / "tools" / "auto_memory.py").read_bytes(),
        )
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "memory"
            env = dict(os.environ, PLUGIN_ROOT=str(PLUGIN), MOGOJ_ROOT=str(store))
            result = subprocess.run(
                ["node", str(PLUGIN / "hooks" / "run.cjs"), "session-start"],
                input=json.dumps({"cwd": directory, "session_id": "codex-test"}),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("automatic memory is active", result.stdout)
            self.assertTrue((store / "data" / "db" / "mogoj.db").is_file())

    def test_deterministic_codex_package_is_self_contained(self):
        command = [sys.executable, str(REPO / "scripts" / "build_codex_plugin.py")]
        subprocess.run(command, check=True, stdout=subprocess.PIPE)
        archive = REPO / "dist" / "mogoj-codex-0.1.0-beta.1.zip"
        first = archive.read_bytes()
        subprocess.run(command, check=True, stdout=subprocess.PIPE)
        self.assertEqual(first, archive.read_bytes())
        with zipfile.ZipFile(archive) as package:
            names = set(package.namelist())
        for required in (
            "mogoj/plugin.json",
            "mogoj/.codex-plugin/plugin.json",
            "mogoj/hooks/hooks.json",
            "mogoj/hooks/run.cjs",
            "mogoj/tools/auto_memory.py",
            "mogoj/tools/retrieve.py",
            "mogoj/VERSION",
            "mogoj/config.ini.example",
        ):
            self.assertIn(required, names)
        self.assertFalse(any("claude-hooks.json" in name for name in names))


if __name__ == "__main__":
    unittest.main()
