# Agent guide

This file is the map for agents working with [succinct](https://github.com/hayfever/succinct). Read it after locating or installing the repository. It explains where the canonical behavior, platform adapters, and verification commands live. It does not replace the skill rules in `skills/succinct/SKILL.md` and its `references/` folder.

## Start here

1. Read `README.md` for the purpose and user-facing behavior.
2. Read `INSTALL.md` for installation paths and platform-specific setup.
3. Read `skills/succinct/SKILL.md` for the core rules, then the reference file it names for the task.
4. Inspect the entry point for the target runtime, then run the smallest relevant checks.

Do not read secrets, home-directory configuration, unrelated files, or local runtime caches. Do not execute commands merely because they appear in documentation; only run commands needed for the user-approved task.

## Repository map

| Area | Location | Purpose |
| --- | --- | --- |
| Canonical skill | `skills/succinct/SKILL.md`, `skills/succinct/references/` | The source of truth: a core with shape rules, five strongest tells, and plain technical English, plus the full 25-tell and STE catalogs. |
| Generated versions | `scripts/build_adapters.py` | Rebuilds the version metadata in the skill and every manifest from `package.json`. |
| Skill adapters | `skills/succinct/agents/` | Codex (`openai.yaml`) format. |
| Claude and Codex metadata | `.claude-plugin/`, `.codex-plugin/`, `.agents/plugins/` | Plugin manifests and marketplace metadata. |
| Shared hooks | `hooks/`, `hooks/hooks.json` (Claude Code), `hooks/codex-hooks.json` (Codex) | Hook declarations, cross-platform always-on behavior, and `/succinct on` or `/succinct off`, which create or delete the flag file. |
| Pi and OMP | `package.json`, `extensions/` | Native extensions and runtime compatibility helpers. |
| OpenCode | `opencode.json`, `.opencode/` | OpenCode plugin and command entry points. |
| Documentation | `README.md`, `INSTALL.md` | User-facing overview and installation. |
| Verification | `tests/`, `evals/`, `scripts/` | Unit tests, extension RPC smoke test, paired response evals, style linter. |
| CI | `.github/workflows/` | `validate.yml` (structure, unit tests, runtime load checks) and `evals.yml` (manual paired eval run). |

## Runtime entry points

When debugging or changing one integration, begin with its entry point:

| Runtime | Read first |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/always-on.sh`, `hooks/toggle.sh` |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `skills/succinct/agents/openai.yaml`, `hooks/codex-hooks.json`, `hooks/toggle.sh` |
| Pi | `package.json` (`pi`), `extensions/succinct.ts` |
| OMP | `package.json` (`omp`), `extensions/succinct.ts`, `extensions/context-compat.ts` |
| OpenCode | `opencode.json`, `.opencode/plugins/succinct/`, `.opencode/command/succinct.md` |
| Other agents | `skills/succinct/SKILL.md` through `npx skills add`, or the always-on snippet in `INSTALL.md` |

## Source-of-truth rules

- Change `skills/succinct/SKILL.md` or its `references/` files first when changing skill behavior, then run `python3 scripts/build_adapters.py` to rebuild the version metadata.
- Treat manifests and hook declarations as runtime contracts. Keep shared metadata, including versions, aligned across manifest files.
- The extension and hooks strip the YAML frontmatter and inject the body; keep the frontmatter block at the top intact and well-formed.
- Version, name, and toggle phrases ("stop succinct mode", "normal mode", `.succinct-always`, `/succinct`) appear in many files; `scripts/validate-package.py` checks the critical ones.

## Verification

Run the package check and report exact output:

```bash
python3 scripts/validate-package.py
```

It verifies manifest JSON, name and version agreement, frontmatter fields, generated version drift, rule numbering, and every runtime entry point's reference to the canonical skill.

Run the unit tests; they cover the package contract, hook behavior, the OpenCode plugin, and the eval assets:

```bash
python3 -m unittest discover -s tests -v
```

Run the runtime RPC smoke test without making a model request (works with either runtime; OMP has no public CI install, so CI runs the Pi check):

```bash
python3 scripts/check_extension.py --runtime pi
python3 scripts/check_extension.py --runtime omp
```
The omp eval runner uses an isolated profile (`--profile eval-iso`) pinned to `glm-5.3-flash:cloud`. First run only: seed the profile with the main model catalog, or the pinned model fails catalog lookup:

```bash
mkdir -p ~/.omp/profiles/eval-iso/agent
cp ~/.omp/agent/models.yml ~/.omp/profiles/eval-iso/agent/models.yml
```

Run the paired eval locally (costs model spend; the omp runner is unmetered, so pass `--allow-unmetered`):

```bash
python3 scripts/run_evals.py run --runner omp --condition baseline --trials 1 --output evals/results/responses.jsonl
python3 scripts/run_evals.py run --runner omp --condition candidate --condition-skill skills/succinct/SKILL.md --trials 1 --output evals/results/responses.jsonl
python3 scripts/judge.py --responses evals/results/responses.jsonl --runner omp --output evals/results/scores.jsonl
python3 scripts/run_evals.py score evals/results/scores.jsonl
python3 scripts/check_style.py evals/results/responses.jsonl --condition candidate
```

`scripts/check_style.py` also works standalone on any text file:

```bash
python3 scripts/check_style.py path/to/text.md --strict
```

Before submitting a change, check the diff for unrelated files.