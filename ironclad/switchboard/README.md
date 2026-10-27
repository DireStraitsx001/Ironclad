# IRONCLAD Safe Resume Preflight — development preview

A conservative, optional companion to Switchboard. This does **not** launch,
resume, pause, kill, or automatically save any game. It only reports RetroArch
history entries on a distinctly mounted TF2 (/roms2), and identifies whether
a conventional single save-state candidate can be found.

It requires a regular TF2 ROM, an existing core matching recorded core_path,
an explicit TF2 savestate_directory in RetroArch configuration, and exactly
one plausible bounded save-state file. A reviewable result does not establish
core-version compatibility or guarantee successful restoration.

Most stock dArkOS installations may report blocked because save-state
directories are not explicitly configured on TF2. This is intentional.

Commands, from your source tree on a test machine:
  python3 ironclad/switchboard/resume_preflight.py
  python3 ironclad/switchboard/resume_preflight.py --json

Optional experimental snapshot: --snapshot N, followed by typing SNAPSHOT.
This copies a state to a private separate file on TF1; it does not restore it,
and never changes the TF2 original. The feature is not hardware-tested.
Snapshots consume TF1 space. No automatic emulator launches or writes to TF2.

This branch is NOT installed in the firmware image. Validate with disposable
cards before future integration.

Run unit tests:
  python3 -m unittest discover -v -s ironclad/switchboard -p 'test_*.py'
