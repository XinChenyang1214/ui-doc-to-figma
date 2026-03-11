[English](README.md) | 中文

# UI Doc to Figma

> 将UI设计文档自动转换为可执行的Figma编辑计划，并通过自托管桥接插件直接应用到Figma中

## 概述

这是一个自动化工具，可将UI markdown文档转换为Figma操作计划，然后通过本地桥接插件将这些操作直接应用到Figma中。支持自动创建页面、框架、文本，设置布局和样式，以及捕获节点ID。

## 核心特性

✨ **文档驱动的设计自动化**
- 从Markdown文档自动生成Figma操作计划
- 支持增量更新和完整刷新

🚀 **自动执行流程**
- 自动生成操作计划JSON
- 通过本地桥接插件执行
- 返回创建/更新的节点ID

🛡️ **多平台支持**
- macOS / Linux / Windows
- 跨平台脚本兼容性

📱 **设备预设**
- iOS (390x844)
- Android (412x915)
- Web (1440x1024)
- iPad (1024x1366)

🧹 **任务隔离和自动清理**
- 任务级临时文件管理
- 执行后自动清理
- 支持并发项目运行

## 快速开始

### 前置条件

1. Figma桌面应用已安装并打开
2. Python 3 环境
3. 包含UI设计文档的Markdown文件

### 安装和设置

#### 1. 导入Figma桥接插件

在Figma桌面应用中：
```
插件 → 开发 → 从清单导入插件 → 选择 assets/figma-bridge-plugin/manifest.json
```

#### 2. 验证插件就绪

```bash
# macOS/Linux
python3 scripts/figma_bridge_apply_plan.py --status-only --expected-file-name "Your Figma File"

# Windows
python scripts/figma_bridge_apply_plan.py --status-only --expected-file-name "Your Figma File"
```

### 基本用法

#### 步骤 1: 列出打开的Figma文件

```bash
scripts/list_open_figma_files.py
```

#### 步骤 2: 生成编辑计划

从UI Markdown文档或HTML源码生成Figma操作计划：

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


从HTML生成（严格一致性流程）：

```bash
python3 scripts/html_to_figma_plan.py \
  --input /path/to/page.html \
  --project-name my-project \
  --task-id task-html-001 \
  --frame-width 1440 \
  --frame-height 1024 \
  --output /tmp/auto-figma/my-project_task-html-001_plan.json
```

#### 步骤 3: 干运行测试

在实际执行前进行验证：

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/my-project_task-001_plan.json \
  --project-name my-project \
  --task-id task-001 \
  --dry-run
```

#### 步骤 4: 执行编辑计划

实际应用到Figma：

```bash
scripts/figma_bridge_apply_plan.py \
  --plan /tmp/auto-figma/my-project_task-001_plan.json \
  --project-name my-project \
  --task-id task-001 \
  --captures-out /tmp/auto-figma/my-project_task-001_captures.json \
  --expected-file-key <fileKey>
```

## 项目结构

```
ui-doc-to-figma/
├── README.md                          # 项目文档（英文版）
├── README-ZH.md                       # 项目文档（中文版）
├── SKILL.md                           # 详细的技能和工作流文档
├── LICENSE                            # MIT许可证
├── assets/
│   └── figma-bridge-plugin/           # 本地Figma插件
│       ├── manifest.json              # 插件清单
│       ├── code.js                    # 插件逻辑
│       └── ui.html                    # 插件UI界面
├── scripts/
│   ├── ui_doc_to_figma_plan.py       # 生成编辑计划的主脚本
│   ├── figma_bridge_apply_plan.py    # 执行编辑计划的脚本
│   ├── list_open_figma_files.py      # 列出打开的Figma文件
│   └── html_to_figma_plan.py         # 从HTML生成编辑计划
├── references/                        # 参考文档
│   ├── auto-edit-plan-format.md      # 编辑计划格式说明
│   ├── bridge-plugin-setup.md        # 插件设置指南
│   ├── doc-to-figma-template.md      # UI文档模板
│   └── html-to-figma-parity.md       # HTML还原一致性指南
└── agents/
    └── openai.yaml                    # 配置文件
```

## 脚本说明

### `scripts/ui_doc_to_figma_plan.py`

从Markdown文档生成Figma操作计划。

**关键参数：**
- `--input`: UI Markdown文档路径（必需）
- `--output`: 输出的编辑计划JSON路径
- `--project-name`: 项目名称
- `--task-id`: 任务ID（用于文件隔离）
- `--device`: 设备预设 (ios/android/web/ipad)
- `--changed-headings`: 仅处理变更的标题（增量更新）
- `--full-refresh`: 完全刷新（初始化时使用）
- `--max-screens`: 最大屏幕数
- `--page-name`: 页面名称

### `scripts/html_to_figma_plan.py`

从HTML文档生成Figma操作计划，目标是严格还原结构和样式。

**关键参数：**
- `--input`: HTML文档路径（必需）
- `--output`: 输出编辑计划JSON路径
- `--project-name`: 项目名称
- `--task-id`: 任务ID（用于文件隔离）
- `--frame-width`: 根画板宽度
- `--frame-height`: 根画板高度

### `scripts/figma_bridge_apply_plan.py`

执行编辑计划，与Figma桥接插件通信。

**关键参数：**
- `--plan`: 编辑计划JSON文件路径（必需）
- `--dry-run`: 干运行模式（不实际修改）
- `--captures-out`: 输出捕获的节点ID的文件路径
- `--project-name`: 项目名称
- `--task-id`: 任务ID
- `--expected-file-key`: 目标Figma文件的key
- `--expected-file-name`: 目标Figma文件的名称
- `--status-only`: 仅检查插件状态
- `--host`: 服务器地址（默认: 127.0.0.1）
- `--port`: 服务器端口（默认: 38450）
- `--no-cleanup-task-files`: 执行后不清理临时文件

### `scripts/list_open_figma_files.py`

列出当前打开的Figma文件及其file key，用于确认目标文件。

## 临时文件管理

项目使用任务级临时文件管理，遵循以下约定：

**临时文件根目录：**
- macOS/Linux: `/tmp/auto-figma`
- Windows: `%TEMP%\auto-figma`

**文件命名格式：**
- `<project>_<taskId>_plan.json` - 编辑计划
- `<project>_<taskId>_captures.json` - 捕获的节点ID

**自动清理：**
- 成功执行后自动删除相关临时文件
- 可通过 `--no-cleanup-task-files` 禁用自动清理

## 增量更新工作流

项目默认使用增量更新来提高效率：

1. **首次运行：** 使用 `--full-refresh` 标志进行完整初始化
2. **后续更新：** 使用 `--changed-headings` 仅处理变更部分
3. **重新获取上下文：** 新的用户需求时，直接从Figma获取最新节点上下文

## 文件选择流程

在编辑前，必须确认目标Figma文件：

1. 运行 `scripts/list_open_figma_files.py` 列出打开的文件
2. 系统会询问 "是否在当前已打开文件上编辑？"
3. 根据选择，使用 `--expected-file-key` 或 `--expected-file-name` 绑定文件

## 编辑计划格式

编辑计划是一个JSON文件，包含以下操作：

- 创建页面
- 切换页面
- 为变更屏幕创建/更新框架
- 在框架中创建/更新标题文本
- 捕获节点ID用于跟踪

详见 [references/auto-edit-plan-format.md](references/auto-edit-plan-format.md)

## 输出结构

执行完成后，响应包含：

1. **输入摘要** - 处理的文档和参数
2. **生成的计划路径** - 编辑计划文件位置
3. **执行结果** - 操作执行情况
4. **捕获的节点ID** - 创建/更新的节点列表
5. **清理结果** - 临时文件清理状态
6. **下一步操作** - 后续补丁或扩展计划

## 跨平台说明

### macOS / Linux
```bash
# 使用 python3 命令
python3 scripts/ui_doc_to_figma_plan.py ...
python3 scripts/figma_bridge_apply_plan.py ...
```

### Windows (PowerShell)
```powershell
# 使用 python 命令
python scripts/ui_doc_to_figma_plan.py ...
python scripts/figma_bridge_apply_plan.py ...
```

## 参考资源

- [SKILL.md](SKILL.md) - 详细的技能定义和工作流
- [references/auto-edit-plan-format.md](references/auto-edit-plan-format.md) - 编辑计划格式参考
- [references/doc-to-figma-template.md](references/doc-to-figma-template.md) - UI文档模板
- [references/html-to-figma-parity.md](references/html-to-figma-parity.md) - HTML还原一致性指南
- [references/bridge-plugin-setup.md](references/bridge-plugin-setup.md) - 插件设置指南

## 常见问题

### Q: 插件不激活怎么办？
A: 在Figma中打开目标文件，然后运行：
```bash
插件 → 开发 → UI Doc Bridge
```
激活后重新运行状态检查。

### Q: 如何查看执行日志？
A: 执行时添加 `--dry-run` 标志进行测试，检查是否有错误提示。

### Q: 支持自定义样式吗？
A: 支持。可以在编辑计划中扩展操作以包含颜色、字体、间距等样式设置。

### Q: 如何处理多项目并发编辑？
A: 为每个任务使用唯一的 `task-id`，系统会自动隔离临时文件。

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 作者

XinChenyang1214

---

**更新日期：** 2026年2月15日
