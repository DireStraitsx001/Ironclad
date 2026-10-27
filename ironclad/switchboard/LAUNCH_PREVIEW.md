# IRONCLAD opt-in launch / Safe Resume experiment

This branch introduces an isolated **command-line** RetroArch launcher.
It is NOT a functional integrated GameSwitcher or a released feature.
Do not install on a working TF1 card. The first hardware trial should use a
disposable TF1/TF2 setup with nonessential games and saves.

## How it works

- Reads RetroArch recent history on a separately mounted TF2.
- Only accepts a listed, present libretro core and an existing ROM on TF2.
- `--launch N` starts a selected ROM without loading a state.
- `--resume N` requires a single preflight-approved unnumbered `.state` file;
  it makes a verified isolated copy on TF1 and starts RetroArch pointing at
  that copy. **The player still has to select Quick Menu -> Load State**.
  Nothing is automatically resumed.
- Requires interactive terminal confirmation by typing LAUNCH or RESUME.
- Refuses to run while EmulationStation or RetroArch is active. The preview
  should be run through a separate text session, NOT over the running frontend.
- Creates a private TF1 session for state and SRAM files. It does not sync
  these back to TF2. This intentionally means in-game saves from preview
  sessions are *not* transferred automatically.
- The RetroArch core and its normal configuration can still have side
  effects and cannot be proven harmless without device-specific testing.

## Limitations

This preview does not manage frontend transitions, force closure of an emulator,
or recover from failed game startups. It cannot guarantee binary compatibility
of historical save states. It does not preserve a running game session.
A state named `*.state.auto` or numbered state is not supported for this
initial launch path. Game-specific system save paths and emulator core
overrides need hardware verification. No auto save/load/exit behavior is added.

The CLI currently uses the stock RetroArch command conventions
(`--config`, `--appendconfig`, `-L`, `--save`, `--savestate`).
Actual flag compatibility must be verified against the binaries built for
RG353V before the launcher is enabled.

## Planned device verification

1. Boot test firmware from a **spare TF1**; use only disposable ROM/save data.
2. Confirm no active EmulationStation/RetroArch is running before preview.
3. Verify `--launch N` works with a known RetroArch core and normal exit.
4. Verify `--resume N` copies a single compatible test state, then choose
   RetroArch Quick Menu -> Load State manually.
5. Confirm the original TF2 ROM/state and user data remain unchanged.
6. Confirm failed/missing cores, ambiguous states, symlinks, and full TF1
   storage refuse to launch.
7. Measure exit behavior, resource cleanup and storage consumption.

Local tests:
`python3 -m unittest discover -v -s ironclad/switchboard -p 'test_*.py'`

No branch merge or integration into `ironclad/1.0` should occur until
device testing is satisfactory.
