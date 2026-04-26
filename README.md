# Fluent Emoji 3D — Webfont

A fork of [fluent-emoji-webfont](https://github.com/tetunori/fluent-emoji-webfont) that builds the [LobeHub Fluent Emoji 3D](https://github.com/lobehub/fluent-emoji-3d) asset pack as a real color webfont.

**[Live showcase →](https://ironexcavater.github.io/fluent-emoji-webfont/)**

## What this adds

The base fork serves the original Microsoft Fluent Emoji in 2D (SVG/CBDT/SBIX). This fork builds the LobeHub 3D renders — high-fidelity 3D emoji — as a sharded color TTF webfont with three browser color formats per shard:

| Format | Supported by |
|--------|-------------|
| `color-CBDT` | Chrome, Edge, Android |
| `color-sbix` | Safari, iOS |
| `color-SVG` | Firefox |

## Usage

The CSS and font filenames now include the quality profile, while the runtime `font-family` name stays:

```css
font-family: 'Fluent Emoji 3D', sans-serif;
```

Do not import multiple quality variants on the same page unless you intentionally want the last one loaded to win.

### Via CDN (GitHub Pages)

```css
@import url('https://ironexcavater.github.io/fluent-emoji-webfont/fonts/balanced/FluentEmoji3D-balanced-128px.css');

.emoji-text {
  font-family: 'Fluent Emoji 3D', sans-serif;
}
```

### Self-hosted

Copy the exported `fonts/` directory into your project:

```html
<link rel="stylesheet" href="/fonts/balanced/FluentEmoji3D-balanced-128px.css" />
```

```css
.emoji-text {
  font-family: 'Fluent Emoji 3D', sans-serif;
}
```

### Glyph list

A JS glyph manifest is included for building pickers or search UIs:

```html
<script src="/fonts/balanced/FluentEmoji3D-balanced-128px.glyphs.js"></script>
```

```js
// exposes window.FluentEmoji3DGlyphs
const glyphs = window.FluentEmoji3DGlyphs;
```

## Building

Requires: `node`, `python3`, `npm`

```shell
./build_lobehub_3d_font.sh
```

Downloads `@lobehub/fluent-emoji-3d` from npm, builds one quality variant, and writes it into `dist/` using quality-specific filenames such as:

```text
FluentEmoji3D-balanced-128px.css
FluentEmoji3D-balanced-128px.manifest.json
FluentEmoji3D-balanced-128px.glyphs.js
FluentEmoji3D-balanced-128px000-cbdt.ttf
```

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

### Build all qualities

```shell
./build_all_lobehub_3d_fonts.sh
```

This writes:

```text
dist/compact/
dist/balanced/
dist/detail/
dist/max/
```

### Preview locally

```shell
python3 -m http.server 4173
# open http://127.0.0.1:4173/
```

## Exporting a clean package

```shell
./export_lobehub_3d_font.sh dist/balanced/FluentEmoji3D-balanced-128px.manifest.json
```

Writes `export/<file-prefix>/` containing only the files needed to ship in another project:

```
fonts/FluentEmoji3D-balanced-128px.css
fonts/FluentEmoji3D-balanced-128px*.ttf
README.txt
```

### GitHub Pages

The Pages workflow builds and stages all four quality variants on push to `main`:

```text
fonts/compact/
fonts/balanced/
fonts/detail/
fonts/max/
```

For `detail` and `max`, the Chromium-facing `cbdt` shards are capped at `128px` because `nanoemoji` fails above that threshold in CBDT generation. The Safari `sbix` and Firefox `svg` shards keep the full `192px` and `256px` resolutions.

> [!IMPORTANT]
> Browser handling of color emoji fonts is still engine-dependent. Test on your target platforms — don't rely on the font file alone.

## Credits

- [fluent-emoji-webfont](https://github.com/tetunori/fluent-emoji-webfont) by Tetsunori Nakayama — base build toolchain. MIT License.
- [@lobehub/fluent-emoji-3d](https://github.com/lobehub/fluent-emoji-3d) by LobeHub — 3D emoji assets. MIT License.
- [fluentui-emoji](https://github.com/microsoft/fluentui-emoji) by Microsoft — original emoji art. MIT License.
