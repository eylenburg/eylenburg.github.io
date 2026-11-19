#!/usr/bin/env python3
"""
Update browser market share percentages in browser_comparison.htm
from OpenStatsLab/statcounterdata (parsed StatCounter data).

Updates only the text values (not the charts).
"""

import json
import re
import urllib.request
from pathlib import Path

JSON_URL = "https://raw.githubusercontent.com/OpenStatsLab/statcounterdata/main/parsed/browsers/all.json"

# Map of HTML id -> key in the JSON
BROWSER_IDS = {
    "firefox_share": "Firefox",
    "safari_share": "Safari",
    "chrome_share": "Chrome",
    "edge_share": "Edge",
    "opera_share": "Opera",
    "brave_share": "Brave",
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "eylenburg-browser-share-updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    data = fetch_json(JSON_URL)
    if not data:
        print("No data fetched. Exiting.")
        return

    # Latest month key is the last one (YYYY-MM)
    latest_key = list(data.keys())[-1]
    latest = data[latest_key]
    print(f"Latest data: {latest_key}")

    # Format date as MM/YYYY
    year, month = latest_key.split("-")
    date_str = f"{month}/{year}"

    html_path = Path("browser_comparison.htm")
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("\r\n", "\n").replace("\r", "\n")

    # Update the date
    html, n = re.subn(
        r'(<span id="browser_share_date">)[^<]*(</span>)',
        rf'\g<1>{date_str}\g<2>',
        html,
        count=1,
    )
    if n:
        print(f"Updated date to {date_str}")
    else:
        print("Warning: browser_share_date not found")

    # Update each browser share
    for td_id, json_key in BROWSER_IDS.items():
        value = latest.get(json_key)
        if value is None:
            print(f"Warning: {json_key} not in data, skipping {td_id}")
            continue
        text = f"{value:.2f}%"
        pattern = rf'(<td[^>]*id="{re.escape(td_id)}"[^>]*>)[^<]*(</td>)'
        html, n = re.subn(pattern, rf'\g<1>{text}\g<2>', html, count=1)
        if n:
            print(f"Updated {td_id}: {text}")
        else:
            print(f"Warning: {td_id} not found")

    html_path.write_text(html, encoding="utf-8", newline="\n")
    print("Updated browser_comparison.htm")


if __name__ == "__main__":
    main()
