#!/usr/bin/env python3
"""Apply generated plan to Figma via self-hosted bridge plugin (no figma-use dependency)."""

from __future__ import annotations

import argparse
import json
import os
import random
import threading
import tempfile
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import re

PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_.-]+)\}\}")
NODE_ID_RE = re.compile(r"\b\d+:\d+\b")
AUTO_TMP_DIR_NAME = "auto-figma"


def parse_padding(raw: str) -> str:
    return raw.strip()


@dataclass
class BridgeState:
    queue: deque[dict[str, Any]] = field(default_factory=deque)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    condition: threading.Condition = field(init=False)
    last_poll_ts: float = 0.0

    def __post_init__(self) -> None:
        self.condition = threading.Condition(self.lock)


def make_handler(state: BridgeState):
    class BridgeHandler(BaseHTTPRequestHandler):
        def _set_headers(self, status: int, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._set_headers(HTTPStatus.NO_CONTENT)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/next":
                with state.lock:
                    state.last_poll_ts = time.time()
                    if state.queue:
                        payload = state.queue.popleft()
                        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        self._set_headers(HTTPStatus.OK)
                        self.wfile.write(data)
                        return
                self._set_headers(HTTPStatus.NO_CONTENT)
                return

            if parsed.path == "/health":
                with state.lock:
                    connected = (time.time() - state.last_poll_ts) < 2.5
                payload = {"connected": connected}
                self._set_headers(HTTPStatus.OK)
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return

            self._set_headers(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/result":
                self._set_headers(HTTPStatus.NOT_FOUND)
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                return

            request_id = str(payload.get("id", ""))
            if not request_id:
                self._set_headers(HTTPStatus.BAD_REQUEST)
                return

            with state.condition:
                state.results[request_id] = payload
                state.condition.notify_all()

            self._set_headers(HTTPStatus.OK)
            self.wfile.write(b'{"ok":true}')

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return BridgeHandler


def substitute_placeholders(token: str, captures: dict[str, str]) -> str:
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in captures:
            raise RuntimeError(f"Missing capture for placeholder: {key}")
        return captures[key]

    return PLACEHOLDER_RE.sub(replacer, token)


def parse_flags(tokens: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--"):
            key = token[2:]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                result[key] = tokens[i + 1]
                i += 2
            else:
                result[key] = "true"
                i += 1
        else:
            i += 1
    return result


def to_number(raw: str | None, *, is_float: bool = False) -> int | float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw) if is_float else int(float(raw))
    except ValueError:
        return None


def map_operation(run_tokens: list[str]) -> tuple[str, dict[str, Any]]:
    if len(run_tokens) < 2:
        raise RuntimeError(f"Invalid run tokens: {run_tokens}")

    if run_tokens[0] == "create" and run_tokens[1] == "page":
        if len(run_tokens) < 3:
            raise RuntimeError("create page requires name")
        return ("create-page", {"name": run_tokens[2]})

    if run_tokens[0] == "page" and run_tokens[1] == "set":
        if len(run_tokens) < 3:
            raise RuntimeError("page set requires name/id")
        return ("set-current-page", {"idOrName": run_tokens[2]})

    if run_tokens[0] == "create" and run_tokens[1] == "frame":
        flags = parse_flags(run_tokens[2:])
        args: dict[str, Any] = {
            "name": flags.get("name", "Frame"),
            "x": to_number(flags.get("x")) or 0,
            "y": to_number(flags.get("y")) or 0,
            "width": to_number(flags.get("width")) or 100,
            "height": to_number(flags.get("height")) or 100,
            "fill": flags.get("fill"),
            "stroke": flags.get("stroke"),
            "strokeWeight": to_number(flags.get("stroke-weight"), is_float=True),
            "radius": to_number(flags.get("radius"), is_float=True),
            "opacity": to_number(flags.get("opacity"), is_float=True),
            "layoutMode": (flags.get("layout") or "NONE").upper(),
            "itemSpacing": to_number(flags.get("gap")),
            "padding": parse_padding(flags["padding"]) if "padding" in flags else None,
            "parentId": flags.get("parent"),
        }
        return ("create-frame", args)

    if run_tokens[0] == "create" and run_tokens[1] == "text":
        flags = parse_flags(run_tokens[2:])
        args = {
            "name": flags.get("name", "Text"),
            "x": to_number(flags.get("x")) or 0,
            "y": to_number(flags.get("y")) or 0,
            "text": flags.get("text", ""),
            "fontSize": to_number(flags.get("font-size"), is_float=True),
            "fontFamily": flags.get("font-family"),
            "fontStyle": flags.get("font-style"),
            "fill": flags.get("fill"),
            "opacity": to_number(flags.get("opacity"), is_float=True),
            "parentId": flags.get("parent"),
        }
        return ("create-text", args)

    if run_tokens[0] == "set" and run_tokens[1] == "text" and len(run_tokens) >= 4:
        return ("set-text", {"id": run_tokens[2], "text": run_tokens[3]})

    if run_tokens[0] == "set" and run_tokens[1] == "fill" and len(run_tokens) >= 4:
        return ("set-fill", {"id": run_tokens[2], "color": run_tokens[3]})

    if run_tokens[0] == "set" and run_tokens[1] == "opacity" and len(run_tokens) >= 4:
        value = to_number(run_tokens[3], is_float=True)
        if value is None:
            raise RuntimeError(f"Invalid opacity value: {run_tokens[3]}")
        return ("set-opacity", {"id": run_tokens[2], "value": value})

    if run_tokens[0] == "set" and run_tokens[1] == "layout" and len(run_tokens) >= 3:
        flags = parse_flags(run_tokens[3:])
        args = {
            "id": run_tokens[2],
            "mode": (flags.get("mode") or "").upper() or None,
            "gap": to_number(flags.get("gap")),
            "padding": parse_padding(flags["padding"]) if "padding" in flags else None,
        }
        return ("set-layout", args)

    raise RuntimeError(f"Unsupported operation run tokens: {run_tokens}")


def extract_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "nodeId", "pageId", "componentId"):
        value = payload.get(key)
        if isinstance(value, str) and NODE_ID_RE.search(value):
            return NODE_ID_RE.search(value).group(0)
    return None


def queue_command(
    state: BridgeState,
    command: str,
    args: dict[str, Any],
    timeout_sec: float,
) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    with state.condition:
        state.queue.append({"id": request_id, "command": command, "args": args})
        deadline = time.time() + timeout_sec
        while request_id not in state.results:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise RuntimeError(
                    f"Timeout waiting for bridge result. Ensure plugin is running:\n"
                    f"assets/figma-bridge-plugin/manifest.json"
                )
            state.condition.wait(timeout=remaining)
        result = state.results.pop(request_id)
    return result


def wait_for_plugin(state: BridgeState, wait_sec: float) -> None:
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        with state.lock:
            if (time.time() - state.last_poll_ts) < 2.5:
                return
        time.sleep(0.2)
    raise RuntimeError(
        "Bridge plugin not connected.\n"
        "Import and run plugin first: assets/figma-bridge-plugin/manifest.json"
    )


def slugify_project_name(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip())
    value = re.sub(r"-{2,}", "-", value).strip("-_")
    return value.lower() or "project"


def normalize_task_id(task_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", task_id.strip())
    value = re.sub(r"-{2,}", "-", value).strip("-_")
    return value


def generate_task_id() -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(4))
    return f"task-{stamp}-{rand}"


def default_temp_root() -> Path:
    if os.name == "nt":
        return Path(tempfile.gettempdir()) / AUTO_TMP_DIR_NAME
    return Path("/tmp") / AUTO_TMP_DIR_NAME


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def cleanup_task_temp_files(temp_root: Path, project_slug: str, task_id: str) -> list[str]:
    removed: list[str] = []
    prefix = f"{project_slug}_{task_id}_"
    if not temp_root.exists():
        return removed
    for path in temp_root.iterdir():
        if not path.is_file():
            continue
        if not path.name.startswith(prefix):
            continue
        if path.exists():
            path.unlink()
        removed.append(str(path))
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply plan via local Figma Bridge plugin.")
    parser.add_argument("--plan", help="Path to operation plan JSON")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Only check bridge/plugin status and exit",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print mapped bridge commands only")
    parser.add_argument("--captures-out", default="", help="Optional output path for captures JSON")
    parser.add_argument("--project-name", default="", help="Project name used for temp file prefix")
    parser.add_argument("--task-id", default="", help="Task ID used to avoid same-project collisions")
    parser.add_argument(
        "--temp-root",
        default="",
        help="Temp root directory. Defaults to system temp/auto-figma",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bridge host")
    parser.add_argument("--port", type=int, default=38450, help="Bridge port")
    parser.add_argument("--wait-plugin-sec", type=float, default=25.0, help="Wait time for plugin connection")
    parser.add_argument("--op-timeout-sec", type=float, default=30.0, help="Per-command timeout")
    parser.add_argument(
        "--expected-file-name",
        default="",
        help="Fail if connected fileName does not match exactly",
    )
    parser.add_argument(
        "--expected-file-key",
        default="",
        help="Fail if connected fileKey does not match exactly",
    )
    parser.add_argument(
        "--no-cleanup-task-files",
        action="store_true",
        help="Do not remove task intermediate files after successful execution",
    )
    args = parser.parse_args()

    captures: dict[str, str] = {}
    mapped_ops: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    plan_path = None
    captures_out_path = None

    if args.status_only and args.dry_run:
        raise SystemExit("--status-only and --dry-run cannot be used together")

    temp_root = Path(args.temp_root).resolve() if args.temp_root else default_temp_root().resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    plan_meta: dict[str, Any] = {}
    if not args.status_only:
        if not args.plan:
            raise SystemExit("--plan is required unless --status-only is used")
        plan_path = Path(args.plan).resolve()
        if not is_within(plan_path, temp_root):
            raise SystemExit(f"Plan path must be under temp root: {temp_root}")
        if not plan_path.exists():
            raise SystemExit(f"Plan not found: {plan_path}")

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_meta = plan.get("meta", {}) if isinstance(plan, dict) else {}
        operations = plan.get("operations")
        if not isinstance(operations, list):
            raise SystemExit("Invalid plan: operations must be list")

        for idx, op in enumerate(operations, start=1):
            if not isinstance(op, dict):
                raise SystemExit(f"Operation #{idx} invalid")
            run = op.get("run")
            if not isinstance(run, list) or not all(isinstance(x, str) for x in run):
                raise SystemExit(f"Operation #{idx} invalid run tokens")
            mapped_ops.append((op.get("name", f"op-{idx}"), op, {"run": run}))

    project_name = args.project_name.strip() or str(plan_meta.get("project_name", "")).strip() or "project"
    project_slug = slugify_project_name(project_name)
    task_id = normalize_task_id(args.task_id) or str(plan_meta.get("task_id", "")).strip() or generate_task_id()

    if args.captures_out:
        captures_out_path = Path(args.captures_out).resolve()
    elif not args.status_only:
        captures_out_path = temp_root / f"{project_slug}_{task_id}_captures.json"

    if captures_out_path and not is_within(captures_out_path, temp_root):
        raise SystemExit(f"captures path must be under temp root: {temp_root}")

    if args.dry_run:
        print(f"Temp root: {temp_root}")
        print(f"Project: {project_name} ({project_slug})")
        print(f"Task ID: {task_id}")
        print("Dry-run mapping:")
        local_caps: dict[str, str] = {}
        for idx, (name, op, raw) in enumerate(mapped_ops, start=1):
            expanded = [substitute_placeholders(t, local_caps) for t in raw["run"]]
            command, command_args = map_operation(expanded)
            print(f"[{idx:02d}] {name}: {command} {json.dumps(command_args, ensure_ascii=False)}")
            capture_name = op.get("capture")
            if isinstance(capture_name, str) and capture_name:
                local_caps[capture_name] = f"dry_{capture_name}"
        print("Dry-run captures:")
        print(json.dumps(local_caps, ensure_ascii=False, indent=2))
        return 0

    state = BridgeState()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Bridge server started at http://{args.host}:{args.port}")
    print(f"Temp root: {temp_root}")
    print(f"Project: {project_name} ({project_slug})")
    print(f"Task ID: {task_id}")

    try:
        wait_for_plugin(state, args.wait_plugin_sec)
        print("Bridge plugin connected.")

        # Preflight command
        status_result = queue_command(state, "status", {}, args.op_timeout_sec)
        if not status_result.get("ok"):
            raise RuntimeError(f"Bridge status failed: {status_result.get('error')}")
        status_payload = status_result.get("result", {}) if isinstance(status_result, dict) else {}
        file_name = status_payload.get("fileName", "unknown")
        file_key = status_payload.get("fileKey", "")
        print(f"Connected file: {file_name}")
        if file_key:
            print(f"Connected fileKey: {file_key}")

        if args.expected_file_name and file_name != args.expected_file_name:
            raise RuntimeError(
                f"Connected file mismatch: expected '{args.expected_file_name}', got '{file_name}'"
            )
        if args.expected_file_key and file_key != args.expected_file_key:
            raise RuntimeError(
                f"Connected file key mismatch: expected '{args.expected_file_key}', got '{file_key}'"
            )

        if args.status_only:
            print(json.dumps(status_payload, ensure_ascii=False, indent=2))
            return 0

        for idx, (name, op, raw) in enumerate(mapped_ops, start=1):
            expanded = [substitute_placeholders(t, captures) for t in raw["run"]]
            command, command_args = map_operation(expanded)
            print(f"\n[{idx:02d}] {name} -> {command}")
            result = queue_command(state, command, command_args, args.op_timeout_sec)
            if not result.get("ok"):
                if op.get("ignore_error"):
                    print(f"ignored error: {result.get('error')}")
                    continue
                raise RuntimeError(f"Operation failed: {result.get('error')}")

            payload = result.get("result") or {}
            if isinstance(payload, dict):
                capture_name = op.get("capture")
                if isinstance(capture_name, str) and capture_name:
                    node_id = extract_id(payload)
                    if not node_id:
                        raise RuntimeError(f"Capture '{capture_name}' missing ID from payload: {payload}")
                    captures[capture_name] = node_id
                    print(f"captured {capture_name}={node_id}")

        print("\nExecution completed.")
        print(json.dumps(captures, ensure_ascii=False, indent=2))

        if captures_out_path:
            captures_out_path.parent.mkdir(parents=True, exist_ok=True)
            captures_out_path.write_text(json.dumps(captures, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Capture map written: {captures_out_path}")

        if not args.no_cleanup_task_files:
            removed = cleanup_task_temp_files(temp_root, project_slug, task_id)
            if removed:
                print("Cleaned task temp files:")
                for item in removed:
                    print(f"- {item}")
            else:
                print("No task temp files to clean.")
        return 0

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
