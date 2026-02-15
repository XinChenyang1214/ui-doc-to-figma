# Auto Edit Plan Format

Use this JSON format with `scripts/figma_bridge_apply_plan.py`.

## Top-level shape

```json
{
  "meta": {
    "generator": "optional",
    "source_doc": "optional",
    "project_name": "optional",
    "project_slug": "optional",
    "task_id": "optional",
    "mode": "incremental|full-refresh",
    "changed_headings": ["optional"]
  },
  "operations": [
    {
      "name": "create-home-page",
      "run": ["create", "page", "Home", "--json"],
      "capture": "home_page_id"
    }
  ]
}
```

## Operation fields

- `name`:
  - Optional label for logs.
- `run`:
  - Required.
  - Tokenized command array in bridge-compatible shape.
  - The bridge runner maps these tokens to internal plugin commands.
  - Example: `["create", "frame", "--x", "0", "--y", "0", "--width", "390", "--height", "844", "--json"]`.
- `capture`:
  - Optional variable name.
  - Captures first detected node ID from command output.
- `ignore_error`:
  - Optional boolean.
  - If true, continue even when this operation fails.

## Placeholder replacement

Use `{{capture_name}}` in any `run` token.

Example:

```json
{
  "name": "create-title",
  "run": [
    "create",
    "text",
    "--x",
    "24",
    "--y",
    "24",
    "--text",
    "Home",
    "--parent",
    "{{home_frame}}",
    "--json"
  ],
  "capture": "home_title"
}
```

`{{home_frame}}` is replaced with the captured ID from a prior operation.

## Minimal executable example

```json
{
  "meta": {
    "generator": "manual",
    "project_name": "prophet",
    "project_slug": "prophet",
    "task_id": "task-20260212-a1",
    "mode": "incremental",
    "changed_headings": ["首页"]
  },
  "operations": [
    {
      "name": "create-page",
      "run": ["create", "page", "AUTO-Example", "--json"],
      "capture": "page_id"
    },
    {
      "name": "set-page",
      "run": ["page", "set", "AUTO-Example"]
    },
    {
      "name": "create-frame",
      "run": [
        "create",
        "frame",
        "--name",
        "S01-Home",
        "--x",
        "0",
        "--y",
        "0",
        "--width",
        "390",
        "--height",
        "844",
        "--fill",
        "#FFFFFF",
        "--json"
      ],
      "capture": "home_frame"
    },
    {
      "name": "create-title",
      "run": [
        "create",
        "text",
        "--x",
        "24",
        "--y",
        "24",
        "--text",
        "Home",
        "--parent",
        "{{home_frame}}",
        "--json"
      ],
      "capture": "home_title"
    }
  ]
}
```
