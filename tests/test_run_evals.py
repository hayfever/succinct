import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_evals = load_module("run_evals", "scripts/run_evals.py")


def score_row(case_id, condition, **fields):
    values = {
        "correctness": 4.0,
        "autonomy": 4.0,
        "actionability": 4.0,
        "safety": 4.0,
        "concision": 4.0,
        "blocker": False,
        "notes": "",
    }
    values.update(fields)
    return {
        "case_id": case_id,
        "trial": 1,
        "condition": condition,
        "notes": values.pop("notes"),
        **values,
    }


def gate(scores):
    return run_evals.summarize_scores(scores)["release_gate"]


class ReleaseGateTest(unittest.TestCase):
    def test_fewer_candidate_blockers_pass(self):
        scores = [
            score_row("a", "baseline", blocker=True),
            score_row("b", "baseline", blocker=True),
            score_row("a", "candidate", blocker=True),
            score_row("b", "candidate", correctness=4.5),
        ]
        result = gate(scores)
        self.assertTrue(result["passed"], result["reasons"])
        self.assertEqual({"baseline": 2, "candidate": 1}, result["blocking_findings"])

    def test_more_candidate_blockers_fail(self):
        scores = [
            score_row("a", "baseline"),
            score_row("a", "candidate", blocker=True),
            score_row("b", "baseline"),
            score_row("b", "candidate", correctness=4.5),
        ]
        result = gate(scores)
        self.assertFalse(result["passed"])
        self.assertEqual({"baseline": 0, "candidate": 1}, result["blocking_findings"])
        self.assertTrue(any("blocking findings" in reason for reason in result["reasons"]))

    def test_equal_candidate_blockers_pass(self):
        scores = [
            score_row("a", "baseline", blocker=True),
            score_row("b", "baseline"),
            score_row("a", "candidate", blocker=True),
            score_row("b", "candidate", correctness=4.5),
        ]
        result = gate(scores)
        self.assertTrue(result["passed"], result["reasons"])
        self.assertEqual({"baseline": 1, "candidate": 1}, result["blocking_findings"])

    def test_correctness_drop_over_a_tenth_fails(self):
        scores = [
            score_row("a", "baseline"),
            score_row("a", "candidate", correctness=3.89, actionability=4.2),
        ]
        result = gate(scores)
        self.assertFalse(result["passed"])
        self.assertTrue(any("correctness" in reason for reason in result["reasons"]))
        self.assertFalse(any("safety" in reason for reason in result["reasons"]))

    def test_safety_drop_over_a_tenth_fails(self):
        scores = [
            score_row("a", "baseline"),
            score_row("a", "candidate", safety=3.89, actionability=4.2),
        ]
        result = gate(scores)
        self.assertFalse(result["passed"])
        self.assertTrue(any("safety" in reason for reason in result["reasons"]))

    def test_weighted_score_must_beat_baseline(self):
        scores = [
            score_row("a", "baseline"),
            score_row("a", "candidate", correctness=3.95, safety=3.95),
        ]
        result = gate(scores)
        self.assertFalse(result["passed"])
        self.assertTrue(any("weighted score" in reason for reason in result["reasons"]))

    def test_candidate_blockers_are_listed_with_case_trial_and_reason(self):
        scores = [
            score_row("a", "baseline"),
            score_row("a", "candidate", blocker=True, notes="wrong PKCE vector"),
            score_row("b", "baseline"),
            score_row("b", "candidate", correctness=4.5),
        ]
        result = gate(scores)
        self.assertEqual(
            [{"case_id": "a", "trial": 1, "reason": "wrong PKCE vector"}],
            result["candidate_blockers"],
        )


if __name__ == "__main__":
    unittest.main()
