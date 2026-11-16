#!/usr/bin/env python3
"""Check succinct's package files without external dependencies.

The check covers the package contract and the harness layout: parsed manifests,
one package version, required skill frontmatter, manifest paths that exist, and
generated adapters that match their canonical source.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACKAGE = ROOT / "package.json"
SKILL_PATHS = (Path("skills/succinct/SKILL.md"),)
SKILL_PATH = ROOT / SKILL_PATHS[0]

JSON_MANIFESTS = (
    "package.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "opencode.json",
    "hooks/hooks.json",
    "hooks/codex-hooks.json",
)

JSON_MANIFESTS_WITH_NAME = (
    "package.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
)

# These manifests must carry the package version. The marketplace manifests
# point at the plugin, so the plugin owns the version they publish.
VERSIONED_MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
)

REQUIRED_FILES = (
    "skills/succinct/SKILL.md",
    "skills/succinct/references/patterns.md",
    "skills/succinct/references/plain-english.md",
    "skills/succinct/agents/openai.yaml",
    "extensions/succinct.ts",
    "extensions/context-compat.ts",
    "hooks/always-on.sh",
    "hooks/always-on.ps1",
    "hooks/toggle.sh",
    "hooks/toggle.ps1",
    "hooks/hooks.json",
    "hooks/codex-hooks.json",
    ".opencode/command/succinct.md",
)

# Manifest fields that name a file or directory this repository ships.
PATH_FIELDS = (
    ("package.json", ("omp", "extensions")),
    ("package.json", ("pi", "extensions")),
    ("package.json", ("pi", "skills")),
    (".codex-plugin/plugin.json", ("skills",)),
    (".codex-plugin/plugin.json", ("hooks",)),
    ("opencode.json", ("plugins",)),
    ("opencode.json", ("skills",)),
)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"Cannot read {path.relative_to(ROOT)}: {error}")


def require_match(match: re.Match[str] | None, message: str) -> re.Match[str]:
    if match is None:
        raise SystemExit(message)
    return match


def require_path(relative: str, keys: tuple[str, ...]) -> None:
    data = json.loads(read(ROOT / relative))
    value: object = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise SystemExit(f"{relative} must declare {'.'.join(keys)}")
        value = value[key]
    entries = value if isinstance(value, list) else [value]
    for entry in entries:
        if not isinstance(entry, str):
            raise SystemExit(f"{relative} path must be a string: {entry!r}")
        normalized = entry[2:] if entry.startswith("./") else entry
        target = ROOT / normalized if normalized else ROOT
        if not target.exists():
            raise SystemExit(f"{relative} points at a missing path: {entry}")


def frontmatter(relative: Path) -> str:
    text = read(ROOT / relative)
    match = require_match(
        re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL),
        f"{relative} must begin with YAML metadata",
    )
    fields = match.group(1)
    for field in ("name", "description"):
        if re.search(rf"(?m)^{field}:\s*\S", fields) is None:
            raise SystemExit(f"{relative} must declare {field} in its frontmatter")
    return fields


# Every skill file declares the same name and description.
skill_names = set()
for relative in SKILL_PATHS:
    fields = frontmatter(relative)
    name = require_match(
        re.search(r"(?m)^name:\s*(\S+)\s*$", fields),
        f"{relative} must declare name in its frontmatter",
    ).group(1)
    if name != "succinct":
        raise SystemExit(f"{relative} must declare name: succinct (found: {name!r})")
    if (ROOT / relative).parent.name != name:
        raise SystemExit(f"{relative} must sit in a folder named {name}")
    skill_names.add(name)
if len(skill_names) != 1:
    raise SystemExit(f"Use one skill name in every SKILL.md: {sorted(skill_names)}")

SKILL = read(SKILL_PATH)
frontmatter_text = frontmatter(SKILL_PATHS[0])

require_match(
    re.search(r"(?m)^disable-model-invocation: true$", frontmatter_text),
    "Frontmatter must declare disable-model-invocation: true",
)
for unsupported_field in ("version:", "compatibility:", "allowed-tools:"):
    if re.search(rf"(?m)^{re.escape(unsupported_field)}", frontmatter_text):
        raise SystemExit(f"Remove unsupported YAML field: {unsupported_field[:-1]}")

skill_version = require_match(
    re.search(
        r'(?m)^\s+version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)["\']?\s*$',
        frontmatter_text,
    ),
    "Add metadata.version to SKILL.md as a three-part version",
).group(1)

if len(SKILL.splitlines()) > 200:
    raise SystemExit("Keep skills/succinct/SKILL.md at 200 lines or fewer")

# Only one skill, and its folder name must match the frontmatter name.
skill_files = {path.relative_to(ROOT) for path in ROOT.rglob("SKILL.md")}
if skill_files != set(SKILL_PATHS):
    raise SystemExit(f"Unexpected SKILL.md locations: {sorted(skill_files)}")

# All manifests parse and agree on name and version.
for relative in JSON_MANIFESTS:
    try:
        json.loads(read(ROOT / relative))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Fix the JSON in {relative}: {error}")

package = json.loads(read(PACKAGE))
package_version = package.get("version")
if not isinstance(package_version, str) or re.fullmatch(
    r"[0-9]+\.[0-9]+\.[0-9]+", package_version
) is None:
    raise SystemExit("package.json must declare a three-part version")
if skill_version != package_version:
    raise SystemExit(
        f"skills/succinct/SKILL.md metadata.version {skill_version} "
        f"must match package.json {package_version}"
    )

for relative in JSON_MANIFESTS_WITH_NAME:
    data = json.loads(read(ROOT / relative))
    name = data.get("name")
    if name != "succinct":
        raise SystemExit(f"{relative} must declare name: succinct (found: {name!r})")

for relative in VERSIONED_MANIFESTS:
    data = json.loads(read(ROOT / relative))
    version = data.get("version")
    if version != package_version:
        raise SystemExit(
            f"{relative} must use the package version {package_version} "
            f"(found: {version!r})"
        )

extension = ["./extensions/succinct.ts"]
if package.get("omp") != {"extensions": extension}:
    raise SystemExit("package.json must declare omp extensions ./extensions/succinct.ts")
if package.get("pi") != {"extensions": extension, "skills": ["./skills"]}:
    raise SystemExit('package.json must declare pi extensions and skills ["./skills"]')

# Every path a manifest publishes must resolve in this checkout.
for relative in REQUIRED_FILES:
    if not (ROOT / relative).exists():
        raise SystemExit(f"Required file is missing: {relative}")
for relative, keys in PATH_FIELDS:
    require_path(relative, keys)

for relative in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
    data = json.loads(read(ROOT / relative))
    for plugin in data.get("plugins", []):
        source = plugin.get("source")
        if isinstance(source, dict):
            source = source.get("path")
        if not isinstance(source, str):
            raise SystemExit(f"{relative} plugin source must be a path")
        normalized = source[2:] if source.startswith("./") else source
        target = ROOT / normalized if normalized else ROOT
        if not target.exists():
            raise SystemExit(f"{relative} points at a missing path: {source}")

# Hook commands name the scripts that do the work. Read the decoded command
# strings so JSON escaping does not hide the path.
HOOK_SCRIPTS = (
    "hooks/always-on.sh",
    "hooks/always-on.ps1",
    "hooks/toggle.sh",
    "hooks/toggle.ps1",
)
for relative in ("hooks/hooks.json", "hooks/codex-hooks.json"):
    data = json.loads(read(ROOT / relative))
    commands: list[str] = []
    for groups in data.get("hooks", {}).values():
        for entry in groups:
            for handler in entry.get("hooks", []):
                for key in ("command", "commandWindows"):
                    if isinstance(handler.get(key), str):
                        commands.append(handler[key])
    text = "\n".join(commands)
    for script in HOOK_SCRIPTS:
        windows_script = script.replace("/", "\\")
        if script not in text and windows_script not in text:
            raise SystemExit(f"{relative} must run {script}")
        if not (ROOT / script).is_file():
            raise SystemExit(f"{relative} runs a missing script: {script}")

# Rule numbering: Part 1 has rules 1 to 10 in the core. The core keeps the
# five strongest tells; the reference keeps all 25. The reference also keeps
# Part 3's 15 numbered rules.
shape_rules = [
    int(number) for number in re.findall(r"(?m)^## ([0-9]+)\. ", SKILL)
]
if shape_rules != list(range(1, 11)):
    raise SystemExit(f"Number the ten shape rules 1 to 10 in order: {shape_rules}")

core_tells_section = SKILL.split("## The tells")[1].split("## When not to act")[0]
core_tells = [
    int(number)
    for number in re.findall(r"(?m)^([0-9]+)\. \*\*", core_tells_section)
]
if core_tells != list(range(1, 6)):
    raise SystemExit(f"Number the five core tells 1 to 5 in order: {core_tells}")

PATTERNS = read(ROOT / "skills/succinct/references/patterns.md")
tells_section = PATTERNS.split("## The tells")[1].split("## When not to act")[0]
tells = [
    int(number) for number in re.findall(r"(?m)^([0-9]+)\. \*\*", tells_section)
]
if tells != list(range(1, 26)):
    raise SystemExit(f"Number the 25 tells 1 to 25 without gaps: {tells}")

PLAIN = read(ROOT / "skills/succinct/references/plain-english.md")
plain_section = PLAIN.split("# Part 3")[1].split("## Quoted text")[0]
plain_rules = [
    int(number) for number in re.findall(r"(?m)^([0-9]+)\. ", plain_section)
]
if plain_rules != list(range(1, 16)):
    raise SystemExit(f"Number the 15 plain rules 1 to 15 in order: {plain_rules}")

for marker in ("references/patterns.md", "references/plain-english.md"):
    if marker not in SKILL:
        raise SystemExit(f"SKILL.md must point at {marker}")

# Runtime entry points must point at the canonical skill and use succinct phrases.
for relative, marker in (
    ("hooks/always-on.sh", "skills/succinct/SKILL.md"),
    ("hooks/always-on.ps1", "../skills/succinct/SKILL.md"),
    (".opencode/plugins/succinct/index.js", '"succinct", "SKILL.md"'),
    ("extensions/succinct.ts", '"succinct",'),
):
    if marker not in read(ROOT / relative):
        raise SystemExit(f"{relative} must reference the canonical skill: {marker}")

# OpenCode 2 renamed the config keys and only loads plugin directories.
opencode_config = json.loads(read(ROOT / "opencode.json"))
if opencode_config.get("plugins") != ["./.opencode/plugins/succinct"]:
    raise SystemExit("opencode.json must list ./.opencode/plugins/succinct in plugins")
if opencode_config.get("skills") != ["./skills"]:
    raise SystemExit("opencode.json must list ./skills in skills")

openai_yaml = read(ROOT / "skills" / "succinct" / "agents" / "openai.yaml")
require_match(
    re.search(r"(?m)^  allow_implicit_invocation: false$", openai_yaml),
    "skills/succinct/agents/openai.yaml must set allow_implicit_invocation: false",
)

# Generated adapters must match the canonical skill and package version.
# This runs last so a specific contract error reports its own cause first.
adapters = subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "build_adapters.py"), "--check"],
    capture_output=True,
    text=True,
)
if adapters.returncode != 0:
    raise SystemExit(adapters.stdout + adapters.stderr)

print(f"succinct package v{package_version} is valid")
