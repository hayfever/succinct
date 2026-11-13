# Changelog

All notable changes to succinct are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org).

## [1.2.0] - 2026-11-13

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

[1.2.0]: https://github.com/hayfever/succinct/releases/tag/v1.2.0
[1.1.0]: https://github.com/hayfever/succinct/releases/tag/v1.1.0
[1.0.0]: https://github.com/hayfever/succinct/releases/tag/v1.0.0
