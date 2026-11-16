import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_adapters.py"

# Fixture versions are computed from the checkout version, never written as
# literals: scripts/bump-version.py fails when the old version appears anywhere
# in the tree, and a fixture is not a stale release reference.
BASE_VERSION = tuple(
    int(part)
    for part in json.loads((ROOT / "package.json").read_text())["version"].split(".")
)
BASE_TEXT = ".".join(str(part) for part in BASE_VERSION)


def shifted_version(offset):
    major, minor, patch = BASE_VERSION
    return f"{major}.{minor}.{patch + offset}"


FIXTURE_VERSION = shifted_version(1)
NEXT_VERSION = shifted_version(2)

MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
)

CANONICAL = """---
name: fixture
description: A fixture skill for the generator.
metadata:
  version: "{fixture_version}"
---

# fixture

Body line.
"""

CANONICAL_TEXT = CANONICAL.format(fixture_version=FIXTURE_VERSION)


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_adapters = load_module("build_adapters", "scripts/build_adapters.py")


class FixtureRepo:
    """A minimal checkout with one canonical skill and two manifests."""

    def __init__(self, root, version=BASE_TEXT):
        self.root = root
        (root / "skills" / "succinct").mkdir(parents=True)
        (root / "skills" / "succinct" / "SKILL.md").write_text(
            CANONICAL_TEXT, encoding="utf8"
        )
        (root / "skills" / "succinct" / "references").mkdir(parents=True)
        (root / "skills" / "succinct" / "references" / "patterns.md").write_text(
            "# Patterns\n\nFull catalog.\n", encoding="utf8"
        )
        (root / "package.json").write_text(
            json.dumps({"name": "fixture", "version": version}, indent=2) + "\n",
            encoding="utf8",
        )
        for relative in MANIFESTS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "name": "fixture",
                        "version": FIXTURE_VERSION,
                        "description": "Keep me.",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf8",
            )

    @property
    def canonical(self):
        return self.root / "skills" / "succinct" / "SKILL.md"


def run_main(argv):
    """Run main and return the exit code with captured stdout and stderr."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = build_adapters.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class BuildAdaptersTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def make_repo(self, **kwargs):
        return FixtureRepo(self.root, **kwargs)

    def test_check_is_clean_after_a_write(self):
        self.make_repo()
        run_main(["--root", str(self.root)])

        code, stdout, stderr = run_main(["--root", str(self.root), "--check"])

        self.assertEqual(0, code, stderr)
        self.assertEqual("", stderr)
        self.assertIn("up to date", stdout)

    def test_check_prints_a_diff_and_writes_nothing(self):
        repo = self.make_repo()
        before = repo.canonical.read_text(encoding="utf8")

        code, stdout, stderr = run_main(["--root", str(self.root), "--check"])

        self.assertEqual(1, code)
        self.assertIn("--- skills/succinct/SKILL.md (on disk)", stdout)
        self.assertIn("+++ skills/succinct/SKILL.md (generated)", stdout)
        self.assertIn(f'-  version: "{FIXTURE_VERSION}"', stdout)
        self.assertIn("out of date", stderr)
        self.assertEqual(before, repo.canonical.read_text(encoding="utf8"))

    def test_version_flows_from_package_json(self):
        repo = self.make_repo(version=NEXT_VERSION)

        code, _, stderr = run_main(["--root", str(self.root)])

        self.assertEqual(0, code, stderr)
        canonical = repo.canonical.read_text(encoding="utf8")
        self.assertIn(f'  version: "{NEXT_VERSION}"', canonical)
        for relative in MANIFESTS:
            data = json.loads((self.root / relative).read_text(encoding="utf8"))
            self.assertEqual(NEXT_VERSION, data["version"], relative)
            self.assertEqual("Keep me.", data["description"], relative)

    def test_check_reports_a_stale_manifest_version(self):
        self.make_repo()
        run_main(["--root", str(self.root)])
        (self.root / "package.json").write_text(
            json.dumps({"name": "fixture", "version": NEXT_VERSION}, indent=2) + "\n",
            encoding="utf8",
        )

        code, stdout, stderr = run_main(["--root", str(self.root), "--check"])

        self.assertEqual(1, code)
        self.assertIn(".claude-plugin/plugin.json", stdout)
        self.assertIn(NEXT_VERSION, stdout)
        self.assertIn("out of date", stderr)

    def test_missing_description_fails_without_writing(self):
        repo = self.make_repo()
        repo.canonical.write_text(
            CANONICAL_TEXT.replace("description: A fixture skill for the generator.\n", ""),
            encoding="utf8",
        )

        code, _, stderr = run_main(["--root", str(self.root)])

        self.assertEqual(2, code)
        self.assertIn("must declare description", stderr)
        self.assertNotIn("version: \"" + BASE_TEXT, repo.canonical.read_text(encoding="utf8"))

    def test_missing_manifest_version_fails(self):
        self.make_repo()
        path = self.root / ".codex-plugin" / "plugin.json"
        path.write_text('{\n  "name": "fixture"\n}\n', encoding="utf8")

        code, _, stderr = run_main(["--root", str(self.root)])

        self.assertEqual(2, code)
        self.assertIn("must declare a version", stderr)

    def test_manifest_formatting_and_trailing_newline_survive(self):
        self.make_repo()
        path = self.root / ".codex-plugin" / "plugin.json"
        path.write_text(
            f'{{\n  "name": "fixture",\n  "version": "{FIXTURE_VERSION}",\n'
            '  "keywords": ["a", "b"],\n  "skills": "./skills/",\n'
            '  "license": "MIT"\n}\n',
            encoding="utf8",
        )

        run_main(["--root", str(self.root)])

        text = path.read_text(encoding="utf8")
        self.assertTrue(text.endswith("}\n"))
        self.assertIn('"keywords": ["a", "b"]', text)
        self.assertEqual(BASE_TEXT, json.loads(text)["version"])

    def test_real_checkout_is_current(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
