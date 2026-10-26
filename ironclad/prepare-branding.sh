#!/usr/bin/env bash
[[ "$UNIT" == "353v" && "$CHIPSET" == "rk3566" ]] || { echo '[IRONCLAD] Wrong target' >&2; return 1; }
a=ironclad/branding/IRONCLAD-kernel-224.png
b=ironclad/branding/IRONCLAD-RG353V-loading.jpg
if [[ -f "$a" && -f "$b" ]]; then
  # RG353V artwork may be a symlink to RG353M. Do not edit shared target.
  rm -f logos/unrotated/dArkos353v.png launchimages/loading.jpg.353v || return 1
  install -m 0644 "$a" logos/unrotated/dArkos353v.png || return 1
  install -m 0644 "$b" launchimages/loading.jpg.353v || return 1
  echo '[IRONCLAD] RG353V-only artwork staged.'
else
  echo '[IRONCLAD] Artwork not yet in GitHub: keeping upstream visuals.'
fi
