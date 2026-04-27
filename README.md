# Fluent Emoji 3D — Webfont

A fork of [fluent-emoji-webfont](https://github.com/tetunori/fluent-emoji-webfont) that builds the [LobeHub Fluent Emoji 3D](https://github.com/lobehub/fluent-emoji-3d) asset pack as a real color webfont.

**[Live showcase →](https://ironexcavater.github.io/fluent-emoji-webfont/)**

## What this adds

The base fork serves the original Microsoft Fluent Emoji in 2D (SVG/CBDT/SBIX). This fork builds the LobeHub 3D renders — high-fidelity 3D emoji — as a color TTF webfont with three browser color formats:

| Format | Supported by |
|--------|-------------|
| `color-CBDT` | Chrome, Edge, Android |
| `color-sbix` | Safari, iOS |
| `color-SVG` | Firefox |

It also keeps the official Microsoft styles buildable:

- `FluentEmojiColor`
- `FluentEmojiFlat`
- `FluentEmojiHighContrast`
- `FluentEmojiHighContrastInverted`

## Usage

The CSS and font filenames now include the quality profile, while the runtime `font-family` name stays:

```css
font-family: 'Fluent Emoji 3D', sans-serif;
```

Do not import multiple quality variants on the same page unless you intentionally want the last one loaded to win.

### Via CDN (GitHub Pages)

```css
@import url('https://ironexcavater.github.io/fluent-emoji-webfont/fonts/FluentEmoji3D-balanced-128px.css');

.emoji-text {
  font-family: 'Fluent Emoji 3D', sans-serif;
}
```

### Self-hosted

Copy the exported `fonts/` directory into your project:

```html
<link rel="stylesheet" href="/fonts/FluentEmoji3D-balanced-128px.css" />
```

```css
.emoji-text {
  font-family: 'Fluent Emoji 3D', sans-serif;
}
```

### Optional glyph metadata

A JS glyph manifest is included for pickers, search UIs, and metadata. It is not required to render the font in the default Unicode build:

```html
<script src="/fonts/FluentEmoji3D-balanced-128px.glyphs.js"></script>
```

```js
// exposes window.FluentEmoji3DGlyphs
const glyphs = window.FluentEmoji3DGlyphs;
```

In the default `unicode` build, `display === emoji`. The old PUA remap path is still available as an explicit compatibility mode.

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
FluentEmoji3D-balanced-128px-cbdt.ttf
```

By default the build is Unicode-first, exported as one font per color format, and does not require a mapper:

```shell
MAPPING_MODE=unicode ./build_lobehub_3d_font.sh
```

If you explicitly want the old private-use display glyph layer for app-level remapping:

```shell
MAPPING_MODE=pua ./build_lobehub_3d_font.sh
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

### Building a subset

You can build a much smaller Unicode-first font by passing an emoji list file:

```text
# one emoji or codepoint sequence per line
❤️
✅
2764 FE0F 200D 1F525
1F1FA 1F1F8
```

```shell
EMOJI_LIST_FILE=./my-emoji-subset.txt \
SUBSET_TAG=my-app \
QUALITY_PROFILE=balanced \
./build_lobehub_3d_font.sh
```

That produces filenames like:

```text
dist/FluentEmoji3D-my-app-balanced-128px.css
dist/FluentEmoji3D-my-app-balanced-128px-cbdt.ttf
dist/FluentEmoji3D-my-app-balanced-128px-sbix.ttf
dist/FluentEmoji3D-my-app-balanced-128px-svg.ttf
```

You can also inject individual emoji directly:

```shell
EMOJI=$'❤️\n✅\n❌' SUBSET_TAG=demo ./build_lobehub_3d_font.sh
```

### Extracting a subset from a repo

You can scan a codebase for supported emoji literals and write a subset list automatically:

```shell
./extract_emoji_subset.sh ./build/app-emoji-subset.txt /path/to/your/app
```

Then build from that extracted list:

```shell
EMOJI_LIST_FILE=./build/app-emoji-subset.txt \
SUBSET_TAG=app \
./build_lobehub_3d_font.sh
```

Important limitation: this only finds literal emoji already present in source/content files. If your app mostly receives emoji from users, databases, APIs, or CMS content, the subset must be curated explicitly instead of inferred from the repo.

### Build all qualities

```shell
./build_all_lobehub_3d_fonts.sh
```

This writes all generated files into `dist/`, with quality already encoded in each filename.

### Build the official Microsoft styles

These are vector styles, so there is no separate raster quality matrix like the 3D build.

```shell
./build_all_official_fonts.sh
```

This writes relative/self-hostable CSS plus `.woff2` shards into `dist/`.

### Preview locally

```shell
python3 -m http.server 4173
# open http://127.0.0.1:4173/
```

## Exporting a clean package

```shell
./export_lobehub_3d_font.sh dist/FluentEmoji3D-balanced-128px.manifest.json
```

Writes `export/<file-prefix>/` containing only the files needed to ship in another project:

```
fonts/FluentEmoji3D-balanced-128px.css
fonts/FluentEmoji3D-balanced-128px*.ttf
README.txt
```

To export every built 3D Unicode package:

```shell
./export_all_lobehub_3d_fonts.sh
```

### GitHub Pages

The Pages workflow builds and stages:

- all four 3D Unicode quality variants
- all official Microsoft vector styles

Everything is published under one flat `fonts/` directory.

For `detail` and `max`, the Chromium-facing `cbdt` shards are capped at `128px` because `nanoemoji` fails above that threshold in CBDT generation. The Safari `sbix` and Firefox `svg` shards keep the full `192px` and `256px` resolutions.

> [!IMPORTANT]
> Browser handling of color emoji fonts is still engine-dependent. Test on your target platforms — don't rely on the font file alone.

## Encoding modes

### `unicode` (default)

- raw emoji Unicode is the primary encoded path
- no app-side remapping is required
- exported as one unsharded font per color format, so raw Unicode sequences stay in a single `@font-face`
- `glyphs.js` is optional metadata only

### `pua`

- also emits private-use display glyphs in `U+E000..U+F8FF`
- useful when an app intentionally remaps emoji text to one-codepoint display glyphs
- preserves the older showcase/editor compatibility path

## Recommended drag-and-drop package

If you want the most predictable integration and you do not mind an official mapper, use the mapped package:

```shell
./build_dragdrop_package.sh
```

That builds and exports:

```text
export/FluentEmoji3D-mapped-balanced-128px/
  fonts/FluentEmoji3D-mapped-balanced-128px.css
  fonts/FluentEmoji3D-mapped-balanced-128px*.ttf
  fonts/FluentEmoji3D-mapped-balanced-128px.runtime.js
  fonts/FluentEmoji3D-mapped-balanced-128px.runtime.mjs
```

For plain browser usage, the runtime can load the sibling CSS for you:

```html
<script src="/fonts/FluentEmoji3D-mapped-balanced-128px.runtime.js"></script>
```

For display-only content:

```html
<div data-fluent-emoji>I ❤️ Fluent Emoji 3D</div>
<script>
  window.FluentEmoji3DMapper.install();
</script>
```

For app code:

```js
const mapped = window.FluentEmoji3DMapper.mapText("Order shipped 🚚");
const raw = window.FluentEmoji3DMapper.unmapText(mapped);
```

For module-based apps:

```js
import mapper from "/fonts/FluentEmoji3D-mapped-balanced-128px.runtime.mjs";

mapper.install();
```

This is the best path when you want the package itself to own the mapping logic instead of every consuming app implementing its own mapper.

## Credits

- [fluent-emoji-webfont](https://github.com/tetunori/fluent-emoji-webfont) by Tetsunori Nakayama — base build toolchain. MIT License.
- [@lobehub/fluent-emoji-3d](https://github.com/lobehub/fluent-emoji-3d) by LobeHub — 3D emoji assets. MIT License.
- [fluentui-emoji](https://github.com/microsoft/fluentui-emoji) by Microsoft — original emoji art. MIT License.
