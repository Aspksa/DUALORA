# DUALORA v0.3.0 — Control Center

DUALORA manages extended monitor desktops on Windows 10/11.

## What's new

- Dark Control Center with a proportional diagram of active monitor desktop rectangles.
- AQ32H3 troubleshooting wizard explaining actual Windows status and physical signal limitations.
- One-click Work and Games position profiles: first use saves the current layout; later use restores it with confirmation.
- Detailed device, monitor and refresh-rate report from Windows display APIs.
- Native projection options, named profiles, diagnostics export.
- Portable DUALORA.exe in successful Windows Actions artifacts (no Python required).

**Limitations:** The visual arrangement is read-only in this version; use profiles or Windows display settings to change layout. Monitor identification is subject to driver/EDID capabilities. An active Windows video mode does not prove a good physical HDMI/DP connection.

## Install

Open [GitHub Actions](https://github.com/Aspksa/DUALORA/actions), select the successful **DUALORA checks** run, download **DUALORA-Windows-v0.2.0** artifact (the artifact label will be updated to v0.3.0 in this version), extract and run DUALORA.exe.

For source use Python 3.10+ and Start_DUALORA.bat.

## Tests

`python -m unittest discover -s tests -v`.
