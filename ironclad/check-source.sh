#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for f in build_rg353v.sh ironclad/prepare-branding.sh ironclad/integrate-image.sh ironclad/rename-image.sh; do bash -n "$f"; done
python3 - <<'PY'
from pathlib import Path
s=Path('build_rg353v.sh').read_text()
for needle in ('ironclad/prepare-branding.sh','ironclad/integrate-image.sh','ironclad/rename-image.sh'):
 assert s.count(needle)==1, needle
assert s.index('ironclad/prepare-branding.sh') < s.index('source ./build_kernel-rk3566.sh')
assert s.index('ironclad/integrate-image.sh') > s.index('source ./finishing_touches-rk3566.sh')
assert s.index('ironclad/rename-image.sh') > s.index('source ./clean_mounts.sh')
print('IRONCLAD build hooks: PASS')
PY
