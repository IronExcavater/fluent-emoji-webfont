#!/bin/bash

set -e

OUT_DIR="${1:-export/LobeHubFluentEmoji3DFont}"

python3 export_lobehub_3d_font.py --out-dir "${OUT_DIR}"
