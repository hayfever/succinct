# Changelog

All notable changes to succinct are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org).

## [Unreleased]

### Breaking

- OpenCode 1 can no longer load the plugin. The OpenCode plugin now uses the OpenCode 2 plugin API.

### Changed

- The skill is now a 1,993-token core plus two reference files. `skills/succinct/references/patterns.md` keeps the full 25-tell catalog and `plain-english.md` keeps the STE detail. The core points to both and stands alone when they are not reachable. The Cursor mirror now copies the whole skill folder, and `scripts/build_adapters.py --check` catches reference drift.
- The core `skills/succinct/SKILL.md` is limited to 200 lines. `scripts/validate-package.py` checks the core rule numbering, the 25 tells, and the 15 STE rules in the references.
- Pi and OMP: the bare `/succinct` toggle and the stop phrases (`stop succinct mode`, `normal mode`) apply to the current session only. Only `/succinct on` and `/succinct off` save the choice for future sessions. This reverses the 1.1.0 behaviour, where every toggle wrote the choice to the agent config.
- The Pi/OMP extension writes `succinct.json` through a temporary file and a rename, so a concurrent session never reads a partial file. An unreadable file is reported once, left as it is, and the toggle stays session-only.
- OpenCode: the plugin moved from `.opencode/plugins/succinct.mjs` to `.opencode/plugins/succinct/index.js`. `opencode.json` uses the `plugins` and `skills` keys.
- The SessionStart hook no longer needs Node. `hooks/always-on.mjs` is removed. `hooks/always-on.sh` runs under `sh`, and `hooks/always-on.ps1` covers Windows without Git Bash. Codex reads `hooks/codex-hooks.json`, which gives its Windows shell `cmd.exe` a command that uses `%CLAUDE_PLUGIN_ROOT%`.
- Gemini CLI: the command moved to `commands/succinct.toml`, so the extension registers `/succinct`. `GEMINI.md` no longer imports the skill a second time.
- `LICENSE` is plain MIT. The third-party notices moved to `THIRD_PARTY_NOTICES.md`.
- CI: `validate.yml` runs the unit tests on Linux, macOS, and Windows, and adds runtime load jobs for Claude Code, Codex, Gemini CLI, OpenCode, OMP, and Pi. `release.yml` calls `validate.yml` before it drafts a release. Every action is pinned to a commit SHA, and Dependabot updates the pins.
- The Codex marketplace entry points at the local plugin root. `INSTALL.md` documents the Codex hook trust step and the always-on snippet route for Codex.
- `README.md` shows a before/after example and the current install commands.

### Fixed

- The PowerShell always-on hook skipped when `sh` was on PATH. The Codex hook passes `-SkipShellCheck`, so its Windows hook injects the ruleset even when Git Bash is installed.
- The Pi section of `INSTALL.md` closed its `<details>` block late, which swallowed the OMP section.

## [2.0.0] - 2026-11-14

### Breaking

- The rename removes `/blunt`, `--blunt`, and `stop blunt mode` with no alias. Use `/succinct`, `--succinct`, and `stop succinct mode` instead. This is why the version jumps to 2.0.0.

### Changed

- Renamed the project from blunt to succinct. The package name, skill name, skill path, command, launch flag, stop phrase, and state files changed. The ruleset did not.
- Skill entry point moved from `skills/blunt/SKILL.md` to `skills/succinct/SKILL.md`. The Cursor mirror moved to `.cursor/skills/succinct/SKILL.md`.
- Extension file is now `extensions/succinct.ts`. The OpenCode plugin is `.opencode/plugins/succinct.mjs` and its command is `.opencode/command/succinct.md`.
- Command is `/succinct`. Launch flag is `--succinct`. Stop phrase is `stop succinct mode`. `normal mode` still works.
- Always-on flag file is `.succinct-always`. The persisted toggle file is `succinct.json`.

### Migration

- Delete the old `.blunt-always` flag file and create `.succinct-always` in the same directory to keep always-on.
- `/blunt`, `--blunt`, and `stop blunt mode` no longer work. There is no alias.
- The old `blunt.json` toggle file is ignored. Run `/succinct` once to save the preference.

## [1.1.0] - 2026-09-16

### Added

- Persisted `/blunt` preference: every toggle (`/blunt`, `/blunt on|off`, `stop blunt mode`) writes the choice to the agent config, so future OMP and Pi sessions start in the same mode without re-running the command. A session's own history and `--blunt` still win for the current run.

### Changed

- `stop blunt mode` and `normal mode` now persist the OFF choice too: earlier 1.0.0 sessions forgot the mode between sessions; 1.1.0 remembers it until you run `/blunt` again.
- `/blunt` command description and mode notifications now state the persisted behavior.

## [1.0.0] - 2026-09-09

### Added

- One ruleset: ten ADHD-friendly shape rules, twenty-five AI-writing tells with the never-invent-a-fact law (tell inventory from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)), and fifteen plain-English rules summarized from [ASD-STE100](https://www.asd-ste100.org) Issue 9.
- Canonical Agent Skills entry point `skills/blunt/SKILL.md`, installable by every harness that reads agent skills (Claude Code, Codex, Gemini CLI, GitHub Copilot, Hermes, Kimi, OpenCode, Pi, OMP, Qwen Code, Zed, Cursor, Antigravity, Amp).
- Plugin manifests for the Claude/Codex/OMP marketplaces, native Pi and OMP extension with session-persistent mode, OpenCode plugin, Claude Code/Codex SessionStart hooks, and per-agent always-on routes.
- `/blunt` toggle with `--blunt` launch flag, `stop blunt mode` deactivation, and compaction-safe ruleset re-injection.
- Test harness: package consistency validator, cross-runtime unit tests, extension RPC smoke tests with no model calls, paired baseline-vs-candidate evals with a blind judge and release gate, and a deterministic style linter.
- GitHub Actions: `validate.yml` on every push and pull request, `evals.yml` on manual dispatch.

[Unreleased]: https://github.com/hayfever/succinct/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/hayfever/succinct/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/hayfever/succinct/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/hayfever/succinct/releases/tag/v1.0.0
