#!/usr/bin/env python3
"""Build deterministic tar/zip archives, SPDX SBOM, and checksums."""

import gzip
import hashlib
import json
import os
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VERSION = (ROOT / "VERSION").read_text().strip()
PREFIX = f"mogoj-{VERSION}"
EXCLUDED = {".git", "dist", "__pycache__", ".DS_Store"}


def files():
    return [
        path for path in sorted(ROOT.rglob("*"))
        if path.is_file() and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)
        and path.suffix not in (".pyc", ".cover")
    ]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_tar(paths, destination):
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in paths:
                    name = f"{PREFIX}/{path.relative_to(ROOT)}"
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as source:
                        archive.addfile(info, source)


def build_zip(paths, destination):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            info = zipfile.ZipInfo(f"{PREFIX}/{path.relative_to(ROOT)}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes())


def main():
    DIST.mkdir(exist_ok=True)
    paths = files()
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": PREFIX,
        "documentNamespace": f"https://github.com/Base13-Labs/mogoj/releases/tag/v{VERSION}/sbom",
        "creationInfo": {"created": "1970-01-01T00:00:00Z", "creators": ["Organization: Base13 Labs"]},
        "packages": [{
            "name": "mogoj", "SPDXID": "SPDXRef-Package-Mogoj", "versionInfo": VERSION,
            "downloadLocation": "NOASSERTION", "licenseConcluded": "MIT",
            "licenseDeclared": "MIT", "filesAnalyzed": True,
            "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl", "referenceLocator": f"pkg:github/Base13-Labs/mogoj@v{VERSION}"}],
        }],
        "files": [{
            "fileName": str(path.relative_to(ROOT)),
            "SPDXID": "SPDXRef-File-" + hashlib.sha256(str(path.relative_to(ROOT)).encode()).hexdigest()[:16],
            "checksums": [{"algorithm": "SHA256", "checksumValue": digest(path)}],
            "licenseConcluded": "NOASSERTION",
        } for path in paths],
        "relationships": [],
        "annotations": [{
            "annotationDate": "1970-01-01T00:00:00Z", "annotationType": "OTHER",
            "annotator": "Tool: mogoj-build-release", "comment": "Runtime dependencies: CPython standard library and SQLite FTS5."
        }],
    }
    sbom_path = DIST / f"{PREFIX}.spdx.json"
    sbom_path.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n")
    tar_path = DIST / f"{PREFIX}.tar.gz"
    zip_path = DIST / f"{PREFIX}.zip"
    build_tar(paths, tar_path)
    build_zip(paths, zip_path)
    artifacts = (tar_path, zip_path, sbom_path)
    checksums = DIST / "SHA256SUMS"
    checksums.write_text("".join(f"{digest(path)}  {path.name}\n" for path in artifacts))
    for path in (*artifacts, checksums):
        print(f"{path.name}  {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
