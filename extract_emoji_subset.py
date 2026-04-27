from __future__ import annotations

import argparse
from pathlib import Path

from build_lobehub_3d_font import emoji_from_sequence, load_assets


IGNORED_DIR_NAMES = {
    ".git",
    ".idea",
    ".next",
    ".turbo",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "public/fonts",
}
TRIE_END = "\0"


def build_trie(sequences: list[tuple[int, ...]]) -> dict[str, dict]:
    root: dict[str, dict] = {}
    for sequence in sequences:
        text = emoji_from_sequence(sequence)
        node = root
        for character in text:
            node = node.setdefault(character, {})
        node[TRIE_END] = sequence
    return root


def should_skip_path(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def iter_text_files(paths: list[Path]) -> list[Path]:
    results: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            if not should_skip_path(path):
                results.append(path)
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and not should_skip_path(child):
                results.append(child)
    return results


def read_text_if_possible(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def extract_sequences_from_text(text: str, trie: dict[str, dict]) -> set[tuple[int, ...]]:
    matches: set[tuple[int, ...]] = set()
    index = 0
    text_length = len(text)
    while index < text_length:
        node = trie
        cursor = index
        last_match: tuple[int, ...] | None = None
        last_index = index
        while cursor < text_length:
            character = text[cursor]
            if character not in node:
                break
            node = node[character]
            cursor += 1
            if TRIE_END in node:
                last_match = node[TRIE_END]
                last_index = cursor
        if last_match is not None:
            matches.add(last_match)
            index = last_index
            continue
        index += 1
    return matches


def write_output(out_file: Path, sequences: list[tuple[int, ...]], scanned_files: int) -> None:
    lines = [
        f"# extracted supported emoji subset",
        f"# files scanned: {scanned_files}",
        f"# emoji count: {len(sequences)}",
        "",
    ]
    lines.extend(emoji_from_sequence(sequence) for sequence in sequences)
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--out-file", type=Path, required=True)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    sequence_to_asset = load_assets(args.assets_dir)
    trie = build_trie(sorted(sequence_to_asset))
    matched_sequences: set[tuple[int, ...]] = set()
    scanned_files = 0

    for path in iter_text_files(args.paths):
        text = read_text_if_possible(path)
        if text is None:
            continue
        scanned_files += 1
        matched_sequences.update(extract_sequences_from_text(text, trie))

    ordered_sequences = sorted(matched_sequences)
    args.out_file.parent.mkdir(parents=True, exist_ok=True)
    write_output(args.out_file, ordered_sequences, scanned_files)
    print(f"Wrote {args.out_file}")
    print(f"Scanned {scanned_files} text files")
    print(f"Found {len(ordered_sequences)} supported emojis")


if __name__ == "__main__":
    main()
