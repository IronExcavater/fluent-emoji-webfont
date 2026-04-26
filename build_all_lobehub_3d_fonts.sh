#!/bin/bash

set -euo pipefail

SOURCE="${1:-@lobehub/fluent-emoji-3d}"
WORKDIR="build/lobehub-3d-font"
QUALITIES="${QUALITIES:-compact balanced detail max}"
COLOR_FORMATS="${COLOR_FORMATS:-cbdt,sbix,svg}"
GROUP_SIZE="${GROUP_SIZE:-128}"
USE_PNGQUANT="${USE_PNGQUANT:-0}"
USE_ZOPFLIPNG="${USE_ZOPFLIPNG:-0}"
FAMILY_NAME="${FAMILY_NAME:-Fluent Emoji 3D}"
FILE_PREFIX_BASE="${FILE_PREFIX_BASE:-FluentEmoji3D}"
DIST_ROOT="${DIST_ROOT:-dist}"

mkdir -p "${WORKDIR}" "${DIST_ROOT}"

if [ -d "${SOURCE}" ] || [ -f "${SOURCE}" ]; then
  PACKED_SOURCE="${SOURCE}"
else
  TARBALL_NAME=$(npm pack "${SOURCE}" --pack-destination "${WORKDIR}" --silent)
  PACKED_SOURCE="${WORKDIR}/${TARBALL_NAME}"
fi

for quality in ${QUALITIES}; do
  quality_group_size="${GROUP_SIZE}"
  case "${quality}" in
    detail)
      quality_group_size="${GROUP_SIZE_DETAIL:-96}"
      ;;
    max)
      quality_group_size="${GROUP_SIZE_MAX:-64}"
      ;;
  esac
  echo "==> Building ${quality}"
  DIST_DIR="${DIST_ROOT}/${quality}" \
  QUALITY_PROFILE="${quality}" \
  COLOR_FORMATS="${COLOR_FORMATS}" \
  GROUP_SIZE="${quality_group_size}" \
  USE_PNGQUANT="${USE_PNGQUANT}" \
  USE_ZOPFLIPNG="${USE_ZOPFLIPNG}" \
  FAMILY_NAME="${FAMILY_NAME}" \
  FILE_PREFIX_BASE="${FILE_PREFIX_BASE}" \
  ./build_lobehub_3d_font.sh "${PACKED_SOURCE}"
done
