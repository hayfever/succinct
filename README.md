[![Validate](https://github.com/hayfever/succinct/actions/workflows/validate.yml/badge.svg)](https://github.com/hayfever/succinct/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/hayfever/succinct?sort=semver)](https://github.com/hayfever/succinct/releases/latest)

# succinct

One output style for coding agents: lead with the next action, sound like a person, write plain English.

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

- **Shape.** Ten rules that shape every response for an ADHD reader: action first, steps numbered, no "Hope this helps!"
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
codex plugin marketplace add hayfever/succinct
codex plugin add succinct@succinct
```

Any agent, through the skills CLI:

```bash
npx skills add hayfever/succinct
```

Gemini CLI, Kimi Code, Qwen Code, OpenCode, Pi, OMP, Cursor, GitHub Copilot, Zed, Antigravity, and Amp have their own routes. See [INSTALL.md](INSTALL.md).

## Activate

Type the command for your harness:

- `/succinct` in Claude Code, Gemini CLI, OpenCode, Pi, and OMP
- `$succinct` in Codex
- `/succinct:succinct` in Qwen Code (extension skills carry the extension name)
- `/skill:succinct:succinct` in Kimi Code

Rules stay on until "stop succinct mode" or "normal mode". In Pi and OMP, the footer shows `● SUCCINCT ON` while the mode is active, and `pi --succinct` starts with the mode on.

## The rules

**Shape (10 rules).** Lead with the next action. Number multi-step tasks. End with one concrete next action. Suppress tangents. Restate state every turn. Specific time estimates. Make wins visible. Matter-of-fact errors. Cap lists at 5 items. No preamble, no recap, no closers.

**Sound human (25 tells).** Cut the machine habits, strongest first: not-X-but-Y contrasts, one-line closers, sayings that sound deep, staged run-ups, arguing with no one, forced triads, repeated openings, dashes everywhere, stacked qualifiers, hyphenated pairs, passive voice, stock AI words ("delve", "pivotal", "robust"), inflated significance, vague connections, shallow -ing riders, sales language, borrowed authority, avoiding "is/are/has", bold decoration, decorative headings, curly quotes, chatbot residue, knowledge-limit guesses, heading echoes, and writing about the previous version.

**Write plain (STE).** One word, one meaning ("ensure" becomes "make sure", "perform" becomes "do", "shall" becomes "must"). No phrasal verbs. Verbs act; nouns sit. Active voice; imperative steps. 20 words per step, 25 per description. No semicolons. Keep articles, subjects, and "that". No contractions. Conditions first, then the command. One technical term per item. Multi-word nouns of three words or fewer.

The source of truth is [skills/succinct/SKILL.md](skills/succinct/SKILL.md). Every harness above loads that one file.

## Always-on

Every agent has a persistent-rules route. Paste the always-on snippet from [INSTALL.md](INSTALL.md#always-on-snippet) into your agent's rules file (`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, Cursor user rules, and so on). Claude Code, Codex, OpenCode, and Pi/OMP also support flag-file always-on; see each agent's section.

## Tune it

Fork, edit `skills/succinct/SKILL.md`, then swap your copy in:

```bash
claude plugin uninstall succinct            # drop the upstream copy first:
claude plugin marketplace remove succinct   # fork and upstream share both names
claude plugin marketplace add <your-username>/succinct
claude plugin install succinct@succinct
```

Restart Claude Code, then re-invoke `/succinct`.

## Results

Paired eval on 17 cases, 3 trials per case, judged blind: baseline weighted 4.46, candidate weighted 4.76. The candidate carries one blocking finding, a wrong PKCE test vector, and the baseline carries two. Numbers, per-dimension means, and gate rule: [evals/RESULTS.md](evals/RESULTS.md).

## Credits

- [i-have-adhd](https://github.com/ayghri/i-have-adhd) by Ayoub G. (MIT), based on *The Adult ADHD Tool Kit* by J. Russell Ramsay and Anthony L. Rostain.
- [humanizer](https://github.com/blader/humanizer) by blader (MIT), patterns from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
- [ASD-STE100 Issue 9](https://www.asd-ste100.org) by the ASD Simplified Technical English Maintenance Group (free download; summarized, not reproduced).

## License

MIT. Full third-party notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
