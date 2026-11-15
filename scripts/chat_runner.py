#!/usr/bin/env python3
"""Run one prompt through an OpenAI-compatible chat endpoint.

The eval measures the skill, so the model must answer as a plain chat model:
one user message, no system prompt, no tools, no working directory. A
coding-agent runner wraps the model in an agent prompt, and without tools the
model then announces tool use ("Let me check ...") instead of answering.

The prompt comes from the last argument, which is how scripts/run_evals.py
passes it, or from stdin, which is how scripts/judge.py passes long judge
prompts. Only the final assistant text is printed, with any think block
removed. Standard library only; third-party attribution: THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Optional


DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
# Reasoning models may prepend a think block to the answer text.
THINK_BLOCK = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)
THINK_OPEN = re.compile(r"<think\b[^>]*>", re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Remove think blocks, keeping only the answer text.

    A block that never closes means the model was still reasoning when it
    stopped: everything from that tag on is reasoning, not an answer, so it is
    dropped. The caller treats an empty result as a failed run.
    """
    text = THINK_BLOCK.sub("", text)
    unterminated = THINK_OPEN.search(text)
    if unterminated:
        text = text[: unterminated.start()]
    return text.strip()


def build_request(model: str, prompt: str) -> bytes:
    """Return the request body for one prompt with no system message."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    return json.dumps(payload).encode("utf-8")


def request_completion(
    base_url: str, model: str, prompt: str, timeout: float
) -> dict[str, Any]:
    """POST one chat completion and return the decoded response."""
    url = base_url.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(
        url,
        data=build_request(model, prompt),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace").strip()
        raise RuntimeError(f"{url} returned HTTP {error.code}: {detail[:500]}")


def extract_answer(payload: dict[str, Any]) -> str:
    """Return the assistant message text from one completion response."""
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            "response has no choices[0].message.content: "
            + json.dumps(payload)[:500]
        )
    if not isinstance(content, str):
        raise RuntimeError(f"assistant content is not text: {content!r}"[:500])
    return strip_thinking(content)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt", nargs="?", help="Prompt text; read from stdin when omitted"
    )
    parser.add_argument("--model", required=True, help="Model name for the endpoint")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=300.0, help="Seconds")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    if not prompt.strip():
        print("chat_runner: empty prompt", file=sys.stderr)
        return 2
    try:
        payload = request_completion(args.base_url, args.model, prompt, args.timeout)
        answer = extract_answer(payload)
    except (RuntimeError, OSError, ValueError) as error:
        print(f"chat_runner: {error}", file=sys.stderr)
        return 1
    if not answer:
        print("chat_runner: empty answer", file=sys.stderr)
        return 1
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
