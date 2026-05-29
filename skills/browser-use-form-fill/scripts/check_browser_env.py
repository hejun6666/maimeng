#!/usr/bin/env python3
"""Check whether a computer is ready for browser-use form filling."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def exists(path: str) -> bool:
    return Path(path).exists()


def command(name: str) -> str | None:
    return shutil.which(name)


def mac_browsers() -> list[tuple[str, str]]:
    candidates = [
        ("Google Chrome", "/Applications/Google Chrome.app"),
        ("Google Chrome", str(Path.home() / "Applications/Google Chrome.app")),
        ("Microsoft Edge", "/Applications/Microsoft Edge.app"),
        ("Microsoft Edge", str(Path.home() / "Applications/Microsoft Edge.app")),
        ("Chromium", "/Applications/Chromium.app"),
        ("Chromium", str(Path.home() / "Applications/Chromium.app")),
    ]
    return [(name, path) for name, path in candidates if exists(path)]


def windows_browsers() -> list[tuple[str, str]]:
    roots = [
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    candidates: list[tuple[str, str]] = []
    for root in filter(None, roots):
        candidates.extend(
            [
                ("Google Chrome", str(Path(root) / "Google/Chrome/Application/chrome.exe")),
                ("Microsoft Edge", str(Path(root) / "Microsoft/Edge/Application/msedge.exe")),
            ]
        )
    for exe, name in (("chrome.exe", "Google Chrome"), ("msedge.exe", "Microsoft Edge")):
        found = command(exe)
        if found:
            candidates.append((name, found))
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for name, path in candidates:
        key = path.lower()
        if key not in seen and exists(path):
            seen.add(key)
            results.append((name, path))
    return results


def linux_browsers() -> list[tuple[str, str]]:
    candidates = [
        ("Google Chrome", "google-chrome"),
        ("Google Chrome", "google-chrome-stable"),
        ("Microsoft Edge", "microsoft-edge"),
        ("Microsoft Edge", "microsoft-edge-stable"),
        ("Microsoft Edge", "msedge"),
        ("Chromium", "chromium"),
        ("Chromium", "chromium-browser"),
    ]
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, exe in candidates:
        found = command(exe)
        if found and found not in seen:
            seen.add(found)
            results.append((name, found))
    return results


def detect_browsers() -> list[tuple[str, str]]:
    system = platform.system()
    if system == "Darwin":
        return mac_browsers()
    if system == "Windows":
        return windows_browsers()
    if system == "Linux":
        return linux_browsers()
    return []


def print_status(label: str, ok: bool, detail: str) -> None:
    mark = "OK" if ok else "MISSING"
    print(f"[{mark}] {label}: {detail}")


def main() -> int:
    browser_use = command("browser-use")
    uvx = command("uvx")
    browsers = detect_browsers()

    print("Browser Use Form Fill environment check")
    print(f"System: {platform.system()} {platform.machine()}")
    print()

    if browser_use:
        print_status("browser-use CLI", True, browser_use)
        automation_command = "browser-use"
    elif uvx:
        print_status("browser-use CLI", True, f"not installed, but uvx is available: {uvx}")
        automation_command = "uvx --python 3.11 browser-use"
    else:
        print_status("browser-use CLI", False, "browser-use and uvx were not found")
        automation_command = ""

    print_status("uvx", bool(uvx), uvx or "not found")

    if browsers:
        print_status("browser", True, f"{len(browsers)} browser(s) found")
        for name, path in browsers:
            print(f"  - {name}: {path}")
    else:
        print_status("browser", False, "Google Chrome, Microsoft Edge, or Chromium was not found")

    print()
    if automation_command and browsers:
        print("Result: READY")
        print(f"Recommended command prefix: {automation_command} --headed --profile Default")
        print("Use the browser where the user normally logs in. Chrome and Edge are both acceptable.")
        return 0

    print("Result: NOT READY")
    print("Next steps:")
    if not automation_command:
        print("- Install browser-use CLI, or install uv so Codex can run browser-use through uvx.")
        if platform.system() in {"Darwin", "Linux"}:
            print("  browser-use installer: curl -fsSL https://browser-use.com/cli/install.sh | bash")
        else:
            print("  browser-use installer: use the official browser-use CLI setup instructions for Windows.")
    if not browsers:
        print("- Install Google Chrome or Microsoft Edge, then log in to the target website in that browser.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
