<p align="center"><img src="docs/succinct-banner.webp" alt="succinct: answer first, next action last, sound human, write plain" width="100%"></p>

<p align="center">
  <a href="https://github.com/hayfever/succinct/actions/workflows/validate.yml"><img src="https://github.com/hayfever/succinct/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/hayfever/succinct/releases/latest"><img src="https://img.shields.io/github/v/release/hayfever/succinct?sort=semver" alt="Release"></a>
</p>

An output style for coding agents, built for readers with ADHD: answer first, end on the next action, sound like a person, write plain English.

## Before

> Great question! Let me think about this. It's not just about the middleware, it's about trust. Your auth flow has a few moving pieces: the middleware, the token verification, and the cookie handling. Looking at `src/auth.ts`, the `verifyToken` function (around lines 42-58) seems to be using an older `jsonwebtoken` API — one approach would be to update the package. After making the change, you'd want to run the auth tests to confirm nothing breaks. Hope this helps! Let me know if you want to dig deeper.

## After

> Update `jsonwebtoken`, then edit `verifyToken` at `src/auth.ts:42` to match the current API.
>
> 1. Open `src/auth.ts`
> 2. Replace `verifyToken` (lines 42 to 58) with the current `jsonwebtoken` call
> 3. Run `npm test -- auth.spec.ts` to confirm the auth tests pass
>
> The auth flow has three parts: middleware, token verification, cookie handling. `verifyToken` uses the older `jsonwebtoken` API.

The rewrite keeps every claim from the original and adds none. That is the work the skill does, in three parts:

- **Shape.** Ten rules that shape every response for an ADHD reader: answer first, steps numbered, next action last, no "Hope this helps!"
- **Sound human.** 25 patterns that mark text as machine-made, from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). Strip them; keep every supported claim; never invent a fact.
- **Stay plain.** Simplified Technical English, the controlled writing standard behind aerospace maintenance docs: active voice, imperative steps, 20-word steps, one term per item, no semicolons.

The standard itself is free to download from ASD; this skill summarizes its Part 1 writing rules and does not reproduce the dictionary.

## Install

Claude Code:

```bash
claude plugin marketplace add hayfever/succinct
claude plugin install succinct@succinct
```

Codex:

```bash
codex plugin marketplace add hayfever/succinct --ref main
codex plugin add succinct@succinct
```

Every harness, with the command to type after install:

| Harness | Install | Type | Always-on | INSTALL |
|---|---|---|---|---|
| Claude Code | see block above | `/succinct` | flag file, `succinct.json` | [Claude Code](INSTALL.md#claude-code) |
| Codex | see block above | `$succinct` | flag file, `succinct.json` | [Codex](INSTALL.md#codex) |
| Gemini CLI | `gemini extensions install https://github.com/hayfever/succinct` | `/succinct` | snippet | [Gemini CLI](INSTALL.md#gemini-cli) |
| Kimi Code | `/plugins install https://github.com/hayfever/succinct` | `/skill:succinct:succinct` | snippet | [Kimi Code](INSTALL.md#kimi-code) |
| Qwen Code | `qwen extensions install hayfever/succinct` | `/succinct:succinct` | snippet | [Qwen Code](INSTALL.md#qwen-code) |
| OpenCode 2 | see INSTALL | `/succinct` | flag file | [OpenCode](INSTALL.md#opencode) |
| Pi | `pi install https://github.com/hayfever/succinct` | `/succinct` | flag file, `succinct.json` | [Pi](INSTALL.md#pi) |
| OMP | see INSTALL | `/succinct` | flag file, `succinct.json` | [OMP](INSTALL.md#omp) |
| Cursor | `npx skills add hayfever/succinct -a cursor -y` | `/succinct` | snippet, user rules | [Cursor and Amp](INSTALL.md#agent-skills-harnesses) |
| GitHub Copilot | `npx skills add hayfever/succinct -a github-copilot` | `/succinct` | snippet | [GitHub Copilot](INSTALL.md#github-copilot) |
| Zed | see INSTALL, Skills manager URL | `/succinct` | snippet | [Zed](INSTALL.md#zed) |
| Antigravity | `agy plugin install https://github.com/hayfever/succinct` | none documented | snippet | [Antigravity](INSTALL.md#antigravity) |
| Hermes | `hermes skills install hayfever/succinct/skills/succinct` | `/succinct` | snippet | [Hermes](INSTALL.md#hermes) |
| Amp | `npx skills add hayfever/succinct` | `/succinct` | snippet | [Cursor and Amp](INSTALL.md#agent-skills-harnesses) |
| Any skills CLI agent | `npx skills add hayfever/succinct` | `/succinct` | snippet | [Any skills CLI agent](INSTALL.md#agent-skills-harnesses) |

Always-on: "snippet" means the rules go in the agent's persistent rules file (`CLAUDE.md`, `AGENTS.md`, Cursor user rules, and so on). One copy lives in [INSTALL.md](INSTALL.md#always-on-snippet). "Flag file" is the one-line version: a `SessionStart` hook or extension loads the full ruleset at session start. Each section in INSTALL.md shows the exact path.

Rules stay on until "stop succinct mode" or "normal mode". In Claude Code, Codex, Pi, and OMP, `/succinct on` or `/succinct off` (`$succinct on` or `$succinct off` in Codex) saves the choice in `succinct.json` for future sessions, and it outranks the flag file. The stop phrases and a bare `/succinct` change only the current session. In Pi and OMP, the footer shows `● SUCCINCT ON` while the mode is active, and `pi --succinct` starts with the mode on.

## Supported harnesses

| Harness | Loads | Status |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json` | manifest checked in CI |
| Codex | `.codex-plugin/plugin.json` | loads in CI |
| Gemini CLI | `gemini-extension.json` | loads in CI |
| Kimi Code | `kimi.plugin.json` | install documented |
| Qwen Code | `qwen-extension.json` | install documented |
| OpenCode | `opencode.json` | loads in CI |
| Pi | `package.json` | loads in CI |
| OMP | `package.json` | loads in CI |
| Cursor | `.cursor/skills/succinct/SKILL.md` | install documented |
| GitHub Copilot | `skills/succinct/SKILL.md` | install documented |
| Zed | `skills/succinct/SKILL.md` | install documented |
| Amp | `skills/succinct/SKILL.md` | install documented |
| Antigravity | `plugin.json` | install documented |
| Hermes | `skills/succinct/SKILL.md` | install documented |
| Skills CLI | `skills/succinct/SKILL.md` | install documented |

Every plugin row resolves to `skills/succinct/SKILL.md`, the canonical ruleset. "Loads in CI" means a job in `.github/workflows/validate.yml` installs the latest harness CLI and loads this checkout with no model request. For Claude Code, CI runs `claude plugin validate . --strict` on the manifests. "Install documented" means the route in [INSTALL.md](INSTALL.md) is written out, but CI does not run that harness.

Edit only `skills/succinct/SKILL.md` and its `references/`. Run `python3 scripts/build_adapters.py` to rebuild the generated files.

## The rules

The [canonical skill](skills/succinct/SKILL.md) is a 164-line core in three parts. Two reference files hold the full detail.

- Shape: ten rules that make an answer actable for a reader with ADHD, from the answer in line one and the next action in the last line to the five-item list cap. ([Part 1](skills/succinct/SKILL.md#part-1-shape-the-response))
- Sound human: 25 patterns that mark text as machine-made, strongest first, from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). The core carries the five strongest. The full catalog is in [references/patterns.md](skills/succinct/references/patterns.md). Keep every supported claim; never invent a fact. ([Part 2](skills/succinct/SKILL.md#part-2-sound-like-a-person))
- Write plain: Simplified Technical English, the controlled standard behind aerospace maintenance docs. Active voice, imperative steps, steps of 20 words or fewer, one term per item. Replacement lists are in [references/plain-english.md](skills/succinct/references/plain-english.md). ([Part 3](skills/succinct/SKILL.md#part-3-write-plain-simplified-technical-english))

### What it costs

The core `SKILL.md` is 164 lines, 1,378 words, and 2,080 tokens with the o200k tokenizer. That is about 1 percent of a 200,000-token context window, added once when the skill loads. The references load only when the model needs them: `patterns.md` is 2,046 tokens and `plain-english.md` is 1,141 tokens.

Before the split, the single file was 5,589 tokens. The up-front load is 63 percent smaller.

Every harness above loads the core file. The ASD standard is a free download; this skill summarizes its writing rules and does not reproduce the dictionary.

## Tune it

Fork the repo, edit `skills/succinct/SKILL.md`, then reinstall from your fork. Every harness in the table installs a fork the same way: swap `hayfever/succinct` for `owner/repo`.

Claude Code, as an example:

```bash
claude plugin uninstall succinct            # drop the upstream copy first:
claude plugin marketplace remove succinct   # fork and upstream share both names
claude plugin marketplace add <your-username>/succinct
claude plugin install succinct@succinct
```

Restart the harness, then invoke the skill again.

## Results

Paired eval of the shipped core on 17 cases, 3 trials per case, judged blind: baseline weighted 4.48, candidate weighted 4.75. The candidate carries no blocking finding and the baseline carries one. The candidate loaded only the core `SKILL.md`, with no reference file. Numbers, per-dimension means, earlier rounds, and the gate rule: [evals/RESULTS.md](evals/RESULTS.md).

## Credits

- [i-have-adhd](https://github.com/ayghri/i-have-adhd) by Ayoub G. (MIT), based on *The Adult ADHD Tool Kit* by J. Russell Ramsay and Anthony L. Rostain.
- [humanizer](https://github.com/blader/humanizer) by blader (MIT), patterns from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
- [ASD-STE100 Issue 9](https://www.asd-ste100.org) by the ASD Simplified Technical English Maintenance Group (free download; summarized, not reproduced).

## License

MIT. Full third-party notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
