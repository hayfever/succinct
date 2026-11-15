import importlib.util
import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chat_runner.py"


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_evals = load_module("run_evals", "scripts/run_evals.py")


class FakeEndpoint:
    """Local OpenAI-compatible endpoint that records requests and replays one reply."""

    def __init__(self):
        self.requests = []
        self.status = 200
        self.payload = {"choices": [{"message": {"role": "assistant", "content": "102"}}]}
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                endpoint.requests.append({"path": self.path, "body": json.loads(body)})
                data = json.dumps(endpoint.payload).encode("utf-8")
                self.send_response(endpoint.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True
        )

    @property
    def base_url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc_info):
        self.server.shutdown()
        self.server.server_close()


def run_runner(endpoint, *args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base-url", endpoint.base_url, *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )


class ChatRunnerTest(unittest.TestCase):
    def test_argument_prompt_is_one_user_message(self):
        with FakeEndpoint() as endpoint:
            result = run_runner(endpoint, "--model", "m", "What is 17 multiplied by 6?")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("102", result.stdout.strip())
        request = endpoint.requests[0]
        self.assertEqual("/v1/chat/completions", request["path"])
        self.assertEqual("m", request["body"]["model"])
        self.assertFalse(request["body"]["stream"])
        self.assertEqual(
            [{"role": "user", "content": "What is 17 multiplied by 6?"}],
            request["body"]["messages"],
        )

    def test_stdin_prompt_is_used_when_no_argument_is_given(self):
        with FakeEndpoint() as endpoint:
            result = run_runner(endpoint, "--model", "m", stdin="Grade these responses.")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "Grade these responses.",
            endpoint.requests[0]["body"]["messages"][0]["content"],
        )

    def test_think_block_is_removed_from_the_answer(self):
        with FakeEndpoint() as endpoint:
            endpoint.payload["choices"][0]["message"]["content"] = (
                "<think>weigh the options</think>Run `npm test`."
            )
            result = run_runner(endpoint, "--model", "m", "what next?")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("Run `npm test`.", result.stdout.strip())

    def test_unterminated_think_block_is_an_empty_answer(self):
        with FakeEndpoint() as endpoint:
            endpoint.payload["choices"][0]["message"]["content"] = (
                "<think>still reasoning when the budget ran out"
            )
            result = run_runner(endpoint, "--model", "m", "what next?")
        self.assertEqual(1, result.returncode)
        self.assertIn("empty answer", result.stderr)
        self.assertEqual("", result.stdout.strip())

    def test_http_error_reports_status_and_body(self):
        with FakeEndpoint() as endpoint:
            endpoint.status = 503
            endpoint.payload = {"error": "model is loading"}
            result = run_runner(endpoint, "--model", "m", "hello")
        self.assertEqual(1, result.returncode)
        self.assertIn("HTTP 503", result.stderr)
        self.assertIn("model is loading", result.stderr)

    def test_response_without_choices_is_an_error(self):
        with FakeEndpoint() as endpoint:
            endpoint.payload = {"error": "unsupported"}
            result = run_runner(endpoint, "--model", "m", "hello")
        self.assertEqual(1, result.returncode)
        self.assertIn("no choices", result.stderr)


class ChatRunnerConfigTest(unittest.TestCase):
    def test_chat_runners_use_the_script_and_different_models(self):
        config = json.loads((ROOT / "evals" / "runners.json").read_text(encoding="utf8"))
        answer = run_evals.resolve_command(config["ollama-answer"]["command"])
        judge = run_evals.resolve_command(config["ollama-judge"]["command"])
        self.assertEqual(str(SCRIPT), answer[1])
        self.assertEqual(str(SCRIPT), judge[1])
        self.assertTrue(Path(answer[1]).is_file())
        self.assertNotEqual(answer[answer.index("--model") + 1], judge[judge.index("--model") + 1])


if __name__ == "__main__":
    unittest.main()
