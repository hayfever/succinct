import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which("node"), "node is required for the OpenCode plugin")
class OpenCodePluginTest(unittest.TestCase):
    """Drive the OpenCode plugin through the V2 plugin API: `setup(ctx)`
    registers the `/succinct` command and a session `context` hook, and the
    always-on flag gates the system-prompt injection. Mirror tests/test_always_on_hooks.py
    for the frontmatter-stripping edge cases."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.plugin_root = Path(self.temp_dir.name) / "plugin"
        shutil.copytree(ROOT / ".opencode", self.plugin_root / ".opencode")
        shutil.copytree(ROOT / "skills", self.plugin_root / "skills")
        # The plugin reads its flag from $XDG_CONFIG_HOME/opencode/.succinct-always.
        self.config_dir = Path(self.temp_dir.name) / "config"
        (self.config_dir / "opencode").mkdir(parents=True)

    def run_plugin(self):
        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(self.config_dir)
        result = subprocess.run(
            [
                "node",
                str(ROOT / "tests" / "opencode_plugin_driver.mjs"),
                str(self.plugin_root / ".opencode" / "plugins" / "succinct" / "index.js"),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def opt_in(self):
        (self.config_dir / "opencode" / ".succinct-always").touch()

    def write_skill(self, text):
        (self.plugin_root / "skills" / "succinct" / "SKILL.md").write_text(text)

    def write_command(self, text):
        (self.plugin_root / ".opencode" / "command" / "succinct.md").write_text(text)

    def test_registers_the_succinct_command(self):
        report = self.run_plugin()
        self.assertEqual("succinct", report["id"])
        self.assertEqual(1, len(report["commands"]))
        command = report["commands"][0]
        self.assertEqual("succinct", command["name"])
        self.assertTrue(command["description"], "the command needs a description")

    def test_command_submits_the_template_without_frontmatter(self):
        report = self.run_plugin()
        self.assertEqual(1, len(report["prompts"]))
        prompt = report["prompts"][0]
        self.assertEqual("ses_test", prompt["sessionID"])
        self.assertEqual("steer", prompt["delivery"])
        self.assertIn("Use the `succinct` skill", prompt["text"])
        self.assertNotIn("description:", prompt["text"])

    def test_command_keeps_content_when_frontmatter_is_unclosed(self):
        self.write_command("---\ndescription: fixture\nTemplate body.\n")
        report = self.run_plugin()
        self.assertIn("Template body.", report["prompts"][0]["text"])

    def test_silent_without_opt_in_flag(self):
        report = self.run_plugin()
        self.assertEqual([], report["system"])

    def test_injects_the_ruleset_when_opted_in(self):
        self.opt_in()
        report = self.run_plugin()
        self.assertEqual(1, len(report["system"]))
        part = report["system"][0]
        self.assertEqual("text", part["type"])
        self.assertTrue(part["text"].startswith("SUCCINCT MODE ACTIVE (always-on)."), part["text"][:80])
        self.assertIn(str(self.config_dir / "opencode" / ".succinct-always"), part["text"])
        self.assertNotIn("name: succinct", part["text"])
        self.assertIn("Lead with the action.", part["text"])

    def test_strips_frontmatter_with_trailing_whitespace(self):
        self.write_skill("---   \nname: fixture\n--- \t\nFixture body.\n")
        self.opt_in()
        report = self.run_plugin()
        self.assertEqual(1, len(report["system"]))
        self.assertNotIn("name: fixture", report["system"][0]["text"])
        self.assertTrue(report["system"][0]["text"].endswith("\n\nFixture body."), report["system"][0]["text"][-60:])

    def test_keeps_content_when_frontmatter_is_unclosed(self):
        self.write_skill("---\nname: fixture\nFixture body, fence never closed.\n")
        self.opt_in()
        report = self.run_plugin()
        self.assertIn("Fixture body, fence never closed.", report["system"][0]["text"])

if __name__ == "__main__":
    unittest.main()
