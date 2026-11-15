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


check_style = load_module("check_style", "scripts/check_style.py")


class CodeSpanTest(unittest.TestCase):
    def test_prose_double_hyphen_still_fails(self):
        violations = check_style.check_text("Run the tests, then deploy -- it is quick.")
        self.assertIn("spaced double hyphen used as a dash", violations)

    def test_inline_code_span_dashes_are_exempt(self):
        text = "Run `git log --oneline -- file` to see the history."
        self.assertEqual([], check_style.check_text(text))

    def test_fenced_code_block_dashes_are_exempt(self):
        text = "Run this command:\n\n```bash\ngit log --oneline -- file\n```\n"
        self.assertEqual([], check_style.check_text(text))

    def test_inline_code_span_em_dash_is_exempt(self):
        text = "The label contains `a — b` in the sample."
        self.assertEqual([], check_style.check_text(text))


if __name__ == "__main__":
    unittest.main()
