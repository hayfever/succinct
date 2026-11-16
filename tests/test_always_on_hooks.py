import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_hooks(relative):
    return json.loads((ROOT / "hooks" / relative).read_text(encoding="utf8"))


CLAUDE_HOOKS = load_hooks("hooks.json")
CODEX_HOOKS = load_hooks("codex-hooks.json")
SESSION_START_COMMAND = CLAUDE_HOOKS["hooks"]["SessionStart"][0]["hooks"][0]["command"]
CODEX_SESSION_START = CODEX_HOOKS["hooks"]["SessionStart"][0]["hooks"][0]
CLAUDE_EXPANSION = CLAUDE_HOOKS["hooks"]["UserPromptExpansion"][0]
CLAUDE_TOGGLE_COMMAND = CLAUDE_EXPANSION["hooks"][0]["command"]
CODEX_PROMPT_SUBMIT = CODEX_HOOKS["hooks"]["UserPromptSubmit"][0]["hooks"][0]


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
        # CODEX_HOME does not exist yet, so the toggle hook must create it.
        self.codex_home = Path(self.temp_dir.name) / "codex home"

    def flag(self, codex=False):
        return (self.codex_home if codex else self.config_dir) / ".succinct-always"

    def opt_in(self, codex=False):
        self.flag(codex).parent.mkdir(parents=True, exist_ok=True)
        self.flag(codex).touch()

    def shell(self):
        return shutil.which("sh")

    def powershell(self):
        return shutil.which("pwsh") or shutil.which("powershell")

    def hook_env(self, path=None):
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        env["CODEX_HOME"] = str(self.codex_home)
        if path is not None:
            env["PATH"] = path
        return env

    def run_sh(self, env=None, script="always-on.sh", extra_args=(), prompt=None):
        shell = self.shell()
        if shell is None:
            self.skipTest("no sh runtime is available")
        return subprocess.run(
            [shell, str(self.plugin_root / "hooks" / script), *extra_args],
            check=False,
            capture_output=True,
            text=True,
            env=env or self.hook_env(),
            input=None if prompt is None else self.prompt_input(prompt),
        )

    def run_powershell(
        self, env=None, extra_args=(), script="always-on.ps1", prompt=None
    ):
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
                str(self.plugin_root / "hooks" / script),
                *extra_args,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env or self.hook_env(),
            input=None if prompt is None else self.prompt_input(prompt),
        )

    def toggle(self, prompt, codex=False):
        return self.run_sh(
            script="toggle.sh",
            extra_args=("--codex",) if codex else (),
            prompt=prompt,
        )

    @staticmethod
    def prompt_input(prompt):
        return json.dumps(
            {
                "session_id": "test-session",
                "cwd": "/tmp",
                "hook_event_name": "UserPromptSubmit",
                "prompt": prompt,
            },
            indent=2,
        )

    def run_session_start_command(
        self, path=None, plugin_root=None, command=None, stdin=None
    ):
        shell = self.shell()
        if shell is None:
            self.skipTest("no sh runtime is available")
        run_env = self.hook_env(path)
        run_env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root or self.plugin_root)
        root = str(plugin_root or self.plugin_root)
        # Claude Code substitutes ${CLAUDE_PLUGIN_ROOT} into the command text.
        command = (command or SESSION_START_COMMAND).replace(
            "${CLAUDE_PLUGIN_ROOT}", root
        )
        return subprocess.run(
            [shell, "-c", command],
            check=False,
            capture_output=True,
            text=True,
            env=run_env,
            input=stdin
            or json.dumps(
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
        self.assertIn('"/succinct off" turns it off for future sessions', result.stdout)
        self.assertIn("## 1. Lead with the answer", result.stdout)
        self.assertIn("references/patterns.md", result.stdout)
        self.assertIn("references/plain-english.md", result.stdout)
        self.assertIn("The core stands alone", result.stdout)
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
        self.assertIn("## 1. Lead with the answer", result.stdout)

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

    def test_codex_hook_declares_sh_and_windows_commands(self):
        claude_session_start = CLAUDE_HOOKS["hooks"]["SessionStart"][0]
        codex_session_start = CODEX_HOOKS["hooks"]["SessionStart"][0]

        self.assertEqual(claude_session_start["matcher"], codex_session_start["matcher"])
        self.assertEqual("command", CODEX_SESSION_START["type"])
        self.assertEqual(30, CODEX_SESSION_START["timeout"])
        command = CODEX_SESSION_START["command"]
        windows = CODEX_SESSION_START["commandWindows"]
        # Codex sets CLAUDE_PLUGIN_ROOT as an environment variable instead of
        # substituting it into the command text, so sh expands it but cmd.exe
        # needs its own syntax.
        self.assertIn('sh "$CLAUDE_PLUGIN_ROOT/hooks/always-on.sh" --codex', command)
        self.assertTrue(command.strip().endswith("exit 0"))
        self.assertIn("%CLAUDE_PLUGIN_ROOT%\\hooks\\always-on.ps1", windows)
        self.assertIn("-SkipShellCheck -Codex", windows)
        self.assertTrue(windows.strip().endswith("exit /b 0"))
        for text in (command, windows):
            self.assertNotIn("node", text)

    def test_codex_sh_command_injects_the_ruleset(self):
        self.opt_in(codex=True)

        result = self.run_session_start_command(
            path_without("node"), command=CODEX_SESSION_START["command"]
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("SUCCINCT MODE ACTIVE (always-on).", result.stdout)
        self.assertIn("## 1. Lead with the answer", result.stdout)

    def test_codex_powershell_command_skips_the_sh_check(self):
        # Codex runs the PowerShell hook on its own, so a POSIX shell on PATH
        # does not mean the ruleset was already injected.
        if shutil.which("sh") is None:
            self.skipTest("no sh on PATH, so the plain deferral test covers this")
        self.opt_in(codex=True)

        result = self.run_powershell(extra_args=("-SkipShellCheck", "-Codex"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertIn("SUCCINCT MODE ACTIVE (always-on).", result.stdout)

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

    # The flag file is the whole saved state: "/succinct on" creates it,
    # "/succinct off" deletes it, and every session starts from it.

    def test_succinct_on_creates_the_flag_and_the_next_session_starts_on(self):
        toggle = self.toggle("/succinct on")

        self.assertEqual(0, toggle.returncode, toggle.stderr)
        self.assertEqual("", toggle.stderr)
        self.assertTrue(self.flag().is_file())
        self.assertIn("The user ran /succinct on.", toggle.stdout)
        self.assertIn("SUCCINCT MODE ACTIVE (always-on).", self.run_sh().stdout)

    def test_succinct_on_keeps_an_existing_flag(self):
        self.opt_in()

        self.toggle("/Succinct:succinct  ON \n")

        self.assertTrue(self.flag().is_file())

    def test_succinct_off_deletes_the_flag_and_the_next_session_starts_off(self):
        self.opt_in()

        toggle = self.toggle("/succinct off")

        self.assertEqual(0, toggle.returncode, toggle.stderr)
        self.assertEqual("", toggle.stderr)
        self.assertFalse(self.flag().exists())
        self.assertIn("The user ran /succinct off.", toggle.stdout)
        self.assertIn("Stop applying the succinct ruleset", toggle.stdout)
        self.assertEqual("", self.run_sh().stdout)

    def test_succinct_off_without_a_flag_is_not_an_error(self):
        toggle = self.toggle("/succinct off")

        self.assertEqual(0, toggle.returncode, toggle.stderr)
        self.assertIn("The user ran /succinct off.", toggle.stdout)
        self.assertFalse(self.flag().exists())

    def test_toggle_writes_only_the_flag(self):
        self.toggle("/succinct on")

        self.assertEqual([".succinct-always"], sorted(p.name for p in self.config_dir.iterdir()))

    def test_session_only_prompts_leave_the_flag_alone(self):
        for opted_in in (False, True):
            if opted_in:
                self.opt_in()
            for prompt in (
                "/succinct",
                "$succinct",
                "stop succinct mode",
                "normal mode",
                "/succinct on the README, please",
                "please run /succinct off",
                "",
            ):
                with self.subTest(prompt=prompt, opted_in=opted_in):
                    result = self.toggle(prompt)

                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual("", result.stdout)
                    self.assertEqual("", result.stderr)
                    self.assertEqual(opted_in, self.flag().exists())

    def test_stop_phrase_keeps_the_next_session_on(self):
        self.opt_in()
        self.toggle("stop succinct mode")

        self.assertIn("SUCCINCT MODE ACTIVE (always-on).", self.run_sh().stdout)

    def test_toggle_ignores_input_that_is_not_json(self):
        shell = self.shell()
        if shell is None:
            self.skipTest("no sh runtime is available")
        result = subprocess.run(
            [shell, str(self.plugin_root / "hooks" / "toggle.sh")],
            check=False,
            capture_output=True,
            text=True,
            env=self.hook_env(),
            input="/succinct on",
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertFalse(self.flag().exists())

    def test_codex_toggle_uses_codex_home(self):
        toggle = self.toggle("$succinct on", codex=True)

        self.assertEqual(0, toggle.returncode, toggle.stderr)
        self.assertIn("The user ran $succinct on.", toggle.stdout)
        self.assertTrue(self.flag(codex=True).is_file())
        # Claude Code keeps its own flag.
        self.assertFalse(self.flag().exists())

        self.toggle("$succinct off", codex=True)
        self.assertFalse(self.flag(codex=True).exists())

    def test_codex_session_start_reads_codex_home(self):
        self.opt_in()
        self.assertEqual("", self.run_sh(extra_args=("--codex",)).stdout)

        self.opt_in(codex=True)
        result = self.run_sh(extra_args=("--codex",))
        self.assertIn("SUCCINCT MODE ACTIVE (always-on).", result.stdout)
        self.assertIn('"$succinct off" turns it off for future sessions', result.stdout)

    def test_claude_expansion_hook_matches_only_the_succinct_command(self):
        matcher = re.compile(CLAUDE_EXPANSION["matcher"])

        for name in ("succinct", "succinct:succinct"):
            self.assertTrue(matcher.search(name), name)
        for name in ("deploy", "succinct-extra", "other:succinct"):
            self.assertFalse(matcher.search(name), name)

    def test_claude_expansion_command_toggles_the_flag(self):
        def expansion(args):
            return json.dumps(
                {
                    "session_id": "test-session",
                    "hook_event_name": "UserPromptExpansion",
                    "expansion_type": "slash_command",
                    "command_name": "succinct",
                    "command_args": args,
                    "command_source": "plugin",
                    "prompt": f"/succinct {args}",
                }
            )

        on = self.run_session_start_command(
            path_without("node"), command=CLAUDE_TOGGLE_COMMAND, stdin=expansion("on")
        )
        self.assertEqual(0, on.returncode, on.stderr)
        self.assertIn("The user ran /succinct on.", on.stdout)
        self.assertTrue(self.flag().is_file())

        off = self.run_session_start_command(
            path_without("node"), command=CLAUDE_TOGGLE_COMMAND, stdin=expansion("off")
        )
        self.assertEqual(0, off.returncode, off.stderr)
        self.assertFalse(self.flag().exists())

    def test_codex_prompt_hook_declares_sh_and_windows_commands(self):
        self.assertNotIn("matcher", CODEX_HOOKS["hooks"]["UserPromptSubmit"][0])
        command = CODEX_PROMPT_SUBMIT["command"]
        windows = CODEX_PROMPT_SUBMIT["commandWindows"]

        self.assertIn('sh "$CLAUDE_PLUGIN_ROOT/hooks/toggle.sh" --codex', command)
        self.assertTrue(command.strip().endswith("exit 0"))
        self.assertIn("%CLAUDE_PLUGIN_ROOT%\\hooks\\toggle.ps1", windows)
        self.assertIn("-SkipShellCheck -Codex", windows)
        self.assertTrue(windows.strip().endswith("exit /b 0"))
        for text in (command, windows):
            self.assertNotIn("node", text)

    def test_codex_prompt_command_creates_the_flag(self):
        result = self.run_session_start_command(
            path_without("node"),
            command=CODEX_PROMPT_SUBMIT["command"],
            stdin=self.prompt_input("$succinct on"),
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(self.flag(codex=True).is_file())

    def test_powershell_toggle_matches_the_sh_toggle(self):
        without_sh = path_without("sh")
        if shutil.which("sh", path=without_sh) is not None:
            self.skipTest("cannot hide sh from PATH on this machine")

        for prompt, codex in (
            ("/succinct on", False),
            ("/succinct off", False),
            ("$succinct on", True),
            ("$succinct off", True),
        ):
            with self.subTest(prompt=prompt):
                before = self.flag(codex).exists()
                sh_result = self.toggle(prompt, codex=codex)
                sh_flag = self.flag(codex).exists()
                # Put the flag back the way it was so PowerShell does the same work.
                if before:
                    self.opt_in(codex)
                else:
                    self.flag(codex).unlink(missing_ok=True)
                ps_result = self.run_powershell(
                    self.hook_env(without_sh),
                    script="toggle.ps1",
                    extra_args=("-Codex",) if codex else (),
                    prompt=prompt,
                )

                self.assertEqual(0, ps_result.returncode, ps_result.stderr)
                self.assertEqual("", ps_result.stderr)
                self.assertEqual(
                    self.normalize(sh_result.stdout), self.normalize(ps_result.stdout)
                )
                self.assertEqual(sh_flag, self.flag(codex).exists())

    def test_powershell_toggle_leaves_the_flag_alone_for_session_only_prompts(self):
        without_sh = path_without("sh")
        self.opt_in()
        for prompt in ("/succinct", "stop succinct mode", "normal mode"):
            with self.subTest(prompt=prompt):
                result = self.run_powershell(
                    self.hook_env(without_sh), script="toggle.ps1", prompt=prompt
                )

                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual("", result.stdout)
                self.assertTrue(self.flag().is_file())

    def test_powershell_codex_flag_matches_the_sh_hook(self):
        without_sh = path_without("sh")
        if shutil.which("sh", path=without_sh) is not None:
            self.skipTest("cannot hide sh from PATH on this machine")
        skill_path = self.plugin_root / "skills" / "succinct" / "SKILL.md"
        skill_path.write_text("---\nname: fixture\n---\nFixture body.\n")

        for codex_flag in (False, True):
            with self.subTest(codex_flag=codex_flag):
                self.opt_in()
                if codex_flag:
                    self.opt_in(codex=True)
                else:
                    self.flag(codex=True).unlink(missing_ok=True)

                sh_result = self.run_sh(extra_args=("--codex",))
                ps_result = self.run_powershell(
                    self.hook_env(without_sh), extra_args=("-SkipShellCheck", "-Codex")
                )

                self.assertEqual(0, ps_result.returncode, ps_result.stderr)
                self.assertEqual("", ps_result.stderr)
                self.assertEqual(
                    self.normalize(sh_result.stdout), self.normalize(ps_result.stdout)
                )
                self.assertEqual(codex_flag, bool(sh_result.stdout))

if __name__ == "__main__":
    unittest.main()
