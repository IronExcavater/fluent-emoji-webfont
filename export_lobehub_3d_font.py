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


def resolve_manifest(dist_dir: Path, manifest: Path | None) -> Path:
    if manifest is not None:
        return manifest

    manifests = sorted(dist_dir.glob("*.manifest.json"))
    if not manifests:
        raise SystemExit(f"No manifest found in {dist_dir}")
    if len(manifests) > 1:
        names = ", ".join(path.name for path in manifests)
        raise SystemExit(
            f"Multiple manifests found in {dist_dir}; pass --manifest explicitly. Found: {names}"
        )
    return manifests[0]


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
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--zip-name", default=None)
    parser.add_argument("--include-showcase", action="store_true")
    args = parser.parse_args()

    manifest_path = resolve_manifest(args.dist_dir, args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_dir = manifest_path.parent
    file_prefix = manifest["filePrefix"]
    family_name = manifest["familyName"]
    quality_profile = manifest.get("qualityProfile", "balanced")
    max_dimension = manifest["maxDimension"]
    out_dir = args.out_dir or Path("export") / file_prefix

    if out_dir.exists():
        shutil.rmtree(out_dir)
    fonts_dir = out_dir / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    font_files = unique_font_files(manifest)
    copy_files([manifest_dir / f"{file_prefix}.css"], fonts_dir)
    copy_files([manifest_dir / name for name in font_files], fonts_dir)

    if args.include_showcase:
        showcase_files = [
            Path("index.html"),
            Path("sample/list/favicon.ico"),
            manifest_dir / f"{file_prefix}.glyphs.js",
            manifest_dir / f"{file_prefix}.manifest.json",
        ]
        for path in showcase_files:
            if path.exists():
                target_name = path.name if path.name != "favicon.ico" else "favicon.ico"
                shutil.copy2(path, out_dir / target_name)

    write_readme(out_dir, family_name, file_prefix, quality_profile, max_dimension, font_files)

    zip_name = args.zip_name or file_prefix
    archive_base = out_dir.parent / zip_name
    shutil.make_archive(str(archive_base), "zip", root_dir=out_dir.parent, base_dir=out_dir.name)
    print(f"Wrote {out_dir}")
    print(f"Wrote {archive_base}.zip")


if __name__ == "__main__":
    main()
