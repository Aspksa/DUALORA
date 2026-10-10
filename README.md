# DUALORA v0.2.0

Windows 10/11 multi-monitor diagnostics, recognition, projection and position profiles.

## Features
- Detect active desktop displays and friendly names / identifiers of connected monitors (including AQ32H3 when the display driver exposes a name).
- Show active video mode, refresh rate, coordinates and monitor device ID.
- Extend, duplicate, internal-only and external-only Windows projection modes.
- Save named monitor **position** profiles and restore them. Before applying, reject a different set of monitors or changed resolutions, test mode changes, and offer an automatic 15-second rollback while the app remains running.
- Export diagnostics JSON.
- Portable `DUALORA.exe` assembled in GitHub Actions, requiring no installed Python on your PC.

## Run
Go to **Actions → DUALORA checks → successful run → Artifacts → DUALORA-Windows-v0.2.0**. Download the ZIP, extract it, run `DUALORA.exe`. This is an unsigned binary: Windows may warn before launch. Alternatively install Python 3.10+ and double-click `Start_DUALORA.bat`.

## Important limitations
Monitor EDID identification and active Windows video mode do **not** prove that HDMI/DisplayPort has a valid electrical signal or the monitor is physically displaying pixels. If AQ32H3 is black, check source selection, cable, adapter and Windows settings. Profiles control **position only**, not physical connectivity, resolution, or refresh rate. A rollback cannot operate if DUALORA exits or Windows crashes. Use manual display settings for recovery.

Project status: [PROJECT_STATE.md](PROJECT_STATE.md).
