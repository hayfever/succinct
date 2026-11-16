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

    def run_plugin(self, args=""):
        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(self.config_dir)
        result = subprocess.run(
            [
                "node",
                str(ROOT / "tests" / "opencode_plugin_driver.mjs"),
                str(self.plugin_root / ".opencode" / "plugins" / "succinct" / "index.js"),
                args,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    @property
    def flag(self):
        return self.config_dir / "opencode" / ".succinct-always"

    def opt_in(self):
        self.flag.touch()

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
        self.assertIn('"/succinct off" turns it off for future sessions', part["text"])
        self.assertNotIn("name: succinct", part["text"])
        self.assertIn("Answer first, next action last.", part["text"])

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

    def test_succinct_on_creates_the_flag_and_injects(self):
        report = self.run_plugin("on")
        self.assertTrue(self.flag.is_file())
        self.assertEqual("", self.flag.read_text())
        self.assertIn("The user ran /succinct on.", report["prompts"][0]["text"])
        self.assertNotIn("Use the `succinct` skill", report["prompts"][0]["text"])
        self.assertEqual(1, len(report["system"]))

        # A new session reads the flag.
        self.assertEqual(1, len(self.run_plugin()["system"]))

    def test_succinct_on_creates_a_missing_config_dir(self):
        (self.config_dir / "opencode").rmdir()
        self.run_plugin("on")
        self.assertTrue(self.flag.is_file())

    def test_succinct_off_deletes_the_flag(self):
        self.opt_in()
        report = self.run_plugin(" OFF ")
        self.assertFalse(self.flag.exists())
        self.assertIn("The user ran /succinct off.", report["prompts"][0]["text"])
        self.assertEqual([], report["system"])

        # A new session reads the missing flag.
        self.assertEqual([], self.run_plugin()["system"])

    def test_succinct_off_without_a_flag_is_not_an_error(self):
        report = self.run_plugin("off")
        self.assertFalse(self.flag.exists())
        self.assertIn("The user ran /succinct off.", report["prompts"][0]["text"])

    def test_bare_command_leaves_the_flag_alone(self):
        self.run_plugin()
        self.assertFalse(self.flag.exists())
        self.opt_in()
        self.run_plugin()
        self.assertTrue(self.flag.is_file())

if __name__ == "__main__":
    unittest.main()
