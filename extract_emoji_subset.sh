#!/bin/bash

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <out-file> <path> [path...]" >&2
  exit 1
fi

OUT_FILE="$1"
shift

SOURCE="${SOURCE:-@lobehub/fluent-emoji-3d}"
WORKDIR="build/lobehub-3d-font"
VENV_DIR="${WORKDIR}/venv"

mkdir -p "${WORKDIR}"

if [ ! -x "${VENV_DIR}/bin/python3" ] && [ ! -x "${VENV_DIR}/Scripts/python.exe" ]; then
  python3 -m venv --upgrade-deps "${VENV_DIR}"
fi

if [ -f "${VENV_DIR}/bin/activate" ]; then
  source "${VENV_DIR}/bin/activate"
else
  source "${VENV_DIR}/Scripts/activate"
fi

pip install nanoemoji pillow brotli > /dev/null

rm -rf "${WORKDIR}/package"

if [ -d "${SOURCE}" ]; then
  ASSETS_DIR="${SOURCE}"
elif [ -f "${SOURCE}" ]; then
  tar -xf "${SOURCE}" -C "${WORKDIR}"
  ASSETS_DIR="${WORKDIR}/package/assets"
else
  TARBALL_NAME=$(npm pack "${SOURCE}" --pack-destination "${WORKDIR}" --silent)
  tar -xf "${WORKDIR}/${TARBALL_NAME}" -C "${WORKDIR}"
  ASSETS_DIR="${WORKDIR}/package/assets"
fi

python3 extract_emoji_subset.py --assets-dir "${ASSETS_DIR}" --out-file "${OUT_FILE}" "$@"
