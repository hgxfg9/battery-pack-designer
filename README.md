# Battery Pack Designer

Battery Pack Designer is a local planning tool for cylindrical battery packs. It helps you lay out cells, validate `SxP` combinations, compare routing options, review node grouping, and step through a welding sequence before building a pack.

The project ships with:

- a shared Python planning core
- a Flask web interface
- a PySide6 desktop wrapper
- a Windows single-file build path based on PyInstaller

## What it does

- Supports common cylindrical cell formats such as `14500`, `18350`, `18650`, `20700`, `21700`, `26650`, `32700`, `32140`, and `46800`
- Generates `RECT`, `HONEYCOMB`, `STACK`, and `TRIANGLE` placement layouts
- Validates whether the requested `series_count * parallel_count` fits in the active slots
- Compares multiple routing schemes and estimates difficulty, jump wires, folds, and bus length
- Produces tab-strip grouping, balance lead anchors, and weld steps
- Renders top, front, side, exploded, and pseudo-3D views

## Project layout

```text
src/
  battery_pack_designer/
    cell_library.py
    models.py
    planner.py
    web/app.py
    desktop/app.py
    templates/index.html
    static/app.css
    static/app.js
tests/
  test_planner.py
  test_web_app.py
battery_pack_designer.spec
```

## Requirements

- Python 3.10 or newer
- Windows for the packaged desktop executable workflow
- A local Python environment with `pip`

## Install from source

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

If you want to run tests as well:

```bash
pip install -e .[dev]
```

## Run the application from source

### Web interface

```bash
python -m battery_pack_designer.web.app --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000` in a browser.

### Desktop interface

```bash
python -m battery_pack_designer.desktop.app
```

The desktop application starts a local Flask server on `127.0.0.1` and embeds it in a PySide6 window. If `QtWebEngine` is unavailable, it falls back to the system browser and keeps a small desktop window open with the local URL.

## API example

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

The response includes:

- `metrics`
- `cells`
- `route_options`
- `tab_strips`
- `jump_wires`
- `balance_leads`
- `weld_steps`

## Hole mask format

Use one `layer,row,col` triple per line:

```text
1,2,3
1,2,4
2,1,1
```

This is useful for irregular pack shapes, fixture clearances, cable paths, or structural cutouts.

## Testing

macOS/Linux:

```bash
PYTHONPATH=src pytest
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
pytest
```

## Build a single-file Windows executable

The repository includes a `PyInstaller` spec file that bundles the desktop application, Flask templates, static assets, and Qt WebEngine dependencies into a single `exe`.

### 1. Install build dependencies

```bash
pip install -r requirements.txt
pip install pyinstaller
pip install -e .
```

### 2. Build the executable

Run this from the repository root:

```bash
python -m PyInstaller --noconfirm --clean battery_pack_designer.spec
```

Expected output:

```text
dist/BatteryPackDesigner.exe
```

### 3. Smoke-test the packaged executable

After the build completes, launch the executable once and confirm that:

- the desktop window opens
- the planner UI loads
- the app can render the default design

If `QtWebEngine` cannot be loaded on the target machine, the executable should open the planner in the default browser and show the fallback window with the local URL.

## Create a release artifact

If you want to publish a release manually, a straightforward Windows flow looks like this:

```powershell
python -m PyInstaller --noconfirm --clean battery_pack_designer.spec
Get-FileHash .\dist\BatteryPackDesigner.exe -Algorithm SHA256
```

You can then upload:

- `dist/BatteryPackDesigner.exe`
- a checksum file such as `BatteryPackDesigner.exe.sha256.txt`

## Dependency Notes

- `Flask` serves the local UI and JSON API
- `PySide6` provides the desktop shell
- `PySide6.QtWebEngine` embeds the local planner in the desktop window
- `pytest` is used for the small regression test suite
- `PyInstaller` is used for the Windows desktop build
