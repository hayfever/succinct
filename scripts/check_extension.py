#!/usr/bin/env python3
"""Smoke-test the Pi or OMP extension without making a model request.

Drives the agent in RPC mode; no model request is made. Third-party
attribution: THIRD_PARTY_NOTICES.md."""


from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RPC_TIMEOUT_SECONDS = 30
SHARED_MANIFEST_FIELDS = ("name", "version", "description", "license", "homepage")

# omp picks a default model while it starts, even in RPC mode with no prompt,
# and exits when the agent dir has no catalog. The isolated agent dir therefore
# gets one placeholder provider so the check needs no API key. The base URL is
# unroutable on purpose: the check must never reach a model.
OMP_PLACEHOLDER_MODEL = "ci/placeholder"
OMP_MODEL_CATALOG = """providers:
  ci:
    api: openai-responses
    auth: none
    baseUrl: http://127.0.0.1:1/v1
    models:
      - id: placeholder
        name: placeholder
        input:
          - text
"""

def validate_package_manifest() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf8"))
    kimi = json.loads((ROOT / "kimi.plugin.json").read_text(encoding="utf8"))

    for field in SHARED_MANIFEST_FIELDS:
        assert package.get(field) == kimi.get(field), (
            f"package.json and kimi.plugin.json disagree on {field}"
        )

    assert package.get("pi") == {
        "extensions": ["./extensions/succinct.ts"],
        "skills": ["./skills"],
    }
    assert package.get("omp") == {
        "extensions": ["./extensions/succinct.ts"],
    }

class RpcClient:
    def __init__(
        self,
        executable: str,
        env: dict[str, str],
        *args: str,
    ) -> None:
        self.stderr_file = tempfile.TemporaryFile(mode="w+t")
        self.process = subprocess.Popen(
            [executable, "--mode", "rpc", *args],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr_file,
            text=True,
        )
        if self.process.stdout is None:
            raise RuntimeError("Agent RPC stdout is unavailable")

        self.stdout_lines: queue.Queue[str | None] = queue.Queue()
        self.stdout_thread = threading.Thread(
            target=self._read_stdout,
            daemon=True,
        )
        self.stdout_thread.start()

    def _read_stdout(self) -> None:
        if self.process.stdout is None:
            self.stdout_lines.put(None)
            return

        for line in self.process.stdout:
            self.stdout_lines.put(line)
        self.stdout_lines.put(None)

    def _read_stderr(self) -> str:
        self.stderr_file.flush()
        self.stderr_file.seek(0)
        return self.stderr_file.read()

    def request(
        self,
        request_id: str,
        command: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if self.process.stdin is None:
            raise RuntimeError("Agent RPC stdin is unavailable")

        payload = {"id": request_id, **command}
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

        events: list[dict[str, Any]] = []
        while True:
            try:
                line = self.stdout_lines.get(timeout=RPC_TIMEOUT_SECONDS)
            except queue.Empty as error:
                raise TimeoutError(
                    f"Agent RPC did not respond within {RPC_TIMEOUT_SECONDS} seconds",
                ) from error

            if line is None:
                raise RuntimeError(
                    f"Agent RPC exited before responding: {self._read_stderr()}",
                )

            event = json.loads(line)
            events.append(event)
            if event.get("type") == "response" and event.get("id") == request_id:
                return event, events

    def events_until(
        self,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            try:
                line = self.stdout_lines.get(timeout=RPC_TIMEOUT_SECONDS)
            except queue.Empty as error:
                raise TimeoutError(
                    f"Agent RPC did not emit the expected event within "
                    f"{RPC_TIMEOUT_SECONDS} seconds",
                ) from error

            if line is None:
                raise RuntimeError(
                    f"Agent RPC exited before emitting the expected event: "
                    f"{self._read_stderr()}",
                )

            event = json.loads(line)
            events.append(event)
            if predicate(event):
                return events

    def close(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()

        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)

        return_code = self.process.returncode
        stderr = self._read_stderr()
        self.stderr_file.close()

        if return_code not in (0, -15):
            raise RuntimeError(f"Agent RPC exited with {return_code}: {stderr}")

def build_isolated_env(agent_dir: str) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.endswith("_API_KEY")
        and key not in {"ANTHROPIC_AUTH_TOKEN", "OPENAI_ACCESS_TOKEN"}
    }
    env.update(
        {
            "PI_CODING_AGENT_DIR": agent_dir,
            "PI_SKIP_VERSION_CHECK": "1",
            "PI_TELEMETRY": "0",
        }
    )
    return env

def status_texts(events: list[dict[str, Any]]) -> list[str | None]:
    return [
        event.get("statusText")
        for event in events
        if event.get("type") == "extension_ui_request"
        and event.get("method") == "setStatus"
        and event.get("statusKey") == "succinct"
    ]

def notification_texts(events: list[dict[str, Any]]) -> list[str | None]:
    return [
        event.get("message")
        for event in events
        if event.get("type") == "extension_ui_request"
        and event.get("method") == "notify"
    ]

def message_count(entries_response: dict[str, Any], custom_type: str) -> int:
    return sum(
        1
        for entry in entries_response["data"]["entries"]
        if entry.get("type") == "custom_message"
        and entry.get("customType") == custom_type
    )

def latest_enabled(entries_response: dict[str, Any]) -> bool:
    states = [
        entry.get("data", {}).get("enabled")
        for entry in entries_response["data"]["entries"]
        if entry.get("type") == "custom"
        and entry.get("customType") == "succinct-state"
    ]
    if not states or not isinstance(states[-1], bool):
        raise AssertionError("No persisted succinct state found")
    return states[-1]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test the succinct extension without a model request."
    )
    parser.add_argument(
        "--runtime",
        choices=("pi", "omp"),
        default="pi",
        help="Agent runtime to exercise (default: pi)",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    validate_package_manifest()
    executable = shutil.which(args.runtime)
    if executable is None:
        raise RuntimeError(f"{args.runtime} executable is not available")

    with tempfile.TemporaryDirectory(
        prefix=f"succinct-{args.runtime}-"
    ) as agent_dir:
        env = build_isolated_env(agent_dir)
        if args.runtime == "omp":
            # omp reads its catalog from the agent dir that PI_CODING_AGENT_DIR
            # names, so both the catalog and the check stay inside the temp dir.
            Path(agent_dir, "models.yml").write_text(
                OMP_MODEL_CATALOG,
                encoding="utf8",
            )
        if args.runtime == "pi":
            subprocess.run(
                [executable, "install", str(ROOT)],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        extension_args = (
            []
            if args.runtime == "pi"
            else ["--no-extensions", "-e", str(ROOT)]
        )

        reload_probe = Path(agent_dir, "reload-probe.ts")
        passthrough_probe_flag = Path(agent_dir, "passthrough-probe-enabled")
        reload_probe_source = """import { existsSync } from \"node:fs\";
import type { ExtensionAPI } from \"@earendil-works/pi-coding-agent\";
const passthroughProbeFlag = __PASSTHROUGH_PROBE_FLAG__;
export default function (pi: ExtensionAPI) {
  pi.registerCommand(\"reload-probe\", {
    description: \"Reload Pi for smoke testing\",
    handler: async (_args, ctx) => { await ctx.reload(); },
  });
  pi.on(\"input\", async (event) => {
    if (!existsSync(passthroughProbeFlag) || event.text.trim().toLowerCase() !== \"normal mode\") {
      return { action: \"continue\" };
    }
    pi.appendEntry(\"passthrough-probe\", { seen: true });
    return { action: \"handled\" };
  });
}
"""
        reload_probe.write_text(
            reload_probe_source.replace(
                "__PASSTHROUGH_PROBE_FLAG__",
                json.dumps(str(passthrough_probe_flag)),
            ),
            encoding="utf8",
        )

        model_args = (
            ["--model", OMP_PLACEHOLDER_MODEL] if args.runtime == "omp" else []
        )
        client = RpcClient(
            executable,
            env,
            "--no-session",
            *model_args,
            *extension_args,
            "-e",
            str(reload_probe),
            "--succinct",
        )
        if args.runtime == "omp":
            try:
                startup_events = client.events_until(
                    lambda event: event.get("type")
                    == "available_commands_update",
                )
                command_event = startup_events[-1]
                command_names = {
                    command["name"]
                    for command in command_event["commands"]
                }
                assert "succinct" in command_names
                assert "skill:succinct" in command_names
                assert any(
                    "SUCCINCT ON" in (text or "")
                    for text in status_texts(startup_events)
                )
            finally:
                client.close()

            print("omp extension smoke test passed")
            return

        try:
            commands, startup_events = client.request("commands", {"type": "get_commands"})
            command_names = {command["name"] for command in commands["data"]["commands"]}
            assert "succinct" in command_names
            assert "skill:succinct" in command_names
            assert any("SUCCINCT ON" in (text or "") for text in status_texts(startup_events))

            entries, _ = client.request("entries-startup", {"type": "get_entries"})
            assert message_count(entries, "succinct-rules") == 1
            assert message_count(entries, "succinct-disabled") == 0

            reloaded, reload_events = client.request(
                "reload-enabled",
                {"type": "prompt", "message": "/reload-probe"},
            )
            assert reloaded["success"] is True
            assert any("SUCCINCT ON" in (text or "") for text in status_texts(reload_events))

            entries, _ = client.request("entries-reloaded", {"type": "get_entries"})
            assert message_count(entries, "succinct-rules") == 1, (
                "Rules were injected twice for one active session"
            )

            toggled_off, toggle_off_events = client.request(
                "toggle-off",
                {"type": "prompt", "message": "/succinct"},
            )
            assert toggled_off["success"] is True
            assert None in status_texts(toggle_off_events)

            entries, _ = client.request("entries-toggled-off", {"type": "get_entries"})
            assert latest_enabled(entries) is False
            assert message_count(entries, "succinct-disabled") == 1
            assert not Path(agent_dir, "succinct.json").exists(), (
                "The bare toggle wrote the preference file"
            )

            reloaded, reload_events = client.request(
                "reload-disabled",
                {"type": "prompt", "message": "/reload-probe"},
            )
            assert reloaded["success"] is True
            assert not any("SUCCINCT ON" in (text or "") for text in status_texts(reload_events))

            entries, _ = client.request("entries-reload-disabled", {"type": "get_entries"})
            assert message_count(entries, "succinct-rules") == 1
            assert message_count(entries, "succinct-disabled") == 1

            toggled_on, toggle_on_events = client.request(
                "toggle-on",
                {"type": "prompt", "message": "/succinct"},
            )
            assert toggled_on["success"] is True
            assert any("SUCCINCT ON" in (text or "") for text in status_texts(toggle_on_events))

            entries, _ = client.request("entries-toggled-on", {"type": "get_entries"})
            assert latest_enabled(entries) is True
            assert message_count(entries, "succinct-rules") == 2
            assert not Path(agent_dir, "succinct.json").exists(), (
                "The bare toggle wrote the preference file"
            )

            explicit_off, _ = client.request(
                "explicit-off",
                {"type": "prompt", "message": "/succinct off"},
            )
            assert explicit_off["success"] is True
            assert json.loads(
                Path(agent_dir, "succinct.json").read_text(encoding="utf8")
            ) == {"enabled": False}

            skill, skill_events = client.request(
                "skill-alias",
                {"type": "prompt", "message": "/skill:succinct"},
            )
            assert skill["success"] is True
            assert not any(event.get("type") == "agent_start" for event in skill_events)

            entries, _ = client.request("entries-enabled", {"type": "get_entries"})
            assert latest_enabled(entries) is True
            assert message_count(entries, "succinct-rules") == 3

            stopped, stop_events = client.request(
                "stop-phrase",
                {"type": "prompt", "message": "normal mode"},
            )
            assert stopped["success"] is True
            assert None in status_texts(stop_events)

            entries, _ = client.request("entries-stopped", {"type": "get_entries"})
            assert latest_enabled(entries) is False

            passthrough_probe_flag.touch()
            passthrough, _ = client.request(
                "disabled-passthrough",
                {"type": "prompt", "message": "normal mode"},
            )
            assert passthrough["success"] is True

            entries, _ = client.request("entries-passthrough", {"type": "get_entries"})
            assert any(
                entry.get("type") == "custom"
                and entry.get("customType") == "passthrough-probe"
                and entry.get("data", {}).get("seen") is True
                for entry in entries["data"]["entries"]
            ), "Disabled mode swallowed ordinary input"
        finally:
            client.close()

        # Only /succinct on and /succinct off write the preference file. The
        # bare toggles and the stop phrase above changed this session only and
        # left the explicit OFF choice in place.
        persisted_config = json.loads(
            Path(agent_dir, "succinct.json").read_text(encoding="utf8")
        )
        assert persisted_config == {"enabled": False}

        persisted_off = RpcClient(executable, env, "--no-session", *extension_args)
        try:
            _, persisted_off_events = persisted_off.request(
                "persisted-off", {"type": "get_state"},
            )
            assert not any(
                "SUCCINCT ON" in (text or "")
                for text in status_texts(persisted_off_events)
            )
            entries, _ = persisted_off.request(
                "entries-persisted-off", {"type": "get_entries"},
            )
            assert message_count(entries, "succinct-rules") == 0
        finally:
            persisted_off.close()

        # The legacy always-on flag still forces ON once the persisted
        # preference is cleared.
        Path(agent_dir, "succinct.json").unlink(missing_ok=True)
        Path(agent_dir, ".succinct-always").touch()
        always_on = RpcClient(
            executable,
            env,
            "--no-session",
            *extension_args,
        )
        try:
            _, always_on_events = always_on.request(
                "always-on",
                {"type": "get_state"},
            )
            assert any(
                "SUCCINCT ON" in (text or "")
                for text in status_texts(always_on_events)
            )
        finally:
            always_on.close()

        # The persisted ON choice restores in a fresh session with no flags.
        Path(agent_dir, ".succinct-always").unlink(missing_ok=True)
        Path(agent_dir, "succinct.json").write_text(
            json.dumps({"enabled": True}), encoding="utf8",
        )
        persisted_on = RpcClient(executable, env, "--no-session", *extension_args)
        try:
            _, persisted_on_events = persisted_on.request(
                "persisted-on", {"type": "get_state"},
            )
            assert any(
                "SUCCINCT ON" in (text or "")
                for text in status_texts(persisted_on_events)
            )
            entries, _ = persisted_on.request(
                "entries-persisted-on", {"type": "get_entries"},
            )
            assert message_count(entries, "succinct-rules") == 1
        finally:
            persisted_on.close()

        # An explicit save keeps the other settings, and hideStatus still
        # applies on the next start.
        Path(agent_dir, "succinct.json").write_text(
            json.dumps({"hideStatus": True}), encoding="utf8",
        )
        saved = RpcClient(executable, env, "--no-session", *extension_args)
        try:
            _, saved_events = saved.request(
                "save-on",
                {"type": "prompt", "message": "/succinct on"},
            )
            assert not any(
                "SUCCINCT ON" in (text or "")
                for text in status_texts(saved_events)
            )
            assert json.loads(
                Path(agent_dir, "succinct.json").read_text(encoding="utf8")
            ) == {"hideStatus": True, "enabled": True}
            entries, _ = saved.request("entries-saved-on", {"type": "get_entries"})
            assert message_count(entries, "succinct-rules") == 1
        finally:
            saved.close()

        # A broken preference file is reported once and never overwritten.
        Path(agent_dir, ".succinct-always").unlink(missing_ok=True)
        corrupt = "{ this is not json"
        Path(agent_dir, "succinct.json").write_text(corrupt, encoding="utf8")
        broken = RpcClient(executable, env, "--no-session", *extension_args)
        try:
            _, broken_events = broken.request(
                "corrupt-start", {"type": "get_state"},
            )
            warnings = [
                text
                for text in notification_texts(broken_events)
                if "Cannot parse" in (text or "")
            ]
            assert len(warnings) == 1, f"expected one warning, got {warnings}"
            entries, _ = broken.request("entries-corrupt", {"type": "get_entries"})
            assert message_count(entries, "succinct-rules") == 0

            broken.request(
                "corrupt-off",
                {"type": "prompt", "message": "/succinct off"},
            )
            assert (
                Path(agent_dir, "succinct.json").read_text(encoding="utf8")
                == corrupt
            ), "A broken preference file was overwritten"
            entries, _ = broken.request(
                "entries-corrupt-off", {"type": "get_entries"},
            )
            assert latest_enabled(entries) is False
        finally:
            broken.close()

    print(f"{args.runtime} extension smoke test passed")

if __name__ == "__main__":
    main()