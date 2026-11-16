# Contributing to succinct

Thanks for considering a contribution. This repository is small and opinionated: one skill file, cross-runtime packaging, a test harness, and paired evals. Changes stay small and verified.

## Project rules

The skill:

1. `skills/succinct/SKILL.md` plus `skills/succinct/references/` are the single source of truth. Everything else mirrors, wraps, or validates them.
2. Keep `SKILL.md` at 200 lines or fewer. Detail belongs in `skills/succinct/references/`. A skill the model skims beats a skill it ignores.
3. Every sentence in the skill obeys the skill. No em dashes, no chatbot residue, steps of 20 words or fewer.

The package:

1. Keep manifests aligned: `name`, `version`, `description`, `license`, and `homepage` agree across `package.json` and `kimi.plugin.json`; all manifests share one version. `scripts/validate-package.py` enforces the critical subset.
2. Change the canonical skill first, then run `python3 scripts/build_adapters.py` to rebuild the Cursor mirror and manifest versions. The validator fails on drift.
3. The toggle phrases ("stop succinct mode", "normal mode"), the flag file (`.succinct-always`), and the command (`/succinct`) are cross-runtime contracts. Do not rename them casually; update every runtime in the same commit.

## Development setup

No build step and no install step. You need Python 3.10+, Node 24, and Bun.

```bash
git clone https://github.com/hayfever/succinct
cd succinct
python3 scripts/validate-package.py
python3 scripts/build_adapters.py --check
python3 -m unittest discover -s tests -v
bun test tests/
bun build extensions/succinct.ts --target=bun \
  --external '@earendil-works/pi-coding-agent' --outfile /tmp/succinct.js
node --check .opencode/plugins/succinct/index.js
```

CI's package job also parses every JSON, YAML, and TOML manifest. A syntax error fails that job before any runtime job starts.

With the runtimes installed locally, also run:

```bash
claude plugin validate . --strict
python3 scripts/check_extension.py --runtime pi
python3 scripts/check_extension.py --runtime omp
```

## Pull requests

1. One change per pull request.
2. Run the checks above and paste the output into the PR description.
3. Bump the version with `python3 scripts/bump-version.py <new-version>`. It sets `package.json`, regenerates the skill metadata, every manifest version, and the Cursor mirror, then fails if a stale version string remains anywhere else.
4. Move the `CHANGELOG.md` entry from "Unreleased" into a new section for the version you ship.
5. Behavior changes to the skill need an eval delta: add or update a case in `evals/cases.jsonl`, run the paired eval, and attach `evals/results/gate.json` to the PR.

The fastest review path: change the skill, add a case that fails without the change, show the gate passing with it.

## Adding an eval case

Each line of `evals/cases.jsonl` is one JSON object with `id`, `category`, `prompt`, `risk` (`low`, `medium`, or `high`), and a non-empty `criteria` list. Good criteria name observable behavior, not wording. Run a smoke pass before opening a PR:

```bash
python3 scripts/run_evals.py run --runner omp --condition candidate \
  --condition-skill skills/succinct/SKILL.md --case <your-id> --trials 1 \
  --allow-unmetered --output evals/results/responses.jsonl
```

## Adding an agent integration

1. Read `INSTALL.md` and find the agent's install mechanics.
2. Add the smallest manifest that makes the agent install the package, and one unit test in `tests/test_package.py` asserting the manifest contract.
3. Document Install, Verify, Update, Uninstall, and Always-on in `INSTALL.md`, and keep the always-on snippet a link to the one canonical copy.
4. If the agent can load extensions, prefer pointing at the canonical `skills/succinct/SKILL.md` over duplicating the ruleset.

## Reporting issues

Open an issue with the agent name, install method, plugin version, and the exact behavior you saw. Style disagreements about the rules themselves are welcome as issues too; the eval suite is how we settle them.