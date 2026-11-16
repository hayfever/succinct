# Summary

What changes, and why. One paragraph.

## Checks

- [ ] `python3 scripts/validate-package.py` passes
- [ ] `python3 -m unittest discover -s tests -v` passes
- [ ] `python3 scripts/build_adapters.py` run after any `skills/succinct/SKILL.md` change
- [ ] Version bumped in all manifests and `CHANGELOG.md` updated (if user-facing)
- [ ] Behavior changes include an eval case and `evals/results/gate.json`
- [ ] `skills/succinct/SKILL.md` stays at 400 lines or fewer

## Eval evidence

Attach `evals/results/gate.json` for behavior changes, or state why none is needed.