# DUALORA project state
- Version: 0.2.0
- Added: Windows device/monitor identification, active video modes (resolution/hz), position profiles, rollback prompt, CI-produced portable EXE.
- Device identification: EnumDisplayDevicesW and EnumDisplaySettingsW; no physical HDMI signal measurement.
- Tests: GitHub Windows+Linux unittest and compile; EXE built on Windows.
- Windows hardware verification: pending on actual AQ32H3 laptop.
- next_action: Verify checks and EXE artifact in GitHub Actions, run the EXE on Windows with AQ32H3 and share the exported diagnostics JSON.
