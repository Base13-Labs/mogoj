import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugins" / "mogoj"


class ClaudePluginTests(unittest.TestCase):
    def test_manifest_marketplace_and_bounded_core(self):
        manifest = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(manifest["name"], "mogoj")
        self.assertEqual(marketplace["plugins"][0]["name"], "mogoj")
        self.assertEqual(marketplace["plugins"][0]["source"], "./")
        self.assertEqual(manifest["userConfig"]["mode"]["default"], "auto")
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertEqual(
            set(hooks),
            {"SessionStart", "UserPromptSubmit", "Stop", "PreCompact", "SessionEnd"},
        )
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
        result = subprocess.run(
            ["claude", "plugin", "validate", str(REPO)],
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
            env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config))
            setup_commands = (
                ["claude", "plugin", "marketplace", "add", str(REPO)],
                ["claude", "plugin", "install", "mogoj@base13-labs", "--scope", "user"],
            )
            lifecycle_commands = (
                ["claude", "plugin", "disable", "mogoj@base13-labs", "--scope", "user"],
                ["claude", "plugin", "enable", "mogoj@base13-labs", "--scope", "user"],
                ["claude", "plugin", "uninstall", "mogoj@base13-labs", "--scope", "user"],
            )
            for command in setup_commands:
                result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(list(config.rglob("tools/auto_memory.py")))
            self.assertTrue(list(config.rglob("plugins/mogoj/hooks/hooks.json")))
            for command in lifecycle_commands:
                result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(memory.read_text(), "preserve me\n")

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_cross_platform_runner_invokes_bundled_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            store = base / "memory with spaces"
            project = base / "project with spaces"
            project.mkdir()
            payload = json.dumps({
                "hook_event_name": "SessionStart",
                "session_id": "runner-test",
                "cwd": str(project),
                "source": "startup",
            })
            env = dict(
                os.environ,
                CLAUDE_PLUGIN_ROOT=str(REPO),
                MOGOJ_ROOT=str(store),
                MOGOJ_AUTOMATION_MODE="auto",
            )
            result = subprocess.run(
                ["node", str(PLUGIN / "hooks" / "run.cjs"), "session-start"],
                env=env,
                input=payload,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertIn("automatic memory is active", output["hookSpecificOutput"]["additionalContext"])
            self.assertTrue((store / ".mogoj/store.json").is_file())


if __name__ == "__main__":
    unittest.main()
