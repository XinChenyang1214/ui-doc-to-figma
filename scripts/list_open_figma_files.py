#!/usr/bin/env python3
"""List currently open Figma design/file tabs from local remote-debug endpoint."""

from __future__ import annotations

import argparse
import json
import re
from urllib.request import urlopen

FILE_KEY_RE = re.compile(r"/(?:design|file)/([A-Za-z0-9]+)")


def fetch_targets(endpoint: str) -> list[dict]:
    with urlopen(endpoint, timeout=3) as resp:  # nosec B310
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        return []
    return [x for x in payload if isinstance(x, dict)]


def extract_file_key(url: str) -> str:
    if not url:
        return ""
    m = FILE_KEY_RE.search(url)
    return m.group(1) if m else ""


def is_figma_file_url(url: str) -> bool:
    return "/design/" in url or "/file/" in url


def main() -> int:
    parser = argparse.ArgumentParser(description="List open Figma files from localhost debug endpoint.")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:9222/json",
        help="CDP endpoint URL",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    try:
        targets = fetch_targets(args.endpoint)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Failed to query {args.endpoint}: {exc}")

    files: list[dict] = []
    for t in targets:
        if t.get("type") != "page":
            continue
        url = str(t.get("url", ""))
        if not is_figma_file_url(url):
            continue
        files.append(
            {
                "id": str(t.get("id", "")),
                "title": str(t.get("title", "")),
                "url": url,
                "fileKey": extract_file_key(url),
            }
        )

    result = {
        "count": len(files),
        "current_candidate": files[0] if files else None,
        "files": files,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not files:
        print("No open Figma design/file tabs detected.")
        return 0

    print(f"Open Figma files: {len(files)}")
    if result["current_candidate"]:
        c = result["current_candidate"]
        print(
            f"Current candidate: {c.get('title', '')} (fileKey={c.get('fileKey', '')})"
        )
    print("")
    for idx, item in enumerate(files, start=1):
        print(f"{idx}. {item.get('title', '')}")
        print(f"   fileKey: {item.get('fileKey', '')}")
        print(f"   url: {item.get('url', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
