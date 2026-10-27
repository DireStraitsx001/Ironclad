# IRONCLAD — RG353V integration candidate

Unofficial fork of Christian Haitian's dArkOS. Preserve upstream history,
copyright notices, and licenses.

**STATUS: INTEGRATION PREVIEW — NOT FLASH-READY OR HARDWARE VALIDATED.**

Target: Anbernic RG353V (RK3566). The original `ironclad/1.0` branch
remains unchanged while a separate VirtualBox build is running.

## Image-integrated on this development branch

1. RG353V-only EmulationStation service failure diagnostics, bounded
   to two approximately 64 KiB files on TF1, with Advanced-menu viewer.
2. A conservative brightness-state guard for the existing RK3566 systemd
   suspend/resume hook, staged on RG353V only.
3. Restart backoff of 2 seconds for EmulationStation and source-preview
   release identity/firmware output naming.

## Source-only (NOT installed or automatically enabled)

- RetroArch game-history / Switchboard prototype.
- Safe Resume preflight for existing ROM, core, and save-state inspection.
- Experimental CLI launcher that requires explicit confirmation and makes
  private TF1 state copies, then expects manual RetroArch state loading.

These features are deliberately excluded from the system image while their
compatibility, data isolation, and session behavior are investigated.

TF1 is the OS card; TF2 holds ROMs, saves, tools, and backups.
Do not test on your only working SD card. We make no promise that an
experimental game launcher preserves all emulator core settings or saves.

## Source checks

```sh
bash ironclad/check-source.sh
python3 -m unittest discover -v -s ironclad/stability -p 'test_*.py'
python3 -m unittest discover -v -s ironclad/switchboard -p 'test_*.py'
bash ironclad/tests/test_integration_staging.sh
```

GitHub Actions runs these checks for this development branch and its draft PR.
The staging smoke test uses a mocked sudo and a disposable filesystem,
not an ARM firmware image or a hardware emulator.

## Next

- Confirm all integration checks pass.
- Complete an RG353V image build from this integration branch on a **separate**
  build workspace after the existing build finishes.
- Boot from a **spare TF1**, preferably with disposable saves/ROMs on TF2.
- Test EmulationStation boot, crash logging, repeat suspend/resume at several
  brightness levels, battery use, ordinary game launch/exit, and both SD cards.
- Test Safe Resume in an isolated text session later; do not ship until safe.

**Never merge this integration candidate into the release branch on the
strength of unit tests alone.**
