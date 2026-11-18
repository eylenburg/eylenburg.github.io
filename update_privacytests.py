#!/usr/bin/env python3
"""
Update privacytests.org scores in browser_comparison.htm
Run weekly via GitHub Action. Only updates if the privacytests git hash changed.
"""

import json
import re
import urllib.request
from pathlib import Path

# Category mappings based on privacytests.org sections
STATE_PARTITIONING = ["supercookies"]  # State Partitioning tests

FINGERPRINTING = [
    "device_fingerprinting",  # Device fingerprinting resistance tests
    "settings_fingerprinting",  # Settings fingerprinting resistance tests
]

TRACKING = [
    "navigation",           # Navigation tests
    "query",                # Tracking query parameter tests
    "trackers",             # Tracker content blocking tests
    "tracker_cookies",      # Tracking cookie protection tests
    "session_1p",           # Cross-session first-party tracking tests
    "session_3p",           # Cross-session third-party tracking tests
]

BROWSER_MAP = {
    "firefox": "firefox",
    "safari": "safari",
    "chrome": "chrome",
    "edge": "edge",
    "opera": "opera",
    "vivaldi": "vivaldi",
    "brave": "brave",
}

OS_MAP = {
    "desktop": "https://privacytests.org/index.json",
    "android": "https://privacytests.org/android.json",
    "ios": "https://privacytests.org/ios.json",
}

# Preferred runner that matches the privacytests.org website display
PREFERRED_RUNNER = "macos-26"

LAST_GIT_FILE = Path(".privacytests_last_git")


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def is_pass(test: dict) -> bool:
    """Count as pass if green checkmark (passed=True) or green hyphen (unsupported=True).
    For device fingerprinting tests that lack a 'passed' field, also treat randomized=True as pass.
    """
    if not isinstance(test, dict):
        return False
    if test.get("passed") is True:
        return True
    if test.get("unsupported") is True:
        return True
    # Device fingerprinting often has no 'passed' key; randomized=True means resistance succeeded
    if test.get("randomized") is True or test.get("randomized") == "true":
        return True
    return False


def select_entry(entries: list) -> dict | None:
    """Select the entry that matches the privacytests.org website display.
    Prefer the macos-26 (ARM) runner; fall back to the most recent otherwise.
    """
    if not entries:
        return None
    preferred = [e for e in entries if e.get("runner") == PREFERRED_RUNNER]
    if preferred:
        # If multiple macos-26 runs, take the latest
        return max(preferred, key=lambda e: e.get("timeStarted", ""))
    # Fallback: most recent non-incognito run
    return max(entries, key=lambda e: e.get("timeStarted", ""))


def count_tests(test_results: dict, categories: list) -> tuple[int, int]:
    """Return (passed_count, total_count) for the given categories."""
    total = 0
    passed = 0
    for cat in categories:
        tests = test_results.get(cat, {})
        if not isinstance(tests, dict):
            continue
        for test in tests.values():
            if not isinstance(test, dict):
                continue
            total += 1
            if is_pass(test):
                passed += 1
    return passed, total


def get_class(passed: int, total: int) -> str:
    if total == 0:
        return ""
    ratio = passed / total
    if ratio == 1.0:
        return "green"
    if ratio >= 0.75:
        return "lgreen"
    return "red"


def update_html(html: str, scores: dict) -> str:
    """scores: {td_id: (text, css_class)}"""
    for td_id, (text, css_class) in scores.items():
        # Prefer matching with class attribute
        pattern = rf'(<td[^>]*id="{re.escape(td_id)}"[^>]*class=")[^"]*("[^>]*>)([^<]*)(</td>)'
        def replacer(m):
            return f'{m.group(1)}{css_class}{m.group(2)}{text}{m.group(4)}'
        html, n = re.subn(pattern, replacer, html, count=1)
        if n == 0:
            # Fallback: content only (no class or different attribute order)
            pattern2 = rf'(<td[^>]*id="{re.escape(td_id)}"[^>]*>)([^<]*)(</td>)'
            def replacer2(m):
                return f'{m.group(1)}{text}{m.group(3)}'
            html = re.sub(pattern2, replacer2, html, count=1)
    return html


def main():
    # Fetch all platforms
    data = {}
    gits = set()
    for os_name, url in OS_MAP.items():
        data[os_name] = fetch_json(url)
        gits.add(data[os_name].get("git", ""))

    current_git = next(iter(gits)) if len(gits) == 1 else "|".join(sorted(gits))
    last_git = LAST_GIT_FILE.read_text().strip() if LAST_GIT_FILE.exists() else ""

    if current_git == last_git:
        print("No new privacytests version. Exiting.")
        return

    print(f"New version detected: {current_git} (was {last_git})")

    # Build scores dict
    scores = {}
    for browser_key, browser_json in BROWSER_MAP.items():
        for os_name in OS_MAP:
            platform_data = data[os_name]
            # Collect all non-incognito, non-nightly entries for this browser
            entries = [
                t for t in platform_data.get("all_tests", [])
                if t.get("browser") == browser_json
                and not t.get("incognito")
                and not t.get("nightly")
            ]
            entry = select_entry(entries)
            if not entry:
                # No data for this browser on this OS → leave blank
                for prefix in ["statepartitioning", "fingerprinting", "tracking"]:
                    td_id = f"{prefix}_{browser_key}_{os_name}"
                    scores[td_id] = ("", "")
                continue

            tr = entry.get("testResults", {})

            # State partitioning
            nf, tot = count_tests(tr, STATE_PARTITIONING)
            text = f"{nf}/{tot}" if tot else ""
            scores[f"statepartitioning_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

            # Fingerprinting
            nf, tot = count_tests(tr, FINGERPRINTING)
            text = f"{nf}/{tot}" if tot else ""
            scores[f"fingerprinting_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

            # Tracking
            nf, tot = count_tests(tr, TRACKING)
            text = f"{nf}/{tot}" if tot else ""
            scores[f"tracking_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

    # Update HTML (Unix line endings)
    html_path = Path("browser_comparison.htm")
    html = html_path.read_text(encoding="utf-8")
    # Normalize to LF so future diffs stay clean
    html = html.replace("\r\n", "\n").replace("\r", "\n")
    new_html = update_html(html, scores)
    html_path.write_text(new_html, encoding="utf-8", newline="\n")

    # Save new git hash
    LAST_GIT_FILE.write_text(current_git + "\n")

    print("Updated browser_comparison.htm and .privacytests_last_git")


if __name__ == "__main__":
    main()
