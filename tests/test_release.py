import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_version_and_private_data_audits(self):
        for script, args in (("check_version.py", ["--tag", "v0.1.0-beta.1"]), ("audit_release.py", [])):
            result = subprocess.run([sys.executable, str(REPO / "scripts" / script), *args], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reproducible_artifacts_sbom_and_clean_install(self):
        subprocess.run([sys.executable, str(REPO / "scripts" / "build_release.py")], check=True, stdout=subprocess.PIPE)
        first = (REPO / "dist" / "SHA256SUMS").read_text()
        subprocess.run([sys.executable, str(REPO / "scripts" / "build_release.py")], check=True, stdout=subprocess.PIPE)
        self.assertEqual(first, (REPO / "dist" / "SHA256SUMS").read_text())
        sbom = json.loads((REPO / "dist" / "mogoj-0.1.0-beta.1.spdx.json").read_text())
        self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
        with tempfile.TemporaryDirectory() as directory:
            archive = REPO / "dist" / "mogoj-0.1.0-beta.1.zip"
            with zipfile.ZipFile(archive) as package:
                package.extractall(directory)
            unpacked = Path(directory) / "mogoj-0.1.0-beta.1"
            result = subprocess.run([sys.executable, str(unpacked / "bin" / "mogoj"), "--help"],
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("mogoj init", result.stdout)


if __name__ == "__main__":
    unittest.main()
