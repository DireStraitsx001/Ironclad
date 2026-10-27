#!/usr/bin/env bash
# RG353V-only development integration. This is not a validated release.
[[ "$UNIT" == "353v" && "$CHIPSET" == "rk3566" ]] || { echo '[IRONCLAD] Wrong target' >&2; return 1; }
[[ -d Arkbuild/etc/systemd/system ]] || { echo '[IRONCLAD] No staged rootfs' >&2; return 1; }

# Preserve stock Restart=on-failure. Diagnose failed unit exits as root,
# while keeping regular launcher execution under the ark user.
sudo install -d -m 0755 Arkbuild/etc/systemd/system/emulationstation.service.d || return 1
printf '[Service]\nRestartSec=2s\nExecStopPost=+/usr/bin/python3 /usr/local/lib/ironclad/report_es_exit.py\n' | sudo tee Arkbuild/etc/systemd/system/emulationstation.service.d/40-ironclad.conf >/dev/null || return 1
sudo chmod 0644 Arkbuild/etc/systemd/system/emulationstation.service.d/40-ironclad.conf || return 1
sudo install -d -m 0755 Arkbuild/usr/local/lib/ironclad Arkbuild/var/lib/ironclad Arkbuild/opt/system/Advanced || return 1
sudo install -m 0644 ironclad/stability/report_es_exit.py Arkbuild/usr/local/lib/ironclad/report_es_exit.py || return 1
sudo install -m 0755 'ironclad/stability/View IRONCLAD Launcher Errors.sh' 'Arkbuild/opt/system/Advanced/View IRONCLAD Launcher Errors.sh' || return 1

# Brightness-only sleep/wake fix. Patch the staged RG353V script, not
# the shared upstream RK3566 source, to keep other devices unaffected.
[[ -f Arkbuild/usr/lib/systemd/system-sleep/sleep ]] || { echo '[IRONCLAD] Missing staged sleep hook' >&2; return 1; }
sudo install -m 0644 ironclad/stability/sleep_brightness.py Arkbuild/usr/local/lib/ironclad/sleep_brightness.py || return 1
sudo python3 ironclad/stability/patch_sleep.py Arkbuild/usr/lib/systemd/system-sleep/sleep || return 1
sudo bash -n Arkbuild/usr/lib/systemd/system-sleep/sleep || return 1
sudo chmod 0755 Arkbuild/usr/lib/systemd/system-sleep/sleep || return 1

# Source-only preview of Safe Resume / Switchboard: DO NOT install
# unverified launcher into the firmware or change TF2.
sudo install -d -m 0755 Arkbuild/etc || return 1
printf 'IRONCLAD_VERSION=1.0-integration-preview\nIRONCLAD_TARGET=RG353V\nIRONCLAD_BASE=dArkOS\n' | sudo tee Arkbuild/etc/ironclad-release >/dev/null || return 1
echo '[IRONCLAD] RG353V launcher diagnostics and brightness guard staged.'
echo '[IRONCLAD] Resume and GameSwitcher remain uninstalled development previews.'
