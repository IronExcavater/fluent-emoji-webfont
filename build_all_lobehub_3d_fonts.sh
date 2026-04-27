#!/bin/bash

set -euo pipefail

SOURCE="${1:-@lobehub/fluent-emoji-3d}"
WORKDIR="build/lobehub-3d-font"
MODES="${MODES:-unicode pua}"
QUALITIES="${QUALITIES:-balanced}"
COLOR_FORMATS="${COLOR_FORMATS:-cbdt,sbix,svg}"
GROUP_SIZE="${GROUP_SIZE:-}"
USE_PNGQUANT="${USE_PNGQUANT:-0}"
USE_ZOPFLIPNG="${USE_ZOPFLIPNG:-0}"
FAMILY_NAME="${FAMILY_NAME:-Fluent Emoji 3D}"
DIST_ROOT="${DIST_ROOT:-dist}"
EMOJI_LIST_FILE="${EMOJI_LIST_FILE:-}"
EMOJI="${EMOJI:-}"
SUBSET_TAG="${SUBSET_TAG:-}"

mkdir -p "${WORKDIR}" "${DIST_ROOT}"

if [ -d "${SOURCE}" ] || [ -f "${SOURCE}" ]; then
  PACKED_SOURCE="${SOURCE}"
else
  TARBALL_NAME=$(npm pack "${SOURCE}" --pack-destination "${WORKDIR}" --silent)
  PACKED_SOURCE="${WORKDIR}/${TARBALL_NAME}"
fi

for mode in ${MODES}; do
  for quality in ${QUALITIES}; do
    quality_group_size="${GROUP_SIZE}"
    if [ -z "${quality_group_size}" ] && [ "${mode}" = "pua" ]; then
      quality_group_size="128"
      case "${quality}" in
        detail) quality_group_size="${GROUP_SIZE_DETAIL:-96}" ;;
        max)    quality_group_size="${GROUP_SIZE_MAX:-64}"    ;;
      esac
    fi
    echo "==> Building ${mode} ${quality}"
    DIST_DIR="${DIST_ROOT}" \
    QUALITY_PROFILE="${quality}" \
    COLOR_FORMATS="${COLOR_FORMATS}" \
    GROUP_SIZE="${quality_group_size}" \
    USE_PNGQUANT="${USE_PNGQUANT}" \
    USE_ZOPFLIPNG="${USE_ZOPFLIPNG}" \
    FAMILY_NAME="${FAMILY_NAME}" \
    MAPPING_MODE="${mode}" \
    EMOJI_LIST_FILE="${EMOJI_LIST_FILE}" \
    EMOJI="${EMOJI}" \
    SUBSET_TAG="${SUBSET_TAG}" \
    ./build_lobehub_3d_font.sh "${PACKED_SOURCE}"
  done
done
