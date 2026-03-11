# HTML to Figma Parity Guide

Use this guide when restoring HTML into Figma and the result must match HTML as closely as possible.

## Goal

- DOM structure parity: keep parent-child nesting.
- Visual parity: geometry, text content, and colors should match source HTML/CSS.
- Execution parity: always dry-run then real apply, and verify captured nodes for each major block.

## Recommended Flow

1. Generate plan from HTML with `scripts/html_to_figma_plan.py`.
2. Run `scripts/figma_bridge_apply_plan.py --dry-run`.
3. Apply real write and export captures.
4. Compare source HTML vs Figma (layout/text/color).
5. If mismatch exists, patch plan and re-run.

## Source Priority

When building/patching plan, use this priority order:

1. Inline style values (`style="..."`)
2. Semantic HTML structure (`body`, `header`, `main`, `section`, `article`, `footer`, etc.)
3. Fallback defaults from the generator (`frame-width`, `frame-height`, `y-gap`)

## Known Limits

Current bridge commands cover page/frame/text and common style properties. Complex CSS effects (pseudo-elements, blend modes, advanced shadows, grid auto-placement, transforms, filters) require manual plan patching and possible plugin extension.
