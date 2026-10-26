# IRONCLAD — RG353V source fork

Unofficial fork of Christian Haitian's [dArkOS](https://github.com/christianhaitian/dArkOS). Preserve upstream project history, copyright notices, and licenses.

**Status: development source preview, NOT completed or tested firmware.** This branch adds actual RG353V-only build hooks for release identity, restart backoff, optional boot artwork, and output naming. It does NOT yet include all the launcher/sleep/Time Machine/GameSense changes developed in the downloadable source kit.

TF1 = OS, TF2 = ROMs/saves/tools/backups. Build hooks never change TF2.

Source lint: `bash ironclad/check-source.sh`

Build environment: native Ubuntu 24.04+ (not WSL), substantial free disk and network access. Use `make rg353v` once dependencies and branding are supplied. A full build has not been run here.

**Do not flash your current working TF1**. Test an eventual image on a separate card only.

Next milestones: import tested launcher and power fixes, commit steel-crest artwork, integrate TF2 tools, compile a real image, run RG353V hardware acceptance tests.
