# DUALORA v0.4.0 — Interactive Display Control

Windows 10/11 utility for two or more desktop displays.

## New in v0.4.0
- Drag monitor rectangles in the Control Center layout, then confirm or revert (15-second timeout while app is running).
- Select supported video resolution and refresh rate through native Windows display API, with preflight validation and confirmation.
- Optional 5-second polling detects new Windows desktop displays and **offers** to restore a matching named monitor profile. It never changes profiles without consent.
- Work / Games presets, AQ32H3 troubleshooting, diagnostics JSON, portable EXE.

## Installation
Open the successful GitHub Actions run and download the `DUALORA-Windows-v0.4.0` artifact ZIP. Unzip and launch `DUALORA.exe` without installing Python.

## Safety and limits
- The tool reads modes exposed by the GPU/display driver, **not** actual HDMI voltage or physical pixel output.
- Monitor IDs (e.g. AQ32H3) are driver dependent.
- Timeout rollback needs a running Tk event loop; Windows may not restore configuration after a system crash or application termination. Keep access to Windows Display settings.
- Connection detection uses polling and prompts; it does not silently apply saved configurations.
- The preview is diagrammatic and drag moves can require further fine-tuning in Windows Settings.

## Tests
`python -m unittest discover -s tests -v`.
