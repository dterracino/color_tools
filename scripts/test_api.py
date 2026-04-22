"""
Smoke test for the deployed Vercel API endpoints.

Usage:
    python scripts/test_api.py
    python scripts/test_api.py --base-url https://color-tools-git-my-branch-dterracino.vercel.app

Exits 0 if all checks pass, 1 if any fail.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from urllib.error import URLError

BASE_URL = "https://color-tools-nine.vercel.app"

ENDPOINTS = [
    "/api/color_of_day",
    "/api/filament_of_day",
]


def check_endpoint(base_url: str, path: str) -> tuple[bool, str]:
    """
    Fetch one endpoint and verify:
    - HTTP 200 status
    - Content-Type contains image/svg+xml
    - Body starts with <svg
    """
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(256).decode("utf-8", errors="replace")
    except URLError as exc:
        return False, f"Connection error: {exc}"

    if status != 200:
        return False, f"HTTP {status}"
    if "image/svg+xml" not in content_type:
        return False, f"Wrong Content-Type: {content_type!r}"
    if not body.lstrip().startswith("<svg"):
        return False, f"Body does not start with <svg: {body[:60]!r}"

    return True, "OK"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the color_tools Vercel API")
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Base URL of the deployment (default: {BASE_URL})",
    )
    args = parser.parse_args()

    passed = 0
    failed = 0

    print(f"Testing: {args.base_url}\n")

    for path in ENDPOINTS:
        ok, message = check_endpoint(args.base_url, path)
        status_str = "PASS" if ok else "FAIL"
        print(f"  [{status_str}] {path} — {message}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
