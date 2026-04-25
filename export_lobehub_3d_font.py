from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def unique_font_files(manifest: dict[str, object]) -> list[str]:
    names: set[str] = set()
    for group in manifest.get("groups", []):
        for source in group.get("sources", []):
            names.add(source["fileName"])
    return sorted(names)


def copy_files(files: list[Path], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in files:
        shutil.copy2(path, destination / path.name)


def write_readme(
    destination: Path,
    family_name: str,
    file_prefix: str,
    quality_profile: str,
    max_dimension: int,
    font_files: list[str],
) -> None:
    tech_counts: dict[str, int] = {}
    for file_name in font_files:
        suffix = file_name.rsplit("-", 1)[-1].replace(".ttf", "")
        tech_counts[suffix] = tech_counts.get(suffix, 0) + 1

    lines = [
        family_name,
        "",
        f"Detail: {quality_profile} ({max_dimension}px)",
        "",
        "Files in this package:",
        f"- fonts/{file_prefix}.css",
        f"- fonts/{file_prefix}*.ttf",
        "",
        "Import:",
        f'<link rel="stylesheet" href="/fonts/{file_prefix}.css" />',
        "",
        ".emoji-text {",
        f'  font-family: "{family_name}", sans-serif;',
        "}",
        "",
        "Counts:",
    ]
    for tech in ("cbdt", "sbix", "svg"):
        count = tech_counts.get(tech)
        if count:
            lines.append(f"- {count} x *-{tech}.ttf")

    (destination / "README.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--out-dir", type=Path, default=Path("export/LobeHubFluentEmoji3DFont"))
    parser.add_argument("--zip-name", default=None)
    parser.add_argument("--include-showcase", action="store_true")
    args = parser.parse_args()

    manifest_path = args.dist_dir / "LobeHubFluentEmoji3DFont.manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_prefix = manifest["filePrefix"]
    family_name = manifest["familyName"]
    quality_profile = manifest.get("qualityProfile", "balanced")
    max_dimension = manifest["maxDimension"]

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    fonts_dir = args.out_dir / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    font_files = unique_font_files(manifest)
    copy_files([args.dist_dir / f"{file_prefix}.css"], fonts_dir)
    copy_files([args.dist_dir / name for name in font_files], fonts_dir)

    if args.include_showcase:
        showcase_files = [
            Path("index.html"),
            Path("sample/list/favicon.ico"),
            args.dist_dir / f"{file_prefix}.glyphs.js",
            args.dist_dir / f"{file_prefix}.manifest.json",
        ]
        for path in showcase_files:
            if path.exists():
                target_name = path.name if path.name != "favicon.ico" else "favicon.ico"
                shutil.copy2(path, args.out_dir / target_name)

    write_readme(args.out_dir, family_name, file_prefix, quality_profile, max_dimension, font_files)

    zip_name = args.zip_name or f"{file_prefix}-{quality_profile}-{max_dimension}px"
    archive_base = args.out_dir.parent / zip_name
    shutil.make_archive(str(archive_base), "zip", root_dir=args.out_dir.parent, base_dir=args.out_dir.name)
    print(f"Wrote {args.out_dir}")
    print(f"Wrote {archive_base}.zip")


if __name__ == "__main__":
    main()
