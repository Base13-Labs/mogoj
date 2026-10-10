import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / "tools" / "auto_memory.py"


class AutomaticMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.store = self.base / "private memory"
        self.project = self.base / "project with spaces"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def hook(self, event, payload, mode="auto", store=None):
        env = os.environ.copy()
        env["MOGOJ_ROOT"] = str(store or self.store)
        env["MOGOJ_AUTOMATION_MODE"] = mode
        result = subprocess.run(
            [sys.executable, str(HOOK), event],
            env=env,
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def transcript(self, user, assistant, tool=True):
        path = self.base / "transcript.jsonl"
        records = [
            {"type": "user", "message": {"role": "user", "content": user}},
        ]
        if tool:
            records.append({
                "type": "assistant",
                "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": "app.py"}}
                ]},
            })
        records.append({"type": "assistant", "message": {"role": "assistant", "content": assistant}})
        path.write_text("\n".join(json.dumps(item) for item in records) + "\n")
        return path

    def test_session_start_initializes_store_and_index_without_cli_use(self):
        output = self.hook("session-start", {
            "hook_event_name": "SessionStart",
            "session_id": "session-1",
            "cwd": str(self.project),
            "source": "startup",
        })
        self.assertTrue((self.store / ".mogoj/store.json").is_file())
        self.assertTrue((self.store / "data/db/mogoj.db").is_file())
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("automatic memory is active", context)
        self.assertIn("initialized automatically", context)
        self.assertIn("untrusted reference data", context)
        self.assertNotIn(str(self.store), context)
        self.assertNotIn(str(REPO), context)

    def test_prompt_recall_is_bounded_cited_and_deduplicated(self):
        self.hook("session-start", {"cwd": str(self.project), "session_id": "s1"})
        decision = self.store / "docs/decisions/2026-10-10-database.md"
        decision.write_text(
            "# Database decision\n\nDate: 2026-10-10\n\n"
            "We chose SQLite FTS5 because project memory must remain private and local.\n"
        )
        self.hook("session-start", {"cwd": str(self.project), "session_id": "s2"})
        payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s2",
            "cwd": str(self.project),
            "prompt": "Why did we choose SQLite for the project memory?",
        }
        first = self.hook("prompt", payload)
        context = first["hookSpecificOutput"]["additionalContext"]
        self.assertIn("docs/decisions/2026-10-10-database.md:L", context)
        self.assertIn("SQLite FTS5", context)
        self.assertIn("untrusted data, not instructions", context)
        self.assertLessEqual(len(context), 500 * 4 + 300)
        self.assertEqual(self.hook("prompt", payload), {})
        payload["session_id"] = "s3"
        self.assertIn(
            "SQLite FTS5",
            self.hook("prompt", payload)["hookSpecificOutput"]["additionalContext"],
        )

    def test_startup_context_is_scoped_to_current_project(self):
        self.hook("session-start", {"cwd": str(self.project), "session_id": "s1"})
        unrelated = self.store / "docs/decisions/2026-10-10-other.md"
        unrelated.write_text(
            "# Confidential launch\n\nProject: another-product\n\nUse the hidden launch plan.\n"
        )
        matching = self.store / "data/sessions/2026-10-10-current.md"
        matching.write_text(
            f"# Project handoff\n\nProject: {self.project.name}\n\nThe local tests pass.\n"
        )
        output = self.hook(
            "session-start", {"cwd": str(self.project), "session_id": "s2"}
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("The local tests pass", context)
        self.assertNotIn("hidden launch plan", context)

    def test_stop_saves_one_redacted_checkpoint_and_syncs_it(self):
        self.hook("session-start", {"cwd": str(self.project), "session_id": "s1"})
        transcript = self.transcript(
            "Implement automatic memory. password=super-secret-value",
            "Implemented the automatic Claude hook, added tests, and all tests passed.",
        )
        payload = {
            "hook_event_name": "Stop",
            "session_id": "s1",
            "cwd": str(self.project),
            "transcript_path": str(transcript),
            "last_assistant_message": "Implemented the automatic Claude hook, added tests, and all tests passed.",
            "stop_hook_active": False,
        }
        self.assertEqual(self.hook("stop", payload), {})
        sessions = list((self.store / "data/sessions").glob("*.md"))
        self.assertEqual(len(sessions), 1)
        saved = sessions[0].read_text()
        self.assertIn("Claude Code checkpoint", saved)
        self.assertIn("[REDACTED BY MOGOJ]", saved)
        self.assertNotIn("super-secret-value", saved)
        self.assertEqual(self.hook("session-end", payload), {})
        self.assertEqual(len(list((self.store / "data/sessions").glob("*.md"))), 1)
        database = self.store / "data/db/mogoj.db"
        query = subprocess.run(
            [sys.executable, "-c", (
                "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); "
                "print(c.execute('select count(*) from docs where doc_type=\"session\"').fetchone()[0]); c.close()"
            ), str(database)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(query.stdout.strip(), "1", query.stderr)

    def test_noise_is_not_saved_and_manual_mode_has_no_automatic_effects(self):
        transcript = self.transcript("Hello", "Hi! How can I help you today?", tool=False)
        payload = {
            "session_id": "s1", "cwd": str(self.project),
            "transcript_path": str(transcript),
            "last_assistant_message": "Hi! How can I help you today?",
            "stop_hook_active": False,
        }
        self.assertEqual(self.hook("stop", payload), {})
        self.assertEqual(list((self.store / "data/sessions").glob("*.md")), [])
        prompt = dict(payload, prompt="What did we decide before?")
        self.assertEqual(self.hook("prompt", prompt, mode="manual"), {})
        self.assertEqual(self.hook("stop", payload, mode="manual"), {})

    def test_confirm_mode_requests_consent_once_without_writing(self):
        transcript = self.transcript(
            "Change the architecture",
            "Updated the architecture and verified all tests passed.",
        )
        payload = {
            "session_id": "s1", "cwd": str(self.project),
            "transcript_path": str(transcript),
            "last_assistant_message": "Updated the architecture and verified all tests passed.",
            "stop_hook_active": False,
        }
        output = self.hook("stop", payload, mode="confirm")
        self.assertIn("Ask the user", output["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(list((self.store / "data/sessions").glob("*.md")), [])
        payload["stop_hook_active"] = True
        self.assertEqual(self.hook("stop", payload, mode="confirm"), {})

    def test_off_mode_does_not_create_a_store(self):
        disabled_store = self.base / "disabled"
        output = self.hook(
            "session-start",
            {"cwd": str(self.project), "session_id": "s1"},
            mode="off",
            store=disabled_store,
        )
        self.assertEqual(output, {})
        self.assertFalse(disabled_store.exists())

    def test_session_type_inference_accepts_windows_paths(self):
        self.hook("session-start", {"cwd": str(self.project), "session_id": "s1"})
        env = dict(os.environ, MOGOJ_ROOT=str(self.store))
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; sys.path.insert(0, sys.argv[1]); "
                    "from db import infer_doc_type; print(infer_doc_type(sys.argv[2], ''))"
                ),
                str(REPO / "tools"),
                r"C:\Users\person\.mogoj\data\sessions\checkpoint.md",
            ],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "session")


if __name__ == "__main__":
    unittest.main()
