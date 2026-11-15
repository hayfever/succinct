#!/usr/bin/env python3
"""Bump the package version and regenerate every derived adapter.

Usage: python3 scripts/bump-version.py <new-version> [--from <old-version>]

Sets version in package.json, then runs scripts/build_adapters.py to write
metadata.version in skills/succinct/SKILL.md, the version in every plugin and
extension manifest, and the Cursor mirror. Then scans the repository for the
old version and fails if one remains, so a hard-coded version in a doc or badge
cannot go stale. Reminds you about CHANGELOG.md, which stays hand-written.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# History files keep old versions on purpose; everything else must move.
HISTORY_FILES = ("CHANGELOG.md",)
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}
TEXT_SUFFIXES = {
    ".json", ".md", ".toml", ".yaml", ".yml", ".ts", ".mjs", ".js",
    ".py", ".sh", ".ps1", ".txt", ".jsonl",
}


def current_version() -> str:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    return str(package["version"])


def replace_in_file(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        rf'(?<![0-9.]){re.escape(old)}(?![0-9.])', new, text
    )
    if count == 0:
        raise SystemExit(f"{path.relative_to(ROOT)}: no occurrence of {old}")
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"{path.relative_to(ROOT)}: {count} replacement(s)")


def run_script(relative: str, *args: str) -> bool:
    """Run a repository script and print its output."""
    result = subprocess.run(
        [sys.executable, str(ROOT / relative), *args],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_version", help="new version, e.g. 1.0.1")
    parser.add_argument("--from", dest="old_version", default=None)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.new_version):
        raise SystemExit(f"not a semantic version: {args.new_version}")

    old = args.old_version or current_version()
    if old == args.new_version:
        raise SystemExit(f"version is already {args.new_version}")
    if current_version() != old:
        raise SystemExit(
            f"package.json is at {current_version()}, not {old}; rerun without --from"
        )

    replace_in_file(ROOT / "package.json", old, args.new_version)
    if not run_script("scripts/build_adapters.py"):
        raise SystemExit("bump applied but adapter generation failed; inspect the diff")

    leftovers = find_leftovers(old)
    if leftovers:
        print("Old version still present in:", file=sys.stderr)
        for relative in leftovers:
            print(f"  {relative}", file=sys.stderr)
        raise SystemExit("update those files, then rerun the bump")

    if not run_script("scripts/validate-package.py"):
        raise SystemExit("bump applied but validation failed; inspect the diff")

    print()
    print("Next:")
    print(f"1. Add a CHANGELOG.md entry for {args.new_version} (or move the Unreleased block).")
    print(f"2. Commit and tag: git commit -am 'v{args.new_version}' && git tag v{args.new_version}")
    print("3. Push the tag; the release workflow drafts the GitHub release.")
    return 0


def find_leftovers(old: str) -> list[str]:
    pattern = re.compile(rf"(?<![0-9.]){re.escape(old)}(?![0-9.])")
    found: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if relative.as_posix() in HISTORY_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(text):
            found.append(relative.as_posix())
    return found


if __name__ == "__main__":
    raise SystemExit(main())
