#!/bin/bash

set -e

SOURCE="${1:-@lobehub/fluent-emoji-3d}"
WORKDIR="build/lobehub-3d-font"
VENV_DIR="${WORKDIR}/venv"
GROUP_SIZE="${GROUP_SIZE:-}"
QUALITY_PROFILE="${QUALITY_PROFILE:-balanced}"
MAX_DIMENSION="${MAX_DIMENSION:-}"
DIST_DIR="${DIST_DIR:-dist}"
COLOR_FORMATS="${COLOR_FORMATS:-cbdt,sbix,svg}"
USE_PNGQUANT="${USE_PNGQUANT:-0}"
USE_ZOPFLIPNG="${USE_ZOPFLIPNG:-0}"
FAMILY_NAME="${FAMILY_NAME:-Fluent Emoji 3D}"
FILE_PREFIX="${FILE_PREFIX:-}"
MAPPING_MODE="${MAPPING_MODE:-unicode}"

if [ -z "${FILE_PREFIX_BASE:-}" ]; then
  if [ "${MAPPING_MODE}" = "pua" ]; then
    FILE_PREFIX_BASE="FluentEmoji3D-pua"
  else
    FILE_PREFIX_BASE="FluentEmoji3D"
  fi
fi
EMOJI_LIST_FILE="${EMOJI_LIST_FILE:-}"
EMOJI="${EMOJI:-}"
SUBSET_TAG="${SUBSET_TAG:-}"

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
  VERSION="local"
elif [ -f "${SOURCE}" ]; then
  tar -xf "${SOURCE}" -C "${WORKDIR}"
  ASSETS_DIR="${WORKDIR}/package/assets"
  VERSION=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("build/lobehub-3d-font/package/package.json").read_text())["version"])
PY
)
else
  TARBALL_NAME=$(npm pack "${SOURCE}" --pack-destination "${WORKDIR}" --silent)
  tar -xf "${WORKDIR}/${TARBALL_NAME}" -C "${WORKDIR}"
  ASSETS_DIR="${WORKDIR}/package/assets"
  VERSION=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("build/lobehub-3d-font/package/package.json").read_text())["version"])
PY
)
fi

BUILD_ARGS=(
  --assets-dir "${ASSETS_DIR}"
  --dist-dir "${DIST_DIR}"
  --work-dir "${WORKDIR}"
  --family-name "${FAMILY_NAME}"
  --file-prefix-base "${FILE_PREFIX_BASE}"
  --quality-profile "${QUALITY_PROFILE}"
  --mapping-mode "${MAPPING_MODE}"
  --color-formats "${COLOR_FORMATS}"
  --version "${VERSION}"
)

if [ -n "${GROUP_SIZE}" ]; then
  BUILD_ARGS+=(--group-size "${GROUP_SIZE}")
fi

if [ -n "${EMOJI_LIST_FILE}" ]; then
  BUILD_ARGS+=(--emoji-list-file "${EMOJI_LIST_FILE}")
fi

if [ -n "${EMOJI}" ]; then
  while IFS= read -r raw_emoji; do
    if [ -n "${raw_emoji}" ]; then
      BUILD_ARGS+=(--emoji "${raw_emoji}")
    fi
  done < <(printf '%s\n' "${EMOJI}")
fi

if [ -n "${SUBSET_TAG}" ]; then
  BUILD_ARGS+=(--subset-tag "${SUBSET_TAG}")
fi

if [ -n "${FILE_PREFIX}" ]; then
  BUILD_ARGS+=(--file-prefix "${FILE_PREFIX}")
fi

if [ -n "${MAX_DIMENSION}" ]; then
  BUILD_ARGS+=(--max-dimension "${MAX_DIMENSION}")
fi

if [ "${USE_PNGQUANT}" = "1" ]; then
  BUILD_ARGS+=(--use-pngquant)
else
  BUILD_ARGS+=(--no-use-pngquant)
fi

if [ "${USE_ZOPFLIPNG}" = "1" ]; then
  BUILD_ARGS+=(--use-zopflipng)
else
  BUILD_ARGS+=(--no-use-zopflipng)
fi

python3 build_lobehub_3d_font.py "${BUILD_ARGS[@]}"
