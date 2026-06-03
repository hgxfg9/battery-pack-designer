# Battery Pack Designer / 电池包规划器

Battery Pack Designer is an open-source planning tool for cylindrical battery packs. It helps engineers preview pack layout, validate `S x P` topology, compare routing schemes, estimate tab-strip and jump-wire work, and walk through weld steps before building a real pack.

电池包规划器是一个面向圆柱电芯电池包的开源规划工具。它用于在实际焊接前预览电池包布局、校验 `S x P` 拓扑、对比布线方案、估算镍片与跳线工作量，并按步骤演示焊接流程。

## Highlights / 项目亮点

- Shared Python planning core for both web and desktop entrypoints.
- Built-in support for `14500`, `18350`, `18650`, `20700`, `21700`, `26650`, `32700`, `32140`, and `46800`.
- Placement modes: `RECT`, `HONEYCOMB`, `STACK`, and `TRIANGLE`.
- Topology validation for `S x P` against active slots after optional hole masking.
- Five routing strategies with difficulty scoring, jump-wire counts, fold hints, and bus-length estimates.
- Automatic node labeling for `B0` through `BS`, tab-strip grouping, and balance-lead anchor hints.
- 2D top/front/side/exploded views plus an offline-friendly pseudo-3D preview.
- PySide6 desktop shell that reuses the same local web experience.

## Architecture / 架构说明

```text
src/
  battery_pack_designer/
    cell_library.py      Built-in cylindrical cell database
    models.py            Shared request/result dataclasses
    planner.py           Core layout, routing, tab-strip, and weld-step logic
    web/app.py           Flask server and JSON API
    desktop/app.py       PySide6 desktop wrapper
    templates/index.html Web UI
    static/app.css       Styles
    static/app.js        Rendering and interaction logic
tests/
  test_planner.py        Smoke tests for the shared planning engine
```

## Quick Start / 快速开始

### 1. Create a virtual environment / 创建虚拟环境

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies / 安装依赖

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Run the web app / 启动 Web 版本

```bash
python -m battery_pack_designer.web.app --host 127.0.0.1 --port 5000
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

随后在浏览器中访问 [http://127.0.0.1:5000](http://127.0.0.1:5000)。

### 4. Run the desktop app / 启动桌面版本

```bash
python -m battery_pack_designer.desktop.app
```

The desktop shell launches a local Flask server and embeds it inside PySide6 when `QtWebEngine` is available. If `QtWebEngine` is not installed, it falls back to the default browser.

桌面版本会先启动本地 Flask 服务，再在 `QtWebEngine` 可用时嵌入到 PySide6 窗口中；如果 `QtWebEngine` 不可用，则自动回退到默认浏览器。

## API Example / API 示例

`POST /api/design`

```json
{
  "cell_model": "18650",
  "placement_mode": "honeycomb",
  "rows": 4,
  "cols": 3,
  "layers": 1,
  "series_count": 4,
  "parallel_count": 3,
  "gap_mm": 2.0,
  "layer_gap_mm": 3.0,
  "route_scheme": "auto",
  "orientation_mode": "alternating",
  "hole_mask_text": ""
}
```

Response fields include:

- `metrics`: capacity, voltage, energy, weight, and pack envelope.
- `cells`: per-cell placement and assigned electrical group.
- `route_options`: alternative routing strategies and their scores.
- `tab_strips`: node-level nickel strip groupings.
- `jump_wires`: estimated jump-wire segments.
- `balance_leads`: anchor hints for `B0 ... BS`.
- `weld_steps`: step-by-step welding sequence for UI playback.

返回结果包含：

- `metrics`：容量、电压、能量、重量与包体尺寸。
- `cells`：每个电芯的位置与串并联分组。
- `route_options`：多种布线策略及其评分。
- `tab_strips`：节点级镍片分组。
- `jump_wires`：跳线段估算。
- `balance_leads`：`B0 ... BS` 平衡线引出建议。
- `weld_steps`：用于界面播放的焊接步骤序列。

## Hole Mask Format / 异形空位格式

To create custom empty slots, enter one `layer,row,col` triple per line:

自定义挖空位置时，每行输入一组 `layer,row,col`：

```text
1,2,3
1,2,4
2,1,1
```

This is useful for irregular enclosures, fixture offsets, structural ribs, or cable passages.

这适用于异形外壳、治具避让、加强筋位置以及走线通道预留。

## Testing / 测试

```bash
PYTHONPATH=src pytest
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
pytest
```

## Dependency Notes / 依赖说明

- `Flask`: local HTTP server and JSON API for the browser-based planner.
- `PySide6`: desktop shell for Windows-friendly packaging and future native controls.
- `pytest`: optional development dependency for smoke tests.

## Packaging Direction / 打包方向

- Web: deploy the Flask app behind a lightweight Python runtime.
- Desktop: package with `PyInstaller` or `Nuitka` into a Windows executable.
- Core: keep `planner.py` and data models framework-agnostic so desktop and web remain aligned.

## Current Scope / 当前范围

This repository ships a strong MVP, not a finished production CAD system. The current implementation focuses on:

当前仓库提供的是高质量首版，不是完整的生产级 CAD 系统。目前重点完成：

- shared computation model,
- route comparison,
- node and weld planning,
- multi-view visualization,
- bilingual project documentation,
- a publish-ready open-source repository layout.

Planned next steps:

后续建议优先补强：

- true Three.js 3D geometry,
- editable drag-and-drop cell placement,
- export to DXF/SVG/CSV,
- richer pack templates and user presets,
- real EXE packaging workflow and CI pipelines.

## GitHub Publishing / 发布到 GitHub

Recommended repository name:

建议仓库名：

```text
battery-pack-designer
```

Suggested commands:

建议命令：

```bash
git init
git add .
git commit -m "Initial MVP for Battery Pack Designer"
gh repo create battery-pack-designer --public --source=. --remote=origin --push
```

If you prefer another repository name or organization, replace the final command accordingly.

如果你想使用其他仓库名或组织名，只需替换最后一条命令即可。
