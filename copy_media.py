#!/usr/bin/env python3
"""Copy photos and videos from an old disk into one-level parent folders."""

from __future__ import annotations

import argparse
import mimetypes
import os
import shutil
import sys
from pathlib import Path


MEDIA_EXTENSIONS = {
    # Common image formats
    ".jpg",
    ".jpeg",
    ".jpe",
    ".png",
    ".gif",
    ".bmp",
    ".dib",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
    ".avif",
    ".jp2",
    ".j2k",
    ".jpf",
    ".jpx",
    ".psd",
    ".svg",
    # Camera RAW formats
    ".raw",
    ".dng",
    ".crw",
    ".cr2",
    ".cr3",
    ".nef",
    ".nrw",
    ".arw",
    ".srf",
    ".sr2",
    ".orf",
    ".rw2",
    ".raf",
    ".pef",
    ".ptx",
    ".rwl",
    ".x3f",
    ".erf",
    ".mef",
    ".mos",
    ".mrw",
    ".kdc",
    ".dcr",
    ".iiq",
    ".3fr",
    # Common video formats
    ".mov",
    ".qt",
    ".mp4",
    ".m4v",
    ".avi",
    ".mkv",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".mpe",
    ".3gp",
    ".3g2",
    ".mts",
    ".m2ts",
    ".ts",
    ".dv",
    ".webm",
    ".flv",
    ".f4v",
    ".vob",
    ".ogv",
    ".asf",
    ".rm",
    ".rmvb",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Recursively copy photos/videos from SOURCE into this script's folder, "
            "grouped by each file's direct parent folder name."
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Mounted old Mac disk or folder to scan",
    )
    return parser.parse_args()


def is_media_file(path: Path) -> bool:
    if path.name.startswith("._"):
        return False

    suffix = path.suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        return True

    mime_type, _ = mimetypes.guess_type(path.name)
    return bool(mime_type and (mime_type.startswith("image/") or mime_type.startswith("video/")))


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path


    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def iter_files(source: Path, destination_root: Path):
    for root, dirnames, filenames in os.walk(source, followlinks=False):
        root_path = Path(root)

        # Prevent accidental self-copying if the destination lives inside SOURCE.
        kept_dirnames = []
        for dirname in dirnames:
            child = root_path / dirname
            try:
                child_resolved = child.resolve()
            except OSError:
                continue
            if child_resolved == destination_root or is_relative_to(child_resolved, destination_root):
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in filenames:
            yield root_path / filename


def copy_media(source: Path, destination_root: Path) -> int:
    copied = 0
    skipped = 0
    errors = 0

    for source_file in iter_files(source, destination_root):
        if not is_media_file(source_file):
            skipped += 1
            continue

        parent_name = source_file.parent.name or source.name
        destination_dir = destination_root / parent_name
        destination_file = unique_destination(destination_dir / source_file.name)

        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination_file = unique_destination(destination_dir / source_file.name)
            shutil.copy2(source_file, destination_file)
        except OSError as exc:
            errors += 1
            print(f"ERROR: {source_file} -> {destination_file}: {exc}", file=sys.stderr)
            continue

        copied += 1
        print(f"Copied: {source_file} -> {destination_file}")

    print()
    print("Summary")
    print(f"Source:      {source}")
    print(f"Destination: {destination_root}")
    print(f"Copied:      {copied}")
    print(f"Skipped:     {skipped}")
    print(f"Errors:      {errors}")

    return 1 if errors else 0


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    destination_root = Path(__file__).resolve().parent

    if not source.exists():
        print(f"Source does not exist: {source}", file=sys.stderr)
        return 2

    if not source.is_dir():
        print(f"Source is not a directory: {source}", file=sys.stderr)
        return 2

    return copy_media(source, destination_root)


if __name__ == "__main__":
    raise SystemExit(main())
