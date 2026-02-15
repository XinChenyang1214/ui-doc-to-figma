---
name: ui-doc-to-figma
description: Convert UI design documents into auto-executable Figma edit plans and apply them directly in Figma through a self-hosted bridge plugin (create page/frame/text, set layout and style, and capture node IDs). Uses task-scoped temp files and auto-cleanup, supports macOS/Linux/Windows, and does not rely on figma-use.
---

# UI Doc to Figma

## Overview

Turn a UI markdown document into an executable command plan, then apply the plan directly to Figma through the local bridge plugin.
Default behavior is automatic editing, not manual guidance.

## Required Inputs

Collect these inputs:

1. UI document path
2. Target Figma file already open in desktop app
3. Device preset (`ios`, `android`, `web`, `ipad`)
4. Project name (for task temp file prefix)
5. Task ID (for same-project conflict isolation)

If one input is missing, ask one concise question and continue.

## Hard Requirement

Use automatic edit flow by default:

1. Generate operation plan JSON
2. Execute plan with `scripts/figma_bridge_apply_plan.py`
3. Return created/updated node IDs
4. Clean task-scoped temp files after successful real write

Only fall back to manual steps if the environment blocks execution.

## Task Temp File Contract (Mandatory)

Always use task-scoped temp files:

1. Temp root:
   - macOS/Linux: `/tmp/auto-figma`
   - Windows: `%TEMP%\auto-figma` (script default)
2. Filename format:
   - `<project>_<taskId>_plan.json`
   - `<project>_<taskId>_captures.json`
3. `taskId` must be unique for concurrent/same-project runs.
4. Do not keep archives.
5. After each successful real write, clean files with the same `<project>_<taskId>_` prefix.

## Incremental Update Contract (Mandatory)

Default to incremental changes:

1. Only generate/apply operations for changed nodes/screens.
2. Use `--changed-headings` for incremental plan generation.
3. Use `--full-refresh` only for initial build, mapping loss, or global refactor.
4. For new user requirements, fetch fresh node context directly from Figma and create a new incremental task. Do not depend on old temp files.

## File Selection Contract

Before any edit command:

1. Run `scripts/list_open_figma_files.py` and show file list to user.
2. If there is a current candidate file, ask:
   - `是否在当前已打开文件上编辑？`
3. If user says no, ask user to pick one file from listed items.
4. After user confirms target file, enforce file binding in execution:
   - pass `--expected-file-key` when available, otherwise `--expected-file-name`.
5. Do not edit until user confirms target file explicitly.

## Required Workflow

### Step 0: Preflight

Before editing:

1. Import bridge plugin once in Figma desktop:
   - Plugins -> Development -> Import plugin from manifest
   - Select: `assets/figma-bridge-plugin/manifest.json`
2. Open target file and run plugin:
   - Plugins -> Development -> UI Doc Bridge
3. Check plugin activation on the confirmed file:
   - `scripts/figma_bridge_apply_plan.py --status-only --expected-file-key <fileKey>`
   - fallback: `scripts/figma_bridge_apply_plan.py --status-only --expected-file-name "<fileName>"`
4. If plugin not active on that file, activate plugin in that file, then rerun status check.
5. Verify local execution with dry-run:
   - `scripts/figma_bridge_apply_plan.py --plan <plan.json> --dry-run`

Cross-platform launcher note:

- macOS/Linux: run scripts with `python3`
- Windows (PowerShell): run scripts with `python`

### Step 1: Parse UI doc into plan

Generate incremental operation plan from markdown:

```bash
scripts/ui_doc_to_figma_plan.py \
  --input /absolute/path/to/ui-spec.md \
  --project-name prophet \
  --task-id task-20260212-a1 \
  --changed-headings "首页,我的" \
  --output /tmp/auto-figma/prophet_task-20260212-a1_plan.json \
  --device ios \
  --max-screens 12
```

Windows example (PowerShell):

```powershell
python scripts/ui_doc_to_figma_plan.py `
  --input C:\work\ui-spec-v2.md `
  --project-name prophet `
  --task-id task-20260212-a1 `
  --changed-headings "首页,我的" `
  --output "$env:TEMP\auto-figma\prophet_task-20260212-a1_plan.json" `
  --device ios `
  --max-screens 12
```

The generated plan contains bridge-compatible operation tokens for changed targets:

1. Create page
2. Switch page
3. Create/update frames for changed screens
4. Create/update title text in changed frames
5. Capture node IDs for traceability

### Step 2: Execute with dry-run first

Always run dry-run before real write:

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/prophet_task-20260212-a1_plan.json \
  --project-name prophet \
  --task-id task-20260212-a1 \
  --dry-run
```

Check for:

1. Placeholder resolution errors
2. Missing captures
3. Invalid command tokens

### Step 3: Execute real write

Run plan on connected Figma:

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/prophet_task-20260212-a1_plan.json \
  --project-name prophet \
  --task-id task-20260212-a1 \
  --captures-out /tmp/auto-figma/prophet_task-20260212-a1_captures.json \
  --expected-file-key <fileKey>
```

The captures file is the source of truth for created node IDs.

### Step 4: Expand or patch plan

When document detail is richer than initial scaffold:

1. Add operations for extra nodes and styles
2. Re-run dry-run
3. Re-run real apply

Plan format reference:

- `references/auto-edit-plan-format.md`

### Step 5: QA and delivery

Report:

1. Executed operations count
2. Created/updated node IDs
3. Failed operations (if any)
4. Next patch batch

Never claim completion without execution logs.
After successful real write, confirm temp cleanup result for current `<project>_<taskId>`.

## Scripts

### `scripts/ui_doc_to_figma_plan.py`

Purpose:

1. Parse UI markdown headings
2. Infer screen list
3. Generate executable plan JSON

Key args:

1. `--input`
2. `--output`
3. `--project-name`
4. `--task-id`
5. `--temp-root`
6. `--changed-headings`
7. `--full-refresh`
8. `--device`
9. `--page-name`
10. `--max-screens`

### `scripts/figma_bridge_apply_plan.py`

Purpose:

1. Start local bridge server
2. Receive command pulls from bridge plugin UI
3. Execute plan operations in order and capture node IDs
4. Check plugin/file status before editing
5. Clean task temp files after successful real write (default)

Key args:

1. `--plan`
2. `--dry-run`
3. `--captures-out`
4. `--project-name`
5. `--task-id`
6. `--temp-root`
7. `--host`
8. `--port`
9. `--status-only`
10. `--expected-file-key`
11. `--expected-file-name`
12. `--no-cleanup-task-files`

### `scripts/list_open_figma_files.py`

Purpose:

1. List currently open Figma files from local debug endpoint
2. Show one current candidate file for quick confirmation
3. Provide fileKey for file binding checks

Port note:

- Plugin UI default points to `127.0.0.1:38450`
- If you change `--port`, update `assets/figma-bridge-plugin/ui.html` `BASE` accordingly

### `assets/figma-bridge-plugin/`

Contains local plugin files:

1. `manifest.json`
2. `code.js`
3. `ui.html`

## Output Contract

Use this structure in responses:

1. `Input Summary`
2. `Generated Plan Path`
3. `Execution Result`
4. `Captured Node IDs`
5. `Cleanup Result`
6. `Next Patch`

## Resources

Use these files as needed:

1. `references/auto-edit-plan-format.md`
2. `references/doc-to-figma-template.md`
3. `references/bridge-plugin-setup.md`
