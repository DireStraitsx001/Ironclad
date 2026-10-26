#!/usr/bin/env bash
[[ "$UNIT" == "353v" && "$CHIPSET" == "rk3566" ]] || { echo '[IRONCLAD] Wrong target' >&2; return 1; }
[[ -d Arkbuild/etc/systemd/system ]] || { echo '[IRONCLAD] No staged rootfs' >&2; return 1; }
sudo install -d -m 0755 Arkbuild/etc/systemd/system/emulationstation.service.d || return 1
printf '[Service]\nRestartSec=2s\n' | sudo tee Arkbuild/etc/systemd/system/emulationstation.service.d/40-ironclad.conf >/dev/null || return 1
sudo chmod 0644 Arkbuild/etc/systemd/system/emulationstation.service.d/40-ironclad.conf || return 1
sudo install -d -m 0755 Arkbuild/etc || return 1
printf 'IRONCLAD_VERSION=1.0-source-preview\nIRONCLAD_TARGET=RG353V\nIRONCLAD_BASE=dArkOS\n' | sudo tee Arkbuild/etc/ironclad-release >/dev/null || return 1
echo '[IRONCLAD] Source-preview identity and restart backoff installed.'
