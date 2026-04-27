#!/bin/bash

set -euo pipefail

SITE_DIR="${1:-_site}"
DIST_ROOT="${DIST_ROOT:-dist}"

rm -rf "${SITE_DIR}"
mkdir -p "${SITE_DIR}/fonts" "${SITE_DIR}/sample/list"

sed \
  -e 's|\./dist/|\./fonts/|g' \
  index.html > "${SITE_DIR}/index.html"

find "${DIST_ROOT}" -maxdepth 1 -type f \( -name 'FluentEmoji3D-*' -o -name 'FluentEmoji*.css' -o -name 'FluentEmoji*.ttf' -o -name 'FluentEmoji*.woff2' \) -exec cp {} "${SITE_DIR}/fonts/" \;

cp sample/list/favicon.ico "${SITE_DIR}/sample/list/"
