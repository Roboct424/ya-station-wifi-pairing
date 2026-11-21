#!/usr/bin/env python3
"""Исходный архив для Linux/macOS: dist/ya-station-wifi-pairing-<version>.tar.gz

    python packaging/build_tar.py
"""
from __future__ import annotations

import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = "1.2.0"
NAME = f"ya-station-wifi-pairing-{VERSION}"

INCLUDE_DIRS = [
    ".github",
    "android",
    "docs",
    "examples",
    "packaging",
    "tools",
]
INCLUDE_FILES = [".gitignore", "LICENSE", "README.md"]

SKIP_PARTS = {".tools", "build", "build_linux", "__pycache__"}
SKIP_SUFFIX = {".pyc", ".pyo", ".pem", ".keystore", ".wav", ".spec"}


def keep(path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    if path.suffix in SKIP_SUFFIX:
        return False
    return path.is_file()


def main() -> int:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{NAME}.tar.gz"
    files: list[Path] = []
    for name in INCLUDE_FILES:
        p = ROOT / name
        if p.exists():
            files.append(p)
    for d in INCLUDE_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        files.extend(p for p in sorted(base.rglob("*")) if keep(p.relative_to(ROOT)))

    with tarfile.open(out, "w:gz") as tar:
        for path in files:
            tar.add(path, arcname=f"{NAME}/{path.relative_to(ROOT).as_posix()}")
    print(f"готово: {out} ({out.stat().st_size} байт, файлов {len(files)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
