#!/usr/bin/env python3
"""
Update privacytests.org scores in browser_comparison.htm
Run weekly via GitHub Action. Only updates if the privacytests git hash changed.

Scoring matches the privacytests.org website:
- State partitioning: aggregate all runs, fail if ANY run failed
- Fingerprinting: website-style consistency scoring
- Tracking: macos-26 single run (matches the site's default display)
"""

import json
import re
import urllib.request
from pathlib import Path
from collections import defaultdict

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
PREFERRED_RUNNER = "macos-26"
EXCLUDED_DEVICE_TESTS = {"Math.tanh(0.123)"}


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def select_preferred(entries: list) -> dict | None:
    """Prefer macos-26 runner; fall back to most recent."""
    if not entries:
        return None
    preferred = [e for e in entries if e.get("runner") == PREFERRED_RUNNER]
    if preferred:
        return max(preferred, key=lambda e: e.get("timeStarted", ""))
    return max(entries, key=lambda e: e.get("timeStarted", ""))


def score_aggregated(entries: list, categories: list) -> tuple[int, int]:
    """Fail a test if ANY run failed it."""
    results = defaultdict(list)
    for entry in entries:
        for cat in categories:
            tests = entry.get("testResults", {}).get(cat, {})
            if not isinstance(tests, dict):
                continue
            for name, test in tests.items():
                if isinstance(test, dict):
                    passed = test.get("passed") is True or test.get("unsupported") is True
                    results[name].append(passed)
    if not results:
        return 0, 0
    total = len(results)
    passed = sum(1 for statuses in results.values() if all(statuses))
    return passed, total


def score_single(entry: dict, categories: list) -> tuple[int, int]:
    """Score a single run."""
    passed = total = 0
    for cat in categories:
        tests = entry.get("testResults", {}).get(cat, {})
        if not isinstance(tests, dict):
            continue
        for test in tests.values():
            if isinstance(test, dict):
                total += 1
                if test.get("passed") is True or test.get("unsupported") is True:
                    passed += 1
    return passed, total


def score_fingerprinting(entries: list) -> tuple[int, int]:
    """Website-style fingerprinting scoring."""
    device_agg = defaultdict(lambda: {"randomized": [], "value": []})
    settings_agg = defaultdict(list)

    for entry in entries:
        tr = entry.get("testResults", {})
        for name, test in tr.get("device_fingerprinting", {}).items():
            if isinstance(test, dict):
                device_agg[name]["randomized"].append(bool(test.get("randomized")))
                device_agg[name]["value"].append(test.get("value"))
        for name, test in tr.get("settings_fingerprinting", {}).items():
            if isinstance(test, dict):
                settings_agg[name].append(test.get("passed") is True)

    device_pass = 0
    device_count = 0
    for name, agg in device_agg.items():
        if name in EXCLUDED_DEVICE_TESTS:
            continue
        rand = agg["randomized"]
        if len(rand) < 2:
            continue
        device_count += 1
        if sum(rand) >= 2:
            device_pass += 1
        elif len(set(str(v) for v in agg["value"])) == 1:
            device_pass += 1

    settings_pass = sum(1 for statuses in settings_agg.values() if all(statuses))
    settings_total = len(settings_agg)

    return device_pass + settings_pass, device_count + settings_total


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
    for td_id, (text, css_class) in scores.items():
        pattern = rf'(<td[^>]*id="{re.escape(td_id)}"[^>]*class=")[^"]*("[^>]*>)([^<]*)(</td>)'
        def replacer(m):
            return f'{m.group(1)}{css_class}{m.group(2)}{text}{m.group(4)}'
        html, n = re.subn(pattern, replacer, html, count=1)
        if n == 0:
            pattern2 = rf'(<td[^>]*id="{re.escape(td_id)}"[^>]*>)([^<]*)(</td>)'
            def replacer2(m):
                return f'{m.group(1)}{text}{m.group(3)}'
            html = re.sub(pattern2, replacer2, html, count=1)
    return html


def main():
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

    scores = {}
    for browser_key, browser_json in BROWSER_MAP.items():
        for os_name in OS_MAP:
            platform_data = data[os_name]
            entries = [
                t for t in platform_data.get("all_tests", [])
                if t.get("browser") == browser_json
                and not t.get("incognito")
                and not t.get("nightly")
            ]
            if not entries:
                for prefix in ["statepartitioning", "fingerprinting", "tracking"]:
                    scores[f"{prefix}_{browser_key}_{os_name}"] = ("", "")
                continue

            preferred = select_preferred(entries)

            # State partitioning: aggregate (fail if any)
            nf, tot = score_aggregated(entries, ["supercookies"])
            text = f"{nf}/{tot}" if tot else ""
            scores[f"statepartitioning_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

            # Fingerprinting: website-style
            nf, tot = score_fingerprinting(entries)
            text = f"{nf}/{tot}" if tot else ""
            scores[f"fingerprinting_{browser_key}_{os_name}"] = (text, get_class(nf, tot))

            # Tracking: macos-26 single run
            if preferred:
                nf, tot = score_single(preferred, [
                    "navigation", "query", "trackers", "tracker_cookies",
                    "session_1p", "session_3p",
                ])
                text = f"{nf}/{tot}" if tot else ""
                scores[f"tracking_{browser_key}_{os_name}"] = (text, get_class(nf, tot))
            else:
                scores[f"tracking_{browser_key}_{os_name}"] = ("", "")

    html_path = Path("browser_comparison.htm")
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("\r\n", "\n").replace("\r", "\n")
    new_html = update_html(html, scores)
    html_path.write_text(new_html, encoding="utf-8", newline="\n")

    LAST_GIT_FILE.write_text(current_git + "\n")
    print("Updated browser_comparison.htm and .privacytests_last_git")


if __name__ == "__main__":
    main()
