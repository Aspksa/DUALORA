# DUALORA 0.5.0 — Display Control & Diagnostics

Windows 10/11 multi-monitor utility. Tkinter UI with draggable monitor diagram, supported mode selection, positional profiles and opt-in connection watcher.

## v0.5.0
- Dedicated **Журнал** history window for diagnostic scans and changes.
- Local bounded JSON Lines journal under `%USERPROFILE%\\DUALORA\\history.jsonl`, last 500 events.
- AQ32H3 recognition cross-checks active Windows display mode and WMI EDID records.
- Clear warnings about monitor signal limitations and driver-dependent identification.
- Portable Python-free executable via GitHub Actions `DUALORA-Windows-v0.5.0`.

## Limitations
This application cannot measure physical HDMI/DP voltage or confirm that the monitor displays a visible image. Diagrammatic screen positioning is based on Windows display geometry. Safety rollback requires the application to remain active. Windows drivers may omit manufacturer/model information. History is stored locally, without cloud upload.

## Install
GitHub Actions → successful DUALORA checks run → Artifacts → DUALORA-Windows-v0.5.0 → unzip and run DUALORA.exe.

## Tests
`python -m unittest discover -s tests -v`.
