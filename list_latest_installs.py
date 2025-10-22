#!/usr/bin/env python3
"""
List macOS applications installed (date added) within the last 14 days.

Results are printed to stdout and stored in latest_installs.txt alongside this script.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path


ROOTS = [
    Path("/Applications"),
    Path("/Applications/Utilities"),
    Path.home() / "Applications",
]
OUTPUT_FILE = Path(__file__).with_name("latest_installs.txt")
DEFAULT_LOOKBACK_DAYS = 14


def _iter_app_bundles(root: Path) -> list[Path]:
    """Yield top-level .app bundles under root (skip nested bundles)."""
    bundles: list[Path] = []
    for path in root.rglob("*.app"):
        if any(parent.suffix == ".app" for parent in path.parents):
            continue
        bundles.append(path)
    return bundles


def _get_date_added(app_path: Path) -> datetime.datetime | None:
    """Fetch Spotlight date-added metadata for an app bundle."""
    proc = subprocess.run(
        ["mdls", "-name", "kMDItemDateAdded", "-raw", str(app_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    date_str = proc.stdout.strip()
    if not date_str or date_str == "(null)":
        return None
    try:
        added = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return None
    return added


def gather_latest_installs(days: int) -> list[tuple[datetime.datetime, Path]]:
    """Return (date_added, app_path) tuples sorted newest first."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    results: list[tuple[datetime.datetime, Path]] = []
    for root in ROOTS:
        if not root.exists():
            continue
        for app_path in _iter_app_bundles(root):
            added = _get_date_added(app_path)
            if added is None:
                continue
            if added.astimezone(datetime.timezone.utc) < cutoff:
                continue
            results.append((added, app_path))
    results.sort(key=lambda item: item[0], reverse=True)
    return results


def build_report(entries: list[tuple[datetime.datetime, Path]], days: int) -> list[str]:
    """Format entries into human-readable report lines."""
    if not entries:
        return [f"No applications found with date-added within the last {days} days."]
    local_tz = datetime.datetime.now().astimezone().tzinfo
    lines = []
    for added, app_path in entries:
        local_added = added.astimezone(local_tz)
        timestamp = local_added.strftime("%Y-%m-%d %H:%M:%S %Z")
        lines.append(f"{timestamp} - {app_path.name} ({app_path})")
    return lines


def write_report(lines: list[str]) -> None:
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List recently installed macOS apps.")
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help=f"Number of days to look back (default: {DEFAULT_LOOKBACK_DAYS}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    if args.days <= 0:
        print("Days must be a positive integer.", file=sys.stderr)
        return 1
    entries = gather_latest_installs(args.days)
    report_lines = build_report(entries, args.days)
    print("\n".join(report_lines))
    try:
        write_report(report_lines)
    except OSError as exc:
        print(f"Failed to write report: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
