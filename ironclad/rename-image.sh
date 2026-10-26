#!/usr/bin/env bash
[[ "$UNIT" == "353v" && "$CHIPSET" == "rk3566" ]] || { echo '[IRONCLAD] Wrong target' >&2; return 1; }
[[ -n "$DISK" && -f "$DISK" ]] || { echo '[IRONCLAD] Image missing' >&2; return 1; }
case "$DISK" in dArkOS_RG353v_*.img) ;; *) echo '[IRONCLAD] Unexpected image name' >&2; return 1 ;; esac
new=$(printf 'IRONCLAD_RG353V_%s_%s.img' "$DEBIAN_CODE_NAME" "$BUILD_DATE")
[[ ! -e "$new" ]] || { echo '[IRONCLAD] Refusing overwrite' >&2; return 1; }
mv -- "$DISK" "$new" || return 1
DISK="$new"
echo "[IRONCLAD] Image renamed to $DISK"
