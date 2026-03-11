#!/usr/bin/env python3
"""Generate a bridge operation plan from an HTML document."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

AUTO_TMP_DIR_NAME = "auto-figma"
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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


def parse_size(value: str) -> float | None:
    if not value:
        return None
    value = value.strip().lower()
    if value.endswith("px"):
        value = value[:-2]
    try:
        return float(value)
    except ValueError:
        return None


def parse_style(style_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in style_text.split(";"):
        if ":" not in token:
            continue
        key, value = token.split(":", 1)
        k = key.strip().lower()
        v = value.strip()
        if k:
            result[k] = v
    return result


def pick_color(styles: dict[str, str], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = styles.get(key, "").strip()
        if HEX_COLOR_RE.match(value):
            return value.upper()
    return None


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    styles: dict[str, str]
    children: list["Node"] = field(default_factory=list)
    text_fragments: list[str] = field(default_factory=list)


class MiniHTMLTree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="document", attrs={}, styles={})
        self.stack: list[Node] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        node = Node(tag=tag.lower(), attrs=attr_map, styles=parse_style(attr_map.get("style", "")))
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == lower:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data: str) -> None:
        text = normalize_whitespace(data)
        if text:
            self.stack[-1].text_fragments.append(text)


def first_tag(node: Node, tag: str) -> Node | None:
    if node.tag == tag:
        return node
    for child in node.children:
        found = first_tag(child, tag)
        if found:
            return found
    return None


def frame_name(node: Node, index: int) -> str:
    cls = normalize_whitespace(node.attrs.get("class", "")).replace(" ", "-")
    node_id = node.attrs.get("id", "").strip()
    parts = [f"N{index:03d}", node.tag]
    if node_id:
        parts.append(f"id-{node_id}")
    elif cls:
        parts.append(f"class-{cls}")
    return "-".join(parts)[:120]


def text_name(node: Node, index: int) -> str:
    return f"T{index:03d}-{node.tag}"[:120]


def build_plan(
    source_html: Path,
    html_root: Node,
    project_name: str,
    project_slug: str,
    task_id: str,
    page_name: str,
    frame_width: int,
    frame_height: int,
    x_gap: int,
    y_gap: int,
) -> dict:
    operations: list[dict] = [
        {"name": "create-page", "run": ["create", "page", page_name, "--json"], "capture": "page_id"},
        {"name": "set-page", "run": ["page", "set", page_name]},
        {
            "name": "create-root-frame",
            "run": [
                "create",
                "frame",
                "--name",
                "HTML-ROOT",
                "--x",
                "0",
                "--y",
                "0",
                "--width",
                str(frame_width),
                "--height",
                str(frame_height),
                "--fill",
                "#FFFFFF",
                "--json",
            ],
            "capture": "html_root",
        },
    ]

    node_counter = 1
    text_counter = 1

    def walk(node: Node, parent_capture: str, cursor_y: int = 0) -> int:
        nonlocal node_counter, text_counter
        block_cursor_y = cursor_y
        for child in node.children:
            if child.tag in {"script", "style", "meta", "link", "head"}:
                continue

            styles = child.styles
            width = int(parse_size(styles.get("width", "")) or 320)
            height = int(parse_size(styles.get("height", "")) or 44)
            x = int(parse_size(styles.get("left", "")) or parse_size(styles.get("x", "")) or 0)
            y = int(parse_size(styles.get("top", "")) or parse_size(styles.get("y", "")) or block_cursor_y)

            color = pick_color(styles, ["background", "background-color"]) or "#FFFFFF"
            capture = f"node_{node_counter:03d}"
            operations.append(
                {
                    "name": f"create-frame-{node_counter:03d}",
                    "run": [
                        "create",
                        "frame",
                        "--name",
                        frame_name(child, node_counter),
                        "--x",
                        str(x),
                        "--y",
                        str(y),
                        "--width",
                        str(max(width, 1)),
                        "--height",
                        str(max(height, 1)),
                        "--fill",
                        color,
                        "--parent",
                        f"{{{{{parent_capture}}}}}",
                        "--json",
                    ],
                    "capture": capture,
                }
            )
            node_counter += 1

            if child.text_fragments:
                text = normalize_whitespace(" ".join(child.text_fragments))[:5000]
                text_fill = pick_color(styles, ["color"]) or "#111111"
                font_size = int(parse_size(styles.get("font-size", "")) or 14)
                operations.append(
                    {
                        "name": f"create-text-{text_counter:03d}",
                        "run": [
                            "create",
                            "text",
                            "--name",
                            text_name(child, text_counter),
                            "--x",
                            "0",
                            "--y",
                            "0",
                            "--text",
                            text,
                            "--font-size",
                            str(max(font_size, 1)),
                            "--fill",
                            text_fill,
                            "--parent",
                            f"{{{{{capture}}}}}",
                            "--json",
                        ],
                        "capture": f"text_{text_counter:03d}",
                    }
                )
                text_counter += 1

            walk(child, capture, 0)
            block_cursor_y = y + height + y_gap

        return block_cursor_y

    body = first_tag(html_root, "body") or html_root
    walk(body, "html_root", 0)

    return {
        "meta": {
            "generator": "html_to_figma_plan.py",
            "source_doc": str(source_html),
            "project_name": project_name,
            "project_slug": project_slug,
            "task_id": task_id,
            "mode": "full-refresh",
            "source_type": "html",
            "parity_target": "strict",
            "page_name": page_name,
            "frame_size": {"width": frame_width, "height": frame_height},
            "gap": {"x": x_gap, "y": y_gap},
        },
        "operations": operations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bridge JSON plan from an HTML file.")
    parser.add_argument("--input", required=True, help="Path to HTML document")
    parser.add_argument("--output", default="", help="Output JSON plan path (must be under temp root)")
    parser.add_argument("--project-name", default="", help="Project name used for temp file prefix")
    parser.add_argument("--task-id", default="", help="Task ID used to avoid same-project collisions")
    parser.add_argument("--temp-root", default="", help="Temp root directory. Defaults to system temp/auto-figma")
    parser.add_argument("--page-name", default="", help="Target Figma page name")
    parser.add_argument("--frame-width", type=int, default=1440, help="Root frame width")
    parser.add_argument("--frame-height", type=int, default=1024, help="Root frame height")
    parser.add_argument("--x-gap", type=int, default=32, help="Horizontal gap fallback")
    parser.add_argument("--y-gap", type=int, default=16, help="Vertical gap fallback")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    parser_tree = MiniHTMLTree()
    parser_tree.feed(input_path.read_text(encoding="utf-8"))

    project_name = args.project_name.strip() or input_path.parent.name or input_path.stem
    project_slug = slugify_project_name(project_name)
    task_id = normalize_task_id(args.task_id) or generate_task_id()
    page_name = args.page_name.strip() or f"HTML-{project_slug}"

    temp_root = Path(args.temp_root).resolve() if args.temp_root else default_temp_root().resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = temp_root / f"{project_slug}_{task_id}_plan.json"

    if not is_within(output_path, temp_root):
        raise SystemExit(f"Output path must be under temp root: {temp_root}")

    plan = build_plan(
        source_html=input_path,
        html_root=parser_tree.root,
        project_name=project_name,
        project_slug=project_slug,
        task_id=task_id,
        page_name=page_name,
        frame_width=max(args.frame_width, 1),
        frame_height=max(args.frame_height, 1),
        x_gap=max(args.x_gap, 0),
        y_gap=max(args.y_gap, 0),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated plan: {output_path}")
    print(f"Project: {project_name} ({project_slug})")
    print(f"Task ID: {task_id}")
    print(f"Operations: {len(plan['operations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
