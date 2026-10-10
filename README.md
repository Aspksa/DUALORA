# DUALORA

**DUALORA** — open-source Windows 10/11 desktop tool for checking and managing laptop/external monitors.

## Features (v0.1.0)

- Russian-language graphical interface, built with Python standard-library Tkinter.
- Enumerates **active desktop monitor rectangles** using Windows `EnumDisplayMonitors` rather than mistaking WMI detection for working video output.
- Reads additional WMI monitor records for diagnostic context.
- Switches Windows projection modes: **Extend**, **Duplicate**, **PC screen only**, **Second screen only** (confirmation required).
- Opens Windows Display settings.
- Exports a JSON report to `%USERPROFILE%\\DUALORA\\diagnostics.json`.

## Run

1. Install Python 3.10+ for Windows with Tkinter enabled.
2. Download the repository (Code → Download ZIP) and extract it.
3. Double-click **Start_DUALORA.bat**.

Or run `python dualora.py` in a terminal.

No administrator rights or third-party Python dependencies required.

## Black external monitor?

1. Turn on the monitor and select its actual **Input/Source** (HDMI/DP).
2. Check both cable ends or try another cable/port.
3. Click **Расширить экраны**, then **Обновить диагностику**.
4. Open Windows Display settings and temporarily select a supported resolution and refresh rate (e.g., 1920×1080 at 60 Hz if available).
5. If Windows shows two active desktops but the screen stays black, software cannot guarantee repair: investigate cable, adapter, source, monitor and GPU drivers.

**Safety:** The app never installs drivers, changes firmware, invokes administrator elevation, or silently switches displays. A detected WMI monitor does not prove video output works. DisplaySwitch requests may not succeed; verify the layout again.

## Project layout

- `dualora.py` — desktop application + diagnostics
- `Start_DUALORA.bat` — Windows launcher
- `tests/test_core.py` — tests for non-hardware behavior
- `.github/workflows/ci.yml` — syntax/tests on Windows and Linux

## Roadmap

- v0.2: Windows display configuration API, named displays, advanced diagnostics, revert-safe settings.
- v0.3: saved monitor layouts and configuration history.
- v1.0: digitally signed Windows installer and optional packaged EXE.

See [PROJECT_STATE.md](PROJECT_STATE.md).
