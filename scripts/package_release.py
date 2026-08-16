#!/usr/bin/env python3
"""Build ZIP and TAR.GZ archives beside the package directory."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT.parent
EXCLUDED_PARTS = {"__pycache__", ".andromeda-state", ".pytest_cache"}


def files():
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and not EXCLUDED_PARTS.intersection(path.parts) and path.suffix != ".pyc":
            yield path


def main() -> None:
    stem = ROOT.name
    zip_path = OUTPUT_DIR / f"{stem}.zip"
    tar_path = OUTPUT_DIR / f"{stem}.tar.gz"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files():
            archive.write(path, Path(stem) / path.relative_to(ROOT))
    with tarfile.open(tar_path, "w:gz", compresslevel=9) as archive:
        for path in files():
            archive.add(path, arcname=Path(stem) / path.relative_to(ROOT), recursive=False)
    print(zip_path)
    print(tar_path)


if __name__ == "__main__":
    main()
