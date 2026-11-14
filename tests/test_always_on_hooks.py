import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SESSION_START_COMMAND = json.loads(
    (ROOT / "hooks" / "hooks.json").read_text(encoding="utf8")
)["hooks"]["SessionStart"][0]["hooks"][0]["command"]


def path_without(executable):
    """Return a PATH that cannot resolve executable, plus whether it changed."""
    entries = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidates = (executable, f"{executable}.exe")
        if any((Path(entry) / name).is_file() for name in candidates):
            continue
        entries.append(entry)
    return os.pathsep.join(entries)


class AlwaysOnHookTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.plugin_root = Path(self.temp_dir.name) / "plugin with spaces"
        shutil.copytree(ROOT / "hooks", self.plugin_root / "hooks")
        shutil.copytree(ROOT / "skills", self.plugin_root / "skills")
        self.config_dir = Path(self.temp_dir.name) / "claude config"
        self.config_dir.mkdir()

    def opt_in(self):
        (self.config_dir / ".succinct-always").touch()

    def shell(self):
        return shutil.which("sh")

    def powershell(self):
        return shutil.which("pwsh") or shutil.which("powershell")

    def hook_env(self, path=None):
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        if path is not None:
            env["PATH"] = path
        return env

    def run_sh(self, env=None):
        shell = self.shell()
        if shell is None:
            self.skipTest("no sh runtime is available")
        return subprocess.run(
            [shell, str(self.plugin_root / "hooks" / "always-on.sh")],
            check=False,
            capture_output=True,
            text=True,
            env=env or self.hook_env(),
        )

    def run_powershell(self, env=None):
        powershell = self.powershell()
        if powershell is None:
            self.skipTest("no PowerShell runtime is available")
        return subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.plugin_root / "hooks" / "always-on.ps1"),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env or self.hook_env(),
        )

    def run_session_start_command(self, path=None, plugin_root=None):
        shell = self.shell()
        if shell is None:
            self.skipTest("no sh runtime is available")
        run_env = self.hook_env(path)
        run_env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root or self.plugin_root)
        return subprocess.run(
            [shell, "-c", SESSION_START_COMMAND],
            check=False,
            capture_output=True,
            text=True,
            env=run_env,
            input=json.dumps(
                {
                    "session_id": "test-session",
                    "cwd": str(self.plugin_root),
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                }
            ),
        )

    @staticmethod
    def normalize(stdout):
        # The banner embeds the flag path. On Windows the sh runtime joins it
        # with "/" while PowerShell joins with "\"; both name the same file, so
        # unify separators (and newlines) before comparing runtimes.
        return stdout.replace("\r\n", "\n").replace("\\", "/")

    def test_sh_hook_is_silent_without_opt_in_flag(self):
        result = self.run_sh()

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_sh_hook_injects_the_ruleset_with_the_opt_in_flag(self):
        self.opt_in()

        result = self.run_sh()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertTrue(
            result.stdout.startswith("SUCCINCT MODE ACTIVE (always-on)."),
            result.stdout[:200],
        )
        self.assertIn(".succinct-always", result.stdout)
        self.assertIn("## 1. Lead with the next action", result.stdout)
        # The YAML frontmatter is stripped, so the injected text starts with the
        # banner and the body, not with the skill's metadata block.
        self.assertNotIn("description: >-", result.stdout.split("\n\n", 1)[1][:500])

    def test_sh_hook_strips_frontmatter_with_trailing_whitespace(self):
        skill_path = self.plugin_root / "skills" / "succinct" / "SKILL.md"
        skill_path.write_text("---   \nname: fixture\n--- \t\nFixture body.\n")
        self.opt_in()

        result = self.run_sh()

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertNotIn("name: fixture", result.stdout)
        self.assertIn("\n\nFixture body.\n", result.stdout)

    def test_sh_hook_keeps_content_when_frontmatter_is_unclosed(self):
        # An opening --- with no closing delimiter is not frontmatter. Keeping
        # the whole file beats injecting a banner that promises "the ruleset
        # below" followed by nothing.
        skill_path = self.plugin_root / "skills" / "succinct" / "SKILL.md"
        skill_path.write_text("---\nname: fixture\nFixture body, fence never closed.\n")
        self.opt_in()

        result = self.run_sh()

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertIn("Fixture body, fence never closed.", result.stdout)

    def test_powershell_hook_matches_the_sh_hook(self):
        skill_path = self.plugin_root / "skills" / "succinct" / "SKILL.md"
        skill_path.write_text("---\nname: fixture\n---\nFixture body.\n")
        self.opt_in()

        # Windows without Git Bash has no sh, so the PowerShell hook skips only
        # when a POSIX shell is on PATH. Hide sh to reach the injecting path.
        without_sh = path_without("sh")
        if shutil.which("sh", path=without_sh) is not None:
            self.skipTest("cannot hide sh from PATH on this machine")

        sh_result = self.run_sh()
        ps_result = self.run_powershell(self.hook_env(without_sh))

        self.assertEqual(0, sh_result.returncode, sh_result.stderr)
        self.assertEqual(0, ps_result.returncode, ps_result.stderr)
        self.assertEqual("", ps_result.stderr)
        self.assertEqual(
            self.normalize(sh_result.stdout), self.normalize(ps_result.stdout)
        )

    def test_powershell_hook_is_silent_without_opt_in_flag(self):
        result = self.run_powershell(self.hook_env(path_without("sh")))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_powershell_hook_defers_to_the_sh_hook(self):
        # Both scripts run from the one command line. When sh is available the
        # PowerShell hook must stay silent, or the ruleset is injected twice.
        if shutil.which("sh") is None:
            self.skipTest("no sh on PATH, so both hooks inject by design")
        self.opt_in()

        result = self.run_powershell()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_session_start_command_needs_no_node(self):
        without_node = path_without("node")
        self.assertIsNone(
            shutil.which("node", path=without_node), "the test PATH still has node"
        )
        self.opt_in()

        result = self.run_session_start_command(without_node)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("SUCCINCT MODE ACTIVE (always-on).", result.stdout)
        self.assertIn("## 1. Lead with the next action", result.stdout)

    def test_session_start_command_is_silent_without_opt_in_flag(self):
        result = self.run_session_start_command(path_without("node"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_session_start_command_survives_a_missing_plugin_root(self):
        self.opt_in()

        result = self.run_session_start_command(
            path_without("node"), plugin_root=self.plugin_root / "missing plugin"
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_session_start_hook_declares_a_portable_command(self):
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf8"))
        session_start = config["hooks"]["SessionStart"][0]
        handlers = session_start["hooks"]

        self.assertEqual("startup|resume|clear|compact|fork", session_start["matcher"])
        self.assertEqual(1, len(handlers))
        handler = handlers[0]
        self.assertEqual("command", handler["type"])
        self.assertNotIn("args", handler)
        self.assertNotIn("node", handler["command"])
        # One command line covers POSIX sh and Windows PowerShell; it must run
        # the sh script first and always exit 0 so a missing interpreter on the
        # other platform never blocks session start.
        self.assertLess(
            handler["command"].index("always-on.sh"),
            handler["command"].index("always-on.ps1"),
        )
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", handler["command"])
        self.assertTrue(handler["command"].strip().endswith("exit 0"))


if __name__ == "__main__":
    unittest.main()
