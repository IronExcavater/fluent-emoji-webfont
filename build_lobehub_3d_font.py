from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import textwrap
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image


@dataclass(frozen=True)
class ColorFormatSpec:
    key: str
    nanoemoji_format: str
    suffix: str
    tech: str


COLOR_FORMAT_SPECS = {
    "cbdt": ColorFormatSpec("cbdt", "cbdt", "cbdt", "color-CBDT"),
    "sbix": ColorFormatSpec("sbix", "sbix", "sbix", "color-sbix"),
    "svg": ColorFormatSpec("svg", "untouchedsvg", "svg", "color-SVG"),
}
DEFAULT_COLOR_FORMATS = ("cbdt", "sbix", "svg")
CBDT_MAX_BITMAP_RESOLUTION = 128
QUALITY_PROFILES = {
    "compact": 96,
    "balanced": 128,
    "detail": 192,
    "max": 256,
}
MAPPING_MODES = ("unicode", "pua")
DISPLAY_PUA_START = 0xE000
DISPLAY_PUA_END = 0xF8FF

EMOJI_COMPONENTS = {
    0x200D: "zwj",
    0xFE0F: "emoji presentation",
}
SKIN_TONES = {
    0x1F3FB: "light skin tone",
    0x1F3FC: "medium-light skin tone",
    0x1F3FD: "medium skin tone",
    0x1F3FE: "medium-dark skin tone",
    0x1F3FF: "dark skin tone",
}


def parse_codepoint_sequence(stem: str) -> tuple[int, ...]:
    return tuple(int(part, 16) for part in re.split(r"[-_]", stem))


def default_file_prefix(base_name: str, quality_profile: str, max_dimension: int) -> str:
    return f"{base_name}-{quality_profile}-{max_dimension}px"


def emoji_from_sequence(sequence: tuple[int, ...]) -> str:
    return "".join(chr(codepoint) for codepoint in sequence)


def svg_name_for_sequence(sequence: tuple[int, ...]) -> str:
    head, *tail = sequence
    suffix = "_".join(f"{codepoint:x}" for codepoint in tail)
    if suffix:
        return f"emoji_u{head:x}_{suffix}.svg"
    return f"emoji_u{head:x}.svg"


def load_assets(assets_dir: Path) -> dict[tuple[int, ...], Path]:
    sequence_to_asset: dict[tuple[int, ...], Path] = {}
    duplicates = 0
    for webp_path in sorted(assets_dir.glob("*.webp")):
        sequence = parse_codepoint_sequence(webp_path.stem)
        if sequence in sequence_to_asset:
            duplicates += 1
            continue
        sequence_to_asset[sequence] = webp_path
    if not sequence_to_asset:
        raise SystemExit(f"No .webp assets found in {assets_dir}")
    if duplicates:
        print(f"Skipped {duplicates} duplicate sequence assets")
    return sequence_to_asset


def parse_subset_line(raw_line: str) -> tuple[int, ...] | None:
    line = raw_line.split("#", 1)[0].strip()
    if not line:
        return None
    if re.fullmatch(r"[0-9A-Fa-f][0-9A-Fa-f _-]*", line):
        return tuple(int(part, 16) for part in re.split(r"[ _-]+", line) if part)
    return tuple(ord(character) for character in line)


def load_subset_sequences(
    emoji_list_files: tuple[Path, ...],
    raw_emojis: tuple[str, ...],
) -> list[tuple[int, ...]]:
    sequences: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()

    for emoji in raw_emojis:
        sequence = tuple(ord(character) for character in emoji)
        if sequence and sequence not in seen:
            seen.add(sequence)
            sequences.append(sequence)

    for emoji_list_file in emoji_list_files:
        for raw_line in emoji_list_file.read_text(encoding="utf-8").splitlines():
            sequence = parse_subset_line(raw_line)
            if sequence is None or sequence in seen:
                continue
            seen.add(sequence)
            sequences.append(sequence)

    return sequences


def filter_assets(
    sequence_to_asset: dict[tuple[int, ...], Path],
    subset_sequences: list[tuple[int, ...]],
) -> dict[tuple[int, ...], Path]:
    if not subset_sequences:
        return sequence_to_asset

    missing = [sequence for sequence in subset_sequences if sequence not in sequence_to_asset]
    if missing:
        rendered = ", ".join(emoji_from_sequence(sequence) for sequence in missing[:10])
        if len(missing) > 10:
            rendered += ", ..."
        raise SystemExit(f"Subset contains emojis not present in assets: {rendered}")

    return {sequence: sequence_to_asset[sequence] for sequence in subset_sequences}


def clear_existing_outputs(dist_dir: Path, file_prefix: str) -> None:
    for pattern in (f"{file_prefix}*.ttf", f"{file_prefix}*.woff2"):
        for path in dist_dir.glob(pattern):
            path.unlink()
    for suffix in (".css", ".manifest.json", ".glyphs.js", ".runtime.js", ".runtime.mjs"):
        target = dist_dir / f"{file_prefix}{suffix}"
        if target.exists():
            target.unlink()


def create_staging_dir(work_dir: Path, file_prefix: str) -> Path:
    staging_dir = work_dir / f"{file_prefix}.staging.{uuid4().hex}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    return staging_dir


def publish_outputs(staging_dir: Path, dist_dir: Path, file_prefix: str) -> None:
    clear_existing_outputs(dist_dir, file_prefix)
    for path in sorted(staging_dir.iterdir()):
        shutil.move(str(path), dist_dir / path.name)
    shutil.rmtree(staging_dir, ignore_errors=True)


def chunked(values: list[tuple[int, ...]], size: int) -> list[list[tuple[int, ...]]]:
    if size <= 0 or size >= len(values):
        return [values]
    return [values[index : index + size] for index in range(0, len(values), size)]


def unicode_range_for_sequences(
    sequences: list[tuple[int, ...]],
    display_codepoints: dict[tuple[int, ...], int] | None = None,
    include_sequence_codepoints: bool = True,
) -> str:
    codepoints: set[int] = set()
    if include_sequence_codepoints:
        codepoints.update(codepoint for sequence in sequences for codepoint in sequence)
    if display_codepoints:
        codepoints.update(
            display_codepoints[sequence]
            for sequence in sequences
            if sequence in display_codepoints
        )
    ordered_codepoints = sorted(codepoints)
    return ", ".join(f"U+{codepoint:X}" for codepoint in ordered_codepoints)


def parse_csv_arg(raw_value: str, valid_values: set[str], label: str) -> tuple[str, ...]:
    values = tuple(part.strip().lower() for part in raw_value.split(",") if part.strip())
    invalid = sorted(set(values) - valid_values)
    if invalid:
        raise SystemExit(f"Unsupported {label}: {', '.join(invalid)}")
    if not values:
        raise SystemExit(f"At least one {label} is required")
    return values


def default_group_size(mapping_mode: str) -> int:
    return 0 if mapping_mode == "unicode" else 128


def default_subset_tag(emoji_list_files: tuple[Path, ...], raw_emojis: tuple[str, ...]) -> str | None:
    if len(emoji_list_files) == 1 and not raw_emojis:
        return emoji_list_files[0].stem
    if emoji_list_files or raw_emojis:
        return "subset"
    return None


def slugify_subset_tag(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise SystemExit("Subset tag must contain at least one letter or digit")
    return slug


def load_png_bytes(webp_path: Path, max_dimension: int) -> bytes:
    with Image.open(webp_path) as image:
        image = image.convert("RGBA")
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        png_bytes = BytesIO()
        image.save(png_bytes, format="PNG", optimize=True, compress_level=9)
        return png_bytes.getvalue()


def write_wrapped_svg(svg_path: Path, encoded_png: str, max_dimension: int) -> None:
    svg_path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{max_dimension}" height="{max_dimension}" '
            f'viewBox="0 0 {max_dimension} {max_dimension}">\n'
            f'  <image href="data:image/png;base64,{encoded_png}" '
            f'x="0" y="0" width="{max_dimension}" height="{max_dimension}"/>\n'
            "</svg>\n"
        ),
        encoding="utf-8",
    )


def strip_fe0f(sequence: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(cp for cp in sequence if cp != 0xFE0F)


def write_wrapped_svgs(
    group_dir: Path,
    group: list[tuple[int, ...]],
    sequence_to_asset: dict[tuple[int, ...], Path],
    max_dimension: int,
    display_codepoints: dict[tuple[int, ...], int] | None = None,
) -> list[Path]:
    svg_dir = group_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)
    svg_paths: list[Path] = []
    written_svg_names: set[str] = set()

    for sequence in group:
        png_bytes = load_png_bytes(sequence_to_asset[sequence], max_dimension)
        encoded_png = base64.b64encode(png_bytes).decode("ascii")
        sequence_svg_path = (svg_dir / svg_name_for_sequence(sequence)).resolve()
        write_wrapped_svg(sequence_svg_path, encoded_png, max_dimension)
        svg_paths.append(sequence_svg_path)
        written_svg_names.add(sequence_svg_path.name)

        # Browsers (HarfBuzz/Chrome) strip FE0F before GSUB lookup, so also emit
        # a FE0F-free variant so those sequences still resolve to the color glyph.
        stripped = strip_fe0f(sequence)
        if stripped != sequence and stripped:
            stripped_name = svg_name_for_sequence(stripped)
            if stripped_name not in written_svg_names:
                stripped_svg_path = (svg_dir / stripped_name).resolve()
                write_wrapped_svg(stripped_svg_path, encoded_png, max_dimension)
                svg_paths.append(stripped_svg_path)
                written_svg_names.add(stripped_name)

        display_codepoint = None if display_codepoints is None else display_codepoints.get(sequence)
        if display_codepoint is not None:
            display_svg_path = (svg_dir / svg_name_for_sequence((display_codepoint,))).resolve()
            write_wrapped_svg(display_svg_path, encoded_png, max_dimension)
            svg_paths.append(display_svg_path)
    return svg_paths


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build_group_fonts(
    group: list[tuple[int, ...]],
    group_index: int,
    total_groups: int,
    sequence_to_asset: dict[tuple[int, ...], Path],
    display_codepoints: dict[tuple[int, ...], int] | None,
    work_dir: Path,
    dist_dir: Path,
    family_name: str,
    file_prefix: str,
    max_dimension: int,
    color_formats: tuple[str, ...],
    use_pngquant: bool,
    use_zopflipng: bool,
) -> list[dict[str, str]]:
    group_dir = work_dir / f"group-{group_index:03d}"
    if group_dir.exists():
        shutil.rmtree(group_dir)
    group_dir.mkdir(parents=True, exist_ok=True)

    svg_paths = write_wrapped_svgs(group_dir, group, sequence_to_asset, max_dimension, display_codepoints)
    shard_stem = file_prefix if total_groups == 1 else f"{file_prefix}{group_index:03d}"

    artifacts: list[dict[str, str]] = []
    for color_format in color_formats:
        spec = COLOR_FORMAT_SPECS[color_format]
        build_cache_dir = group_dir / "build"
        if build_cache_dir.exists():
            shutil.rmtree(build_cache_dir)

        output_name = f"{shard_stem}-{spec.suffix}.ttf"
        command = [
            "nanoemoji",
            "--family",
            family_name,
            "--output_file",
            output_name,
            "--color_format",
            spec.nanoemoji_format,
        ]
        if color_format in {"cbdt", "sbix"}:
            bitmap_resolution = (
                min(max_dimension, CBDT_MAX_BITMAP_RESOLUTION)
                if color_format == "cbdt"
                else max_dimension
            )
            command.append("--use_pngquant" if use_pngquant else "--nouse_pngquant")
            command.append("--use_zopflipng" if use_zopflipng else "--nouse_zopflipng")
            command.extend(["--bitmap_resolution", str(bitmap_resolution)])
        command.extend(str(path) for path in svg_paths)
        run_command(command, cwd=group_dir)

        built_font = group_dir / "build" / output_name
        if not built_font.exists():
            raise SystemExit(f"nanoemoji did not produce {built_font}")
        shutil.move(str(built_font), dist_dir / output_name)
        artifacts.append(
            {
                "fileName": output_name,
                "fileFormat": "ttf",
                "cssFormat": "truetype",
                "colorFormat": spec.key,
                "tech": spec.tech,
                "bitmapResolution": (
                    min(max_dimension, CBDT_MAX_BITMAP_RESOLUTION)
                    if color_format == "cbdt"
                    else max_dimension
                ),
            }
        )

    return artifacts


def load_official_metadata(assets_root: Path) -> dict[tuple[int, ...], dict[str, object]]:
    metadata_by_sequence: dict[tuple[int, ...], dict[str, object]] = {}
    if not assets_root.exists():
        return metadata_by_sequence

    for metadata_path in assets_root.rglob("metadata.json"):
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        unicode_value = data.get("unicode")
        if not unicode_value:
            continue
        try:
            sequence = tuple(int(part, 16) for part in str(unicode_value).split())
        except ValueError:
            continue
        metadata_by_sequence[sequence] = {
            "name": data.get("tts") or data.get("cldr") or metadata_path.parent.name,
            "group": data.get("group") or "",
            "keywords": data.get("keywords") or [],
        }
    return metadata_by_sequence


def fallback_name(sequence: tuple[int, ...]) -> str:
    if len(sequence) == 2 and all(0x1F1E6 <= codepoint <= 0x1F1FF for codepoint in sequence):
        letters = "".join(chr(ord("A") + codepoint - 0x1F1E6) for codepoint in sequence)
        return f"flag: {letters}"
    if sequence[-1] == 0x20E3 and sequence:
        keycap_base = emoji_from_sequence(tuple(codepoint for codepoint in sequence if codepoint not in {0xFE0F, 0x20E3}))
        return f"keycap: {keycap_base}"

    parts: list[str] = []
    has_zwj = 0x200D in sequence
    for codepoint in sequence:
        if codepoint in EMOJI_COMPONENTS:
            continue
        if codepoint in SKIN_TONES:
            parts.append(SKIN_TONES[codepoint])
            continue
        if has_zwj and codepoint == 0x2640:
            parts.append("woman")
            continue
        if has_zwj and codepoint == 0x2642:
            parts.append("man")
            continue
        name = unicodedata.name(chr(codepoint), f"U+{codepoint:X}").lower()
        if name.startswith("regional indicator symbol letter "):
            name = name.removeprefix("regional indicator symbol letter ").upper()
        parts.append(name)
    return " ".join(parts) if parts else "emoji"


def fallback_group(sequence: tuple[int, ...]) -> str:
    if len(sequence) == 2 and all(0x1F1E6 <= codepoint <= 0x1F1FF for codepoint in sequence):
        return "Flags"
    if sequence[-1] == 0x20E3:
        return "Symbols"
    return "Uncategorized"


def metadata_for_sequence(
    sequence: tuple[int, ...],
    official_metadata: dict[tuple[int, ...], dict[str, object]],
) -> dict[str, object]:
    metadata = official_metadata.get(sequence)
    if metadata:
        return metadata
    return {
        "name": fallback_name(sequence),
        "group": fallback_group(sequence),
        "keywords": [],
    }


def display_codepoints_for_sequences(
    ordered_sequences: list[tuple[int, ...]],
) -> dict[tuple[int, ...], int]:
    available = DISPLAY_PUA_END - DISPLAY_PUA_START + 1
    if len(ordered_sequences) > available:
        raise SystemExit(
            f"Too many emojis ({len(ordered_sequences)}) for BMP private-use display mapping ({available})"
        )
    return {
        sequence: DISPLAY_PUA_START + index
        for index, sequence in enumerate(ordered_sequences)
    }


def write_glyphs_js(
    dist_dir: Path,
    file_prefix: str,
    ordered_sequences: list[tuple[int, ...]],
    official_metadata: dict[tuple[int, ...], dict[str, object]],
    display_codepoints: dict[tuple[int, ...], int] | None,
) -> Path:
    glyphs_path = dist_dir / f"{file_prefix}.glyphs.js"
    glyphs = []
    for sequence in ordered_sequences:
        metadata = metadata_for_sequence(sequence, official_metadata)
        display_codepoint = None if display_codepoints is None else display_codepoints.get(sequence)
        glyphs.append(
            {
                "emoji": emoji_from_sequence(sequence),
                "display": chr(display_codepoint) if display_codepoint is not None else emoji_from_sequence(sequence),
                "displayCodepoint": f"{display_codepoint:04X}" if display_codepoint is not None else None,
                "name": metadata["name"],
                "group": metadata["group"],
                "keywords": metadata["keywords"],
                "codepoints": " ".join(f"{codepoint:04X}" for codepoint in sequence),
            }
        )
    glyphs_path.write_text(
        (
            "(function (global) {\n"
            "  const glyphs = "
            + json.dumps(glyphs, ensure_ascii=False, separators=(",", ":"))
            + ";\n"
            "  global.FluentEmoji3DGlyphs = glyphs;\n"
            "  global.LobeHubFluentEmoji3DFontGlyphs = glyphs;\n"
            "})(typeof window !== 'undefined' ? window : globalThis);\n"
        ),
        encoding="utf-8",
    )
    return glyphs_path


def mapper_runtime_source(
    family_name: str,
    file_prefix: str,
    entries: list[dict[str, str]],
    module: bool,
) -> str:
    family_name_json = json.dumps(family_name, ensure_ascii=False)
    file_prefix_json = json.dumps(file_prefix, ensure_ascii=False)
    font_family_css_json = json.dumps(f"'{family_name}', sans-serif", ensure_ascii=False)
    css_file_json = json.dumps(f"{file_prefix}.css", ensure_ascii=False)
    entries_json = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))

    shared_body = textwrap.dedent(
        f"""\
        const familyName = {family_name_json};
        const filePrefix = {file_prefix_json};
        const fontFamilyCss = {font_family_css_json};
        const entries = {entries_json};
        const rawToDisplay = new Map(entries.map((entry) => [entry.emoji, entry.display]));
        const displayToRaw = new Map(entries.map((entry) => [entry.display, entry.emoji]));
        const sortedEntries = entries
          .slice()
          .sort((left, right) => right.emoji.length - left.emoji.length || left.emoji.localeCompare(right.emoji));
        const defaultSelector = '[data-fluent-emoji]';
        const styleElementId = `fluent-emoji-3d-style-${{filePrefix}}`;

        function escapeRegExp(value) {{
          return value.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
        }}

        const rawPattern = sortedEntries.length
          ? new RegExp(sortedEntries.map((entry) => escapeRegExp(entry.emoji)).join('|'), 'gu')
          : null;

        function mapText(value) {{
          const text = value == null ? '' : String(value);
          if (!rawPattern) {{
            return text;
          }}
          return text.replace(rawPattern, (match) => rawToDisplay.get(match) || match);
        }}

        function unmapText(value) {{
          const text = value == null ? '' : String(value);
          return Array.from(text, (character) => displayToRaw.get(character) || character).join('');
        }}

        function resolveDocument(root) {{
          if (typeof document === 'undefined') {{
            return null;
          }}
          if (!root) {{
            return document;
          }}
          if (root.nodeType === 9) {{
            return root;
          }}
          return root.ownerDocument || document;
        }}

        function matchesSelector(node, selector) {{
          return typeof Element !== 'undefined' && node instanceof Element && node.matches(selector);
        }}

        function closestMappedElement(node, selector) {{
          if (typeof Element === 'undefined') {{
            return null;
          }}
          const element = node instanceof Element ? node : node && node.parentElement;
          return element && element.closest ? element.closest(selector) : null;
        }}

        function ensureStylesheet(options) {{
          const root = options && options.root ? options.root : null;
          const doc = resolveDocument(root);
          if (!doc) {{
            return null;
          }}
          const href = options && options.href ? options.href : defaultCssHref;
          if (!href) {{
            return null;
          }}
          const absoluteHref = new URL(href, doc.baseURI).href;
          const existing = Array.from(doc.querySelectorAll('link[rel="stylesheet"]')).find((link) => link.href === absoluteHref);
          if (existing) {{
            return existing;
          }}
          const link = doc.createElement('link');
          link.rel = 'stylesheet';
          link.href = absoluteHref;
          link.setAttribute('data-fluent-emoji-file-prefix', filePrefix);
          (doc.head || doc.documentElement).appendChild(link);
          return link;
        }}

        function ensureSelectorStyle(options) {{
          const selector = options && options.selector ? options.selector : defaultSelector;
          const root = options && options.root ? options.root : null;
          const doc = resolveDocument(root);
          if (!doc) {{
            return null;
          }}
          const css = `${{selector}} {{ font-family: ${{fontFamilyCss}} !important; }}`;
          let style = doc.getElementById(styleElementId);
          if (style) {{
            if (style.textContent !== css) {{
              style.textContent = css;
            }}
            return style;
          }}
          style = doc.createElement('style');
          style.id = styleElementId;
          style.textContent = css;
          (doc.head || doc.documentElement).appendChild(style);
          return style;
        }}

        function mapElementText(element, rawText) {{
          const raw = rawText == null ? unmapText(element.textContent ?? '') : String(rawText);
          element.setAttribute('data-fluent-emoji-raw', raw);
          element.textContent = mapText(raw);
          return raw;
        }}

        function unmapElementText(element) {{
          const raw = unmapText(element.textContent ?? '');
          element.removeAttribute('data-fluent-emoji-raw');
          element.textContent = raw;
          return raw;
        }}

        function mapElements(root, options) {{
          const resolvedRoot = root || (typeof document !== 'undefined' ? document : null);
          if (!resolvedRoot) {{
            return;
          }}
          const selector = options && options.selector ? options.selector : defaultSelector;
          if (matchesSelector(resolvedRoot, selector)) {{
            mapElementText(resolvedRoot);
          }}
          if (resolvedRoot.querySelectorAll) {{
            resolvedRoot.querySelectorAll(selector).forEach((element) => mapElementText(element));
          }}
        }}

        function observe(root, options) {{
          const resolvedRoot = root || (typeof document !== 'undefined' ? (document.body || document.documentElement) : null);
          if (!resolvedRoot || typeof MutationObserver === 'undefined') {{
            return null;
          }}
          const selector = options && options.selector ? options.selector : defaultSelector;
          mapElements(resolvedRoot, {{ selector }});
          const observer = new MutationObserver((records) => {{
            for (const record of records) {{
              if (record.type === 'characterData') {{
                const mapped = closestMappedElement(record.target, selector);
                if (mapped) {{
                  mapElementText(mapped);
                }}
                continue;
              }}
              for (const node of record.addedNodes) {{
                const mapped = closestMappedElement(node, selector);
                if (mapped) {{
                  mapElementText(mapped);
                }}
                if (node && node.querySelectorAll) {{
                  mapElements(node, {{ selector }});
                }}
              }}
            }}
          }});
          observer.observe(resolvedRoot, {{ childList: true, subtree: true, characterData: true }});
          return observer;
        }}

        function install(options) {{
          const resolvedOptions = options || {{}};
          const root = resolvedOptions.root || (typeof document !== 'undefined' ? document : null);
          ensureStylesheet({{ root, href: resolvedOptions.href }});
          ensureSelectorStyle({{ root, selector: resolvedOptions.selector }});
          mapElements(root, {{ selector: resolvedOptions.selector }});
          if (resolvedOptions.observe === false) {{
            return null;
          }}
          const observeRoot = root && root.nodeType === 9 ? (root.body || root.documentElement) : root;
          return observe(observeRoot, {{ selector: resolvedOptions.selector }});
        }}

        const api = {{
          familyName,
          filePrefix,
          entries,
          defaultCssHref,
          mapText,
          unmapText,
          ensureStylesheet,
          ensureSelectorStyle,
          mapElementText,
          unmapElementText,
          mapElements,
          observe,
          install,
        }};
        """
    )

    if module:
        header = textwrap.dedent(
            f"""\
            const runtimeUrl = new URL(import.meta.url);
            const defaultCssHref = new URL({css_file_json}, runtimeUrl).href;
            """
        )
        footer = textwrap.dedent(
            """\
            export {
              defaultCssHref,
              entries,
              ensureSelectorStyle,
              ensureStylesheet,
              familyName,
              filePrefix,
              install,
              mapElementText,
              mapElements,
              mapText,
              observe,
              unmapElementText,
              unmapText,
            };

            export default api;
            """
        )
        return header + "\n" + shared_body + "\n" + footer

    header = textwrap.dedent(
        f"""\
        (function (global) {{
          const runtimeUrl =
            typeof document !== 'undefined' && document.currentScript && document.currentScript.src
              ? new URL(document.currentScript.src, document.baseURI)
              : null;
          const defaultCssHref = runtimeUrl ? new URL({css_file_json}, runtimeUrl).href : null;
        """
    )
    footer = textwrap.dedent(
        """\
          global.FluentEmoji3DMapper = api;
        })(typeof window !== 'undefined' ? window : globalThis);
        """
    )
    return header + "\n" + textwrap.indent(shared_body, "  ") + "\n" + footer


def write_mapper_runtime_files(
    dist_dir: Path,
    family_name: str,
    file_prefix: str,
    ordered_sequences: list[tuple[int, ...]],
    display_codepoints: dict[tuple[int, ...], int] | None,
) -> list[Path]:
    if not display_codepoints:
        return []

    entries = [
        {
            "emoji": emoji_from_sequence(sequence),
            "display": chr(display_codepoints[sequence]),
        }
        for sequence in ordered_sequences
        if sequence in display_codepoints
    ]
    outputs = [
        (
            dist_dir / f"{file_prefix}.runtime.js",
            mapper_runtime_source(family_name, file_prefix, entries, module=False),
        ),
        (
            dist_dir / f"{file_prefix}.runtime.mjs",
            mapper_runtime_source(family_name, file_prefix, entries, module=True),
        ),
    ]
    for path, content in outputs:
        path.write_text(content, encoding="utf-8")
    return [path for path, _ in outputs]


def write_css(
    dist_dir: Path,
    family_name: str,
    file_prefix: str,
    groups: list[list[tuple[int, ...]]],
    shard_artifacts: list[list[dict[str, str]]],
    mapping_mode: str,
    display_codepoints: dict[tuple[int, ...], int] | None,
) -> Path:
    css_path = dist_dir / f"{file_prefix}.css"
    blocks: list[str] = []
    for index, (group, artifacts) in enumerate(zip(groups, shard_artifacts)):
        src_lines = [
            f"    url('./{artifact['fileName']}') format('{artifact['cssFormat']}') tech({artifact['tech']})"
            for artifact in artifacts
        ]
        lines = [
            f"/* [{index:03d}] */",
            "@font-face {",
            f"  font-family: '{family_name}';",
            "  font-style: normal;",
            "  font-weight: 400;",
            "  font-display: swap;",
            "  src:",
            ",\n".join(src_lines) + ";",
        ]
        if len(groups) > 1:
            lines.append(
                "  unicode-range: "
                + unicode_range_for_sequences(
                    group,
                    display_codepoints,
                    include_sequence_codepoints=(mapping_mode == "unicode"),
                )
                + ";"
            )
        lines.append("}")
        blocks.append("\n".join(lines))
    css_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return css_path


def write_manifest(
    dist_dir: Path,
    family_name: str,
    file_prefix: str,
    groups: list[list[tuple[int, ...]]],
    ordered_sequences: list[tuple[int, ...]],
    version: str,
    quality_profile: str,
    max_dimension: int,
    mapping_mode: str,
    group_size: int,
    color_formats: tuple[str, ...],
    shard_artifacts: list[list[dict[str, str]]],
    official_metadata: dict[tuple[int, ...], dict[str, object]],
    display_codepoints: dict[tuple[int, ...], int] | None,
) -> Path:
    manifest_path = dist_dir / f"{file_prefix}.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": version,
                "familyName": family_name,
                "filePrefix": file_prefix,
                "emojiCount": len(ordered_sequences),
                "groupCount": len(groups),
                "qualityProfile": quality_profile,
                "maxDimension": max_dimension,
                "mappingMode": mapping_mode,
                "groupSize": group_size,
                "colorFormats": list(color_formats),
                "groups": [
                    {
                        "index": index,
                        "count": len(group),
                        "unicodeRange": unicode_range_for_sequences(
                            group,
                            display_codepoints,
                            include_sequence_codepoints=(mapping_mode == "unicode"),
                        ),
                        "sources": artifacts,
                    }
                    for index, (group, artifacts) in enumerate(zip(groups, shard_artifacts))
                ],
                "emojis": [
                    {
                        "emoji": emoji_from_sequence(sequence),
                        "display": (
                            chr(display_codepoints[sequence])
                            if display_codepoints is not None and sequence in display_codepoints
                            else emoji_from_sequence(sequence)
                        ),
                        "displayCodepoint": (
                            f"{display_codepoints[sequence]:04X}"
                            if display_codepoints is not None and sequence in display_codepoints
                            else None
                        ),
                        "name": metadata_for_sequence(sequence, official_metadata)["name"],
                        "codepoints": " ".join(f"{codepoint:04X}" for codepoint in sequence),
                    }
                    for sequence in ordered_sequences
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--work-dir", type=Path, default=Path("build/lobehub-3d-font"))
    parser.add_argument("--family-name", default="Fluent Emoji 3D")
    parser.add_argument("--file-prefix", default=None)
    parser.add_argument("--file-prefix-base", default="FluentEmoji3D")
    parser.add_argument("--group-size", type=int, default=None)
    parser.add_argument(
        "--quality-profile",
        choices=tuple(QUALITY_PROFILES),
        default="balanced",
        help="Output detail preset. Use --max-dimension to override the preset value.",
    )
    parser.add_argument("--max-dimension", type=int, default=None)
    parser.add_argument("--version", default="unknown")
    parser.add_argument(
        "--emoji-list-file",
        type=Path,
        action="append",
        default=[],
        help="Optional text file containing one emoji or codepoint sequence per line to build a subset.",
    )
    parser.add_argument(
        "--emoji",
        action="append",
        default=[],
        help="Optional emoji to include directly in the subset. May be repeated.",
    )
    parser.add_argument(
        "--subset-tag",
        default=None,
        help="Optional label inserted into the generated filename prefix for subset builds.",
    )
    parser.add_argument(
        "--mapping-mode",
        choices=MAPPING_MODES,
        default="unicode",
        help="How display glyphs are encoded. 'unicode' uses raw emoji sequences only; 'pua' also emits private-use display glyphs.",
    )
    parser.add_argument(
        "--use-pngquant",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to quantize PNGs during bitmap font generation.",
    )
    parser.add_argument(
        "--use-zopflipng",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to run zopflipng during bitmap font generation.",
    )
    parser.add_argument(
        "--color-formats",
        default=",".join(DEFAULT_COLOR_FORMATS),
        help="Comma-separated list from: cbdt,sbix,svg",
    )
    parser.add_argument(
        "--official-assets-dir",
        type=Path,
        default=Path("fluentui-emoji/assets"),
        help="Optional Fluent UI Emoji metadata root for names and groups",
    )
    args = parser.parse_args()

    color_formats = parse_csv_arg(args.color_formats, set(COLOR_FORMAT_SPECS), "color formats")
    emoji_list_files = tuple(args.emoji_list_file)
    raw_emojis = tuple(args.emoji)
    sequence_to_asset = load_assets(args.assets_dir)
    subset_sequences = load_subset_sequences(emoji_list_files, raw_emojis)
    sequence_to_asset = filter_assets(sequence_to_asset, subset_sequences)
    max_dimension = args.max_dimension if args.max_dimension is not None else QUALITY_PROFILES[args.quality_profile]
    group_size = args.group_size if args.group_size is not None else default_group_size(args.mapping_mode)
    file_prefix_base = args.file_prefix_base
    subset_tag = args.subset_tag or default_subset_tag(emoji_list_files, raw_emojis)
    if subset_tag:
        file_prefix_base = f"{file_prefix_base}-{slugify_subset_tag(subset_tag)}"
    file_prefix = args.file_prefix or default_file_prefix(
        file_prefix_base, args.quality_profile, max_dimension
    )

    args.dist_dir.mkdir(parents=True, exist_ok=True)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = create_staging_dir(args.work_dir, file_prefix)

    ordered_sequences = sorted(sequence_to_asset)
    groups = chunked(ordered_sequences, group_size)
    official_metadata = load_official_metadata(args.official_assets_dir)
    display_codepoints = (
        display_codepoints_for_sequences(ordered_sequences)
        if args.mapping_mode == "pua"
        else None
    )

    shard_artifacts: list[list[dict[str, str]]] = []
    for index, group in enumerate(groups):
        artifacts = build_group_fonts(
            group,
            index,
            len(groups),
            sequence_to_asset,
            display_codepoints,
            args.work_dir,
            staging_dir,
            args.family_name,
            file_prefix,
            max_dimension,
            color_formats,
            args.use_pngquant,
            args.use_zopflipng,
        )
        shard_artifacts.append(artifacts)
        generated = ", ".join(artifact["fileName"] for artifact in artifacts)
        print(f"Built shard {index:03d}: {len(group)} target -> {generated}")

    css_path = write_css(
        staging_dir,
        args.family_name,
        file_prefix,
        groups,
        shard_artifacts,
        args.mapping_mode,
        display_codepoints,
    )
    manifest_path = write_manifest(
        staging_dir,
        args.family_name,
        file_prefix,
        groups,
        ordered_sequences,
        args.version,
        args.quality_profile,
        max_dimension,
        args.mapping_mode,
        group_size,
        color_formats,
        shard_artifacts,
        official_metadata,
        display_codepoints,
    )
    glyphs_path = write_glyphs_js(
        staging_dir,
        file_prefix,
        ordered_sequences,
        official_metadata,
        display_codepoints,
    )
    runtime_paths = write_mapper_runtime_files(
        staging_dir,
        args.family_name,
        file_prefix,
        ordered_sequences,
        display_codepoints,
    )
    publish_outputs(staging_dir, args.dist_dir, file_prefix)
    print(f"Wrote {css_path}")
    print(f"Wrote {manifest_path}")
    print(f"Wrote {glyphs_path}")
    for runtime_path in runtime_paths:
        print(f"Wrote {runtime_path}")


if __name__ == "__main__":
    main()
