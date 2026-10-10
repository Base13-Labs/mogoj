import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "mogoj"


class ClaudePluginTests(unittest.TestCase):
    def test_manifest_marketplace_and_bounded_core(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(manifest["name"], "mogoj")
        self.assertEqual(marketplace["plugins"][0]["name"], "mogoj")
        self.assertFalse((PLUGIN / "hooks").exists())
        self.assertFalse((PLUGIN / ".mcp.json").exists())
        skills = list((PLUGIN / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 4)
        for skill in skills:
            content = skill.read_text()
            self.assertIn("mogoj", content.lower())
            self.assertNotIn("~/code/", content)
            self.assertNotIn("[TODO", content)

    @unittest.skipUnless(shutil.which("claude"), "Claude Code is not installed")
    def test_official_validator_accepts_plugin_and_marketplace(self):
        for path in (PLUGIN, REPO):
            result = subprocess.run(
                ["claude", "plugin", "validate", str(path)],
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("claude"), "Claude Code is not installed")
    def test_install_disable_enable_and_uninstall_preserve_store(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = base / "claude"
            store = base / "memory"
            store.mkdir()
            memory = store / "memory.md"
            memory.write_text("preserve me\n")
            env = dict(__import__("os").environ, CLAUDE_CONFIG_DIR=str(config))
            commands = (
                ["claude", "plugin", "marketplace", "add", str(REPO)],
                ["claude", "plugin", "install", "mogoj@base13-labs", "--scope", "user"],
                ["claude", "plugin", "disable", "mogoj@base13-labs", "--scope", "user"],
                ["claude", "plugin", "enable", "mogoj@base13-labs", "--scope", "user"],
                ["claude", "plugin", "uninstall", "mogoj@base13-labs", "--scope", "user"],
            )
            for command in commands:
                result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(memory.read_text(), "preserve me\n")


if __name__ == "__main__":
    unittest.main()
