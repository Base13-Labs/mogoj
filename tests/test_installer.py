import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "managed shell installer supports macOS/Linux; Windows uses the PowerShell launcher")
    def test_five_clean_machine_personas_and_data_preserving_uninstall(self):
        for persona in ("default", "with space", "মগজ", "import", "cli-only"):
            with self.subTest(persona=persona), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                home = base / "home"; home.mkdir()
                prefix = base / "installed engine"
                bin_dir = base / "local bin"
                store = base / f"store {persona}"
                env = os.environ.copy(); env["HOME"] = str(home)
                installed = subprocess.run(
                    ["sh", str(REPO / "install.sh"), "--source", str(REPO), "--prefix", str(prefix),
                     "--bin-dir", str(bin_dir), "--yes", "--no-onboard"], env=env, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(installed.returncode, 0, installed.stderr)
                command = bin_dir / "mogoj"
                subprocess.run([str(command), "--root", str(store), "init"], env=env, check=True, stdout=subprocess.PIPE)
                subprocess.run([str(command), "--root", str(store), "save", "first recall memory", "--title", "Welcome"], env=env, check=True, stdout=subprocess.PIPE)
                subprocess.run([str(command), "--root", str(store), "rebuild"], env=env, check=True, stdout=subprocess.PIPE)
                recalled = subprocess.run([str(command), "--root", str(store), "search", "first recall"], env=env, check=True, text=True, stdout=subprocess.PIPE)
                self.assertIn("docs/notes", recalled.stdout)
                subprocess.run([str(command), "--root", str(store), "doctor"], env=env, check=True, stdout=subprocess.PIPE)
                removed = subprocess.run(["sh", str(REPO / "uninstall.sh"), "--prefix", str(prefix), "--bin-dir", str(bin_dir), "--yes"], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(removed.returncode, 0, removed.stderr)
                self.assertTrue((store / "docs" / "notes").exists())
                self.assertFalse(command.exists())


if __name__ == "__main__":
    unittest.main()
