#!/usr/bin/env bash
# Offline staging test: exercise RG353V-only image hooks in a disposable tree.
set -euo pipefail
source_root="$(cd "$(dirname "$0")/../.." && pwd -P)"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT

mkdir -p "$work/bin" "$work/ironclad/stability" \
  "$work/Arkbuild/etc/systemd/system" \
  "$work/Arkbuild/usr/lib/systemd/system-sleep"
# GitHub Actions runners do not need privileged access for a fake image tree.
cat >"$work/bin/sudo" <<'EOF'
#!/usr/bin/env sh
exec "$@"
EOF
chmod +x "$work/bin/sudo"
export PATH="$work/bin:$PATH"

cp -- "$source_root/ironclad/integrate-image.sh" "$work/ironclad/"
cp -- "$source_root/ironclad/stability/report_es_exit.py" "$work/ironclad/stability/"
cp -- "$source_root/ironclad/stability/sleep_brightness.py" "$work/ironclad/stability/"
cp -- "$source_root/ironclad/stability/patch_sleep.py" "$work/ironclad/stability/"
cp -- "$source_root/ironclad/stability/View IRONCLAD Launcher Errors.sh" "$work/ironclad/stability/"
cp -- "$source_root/scripts/sleep.rk3566" "$work/Arkbuild/usr/lib/systemd/system-sleep/sleep"

(
  cd "$work"
  export UNIT="353v" CHIPSET="rk3566"
  # Explicitly source because production integration uses 'return 1'.
  source ./ironclad/integrate-image.sh
)

hook="$work/Arkbuild/usr/lib/systemd/system-sleep/sleep"
dropin="$work/Arkbuild/etc/systemd/system/emulationstation.service.d/40-ironclad.conf"
bash -n "$hook"
grep -Fq 'sleep_brightness.py pre' "$hook"
grep -Fq 'sleep_brightness.py post' "$hook"
! grep -Fq '/var/local/cur_bright.state' "$hook"
grep -Fq 'RestartSec=2s' "$dropin"
grep -Fq 'ExecStopPost=+' "$dropin"
test -f "$work/Arkbuild/usr/local/lib/ironclad/report_es_exit.py"
test -f "$work/Arkbuild/usr/local/lib/ironclad/sleep_brightness.py"
test -x "$work/Arkbuild/opt/system/Advanced/View IRONCLAD Launcher Errors.sh"
grep -Fq 'IRONCLAD_TARGET=RG353V' "$work/Arkbuild/etc/ironclad-release"

# Never install those RG353V patches into a different hardware target.
if (
  cd "$work"
  export UNIT="rgb30" CHIPSET="rk3566"
  source ./ironclad/integrate-image.sh
); then
  echo "ERROR: RG353V integration accepted a different device" >&2
  exit 1
fi

echo "IRONCLAD staging smoke checks: PASS"
