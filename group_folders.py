#!/usr/bin/env python3
"""Move immediate child folders into first-character bucket folders."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


BUCKETS = {str(number) for number in range(10)} | {chr(letter) for letter in range(ord("A"), ord("Z") + 1)}
OTHER_BUCKET = "Other"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Move immediate child folders from SOURCE into MIGRATION_PATH buckets "
            "named A-Z, 0-9, or Other. Files inside those folders are not reorganized."
        )
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Folder containing many immediate child folders, such as IMac_Photos",
    )
    parser.add_argument(
        "migration_path",
        type=Path,
        help="Destination root where bucket folders will be created",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without changing anything",
    )
    return parser.parse_args()


def bucket_for(folder_name: str) -> str:
    if not folder_name:
        return OTHER_BUCKET

    first_character = folder_name[0].upper()
    if first_character in BUCKETS:
        return first_character
    return OTHER_BUCKET


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def unique_destination(path: Path) -> tuple[Path, bool]:
    if not path.exists():
        return path, False

    parent = path.parent
    name = path.name
    counter = 1

    while True:
        candidate = parent / f"{name}_{counter}"
        if not candidate.exists():
            return candidate, True
        counter += 1


def iter_source_children(source: Path) -> list[Path]:
    return sorted(source.iterdir(), key=lambda path: path.name.lower())


def validate_paths(source: Path, migration_path: Path) -> int:
    if not source.exists():
        print(f"Source does not exist: {source}", file=sys.stderr)
        return 2


    if not source.is_dir():
        print(f"Source is not a directory: {source}", file=sys.stderr)
        return 2

    if source == migration_path:
        print("Migration path must be different from source.", file=sys.stderr)
        return 2

    if is_relative_to(migration_path, source):
        print("Migration path must not be inside source.", file=sys.stderr)
        return 2

    return 0


def move_folders(source: Path, migration_path: Path, *, dry_run: bool) -> int:
    moved = 0
    planned = 0
    skipped = 0
    renamed = 0
    errors = 0

    source_children = iter_source_children(source)
    source_folders = [child for child in source_children if child.is_dir()]
    skipped = len(source_children) - len(source_folders)

    if not source_folders:
        print(f"No immediate child folders found in: {source}")
        return 0

    for source_folder in source_folders:
        destination_dir = migration_path / bucket_for(source_folder.name)
        destination_folder, was_renamed = unique_destination(destination_dir / source_folder.name)

        if dry_run:
            action = "Would move"
            if was_renamed:
                action = "Would move with rename"
            print(f"{action}: {source_folder} -> {destination_folder}")
            planned += 1
            if was_renamed:
                renamed += 1
            continue

        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination_folder, was_renamed = unique_destination(destination_dir / source_folder.name)
            shutil.move(str(source_folder), str(destination_folder))
        except OSError as exc:
            errors += 1
            print(f"ERROR: {source_folder} -> {destination_folder}: {exc}", file=sys.stderr)
            continue

        moved += 1
        if was_renamed:
            renamed += 1
            print(f"Moved with rename: {source_folder} -> {destination_folder}")
        else:
            print(f"Moved: {source_folder} -> {destination_folder}")

    print()
    print("Summary")
    print(f"Source:         {source}")
    print(f"Migration path: {migration_path}")
    print(f"Moved:          {moved}")
    print(f"Dry-run moves:  {planned}")
    print(f"Skipped:        {skipped}")
    print(f"Renamed:        {renamed}")
    print(f"Errors:         {errors}")

    return 1 if errors else 0


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    migration_path = args.migration_path.expanduser().resolve()

    validation_error = validate_paths(source, migration_path)
    if validation_error:
        return validation_error

    return move_folders(source, migration_path, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
