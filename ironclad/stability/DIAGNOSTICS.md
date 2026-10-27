# IRONCLAD Launcher Diagnostics (development)

This feature records unexpected **systemd EmulationStation unit** failures on TF1 only.

- Service drop-in uses `ExecStopPost` and passes systemd exit metadata.
- The Python logger ignores successful clean stops.
- Two generations of a 64 KiB log are retained in `/var/lib/ironclad/`.
- The read-only viewer is installed under Advanced tools.
- No firmware, emulators, game saves, ROMs, or TF2 content are changed by the logger.
- Does **not** guarantee detection of internally handled game or launcher crashes.
- Existing upstream `Restart=on-failure` is preserved.
- Test with `python3 -m unittest discover -s ironclad/stability -p 'test_*.py'`.
- Not hardware-tested: validate with a disposable TF1 on RG353V.
