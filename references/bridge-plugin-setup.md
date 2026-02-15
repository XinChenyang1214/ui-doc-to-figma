# Bridge Plugin Setup

Use this when running the self-hosted tool layer (without figma-use).

## 1. Import plugin once

In Figma desktop:

1. Open any design file.
2. Plugins -> Development -> Import plugin from manifest.
3. Select:
   - `assets/figma-bridge-plugin/manifest.json`

## 2. Start plugin for current file

1. Plugins -> Development -> UI Doc Bridge.
2. Keep plugin running while executing plan scripts.

## 3. Confirm target file before edit

List open files:

```bash
scripts/list_open_figma_files.py
```

After user confirms target file, check plugin binding:

```bash
scripts/figma_bridge_apply_plan.py --status-only --expected-file-key <fileKey>
```

Fallback when fileKey is unavailable in status payload:

```bash
scripts/figma_bridge_apply_plan.py --status-only --expected-file-name "<fileName>"
```

If status fails, run plugin in that file and retry.

## 4. Run apply script

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/prophet_task-20260212-a1_plan.json \
  --project-name prophet \
  --task-id task-20260212-a1
```

Optional:

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/prophet_task-20260212-a1_plan.json \
  --project-name prophet \
  --task-id task-20260212-a1 \
  --captures-out /tmp/auto-figma/prophet_task-20260212-a1_captures.json
```

Windows (PowerShell):

```powershell
python scripts/figma_bridge_apply_plan.py `
  --plan "$env:TEMP\auto-figma\prophet_task-20260212-a1_plan.json" `
  --project-name prophet `
  --task-id task-20260212-a1 `
  --captures-out "$env:TEMP\auto-figma\prophet_task-20260212-a1_captures.json"
```

## 5. Troubleshooting

1. If script says bridge plugin not connected:
   - Ensure plugin is running in the same file window.
2. If timeout occurs:
   - Re-run plugin and retry script.
3. If port conflict occurs:
   - Change script `--port` and keep `ui.html` `BASE` in sync.
4. If incremental run finds no matching screens:
   - Verify `--changed-headings` and rerun.
5. If task temp files need to be kept for debugging:
   - Add `--no-cleanup-task-files` once, then clean manually later.
