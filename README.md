# LobeHub Fluent Emoji 3D — Webfont

A fork of [fluent-emoji-webfont](https://github.com/tetunori/fluent-emoji-webfont) that adds a real color webfont built from the [LobeHub Fluent Emoji 3D](https://github.com/lobehub/fluent-emoji-3d) asset pack — 3D-rendered emoji usable anywhere via `font-family`.

**[Live showcase →](https://ironexcavater.github.io/fluent-emoji-webfont/)**

## What this adds

The base fork serves the original Microsoft Fluent Emoji in 2D (SVG/CBDT/SBIX). This fork builds the LobeHub 3D renders — high-fidelity 3D emoji — as a sharded color TTF webfont with three browser color formats per shard:

| Format | Supported by |
|--------|-------------|
| `color-CBDT` | Chrome, Edge, Android |
| `color-sbix` | Safari, iOS |
| `color-SVG` | Firefox |

## Usage

### Via CDN (GitHub Pages)

```css
@import url('https://ironexcavater.github.io/fluent-emoji-webfont/fonts/LobeHubFluentEmoji3DFont.css');

.emoji-text {
  font-family: 'LobeHub Fluent Emoji 3D Font', sans-serif;
}
```

### Self-hosted

Copy the exported `fonts/` directory into your project:

```html
<link rel="stylesheet" href="/fonts/LobeHubFluentEmoji3DFont.css" />
```

```css
.emoji-text {
  font-family: 'LobeHub Fluent Emoji 3D Font', sans-serif;
}
```

### Glyph list

A JS glyph manifest is included for building pickers or search UIs:

```html
<script src="/fonts/LobeHubFluentEmoji3DFont.glyphs.js"></script>
```

```js
// exposes window.LobeHubFluentEmoji3DFontGlyphs
const glyphs = window.LobeHubFluentEmoji3DFontGlyphs;
```

## Building

Requires: `node`, `python3`, `npm`

```shell
./build_lobehub_3d_font.sh
```

Downloads `@lobehub/fluent-emoji-3d` from npm, builds the full sharded font into `dist/`, and writes the showcase `index.html`.

### Quality profiles

| Profile | Render size | Flag |
|---------|------------|------|
| `compact` | 96 px | `QUALITY_PROFILE=compact` |
| `balanced` | 128 px *(default)* | |
| `detail` | 192 px | `QUALITY_PROFILE=detail` |
| `max` | 256 px | `QUALITY_PROFILE=max` |

```shell
QUALITY_PROFILE=detail ./build_lobehub_3d_font.sh
# or override size directly:
MAX_DIMENSION=160 ./build_lobehub_3d_font.sh
```

### Preview locally

```shell
python3 -m http.server 4173
# open http://127.0.0.1:4173/
```

## Exporting a clean package

```shell
./export_lobehub_3d_font.sh
```

Writes `export/LobeHubFluentEmoji3DFont/` containing only the files needed to ship in another project:

```
fonts/LobeHubFluentEmoji3DFont.css
fonts/LobeHubFluentEmoji3DFont*.ttf
README.txt
```

> [!IMPORTANT]
> Browser handling of color emoji fonts is still engine-dependent. Test on your target platforms — don't rely on the font file alone.

## Credits

- [fluent-emoji-webfont](https://github.com/tetunori/fluent-emoji-webfont) by Tetsunori Nakayama — base build toolchain. MIT License.
- [@lobehub/fluent-emoji-3d](https://github.com/lobehub/fluent-emoji-3d) by LobeHub — 3D emoji assets. MIT License.
- [fluentui-emoji](https://github.com/microsoft/fluentui-emoji) by Microsoft — original emoji art. MIT License.
