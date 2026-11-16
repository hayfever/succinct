# Changelog

All notable changes to succinct are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org).

## [1.0.0] - 2026-11-15

First release of succinct: one output style for coding agents. It puts the answer first and the next action last, strips AI writing tells, and writes technical text in plain Simplified Technical English.

### The skill

- The skill is a 164-line core, `skills/succinct/SKILL.md`, at 2,080 o200k tokens. Two reference files load only on demand: `references/patterns.md` has the full 25-tell catalog, and `references/plain-english.md` has the STE detail and replacement lists. The core stands alone when the references do not resolve.
- Part 1 has ten shape rules for an ADHD reader: the answer first, numbered steps, one concrete next action last, no tangents, state restated every turn, specific time estimates, visible wins, matter-of-fact errors, lists capped at five items, and no preamble or recap.
- Every response obeys three more rules. A compressed rule must keep its full meaning. No dash is a connector in prose (em dash, en dash, " -- ", " - "). No response ends with a pleasantry or a stock offer. An explicit output contract ("return only X", a word limit, an exact format) overrides the skill habits.
- Part 2 removes the five strongest AI writing tells and never invents a fact. The tell inventory comes from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
- Part 3 summarizes the writing rules of [ASD-STE100](https://www.asd-ste100.org) Issue 9. It does not reproduce the dictionary.

### Harnesses

- Install routes for Claude Code, Codex, OpenCode 2, Pi, and OMP, plus `npx skills add` for any skills CLI agent and an always-on snippet for other agents. `INSTALL.md` has each route.
- One activation model in all five harnesses. `/succinct` turns the mode on for the current session (`$succinct` in Codex). `/succinct on` creates a `.succinct-always` flag file and `/succinct off` deletes it. Every session starts from the flag. "stop succinct mode" or "normal mode" turns the mode off for the current session only. In Pi and OMP, the footer shows `● SUCCINCT ON`, and `pi --succinct` starts with the mode on.
- Claude Code and Codex read the flag in a `SessionStart` hook and set it in a prompt hook (`hooks/always-on.sh`, `hooks/toggle.sh`, their PowerShell versions, and `hooks/codex-hooks.json` for Codex). No hook needs Node.

### Tooling

- `scripts/build_adapters.py` generates the skill metadata version and every manifest version from `package.json`. `--check` fails on drift. `scripts/validate-package.py` checks frontmatter, versions, paths, rule numbering, and drift.
- CI runs the unit tests on Linux, macOS, and Windows, and load checks for Claude Code, Codex, OpenCode, OMP, and Pi with no model request. `release.yml` drafts a release only after the full matrix passes.
- Paired evals: 17 cases, 3 trials, a blind judge, and a relative release gate. The shipped core scored 4.75 against a 4.48 baseline with no blocking finding. See `evals/RESULTS.md`.

[1.0.0]: https://github.com/hayfever/succinct/releases/tag/v1.0.0
