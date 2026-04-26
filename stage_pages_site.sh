#!/bin/bash

set -euo pipefail

SITE_DIR="${1:-_site}"
DIST_ROOT="${DIST_ROOT:-dist}"
QUALITIES="${QUALITIES:-compact balanced detail max}"

rm -rf "${SITE_DIR}"
mkdir -p "${SITE_DIR}/fonts" "${SITE_DIR}/sample/list"

sed \
  -e 's|\./dist/|\./fonts/|g' \
  index.html > "${SITE_DIR}/index.html"

for quality in ${QUALITIES}; do
  mkdir -p "${SITE_DIR}/fonts/${quality}"
  cp "${DIST_ROOT}/${quality}/"* "${SITE_DIR}/fonts/${quality}/"
done

cp sample/list/favicon.ico "${SITE_DIR}/sample/list/"
