# Eval results

Every documented run lists cases, models, trials, rubric, and release-gate result. Public performance claims must reproduce a row of this table with the same inputs.

## 2026-11-15-slim

This run measures the shipped core. The candidate loaded only `skills/succinct/SKILL.md` (2,055 tokens). No reference file was loaded, so this is the worst case for the split skill.

| Field | Value |
| --- | --- |
| Cases | 17 (`evals/cases.jsonl`) |
| Trials | 3 per case per condition, 51 judged rows per condition |
| Runner | `ollama-answer`, model `glm-5.3-flash:cloud`, one user message, no system prompt, no tools |
| Judge | `ollama-judge`, model `kimi-k3:cloud`, blind labels |
| Rubric | `evals/rubric.md` (correctness 35%, autonomy 25%, actionability 20%, safety 10%, concision 10%) |
| Candidate skill | Core `SKILL.md` only, no `references/` files |
| Baseline weighted | 4.48 |
| Candidate weighted | 4.75 |
| Blocking findings | Baseline 1, candidate 0 |
| Style violations (candidate) | 0 of 51 rows |
| Release gate | Passed under the relative rule |

Per-dimension means:

| Dimension | Baseline | Candidate |
| --- | ---: | ---: |
| Correctness | 4.49 | 4.53 |
| Autonomy | 4.78 | 4.90 |
| Actionability | 4.37 | 4.86 |
| Safety | 4.86 | 4.88 |
| Concision | 3.49 | 4.80 |

The core scores within 0.01 of the full 5,589-token skill in round 4 (4.75 against 4.76) and carries no blocker.

## 2026-11-15-r4

This run measured the full single-file skill before the split into a core and references.

| Field | Value |
| --- | --- |
| Cases | 17 (`evals/cases.jsonl`) |
| Trials | 3 per case per condition, 51 judged rows per condition |
| Runner | `ollama-answer`, model `glm-5.3-flash:cloud`, one user message, no system prompt, no tools |
| Judge | `ollama-judge`, model `kimi-k3:cloud`, blind labels |
| Rubric | `evals/rubric.md` (correctness 35%, autonomy 25%, actionability 20%, safety 10%, concision 10%) |
| Baseline weighted | 4.46 |
| Candidate weighted | 4.76 |
| Blocking findings | Baseline 2, candidate 1 |
| Style violations (candidate) | 0 of 51 rows |
| Release gate | Passed under the relative rule |

Per-dimension means:

| Dimension | Baseline | Candidate |
| --- | ---: | ---: |
| Correctness | 4.53 | 4.59 |
| Autonomy | 4.78 | 4.84 |
| Actionability | 4.26 | 4.94 |
| Safety | 4.92 | 4.86 |
| Concision | 3.37 | 4.67 |

Rounds 1 to 3 (`2026-11-15`, `2026-11-15-r2`, `2026-11-15-r3`) gave the same picture: the candidate scored higher and carried fewer blockers than baseline.

The remaining candidate blocker is a wrong PKCE test vector in `long-form-request` trial 2, where the model trusted its memory of RFC 7636 instead of matching the printed challenge.

### Caveats

- One model family answered and another judged, so these numbers describe that pairing, not every coding agent.
- The gate compares the candidate with the baseline. It does not require zero blockers, because the baseline does not have zero either. Both counts and every candidate blocker stay in the `score` output.
