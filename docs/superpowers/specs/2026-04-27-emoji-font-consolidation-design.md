# Fluent Emoji Webfont Consolidation Design

Date: 2026-04-27

## Goal

Consolidate the fluent-emoji-webfont build pipeline into a clean, reliable system:
- Unicode/GSUB as primary font (pure CSS, no JS required)
- PUA + mapper as secondary (opt-in, guaranteed rendering for controlled DOM)
- GitHub Pages CDN as the distribution mechanism
- Dead code removed, scripts halved
- iotbay consuming the unicode font from CDN (fixes blank emoji)

## Architecture

```
@lobehub/fluent-emoji-3d (npm, packed once per CI run)
              │
    ┌─────────┴──────────┐
    ▼                    ▼
 GSUB/unicode          PUA
 group-size=0        group-size=128
 1 TTF per format    ~11 shards + runtime.js/mjs
    │                    │
    └────────┬───────────┘
             ▼
          dist/
    FluentEmoji3D-balanced-128px.*          ← unicode primary
    FluentEmoji3D-pua-balanced-128px.*      ← PUA secondary
             │
        stage_pages_site.sh
             │
          _site/fonts/  ──→  GitHub Pages CDN
             │
    ┌────────┴────────────────────────┐
    ▼                                 ▼
iotbay (CSS @import from CDN)     other consumers
zero JS, font-family fallback     can load runtime.mjs for PUA
```

## Why Unicode Primary, PUA Secondary

Unicode/GSUB is the industry standard for font-based emoji (JoyPixels, etc.). A single
font file per color format with GSUB ligature tables handles all multi-codepoint sequences
(ZWJ, skin tones, FE0F) without sharding. Works as a plain CSS font-family fallback.
Well-supported in Chrome 93+, Safari 15.4+, Firefox 96+.

PUA is available as opt-in: each emoji sequence maps to one BMP private-use codepoint,
shards cover disjoint PUA ranges (no overlap, no browser ambiguity), the mapper runtime
rewrites display text. Useful for React apps that want guaranteed rendering regardless of
browser GSUB behaviour.

The root cause of blank emoji in iotbay was a 404: fonts were not served from
`web/public/fonts/` during development. The unicode font was structurally correct.

## Script Consolidation

### Delete (8 files)

| File | Reason |
|---|---|
| `build_ttf.sh` | Pre-nanoemoji pipeline, superseded |
| `build_ttf01.sh` | Pre-nanoemoji pipeline, superseded |
| `build_ttf02.sh` | Pre-nanoemoji pipeline, superseded |
| `build_dragdrop_package.sh` | PUA wrapper, superseded by MAPPING_MODE=pua flag |
| `build_woff2.sh` | Official bitmap fonts dropped |
| `build_all_official_fonts.sh` | Official bitmap fonts dropped |
| `makelist.py` | Old one-off tooling |
| `prepare.py` | Old one-off tooling |

### Keep and Update

| File | Change |
|---|---|
| `build_lobehub_3d_font.py` | No changes — core engine is correct |
| `build_lobehub_3d_font.sh` | Auto-set FILE_PREFIX_BASE from MAPPING_MODE |
| `build_all_lobehub_3d_fonts.sh` | Add MODES var; default to both unicode+pua at balanced quality |
| `export_lobehub_3d_font.py` | No changes |
| `export_lobehub_3d_font.sh` | No changes |
| `export_all_lobehub_3d_fonts.sh` | No changes |
| `stage_pages_site.sh` | No changes (already globs FluentEmoji3D-*) |
| `extract_emoji_subset.py` | No changes |
| `extract_emoji_subset.sh` | No changes |

## Build Pipeline Changes

### build_lobehub_3d_font.sh

Add auto FILE_PREFIX_BASE derivation before the BUILD_ARGS block:

```bash
if [ -z "${FILE_PREFIX_BASE}" ]; then
  if [ "${MAPPING_MODE}" = "pua" ]; then
    FILE_PREFIX_BASE="FluentEmoji3D-pua"
  else
    FILE_PREFIX_BASE="FluentEmoji3D"
  fi
fi
```

Remove the hardcoded `FILE_PREFIX_BASE="FluentEmoji3D"` default.

### build_all_lobehub_3d_fonts.sh

Add `MODES` variable, default to `"unicode pua"`.
Change `QUALITIES` default to `"balanced"` (was `"compact balanced detail max"`).
Pack npm tarball once, pass to all builds:

```bash
MODES="${MODES:-unicode pua}"
QUALITIES="${QUALITIES:-balanced}"

# pack once
TARBALL_NAME=$(npm pack "${SOURCE}" --pack-destination "${WORKDIR}" --silent)
PACKED_SOURCE="${WORKDIR}/${TARBALL_NAME}"

for mode in ${MODES}; do
  for quality in ${QUALITIES}; do
    MAPPING_MODE="${mode}" QUALITY_PROFILE="${quality}" \
      ./build_lobehub_3d_font.sh "${PACKED_SOURCE}"
  done
done
```

Local full build: `QUALITIES="compact balanced detail max" ./build_all_lobehub_3d_fonts.sh`
CI release: `./build_all_lobehub_3d_fonts.sh` (defaults: both modes, balanced only)

## CI Workflow Changes (deploy-pages.yml)

- Remove `build_all_official_fonts.sh` step
- Remove `build_all_lobehub_3d_fonts.sh` reference to official fonts build
- Keep Node.js 22 setup (needed for npm pack)
- Keep Python 3.12 setup

Simplified build step:
```yaml
- name: Build fonts
  run: |
    chmod +x ./build_all_lobehub_3d_fonts.sh ./build_lobehub_3d_font.sh ./stage_pages_site.sh
    ./build_all_lobehub_3d_fonts.sh

- name: Stage site
  run: ./stage_pages_site.sh _site
```

## dist/ Output After CI Build

```
FluentEmoji3D-balanced-128px.css           unicode, single @font-face block
FluentEmoji3D-balanced-128px-cbdt.ttf
FluentEmoji3D-balanced-128px-sbix.ttf
FluentEmoji3D-balanced-128px-svg.ttf
FluentEmoji3D-balanced-128px.manifest.json
FluentEmoji3D-balanced-128px.glyphs.js

FluentEmoji3D-pua-balanced-128px.css       PUA, ~11 sharded @font-face blocks
FluentEmoji3D-pua-balanced-128px000-cbdt.ttf
... (~33 shard TTFs total)
FluentEmoji3D-pua-balanced-128px.runtime.js
FluentEmoji3D-pua-balanced-128px.runtime.mjs
FluentEmoji3D-pua-balanced-128px.manifest.json
FluentEmoji3D-pua-balanced-128px.glyphs.js
```

## GitHub Pages

`stage_pages_site.sh` already globs all `FluentEmoji3D-*` from dist/ into `_site/fonts/`.
No changes required. Both variants land there automatically.

CDN URLs:
- `https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-balanced-128px.css`
- `https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-pua-balanced-128px.css`
- `https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-pua-balanced-128px.runtime.mjs`

## iotbay Integration

### web/src/app/styles/base.css

Change the @import to point to GitHub Pages CDN:

```css
/* remove */
@import url('/fonts/FluentEmoji3D-balanced-128px.css');

/* add */
@import url('https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-balanced-128px.css');
```

Keep `--font-family: 'Inter Variable', 'Fluent Emoji 3D', sans-serif` unchanged.
The unicode font's @font-face declaration (from the CDN CSS) makes the family name available;
the browser resolves emoji sequences via GSUB ligatures and renders color glyphs.

### web/dist/fonts/ — remove from version control

This directory contains manually copied font files that conflict with the CDN approach.
Remove from git, add `web/dist/` to `.gitignore` if not already present.

### PUA opt-in (future, no changes now)

Any component can dynamically load the PUA mapper:

```typescript
import(/* @vite-ignore */ 'https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-pua-balanced-128px.runtime.mjs')
  .then(m => m.default.install({ selector: '[data-fluent-emoji]' }));
```

## Success Criteria

- `./build_all_lobehub_3d_fonts.sh` produces both unicode and PUA balanced builds in dist/
- CI deploys both to GitHub Pages without errors
- Fetching the CDN CSS URL returns a valid @font-face block
- iotbay dev server shows color Fluent Emoji 3D in the browser (not blank, not system emoji)
- 8 dead scripts removed from the repo
- export/ packages generated cleanly for both variants
