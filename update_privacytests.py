#!/usr/bin/env python3
"""
Update privacytests.org scores in browser_comparison.htm
Run weekly via GitHub Action. Only updates if the privacytests git hash changed.
"""

import json
import re
import urllib.request
from pathlib import Path
from collections import defaultdict

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


def aggregate_results(entries: list, categories: list) -> tuple[int, int]:
    """Aggregate across all runs for a browser.
    A test counts as failed if ANY run failed it (matches privacytests.org display).
    Returns (passed_count, total_count).
    """
    # Collect all test names and their pass status across runs
    # test_name -> list of is_pass results
    results = defaultdict(list)
    for entry in entries:
        tr = entry.get("testResults", {})
        for cat in categories:
            tests = tr.get(cat, {})
            if not isinstance(tests, dict):
                continue
            for name, test in tests.items():
                if isinstance(test, dict):
                    results[name].append(is_pass(test))

    if not results:
        return 0, 0

    total = len(results)
    # Pass only if EVERY run passed (i.e. no run failed it)
    passed = sum(1 for statuses in results.values() if all(statuses))
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
            if not entries:
                # No data for this browser on this OS → leave blank
                for prefix in ["statepartitioning", "fingerprinting", "tracking"]:
                    td_id = f"{prefix}_{browser_key}_{os_name}"
                    scores[td_id] = ("", "")
                continue

            # State partitioning
            nf, tot = aggregate_results(entries, STATE_PARTITIONING)
            text = f"{nf}/{tot}" if tot else ""
            scores[f"statepartitioning_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

            # Fingerprinting
            nf, tot = aggregate_results(entries, FINGERPRINTING)
            text = f"{nf}/{tot}" if tot else ""
            scores[f"fingerprinting_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

            # Tracking
            nf, tot = aggregate_results(entries, TRACKING)
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
