#!/usr/bin/env python3
"""
List macOS applications installed (date added) within the last 14 days.

Results are printed to stdout and stored in latest_installs.txt alongside this script.
"""

from __future__ import annotations

import datetime
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Optional


ROOTS = [
    Path("/Applications"),
    Path("/Applications/Utilities"),
    Path.home() / "Applications",
]
OUTPUT_FILE = Path(__file__).with_name("latest_installs.txt")
LOOKBACK_DAYS = 14


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


def _get_download_source(app_path: Path) -> Optional[str]:
    """Return download source URL from metadata if available."""
    where_froms = _get_where_froms(app_path)
    if where_froms:
        return where_froms
    return _get_quarantine_source(app_path)


def _get_where_froms(app_path: Path) -> Optional[str]:
    """Extract download URL from kMDItemWhereFroms metadata."""
    proc = subprocess.run(
        ["xattr", "-p", "com.apple.metadata:kMDItemWhereFroms", str(app_path)],
        capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        return None
    try:
        values = plistlib.loads(proc.stdout)
    except Exception:
        return None
    if isinstance(values, (list, tuple)):
        for value in values:
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
    elif isinstance(values, str) and values.startswith(("http://", "https://")):
        return values
    return None


def _get_quarantine_source(app_path: Path) -> Optional[str]:
    """Extract download URL from quarantine attribute if present."""
    proc = subprocess.run(
        ["xattr", "-p", "com.apple.quarantine", str(app_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    if not value:
        return None
    parts = value.split(";")
    if len(parts) >= 4:
        url = parts[-1].strip()
        if url.startswith(("http://", "https://")):
            return url
    return None


def gather_latest_installs() -> list[tuple[datetime.datetime, Path, Optional[str]]]:
    """Return (date_added, app_path, source_url) tuples sorted newest first."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=LOOKBACK_DAYS)
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
            source = _get_download_source(app_path)
            results.append((added, app_path, source))
    results.sort(key=lambda item: item[0], reverse=True)
    return results


def build_report(entries: list[tuple[datetime.datetime, Path, Optional[str]]]) -> list[str]:
    """Format entries into human-readable report lines."""
    if not entries:
        return ["No applications found with date-added within the last 14 days."]
    local_tz = datetime.datetime.now().astimezone().tzinfo
    lines = []
    for added, app_path, source in entries:
        local_added = added.astimezone(local_tz)
        timestamp = local_added.strftime("%Y-%m-%d %H:%M:%S %Z")
        source_text = source if source else "Source unknown"
        lines.append(f"{timestamp} - {app_path.name} ({app_path}) | {source_text}")
    return lines


def write_report(lines: list[str]) -> None:
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    entries = gather_latest_installs()
    report_lines = build_report(entries)
    print("\n".join(report_lines))
    try:
        write_report(report_lines)
    except OSError as exc:
        print(f"Failed to write report: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
