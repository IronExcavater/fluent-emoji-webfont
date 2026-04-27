# Emoji Font Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove dead build scripts, consolidate the pipeline to unicode-primary + PUA-secondary at balanced quality, and fix iotbay to load the font from GitHub Pages CDN.

**Architecture:** `build_all_lobehub_3d_fonts.sh` drives two sequential builds (unicode + PUA) at balanced quality by default, packing the npm source once. `build_lobehub_3d_font.sh` auto-derives the file prefix from `MAPPING_MODE`. iotbay imports the unicode CSS directly from the GitHub Pages CDN — no local copies, no JS required.

**Tech Stack:** bash, Python 3.12, nanoemoji, GitHub Actions, Vite/React (iotbay)

---

## File Map

| File | Action |
|---|---|
| `build_ttf.sh` | Delete |
| `build_ttf01.sh` | Delete |
| `build_ttf02.sh` | Delete |
| `build_dragdrop_package.sh` | Delete |
| `build_woff2.sh` | Delete |
| `build_all_official_fonts.sh` | Delete |
| `makelist.py` | Delete |
| `prepare.py` | Delete |
| `build_lobehub_3d_font.sh` | Modify — auto-derive `FILE_PREFIX_BASE` from `MAPPING_MODE` |
| `build_all_lobehub_3d_fonts.sh` | Rewrite — add `MODES`, change `QUALITIES` default, pack npm once |
| `.github/workflows/deploy-pages.yml` | Modify — remove official fonts build step |
| `iotbay/web/src/app/styles/base.css` | Modify — change `@import` to GitHub Pages CDN URL |

---

## Task 1: Delete dead scripts and commit staged dist cleanup

**Files:**
- Delete: `build_ttf.sh`, `build_ttf01.sh`, `build_ttf02.sh`, `build_dragdrop_package.sh`, `build_woff2.sh`, `build_all_official_fonts.sh`, `makelist.py`, `prepare.py`

- [ ] **Step 1: Delete the dead scripts**

```bash
cd /Users/niclas/WebstormProjects/fluent-emoji-webfont
rm build_ttf.sh build_ttf01.sh build_ttf02.sh
rm build_dragdrop_package.sh
rm build_woff2.sh build_all_official_fonts.sh
rm makelist.py prepare.py
```

- [ ] **Step 2: Verify only intended files are gone**

```bash
git status --short
```

Expected: the 8 deleted scripts appear as `D` entries, plus the already-staged `dist/FluentEmojiColor*` deletions. No unintended deletions.

- [ ] **Step 3: Stage and commit everything**

```bash
git add build_ttf.sh build_ttf01.sh build_ttf02.sh \
        build_dragdrop_package.sh \
        build_woff2.sh build_all_official_fonts.sh \
        makelist.py prepare.py
git commit -m "chore: remove dead build scripts and old dist artifacts"
```

---

## Task 2: Update build_lobehub_3d_font.sh — auto-derive file prefix

**Files:**
- Modify: `build_lobehub_3d_font.sh`

- [ ] **Step 1: Replace the FILE_PREFIX_BASE default with auto-derivation**

Find this block near the top of `build_lobehub_3d_font.sh`:
```bash
MAPPING_MODE="${MAPPING_MODE:-unicode}"
EMOJI_LIST_FILE="${EMOJI_LIST_FILE:-}"
EMOJI="${EMOJI:-}"
SUBSET_TAG="${SUBSET_TAG:-}"
FILE_PREFIX_BASE="${FILE_PREFIX_BASE:-FluentEmoji3D}"
```

Replace with:
```bash
MAPPING_MODE="${MAPPING_MODE:-unicode}"
EMOJI_LIST_FILE="${EMOJI_LIST_FILE:-}"
EMOJI="${EMOJI:-}"
SUBSET_TAG="${SUBSET_TAG:-}"

if [ -z "${FILE_PREFIX_BASE:-}" ]; then
  if [ "${MAPPING_MODE}" = "pua" ]; then
    FILE_PREFIX_BASE="FluentEmoji3D-pua"
  else
    FILE_PREFIX_BASE="FluentEmoji3D"
  fi
fi
```

- [ ] **Step 2: Verify the logic produces correct prefixes**

```bash
FILE_PREFIX_BASE="" MAPPING_MODE=unicode bash -c '
  MAPPING_MODE="${MAPPING_MODE:-unicode}"
  if [ -z "${FILE_PREFIX_BASE:-}" ]; then
    if [ "${MAPPING_MODE}" = "pua" ]; then
      FILE_PREFIX_BASE="FluentEmoji3D-pua"
    else
      FILE_PREFIX_BASE="FluentEmoji3D"
    fi
  fi
  echo "unicode prefix: ${FILE_PREFIX_BASE}"
'

FILE_PREFIX_BASE="" MAPPING_MODE=pua bash -c '
  MAPPING_MODE="${MAPPING_MODE:-unicode}"
  if [ -z "${FILE_PREFIX_BASE:-}" ]; then
    if [ "${MAPPING_MODE}" = "pua" ]; then
      FILE_PREFIX_BASE="FluentEmoji3D-pua"
    else
      FILE_PREFIX_BASE="FluentEmoji3D"
    fi
  fi
  echo "pua prefix: ${FILE_PREFIX_BASE}"
'
```

Expected output:
```
unicode prefix: FluentEmoji3D
pua prefix: FluentEmoji3D-pua
```

- [ ] **Step 3: Verify an explicit FILE_PREFIX_BASE override is still honoured**

```bash
FILE_PREFIX_BASE="MyCustomFont" MAPPING_MODE=pua bash -c '
  MAPPING_MODE="${MAPPING_MODE:-unicode}"
  if [ -z "${FILE_PREFIX_BASE:-}" ]; then
    if [ "${MAPPING_MODE}" = "pua" ]; then
      FILE_PREFIX_BASE="FluentEmoji3D-pua"
    else
      FILE_PREFIX_BASE="FluentEmoji3D"
    fi
  fi
  echo "override prefix: ${FILE_PREFIX_BASE}"
'
```

Expected:
```
override prefix: MyCustomFont
```

- [ ] **Step 4: Commit**

```bash
git add build_lobehub_3d_font.sh
git commit -m "feat: auto-derive file prefix base from mapping mode"
```

---

## Task 3: Rewrite build_all_lobehub_3d_fonts.sh

**Files:**
- Modify: `build_all_lobehub_3d_fonts.sh`

- [ ] **Step 1: Replace the entire file with the new version**

```bash
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
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x build_all_lobehub_3d_fonts.sh
```

- [ ] **Step 3: Verify the script is syntactically valid**

```bash
bash -n build_all_lobehub_3d_fonts.sh && echo "syntax OK"
```

Expected:
```
syntax OK
```

- [ ] **Step 4: Verify defaults print correctly in dry-run**

```bash
bash -c '
  SOURCE="@lobehub/fluent-emoji-3d"
  MODES="${MODES:-unicode pua}"
  QUALITIES="${QUALITIES:-balanced}"
  for mode in ${MODES}; do
    for quality in ${QUALITIES}; do
      echo "would build: mode=${mode} quality=${quality}"
    done
  done
'
```

Expected:
```
would build: mode=unicode quality=balanced
would build: mode=pua quality=balanced
```

- [ ] **Step 5: Commit**

```bash
git add build_all_lobehub_3d_fonts.sh
git commit -m "feat: build both unicode and PUA at balanced quality by default"
```

---

## Task 4: Update CI workflow

**Files:**
- Modify: `.github/workflows/deploy-pages.yml`

- [ ] **Step 1: Remove the official fonts build step**

Find the build step in `.github/workflows/deploy-pages.yml`:
```yaml
      - name: Build all quality variants
        run: |
          chmod +x ./build_lobehub_3d_font.sh ./build_all_lobehub_3d_fonts.sh ./build_all_official_fonts.sh ./stage_pages_site.sh
          ./build_all_lobehub_3d_fonts.sh
          ./build_all_official_fonts.sh
```

Replace with:
```yaml
      - name: Build fonts
        run: |
          chmod +x ./build_lobehub_3d_font.sh ./build_all_lobehub_3d_fonts.sh ./stage_pages_site.sh
          ./build_all_lobehub_3d_fonts.sh
```

- [ ] **Step 2: Verify the YAML is valid**

```bash
python3 -c "import sys, yaml; yaml.safe_load(open('.github/workflows/deploy-pages.yml'))" 2>/dev/null \
  && echo "YAML valid" \
  || python3 -c "
import sys
try:
    import yaml
    yaml.safe_load(open('.github/workflows/deploy-pages.yml'))
    print('YAML valid')
except ImportError:
    print('PyYAML not installed, checking with python json fallback')
    import json
    print('cannot validate without PyYAML')
except Exception as e:
    print(f'YAML error: {e}')
    sys.exit(1)
"
```

Expected: `YAML valid` (or the PyYAML fallback message if not installed — that is fine, the workflow will be validated by GitHub on push).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy-pages.yml
git commit -m "ci: remove official fonts build step, keep only 3D font pipeline"
```

---

## Task 5: Fix iotbay font import

**Files:**
- Modify: `iotbay/web/src/app/styles/base.css`

- [ ] **Step 1: Change the @import to the GitHub Pages CDN URL**

In `/Users/niclas/WebstormProjects/iotbay/web/src/app/styles/base.css`, line 1:

```css
/* remove */
@import url('/fonts/FluentEmoji3D-balanced-128px.css');

/* replace with */
@import url('https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-balanced-128px.css');
```

Leave everything else in the file unchanged. `--font-family: 'Inter Variable', 'Fluent Emoji 3D', sans-serif` stays as-is.

- [ ] **Step 2: Verify the change is correct**

```bash
head -3 /Users/niclas/WebstormProjects/iotbay/web/src/app/styles/base.css
```

Expected:
```css
@import url('https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-balanced-128px.css');
@import 'tailwindcss';
```

- [ ] **Step 3: Commit in the iotbay repo**

```bash
cd /Users/niclas/WebstormProjects/iotbay
git add web/src/app/styles/base.css
git commit -m "fix: load Fluent Emoji 3D from GitHub Pages CDN instead of missing local path"
```

---

## Task 6: Full build verification

Run the complete local build to confirm both variants are produced correctly. Requires the npm package and Python env to be set up (the build script handles the venv automatically).

- [ ] **Step 1: Run the build**

```bash
cd /Users/niclas/WebstormProjects/fluent-emoji-webfont
./build_all_lobehub_3d_fonts.sh
```

Expected: both unicode and PUA balanced builds complete without errors. Approximate output:
```
==> Building unicode balanced
Built shard 000: 1427 targets -> FluentEmoji3D-balanced-128px-cbdt.ttf, ...
==> Building pua balanced
Built shard 000: 128 targets -> FluentEmoji3D-pua-balanced-128px000-cbdt.ttf, ...
Built shard 001: 128 targets -> FluentEmoji3D-pua-balanced-128px001-cbdt.ttf, ...
...
```

- [ ] **Step 2: Confirm output file names**

```bash
ls dist/ | grep "FluentEmoji3D" | head -20
```

Expected to include:
```
FluentEmoji3D-balanced-128px.css
FluentEmoji3D-balanced-128px-cbdt.ttf
FluentEmoji3D-balanced-128px-sbix.ttf
FluentEmoji3D-balanced-128px-svg.ttf
FluentEmoji3D-pua-balanced-128px.css
FluentEmoji3D-pua-balanced-128px.runtime.js
FluentEmoji3D-pua-balanced-128px.runtime.mjs
FluentEmoji3D-pua-balanced-128px000-cbdt.ttf
```

- [ ] **Step 3: Confirm unicode CSS has no unicode-range (single @font-face)**

```bash
grep -c "unicode-range" dist/FluentEmoji3D-balanced-128px.css
```

Expected: `0`

- [ ] **Step 4: Confirm PUA CSS has unicode-range on every block**

```bash
grep -c "unicode-range" dist/FluentEmoji3D-pua-balanced-128px.css
```

Expected: a number equal to the shard count (typically 10–12).

- [ ] **Step 5: Confirm PUA unicode-ranges are PUA codepoints only (E000–F8FF)**

```bash
grep "unicode-range" dist/FluentEmoji3D-pua-balanced-128px.css | head -3
```

Expected: all values are in the `U+E` range, e.g. `unicode-range: U+E000, U+E001, ...`

- [ ] **Step 6: Stage the pages site and check it contains both variants**

```bash
./stage_pages_site.sh _site
ls _site/fonts/ | grep "FluentEmoji3D" | wc -l
```

Expected: a count covering both unicode (4 files: css + 3 ttf) and PUA (~37 files: css + shards + runtime). Total should be 40+.

---

## Task 7: Push fluent-emoji-webfont to trigger Pages deployment

- [ ] **Step 1: Push all commits to main**

```bash
cd /Users/niclas/WebstormProjects/fluent-emoji-webfont
git push origin main
```

- [ ] **Step 2: Wait for GitHub Actions to complete**

Open `https://github.com/IronExcavater/fluent-emoji-webfont/actions` and wait for the `Deploy to GitHub Pages` workflow to show a green checkmark. This typically takes 5–15 minutes (nanoemoji builds both variants).

- [ ] **Step 3: Confirm CDN URL resolves**

```bash
curl -sI "https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-balanced-128px.css" \
  | grep "HTTP/"
```

Expected: `HTTP/2 200`

---

## Task 8: Verify iotbay renders emoji (requires Task 7 to be complete)

- [ ] **Step 1: Start iotbay dev server**

```bash
cd /Users/niclas/WebstormProjects/iotbay/web
npm run dev
```

- [ ] **Step 2: Open browser and check emoji rendering**

Open `http://localhost:5173` in Chrome or Safari. Find a UI element that displays an emoji (product name, category, any text). The emoji should render as a Fluent 3D color glyph, not as a system emoji and not blank.

Note: requires internet access during development (browser fetches font from GitHub Pages CDN). The GitHub Pages site must have been deployed at least once for the CDN URL to resolve. If the CDN is not yet live, the font will silently fall back to system emoji — not blank, just the OS default appearance.

- [ ] **Step 3: Confirm font is loading via DevTools**

Open DevTools → Network tab → filter by "Font". Reload the page. Confirm requests to `ironexcavater.github.io/.../FluentEmoji3D-balanced-128px.css` return 200.
