English | [中文](README-ZH.md)

# UI Doc to Figma

> Automatically convert UI design documents into executable Figma edit plans and apply them directly to Figma through a self-hosted bridge plugin

## Overview

This is an automation tool that converts UI markdown documents into Figma operation plans, then applies these operations directly to Figma through a local bridge plugin. It supports automatically creating pages, frames, text, setting layouts and styles, and capturing node IDs.

## Key Features

✨ **Document-Driven Design Automation**
- Automatically generate Figma operation plans from Markdown documents
- Support incremental updates and full refresh

🚀 **Automatic Execution Flow**
- Auto-generate operation plan JSON
- Execute through local bridge plugin
- Return created/updated node IDs

🛡️ **Cross-Platform Support**
- macOS / Linux / Windows
- Cross-platform script compatibility

📱 **Device Presets**
- iOS (390x844)
- Android (412x915)
- Web (1440x1024)
- iPad (1024x1366)

🧹 **Task Isolation and Auto-Cleanup**
- Task-level temporary file management
- Auto-cleanup after execution
- Support concurrent project runs

## Quick Start

### Prerequisites

1. Figma desktop application installed and open
2. Python 3 environment
3. Markdown file containing UI design document

### Installation and Setup

#### 1. Import Figma Bridge Plugin

In the Figma desktop app:
```
Plugins → Development → Import plugin from manifest → Select assets/figma-bridge-plugin/manifest.json
```

#### 2. Verify Plugin is Ready

```bash
# macOS/Linux
python3 scripts/figma_bridge_apply_plan.py --status-only --expected-file-name "Your Figma File"

# Windows
python scripts/figma_bridge_apply_plan.py --status-only --expected-file-name "Your Figma File"
```

### Basic Usage

#### Step 1: List Open Figma Files

```bash
scripts/list_open_figma_files.py
```

#### Step 2: Generate Edit Plan

Generate Figma operation plan from UI Markdown document:

```bash
# macOS/Linux
python3 scripts/ui_doc_to_figma_plan.py \
  --input /path/to/ui-spec.md \
  --project-name my-project \
  --task-id task-001 \
  --device ios \
  --output /tmp/auto-figma/my-project_task-001_plan.json

# Windows (PowerShell)
python scripts/ui_doc_to_figma_plan.py `
  --input C:\path\to\ui-spec.md `
  --project-name my-project `
  --task-id task-001 `
  --device ios `
  --output "$env:TEMP\auto-figma\my-project_task-001_plan.json"
```

#### Step 3: Dry Run Test

Verify before actual execution:

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/my-project_task-001_plan.json \
  --project-name my-project \
  --task-id task-001 \
  --dry-run
```

#### Step 4: Execute Edit Plan

Apply changes to Figma:

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/my-project_task-001_plan.json \
  --project-name my-project \
  --task-id task-001 \
  --captures-out /tmp/auto-figma/my-project_task-001_captures.json \
  --expected-file-key <fileKey>
```

## Project Structure

```
ui-doc-to-figma/
├── README.md                          # Project documentation (English)
├── README-ZH.md                       # Project documentation (Chinese)
├── SKILL.md                           # Detailed skill and workflow documentation
├── LICENSE                            # MIT License
├── assets/
│   └── figma-bridge-plugin/           # Local Figma plugin
│       ├── manifest.json              # Plugin manifest
│       ├── code.js                    # Plugin logic
│       └── ui.html                    # Plugin UI interface
├── scripts/
│   ├── ui_doc_to_figma_plan.py       # Main script for generating edit plans
│   ├── figma_bridge_apply_plan.py    # Script for executing edit plans
│   └── list_open_figma_files.py      # Script to list open Figma files
├── references/                        # Reference documentation
│   ├── auto-edit-plan-format.md      # Edit plan format reference
│   ├── bridge-plugin-setup.md        # Plugin setup guide
│   └── doc-to-figma-template.md      # UI document template
└── agents/
    └── openai.yaml                    # Configuration file
```

## Script Documentation

### `scripts/ui_doc_to_figma_plan.py`

Generate Figma operation plan from Markdown document.

**Key Parameters:**
- `--input`: UI Markdown document path (required)
- `--output`: Output edit plan JSON file path
- `--project-name`: Project name
- `--task-id`: Task ID (for file isolation)
- `--device`: Device preset (ios/android/web/ipad)
- `--changed-headings`: Only process changed headings (incremental update)
- `--full-refresh`: Full refresh (use on initial build)
- `--max-screens`: Maximum number of screens
- `--page-name`: Page name

### `scripts/figma_bridge_apply_plan.py`

Execute edit plan and communicate with Figma bridge plugin.

**Key Parameters:**
- `--plan`: Edit plan JSON file path (required)
- `--dry-run`: Dry run mode (no actual modification)
- `--captures-out`: Output file path for captured node IDs
- `--project-name`: Project name
- `--task-id`: Task ID
- `--expected-file-key`: Target Figma file key
- `--expected-file-name`: Target Figma file name
- `--status-only`: Only check plugin status
- `--host`: Server address (default: 127.0.0.1)
- `--port`: Server port (default: 38450)
- `--no-cleanup-task-files`: Do not cleanup temporary files after execution

### `scripts/list_open_figma_files.py`

List currently open Figma files and their file keys for target file confirmation.

## Temporary File Management

The project uses task-level temporary file management following these conventions:

**Temporary File Root Directory:**
- macOS/Linux: `/tmp/auto-figma`
- Windows: `%TEMP%\auto-figma`

**File Naming Format:**
- `<project>_<taskId>_plan.json` - Edit plan
- `<project>_<taskId>_captures.json` - Captured node IDs

**Auto-Cleanup:**
- Automatically delete related temp files after successful execution
- Can be disabled with `--no-cleanup-task-files`

## Incremental Update Workflow

The project uses incremental updates by default for efficiency:

1. **First Run:** Use `--full-refresh` flag for complete initialization
2. **Subsequent Updates:** Use `--changed-headings` to process only changed parts
3. **Fetch Fresh Context:** For new user requirements, fetch fresh node context directly from Figma

## File Selection Flow

Before editing, you must confirm the target Figma file:

1. Run `scripts/list_open_figma_files.py` to list open files
2. System will ask "Edit on the currently open file?"
3. Based on your choice, use `--expected-file-key` or `--expected-file-name` to bind the file

## Edit Plan Format

Edit plan is a JSON file containing the following operations:

- Create page
- Switch page
- Create/update frames for changed screens
- Create/update title text in frames
- Capture node IDs for tracing

See [references/auto-edit-plan-format.md](references/auto-edit-plan-format.md) for details

## Output Structure

After execution, the response contains:

1. **Input Summary** - Processed document and parameters
2. **Generated Plan Path** - Edit plan file location
3. **Execution Result** - Operation execution status
4. **Captured Node IDs** - List of created/updated nodes
5. **Cleanup Result** - Temporary file cleanup status
6. **Next Steps** - Subsequent patches or expansion plans

## Cross-Platform Notes

### macOS / Linux
```bash
# Use python3 command
python3 scripts/ui_doc_to_figma_plan.py ...
python3 scripts/figma_bridge_apply_plan.py ...
```

### Windows (PowerShell)
```powershell
# Use python command
python scripts/ui_doc_to_figma_plan.py ...
python scripts/figma_bridge_apply_plan.py ...
```

## Reference Resources

- [SKILL.md](SKILL.md) - Detailed skill definition and workflow
- [references/auto-edit-plan-format.md](references/auto-edit-plan-format.md) - Edit plan format reference
- [references/doc-to-figma-template.md](references/doc-to-figma-template.md) - UI document template
- [references/bridge-plugin-setup.md](references/bridge-plugin-setup.md) - Plugin setup guide

## FAQ

### Q: What if the plugin won't activate?
A: Open your target file in Figma, then run:
```
Plugins → Development → UI Doc Bridge
```
After activation, rerun the status check.

### Q: How do I view execution logs?
A: Add the `--dry-run` flag during execution to test and check for error messages.

### Q: Can I apply custom styles?
A: Yes. You can extend operations in the edit plan to include colors, fonts, spacing, and more.

### Q: How do I handle concurrent editing on multiple projects?
A: Use a unique `task-id` for each task, and the system will automatically isolate temporary files.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Author

XinChenyang1214

---

**Last Updated:** February 15, 2026
