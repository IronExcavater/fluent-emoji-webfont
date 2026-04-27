#!/bin/bash

set -euo pipefail

DIST_DIR="${DIST_DIR:-dist}"

shopt -s nullglob
manifests=("${DIST_DIR}"/FluentEmoji3D-*.manifest.json)

if [ "${#manifests[@]}" -eq 0 ]; then
  echo "No FluentEmoji3D manifests found in ${DIST_DIR}" >&2
  exit 1
fi

for manifest in "${manifests[@]}"; do
  echo "==> Exporting ${manifest}"
  ./export_lobehub_3d_font.sh "${manifest}"
done
