#!/usr/bin/env python3
"""Generate a bridge operation plan from a UI markdown document."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

DEVICE_PRESETS = {
    "ios": (390, 844),
    "android": (412, 915),
    "web": (1440, 1024),
    "ipad": (1024, 1366),
}

EXCLUDE_HINTS = {
    "acceptance",
    "non-functional",
    "nfr",
    "appendix",
    "changelog",
    "base",
    "update",
    "验收",
    "附录",
    "变更",
    "非功能",
}

SCREEN_HINTS = {
    "screen",
    "page",
    "flow",
    "module",
    "home",
    "login",
    "setting",
    "profile",
    "detail",
    "dashboard",
    "页面",
    "页",
    "流程",
    "模块",
    "登录",
    "首页",
    "详情",
    "设置",
}

AUTO_TMP_DIR_NAME = "auto-figma"


def clean_heading(text: str) -> str:
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"[*_>#]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def should_exclude(title: str) -> bool:
    lower = title.lower()
    return any(hint in lower for hint in EXCLUDE_HINTS)


def has_screen_signal(title: str) -> bool:
    lower = title.lower()
    return any(hint in lower for hint in SCREEN_HINTS)


def extract_headings(markdown: str) -> list[str]:
    collected: list[str] = []
    fallback: list[str] = []

    for line in markdown.splitlines():
        match = re.match(r"^(#{2,4})\s+(.+)$", line)
        if not match:
            continue
        title = clean_heading(match.group(2))
        if not title or should_exclude(title):
            continue
        fallback.append(title)
        if has_screen_signal(title):
            collected.append(title)

    if not collected:
        collected = fallback

    unique: list[str] = []
    seen = set()
    for title in collected:
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(title)
    return unique


def trim_screens(screens: Iterable[str], max_screens: int) -> list[str]:
    result = [s[:80] for s in screens]
    if not result:
        return ["Main Screen"]
    return result[:max_screens]


def parse_changed_headings(raw: str) -> list[str]:
    if not raw.strip():
        return []
    items = [clean_heading(item) for item in raw.split(",")]
    return [item for item in items if item]


def filter_incremental_screens(screen_names: list[str], changed: list[str]) -> list[str]:
    if not changed:
        return screen_names
    changed_lower = [item.lower() for item in changed]
    result: list[str] = []
    for screen in screen_names:
        lower = screen.lower()
        if any(token in lower or lower in token for token in changed_lower):
            result.append(screen)
    return result


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


def frame_alias(index: int) -> str:
    return f"screen_{index:02d}"


def build_operations(
    screen_names: list[str],
    page_name: str,
    frame_width: int,
    frame_height: int,
    x_gap: int,
) -> list[dict]:
    ops: list[dict] = []
    ops.append(
        {
            "name": "create-page",
            "run": ["create", "page", page_name, "--json"],
            "capture": "page_id",
        }
    )
    ops.append({"name": "set-page", "run": ["page", "set", page_name]})

    cursor_x = 0
    for idx, screen_name in enumerate(screen_names, start=1):
        alias = frame_alias(idx)
        frame_name = f"S{idx:02d}-{screen_name}"
        ops.append(
            {
                "name": f"create-frame-{idx:02d}",
                "run": [
                    "create",
                    "frame",
                    "--name",
                    frame_name,
                    "--x",
                    str(cursor_x),
                    "--y",
                    "0",
                    "--width",
                    str(frame_width),
                    "--height",
                    str(frame_height),
                    "--fill",
                    "#FFFFFF",
                    "--layout",
                    "VERTICAL",
                    "--gap",
                    "16",
                    "--padding",
                    "24",
                    "--json",
                ],
                "capture": alias,
            }
        )
        ops.append(
            {
                "name": f"create-title-{idx:02d}",
                "run": [
                    "create",
                    "text",
                    "--name",
                    "ScreenTitle",
                    "--x",
                    "24",
                    "--y",
                    "24",
                    "--text",
                    frame_name,
                    "--font-size",
                    "24",
                    "--fill",
                    "#111111",
                    "--parent",
                    f"{{{{{alias}}}}}",
                    "--json",
                ],
                "capture": f"{alias}_title",
            }
        )
        cursor_x += frame_width + x_gap
    return ops


def build_plan(
    source_doc: Path,
    project_name: str,
    project_slug: str,
    task_id: str,
    mode: str,
    changed_headings: list[str],
    page_name: str,
    screen_names: list[str],
    frame_width: int,
    frame_height: int,
    x_gap: int,
) -> dict:
    operations = build_operations(screen_names, page_name, frame_width, frame_height, x_gap)
    return {
        "meta": {
            "generator": "ui_doc_to_figma_plan.py",
            "source_doc": str(source_doc),
            "project_name": project_name,
            "project_slug": project_slug,
            "task_id": task_id,
            "mode": mode,
            "changed_headings": changed_headings,
            "page_name": page_name,
            "screen_count": len(screen_names),
            "frame_size": {"width": frame_width, "height": frame_height},
        },
        "operations": operations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bridge JSON plan from a UI markdown doc.")
    parser.add_argument("--input", required=True, help="Path to UI markdown document")
    parser.add_argument("--output", default="", help="Output JSON plan path (must be under temp root)")
    parser.add_argument(
        "--device",
        default="ios",
        choices=sorted(DEVICE_PRESETS.keys()),
        help="Frame size preset",
    )
    parser.add_argument("--project-name", default="", help="Project name used for temp file prefix")
    parser.add_argument("--task-id", default="", help="Task ID used to avoid same-project collisions")
    parser.add_argument(
        "--temp-root",
        default="",
        help="Temp root directory. Defaults to system temp/auto-figma",
    )
    parser.add_argument("--page-name", default="", help="Target Figma page name")
    parser.add_argument("--max-screens", type=int, default=12, help="Max number of screens to generate")
    parser.add_argument("--x-gap", type=int, default=120, help="Horizontal gap between generated frames")
    parser.add_argument(
        "--changed-headings",
        default="",
        help="Comma-separated changed screen headings for incremental updates",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Allow full-screen regeneration (initial build or global refactor)",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    markdown = input_path.read_text(encoding="utf-8")
    heading_candidates = extract_headings(markdown)
    changed = parse_changed_headings(args.changed_headings)
    mode = "full-refresh" if args.full_refresh else "incremental"

    if not args.full_refresh and not changed:
        raise SystemExit(
            "Incremental mode requires --changed-headings. "
            "Use --full-refresh only for initial build or global refactor."
        )

    screen_pool = heading_candidates if args.full_refresh else filter_incremental_screens(heading_candidates, changed)
    if not screen_pool:
        raise SystemExit("No matching screens found for incremental update. Check --changed-headings.")
    screen_names = trim_screens(screen_pool, args.max_screens)

    frame_width, frame_height = DEVICE_PRESETS[args.device]
    project_name = args.project_name.strip() or input_path.parent.name or input_path.stem
    project_slug = slugify_project_name(project_name)
    task_id = normalize_task_id(args.task_id) or generate_task_id()
    page_name = args.page_name.strip() or f"AUTO-{project_slug}"

    temp_root = Path(args.temp_root).resolve() if args.temp_root else default_temp_root().resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = temp_root / f"{project_slug}_{task_id}_plan.json"

    if not is_within(output_path, temp_root):
        raise SystemExit(f"Output path must be under temp root: {temp_root}")

    plan = build_plan(
        input_path,
        project_name,
        project_slug,
        task_id,
        mode,
        changed,
        page_name,
        screen_names,
        frame_width,
        frame_height,
        args.x_gap,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated plan: {output_path}")
    print(f"Temp root: {temp_root}")
    print(f"Project: {project_name} ({project_slug})")
    print(f"Task ID: {task_id}")
    print(f"Mode: {mode}")
    print(f"Page name: {page_name}")
    print(f"Screens: {len(screen_names)}")
    for idx, screen in enumerate(screen_names, start=1):
        print(f"  {idx:02d}. {screen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
