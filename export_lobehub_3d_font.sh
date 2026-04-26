#!/bin/bash

set -e

MANIFEST_PATH="${1:-}"
OUT_DIR="${2:-}"

if [ -n "${MANIFEST_PATH}" ] && [ -n "${OUT_DIR}" ]; then
  python3 export_lobehub_3d_font.py --manifest "${MANIFEST_PATH}" --out-dir "${OUT_DIR}"
elif [ -n "${MANIFEST_PATH}" ]; then
  python3 export_lobehub_3d_font.py --manifest "${MANIFEST_PATH}"
else
  python3 export_lobehub_3d_font.py
fi
