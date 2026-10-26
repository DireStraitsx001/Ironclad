# IRONCLAD Switchboard (experimental preview)

The [OnionOS GameSwitcher](https://github.com/OnionUI/Onion/tree/main/src/gameSwitcher) inspired this interaction. Onion's Miyoo-specific SDL and launcher code cannot simply run on RG353V. This is independently written code: no Onion assets or code copied. Onion upstream is GPLv3; future direct reuse must honor its terms.

Current preview reads RetroArch history and displays recent *TF2-only* ROMs. It detects possible state filenames but does not assume compatibility or launch an emulator. It is not Onion's live GameSwitcher, not an auto-save-on-exit system, and not currently automatically installed. No background services. No save/ROM writes.

Roadmap: trace dArkOS per-emulator launch wrappers; implement opt-in per-core save confirmations and quick-resume; verify on a disposable TF1 card before enabling any automatic session changes.

Standalone tests: `python3 ironclad/switchboard/test_switchboard.py`.
