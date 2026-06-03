#!/usr/bin/env python3
"""Sync Google Takeout photos from laptop (sshfs mount) to NAS.

Runs on the Pi. Expects the laptop's Takeout folder mounted via sshfs.

Mount:
  sshfs -o IdentityFile=~/.ssh/laptop_key \
    U6122976@tr-wt3hm659rf:"/Users/U6122976/Downloads/Takeout/Google Photos" \
    /tmp/takeout

Usage:
  nas-photos-sync.py plan                 — show what would be synced
  nas-photos-sync.py [--dry-run] sync     — sync everything
  nas-photos-sync.py [--dry-run] sync-years
  nas-photos-sync.py [--dry-run] sync-albums
  nas-photos-sync.py mount                — mount laptop Takeout via sshfs
  nas-photos-sync.py unmount              — unmount
"""

import argparse
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

TAKEOUT_MOUNT = Path(os.environ.get("TAKEOUT_MOUNT", "/tmp/takeout"))
NAS_PHOTOS = Path(os.environ.get("NAS_PHOTOS", "/mnt/nas-photos/Photos"))
LAPTOP_HOST = os.environ.get("LAPTOP_HOST", "U6122976@tr-wt3hm659rf")
LAPTOP_KEY = os.environ.get("LAPTOP_KEY", "{{HOME}}/.ssh/laptop_key")
LAPTOP_TAKEOUT_PATH = os.environ.get(
    "LAPTOP_TAKEOUT_PATH",
    "/Users/U6122976/Downloads/Takeout/Google Photos",
)

SKIP_FOLDERS = {"Archive", "Trash", "Camera", "100MEDIA", "Failed Videos"}

YEAR_PATTERNS = [
    re.compile(r"^(?:PXL|IMG|VID|Screenshot)[_-](\d{4})\d{4}"),
    re.compile(r"^(\d{4})-\d{2}-\d{2}"),
    re.compile(r"BURST(\d{4})\d{4}"),
]

FOLDER_YEAR_PATTERN = re.compile(r"\s(\d{4})$")


def check_mount():
    if not TAKEOUT_MOUNT.is_dir() or not any(TAKEOUT_MOUNT.iterdir()):
        print(f"ERROR: {TAKEOUT_MOUNT} is not mounted or empty.")
        print(f"Run: {sys.argv[0]} mount")
        sys.exit(1)


def count_files(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for f in path.iterdir() if f.is_file())


def count_non_json(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for f in path.iterdir() if f.is_file() and f.suffix != ".json")


def guess_year(album_dir: Path) -> str | None:
    """Guess year from filenames in a directory."""
    years = Counter()
    samples = 0
    for f in album_dir.iterdir():
        if not f.is_file() or f.suffix == ".json":
            continue
        for pat in YEAR_PATTERNS:
            m = pat.search(f.name)
            if m:
                years[m.group(1)] += 1
                break
        samples += 1
        if samples >= 15:
            break

    if years:
        return years.most_common(1)[0][0]

    # Fall back to year in folder name (e.g. "Chicago 2018")
    m = FOLDER_YEAR_PATTERN.search(album_dir.name)
    if m:
        return m.group(1)

    return None


def get_takeout_folders():
    """Return sorted list of folder names in the Takeout mount."""
    return sorted(
        d.name for d in TAKEOUT_MOUNT.iterdir() if d.is_dir()
    )


def is_year_folder(name: str) -> bool:
    return name.startswith("Photos from ")


def year_from_folder(name: str) -> str:
    return name.removeprefix("Photos from ")


# --- Commands ---


def cmd_mount():
    if TAKEOUT_MOUNT.is_dir() and any(TAKEOUT_MOUNT.iterdir()):
        print(f"Already mounted at {TAKEOUT_MOUNT}")
        return
    TAKEOUT_MOUNT.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "sshfs",
            "-o", f"IdentityFile={LAPTOP_KEY}",
            f"{LAPTOP_HOST}:{LAPTOP_TAKEOUT_PATH}",
            str(TAKEOUT_MOUNT),
        ],
        check=True,
    )
    print(f"Mounted at {TAKEOUT_MOUNT}")


def cmd_unmount():
    subprocess.run(["fusermount", "-u", str(TAKEOUT_MOUNT)], check=False)
    print(f"Unmounted {TAKEOUT_MOUNT}")


def cmd_plan():
    check_mount()
    folders = get_takeout_folders()

    # Year folders
    year_folders = [(f, year_from_folder(f)) for f in folders if is_year_folder(f)]
    album_folders = [
        f for f in folders if not is_year_folder(f) and f not in SKIP_FOLDERS
    ]

    print("=== YEAR FOLDERS ===")
    print()
    print(f"  {'Folder':<25} {'Laptop':>10} {'NAS':>10} {'Delta':>10}")
    print(f"  {'------':<25} {'------':>10} {'---':>10} {'-----':>10}")

    total_laptop = 0
    total_nas = 0

    for folder_name, year in year_folders:
        laptop_count = count_files(TAKEOUT_MOUNT / folder_name)
        nas_count = count_files(NAS_PHOTOS / year)
        delta = laptop_count - nas_count
        sign = "+" if delta >= 0 else ""
        print(f"  {folder_name:<25} {laptop_count:>10} {nas_count:>10} {sign + str(delta):>10}")
        total_laptop += laptop_count
        total_nas += nas_count

    print()
    total_delta = total_laptop - total_nas
    sign = "+" if total_delta >= 0 else ""
    print(f"  {'TOTAL':<25} {total_laptop:>10} {total_nas:>10} {sign + str(total_delta):>10}")

    # Named albums
    print()
    print("=== NAMED ALBUMS ===")
    print()
    print(f"  {'Album':<45} {'Photos':>8} {'→ Destination'}")
    print(f"  {'-----':<45} {'------':>8} {'-------------'}")

    for folder_name in album_folders:
        album_path = TAKEOUT_MOUNT / folder_name
        photo_count = count_non_json(album_path)
        if photo_count == 0:
            continue

        year_guess = guess_year(album_path)
        if year_guess:
            dest = f"{year_guess}/{folder_name}/"
        else:
            dest = f"_unsorted/{folder_name}/"
        print(f"  {folder_name:<45} {photo_count:>8} → {dest}")


def rsync_copy(src: Path, dst: Path, dry_run: bool):
    """rsync from src to dst with --ignore-existing."""
    dst.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-av", "--ignore-existing"]
    if dry_run:
        cmd.append("--dry-run")
    cmd += [str(src) + "/", str(dst) + "/"]
    subprocess.run(cmd, check=True)


def cmd_sync_years(dry_run: bool):
    check_mount()
    folders = get_takeout_folders()
    year_folders = [(f, year_from_folder(f)) for f in folders if is_year_folder(f)]

    print("Syncing year folders from laptop to NAS...")
    for folder_name, year in year_folders:
        src = TAKEOUT_MOUNT / folder_name
        dst = NAS_PHOTOS / year
        print(f"\n--- {folder_name} → {dst}/ ---")
        rsync_copy(src, dst, dry_run)

    print()
    if dry_run:
        print("(dry run — no files were transferred)")
    print("Done syncing year folders.")


def cmd_sync_albums(dry_run: bool):
    check_mount()
    folders = get_takeout_folders()
    album_folders = [
        f for f in folders if not is_year_folder(f) and f not in SKIP_FOLDERS
    ]

    print("Syncing named album folders from laptop to NAS...")
    for folder_name in album_folders:
        album_path = TAKEOUT_MOUNT / folder_name
        photo_count = count_non_json(album_path)
        if photo_count == 0:
            continue

        year_guess = guess_year(album_path)
        if year_guess:
            dst = NAS_PHOTOS / year_guess / folder_name
        else:
            dst = NAS_PHOTOS / "_unsorted" / folder_name
        print(f"\n--- {folder_name} → {dst}/ ---")
        rsync_copy(album_path, dst, dry_run)

    print()
    if dry_run:
        print("(dry run — no files were transferred)")
    print("Done syncing album folders.")


def cmd_sync_all(dry_run: bool):
    cmd_sync_years(dry_run)
    print()
    cmd_sync_albums(dry_run)


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description="Sync Google Takeout photos from laptop to NAS"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be transferred without copying")
    parser.add_argument(
        "command",
        choices=["mount", "unmount", "plan", "sync-years", "sync-albums", "sync-all", "sync"],
        help="Command to run",
    )
    args = parser.parse_args()

    match args.command:
        case "mount":
            cmd_mount()
        case "unmount":
            cmd_unmount()
        case "plan":
            cmd_plan()
        case "sync-years":
            cmd_sync_years(args.dry_run)
        case "sync-albums":
            cmd_sync_albums(args.dry_run)
        case "sync-all" | "sync":
            cmd_sync_all(args.dry_run)


if __name__ == "__main__":
    main()
