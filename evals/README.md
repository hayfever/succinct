# Evals

Paired response-quality evaluation: the same case is answered twice, once without the skill (`baseline`) and once with `skills/succinct/SKILL.md` injected into the prompt (`candidate`). A judge model grades blind and a release gate decides.

## Pipeline

```bash
# 1. Generate responses (one row per case, trial, condition).
python3 scripts/run_evals.py run --runner ollama-answer --condition baseline \
  --trials 1 --allow-unmetered --output evals/results/responses.jsonl
python3 scripts/run_evals.py run --runner ollama-answer --condition candidate \
  --condition-skill skills/succinct/SKILL.md \
  --trials 1 --allow-unmetered --output evals/results/responses.jsonl

# 2. Judge blind: responses get opaque labels, the judge never sees condition names.
python3 scripts/judge.py --responses evals/results/responses.jsonl \
  --runner ollama-judge --output evals/results/scores.jsonl

# 3. Aggregate and apply the release gate.
python3 scripts/run_evals.py score evals/results/scores.jsonl

# 4. Deterministic style check on candidate rows only.
python3 scripts/check_style.py evals/results/responses.jsonl \
  --condition candidate --strict
```

Runners are configured in `evals/runners.json`. `run_evals.py run --runner` names the model that answers; `judge.py --runner` names the model that grades. Answer with a plain chat runner and judge with a different, stronger model.

## Choosing runners

- **Answer with a plain chat model.** `ollama-answer` runs `scripts/chat_runner.py`, which sends one user message to an OpenAI-compatible `/v1/chat/completions` endpoint with no system prompt and no tools. Agent CLIs (`claude`, `omp`) send a coding-agent system prompt; without tools the model then announces tool calls instead of answering, and the CLI's text output concatenates those turns.
- **Judge with a different model family.** `judge.py --runner` is the grading model, separate from the runner that produced the answers. When both are the same model, it grades its own answers and one noisy verdict blocks the gate. `ollama-judge` grades with `kimi-k3:cloud` against `glm-5.3-flash:cloud` answers.
- **Text runners are unmetered**, so every `run` and `judge` call against them needs `--allow-unmetered`. `claude` reports cost through `claude --print --output-format json` and enforces `--budget-usd` per run.

`chat_runner.py` takes the prompt from its last argument (how `run_evals.py` passes it) or from stdin (how `judge.py` passes long judge prompts), and prints only the final assistant text, with any `<think>` block removed. Flags: `--model` (required), `--base-url` (default `http://127.0.0.1:11434/v1`), `--timeout` (default 300 seconds). A command in `runners.json` may use `{root}` for the repository root: runners execute in an empty scratch directory, so a relative script path would not resolve.

## Runners

| Runner | Cost control | Isolation |
| --- | --- | --- |
| `ollama-answer` (default) | none; local, needs `--allow-unmetered` | one user message, no system prompt, no tools |
| `ollama-judge` | none; local, needs `--allow-unmetered` | the same script, a different model family for grading |
| `omp` (local) | none; cap with `--budget-usd` and stop between conditions | `--profile eval-iso`, `--no-session --no-tools --no-rules --no-skills --no-extensions`; still sends an agent system prompt |
| `claude` (CI) | `--budget-usd` per invocation | `--setting-sources ""`, no tools, no session persistence |

The omp runner needs its profile seeded once with the main model catalog:

```bash
mkdir -p ~/.omp/profiles/eval-iso/agent
cp ~/.omp/agent/models.yml ~/.omp/profiles/eval-iso/agent/models.yml
```

## Adding cases

Append one JSON line per case to `evals/cases.jsonl` with `id`, `category`, `prompt`, `risk` (`low`, `medium`, `high`), and a non-empty `criteria` list. `python3 scripts/run_evals.py validate` checks the schema. Good criteria name observable behavior ("Restates the current step", "Does not invent a founding date"), not specific wording.

Every case must be answerable with no tools and no repository. The runner sees one prompt and nothing else, so inline any file content or command output the case needs, and say that the model cannot run commands. A case that needs repo access grades the harness, not the skill.

The rubric lives in `evals/rubric.md`. Everything between the `judge:begin` and `judge:end` markers goes verbatim to the grader; release-gate rules live outside that block so the judge stays blind to condition names.

## Style linter

`scripts/check_style.py` grades the mechanical tells without a model: chatbot residue, staged openers, closing pleasantry, dashes as connectors, curly quotes, Latin abbreviations, not-X-but-Y contrasts, and lists longer than five items. Code fences, inline code, and quoted spans are exempt, mirroring the skill's own quoted-text rule. It also works standalone on any text file:

```bash
python3 scripts/check_style.py some-text.md --strict
```

## Interpreting the gate

The release gate passes only when the candidate has no blocking findings, correctness and safety are each within 0.1 points of baseline or better, and the weighted score beats baseline. Documented runs live in `RESULTS.md`.