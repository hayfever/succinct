import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_evals = load_module("run_evals", "scripts/run_evals.py")


class PackageContractTest(unittest.TestCase):
    def test_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate-package.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_omp_and_pi_extension_manifests_are_declared(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf8"))
        extension = ["./extensions/succinct.ts"]
        self.assertEqual({"extensions": extension}, package["omp"])
        self.assertEqual(
            {"extensions": extension, "skills": ["./skills"]},
            package["pi"],
        )
        self.assertTrue((ROOT / "extensions" / "succinct.ts").is_file())

    def test_skill_remains_explicitly_invoked(self):
        skill = (ROOT / "skills" / "succinct" / "SKILL.md").read_text(encoding="utf8")
        frontmatter = skill.split("---\n", 2)[1]
        self.assertIn("name: succinct", frontmatter)
        self.assertIn("disable-model-invocation: true", frontmatter)

    def test_stop_phrases_agree_across_runtimes(self):
        # "stop succinct mode" and "normal mode" are a cross-runtime contract:
        # the extension, the hooks, the OpenCode plugin, the command file, the
        # skill body, and both INSTALL docs must all agree on the same phrases.
        expectation = {
            "extensions/succinct.ts": [
                '"stop succinct mode": true,',
                '"normal mode": true,',
            ],
            ".opencode/plugins/succinct/index.js": ['"stop succinct mode" or "normal mode"'],
            ".opencode/command/succinct.md": ['"stop succinct mode" or "normal mode"'],
            "skills/succinct/SKILL.md": ["stop succinct mode", "normal mode"],
        }
        for relative, markers in expectation.items():
            text = (ROOT / relative).read_text(encoding="utf8")
            for marker in markers:
                self.assertIn(marker, (ROOT / relative).read_text(encoding="utf8"),
                              f"{relative} lost the toggle phrase: {marker}")

    def test_codex_policy_disables_implicit_invocation(self):
        text = (ROOT / "skills" / "succinct" / "agents" / "openai.yaml").read_text(
            encoding="utf8"
        )
        self.assertIn("allow_implicit_invocation: false", text)

    def test_skill_points_at_its_reference_files(self):
        skill = (ROOT / "skills" / "succinct" / "SKILL.md").read_text(encoding="utf8")
        for relative in (
            "skills/succinct/references/patterns.md",
            "skills/succinct/references/plain-english.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertIn("references/patterns.md", skill)
        self.assertIn("references/plain-english.md", skill)

    def test_all_runtime_files_reference_the_canonical_skill(self):
        markers = {
            "extensions/succinct.ts": '"SKILL.md",',
            "hooks/always-on.sh": "skills/succinct/SKILL.md",
            "hooks/always-on.ps1": "../skills/succinct/SKILL.md",
            ".opencode/plugins/succinct/index.js": '"succinct", "SKILL.md"',
        }
        for relative, marker in markers.items():
            text = (ROOT / relative).read_text(encoding="utf8")
            self.assertIn(marker, text, f"{relative} must reference the canonical skill")


class PackageGateTest(unittest.TestCase):
    """Run the validator against a copy of the checkout with one defect."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "repo"
        shutil.copytree(
            ROOT,
            self.root,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "*.pyc", ".omp-report.md", ".mayfly"
            ),
        )

    def run_validator(self):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "validate-package.py")],
            capture_output=True,
            text=True,
        )

    @staticmethod
    def next_version():
        major, minor, patch = (
            int(part)
            for part in json.loads((ROOT / "package.json").read_text())["version"].split(".")
        )
        return f"{major}.{minor}.{patch + 1}"

    def test_validator_rejects_a_manifest_version_mismatch(self):
        path = self.root / ".codex-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf8"))
        data["version"] = self.next_version()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")

        result = self.run_validator()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must use the package version", result.stdout + result.stderr)

    def test_validator_rejects_a_missing_skill_description(self):
        path = self.root / "skills" / "succinct" / "SKILL.md"
        text = re.sub(
            r"(?ms)^description:.*?(?=^disable-model-invocation:)",
            "",
            path.read_text(encoding="utf8"),
        )
        path.write_text(text, encoding="utf8")

        result = self.run_validator()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must declare description", result.stdout + result.stderr)

    def test_validator_rejects_a_missing_manifest_path(self):
        path = self.root / ".codex-plugin" / "plugin.json"
        data = json.loads(path.read_text(encoding="utf8"))
        data["skills"] = "./missing-skills"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf8")

        result = self.run_validator()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("points at a missing path", result.stdout + result.stderr)

    def test_validator_rejects_a_missing_required_file(self):
        (self.root / "hooks" / "toggle.ps1").unlink()

        result = self.run_validator()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Required file is missing: hooks/toggle.ps1", result.stdout + result.stderr)

    def test_validator_rejects_a_stale_skill_version(self):
        path = self.root / "skills" / "succinct" / "SKILL.md"
        text = re.sub(
            r'(?m)^(\s+version:\s*")[0-9.]+(")',
            lambda match: match.group(1) + self.next_version() + match.group(2),
            path.read_text(encoding="utf8"),
            count=1,
        )
        path.write_text(text, encoding="utf8")

        result = self.run_validator()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must match package.json", result.stdout + result.stderr)


class EvalAssetsTest(unittest.TestCase):
    def test_cases_validate(self):
        cases = run_evals.load_cases(ROOT / "evals" / "cases.jsonl")
        errors = run_evals.validate_cases(cases)
        self.assertEqual([], errors)

    def test_runner_config_is_well_formed(self):
        config = json.loads((ROOT / "evals" / "runners.json").read_text(encoding="utf8"))
        known_formats = {"text", "claude-json", "codex-jsonl"}
        for name, runner in config.items():
            self.assertTrue(runner.get("command"), f"runner {name}: empty command")
            self.assertIn(runner.get("response_format", "text"), known_formats,
                          f"runner {name}: unknown response_format")

    def test_rubric_has_judge_slice_and_gate(self):
        rubric = (ROOT / "evals" / "rubric.md").read_text(encoding="utf8")
        self.assertIn("<!-- judge:begin -->", rubric)
        self.assertIn("<!-- judge:end -->", rubric)
        self.assertIn("Release", rubric)


if __name__ == "__main__":
    unittest.main()