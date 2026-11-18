#!/usr/bin/env python3
"""
Update desktop environment market share percentages in de_comparison.htm.
Sources: Arch pkgstats, GamingOnLinux, linux-hardware.org.
"""

import re
import urllib.request
from pathlib import Path

# Column order in the HTML table
COLUMNS = ["plasma", "gnome", "xfce", "mate", "cinnamon", "lxqt", "cosmic", "budgie"]

# Arch package names
ARCH_PACKAGES = {
    "plasma": "plasma-workspace",
    "gnome": "gnome-shell",
    "xfce": "xfdesktop",
    "mate": "mate-panel",
    "cinnamon": "cinnamon",
    "lxqt": "lxqt-session",
    "cosmic": "cosmic-session",
    "budgie": "budgie-desktop",
}

# GamingOnLinux name mapping
GOL_NAMES = {
    "KDE Plasma": "plasma",
    "GNOME": "gnome",
    "Xfce": "xfce",
    "MATE": "mate",
    "Cinnamon": "cinnamon",
    "LXQt": "lxqt",
    "COSMIC": "cosmic",
    "Budgie": "budgie",
}

# linux-hardware.org name mapping (sum variants)
LHW_GROUPS = {
    "plasma": ["KDE6", "KDE5", "KDE4", "KDE"],
    "gnome": ["GNOME", "GNOME Flashback", "GNOME Classic"],
    "cinnamon": ["X-Cinnamon", "Cinnamon"],
    "xfce": ["Xfce", "XFCE"],
    "mate": ["MATE"],
    "lxqt": ["LXQt"],
    "cosmic": ["COSMIC"],
    "budgie": ["Budgie"],
}


def fetch(url: str, timeout: int = 30) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "eylenburg-de-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None


def mktshare_class(pct: float) -> str:
    if pct < 1:
        return "mktshare1"
    if pct < 5:
        return "mktshare5"
    if pct < 20:
        return "mktshare20"
    if pct < 30:
        return "mktshare30"
    if pct < 40:
        return "mktshare40"
    return "mktshare100"


def fetch_arch() -> dict[str, float] | None:
    counts = {}
    for key, pkg in ARCH_PACKAGES.items():
        data = fetch(f"https://pkgstats.archlinux.de/api/packages/{pkg}")
        if not data:
            return None
        import json
        try:
            j = json.loads(data)
            counts[key] = j.get("count", 0)
        except Exception:
            return None
    total = sum(counts.values())
    if total == 0:
        return None
    return {k: (v / total) * 100 for k, v in counts.items()}


def fetch_gol() -> dict[str, float] | None:
    html = fetch("https://www.gamingonlinux.com/users/statistics/")
    if not html:
        return None
    # Find the Desktop Environment section and the first spoiler after it
    idx = html.find('id="DesktopEnvironment"')
    if idx < 0:
        idx = html.find(">Desktop Environment<")
    if idx < 0:
        print("Could not find Desktop Environment section on GamingOnLinux")
        return None
    # Find the next spoiler
    spoiler_start = html.find('<details class="spoiler_container">', idx)
    if spoiler_start < 0:
        return None
    spoiler_end = html.find("</details>", spoiler_start)
    spoiler = html[spoiler_start:spoiler_end]
    # Parse <strong>Name</strong>: N (X.XX%)
    results = {}
    for m in re.finditer(r"<strong>([^<]+)</strong>:\s*\d+\s*\(([\d.]+)%\)", spoiler):
        name, pct = m.group(1), float(m.group(2))
        key = GOL_NAMES.get(name)
        if key:
            results[key] = pct
    return results if results else None


def fetch_lhw() -> dict[str, float] | None:
    html = fetch("https://linux-hardware.org/?view=os_de&page_size=all")
    if not html:
        return None
    # Find the stats table
    idx = html.find("<table class='tbl stats highlight'>")
    if idx < 0:
        print("Could not find stats table on linux-hardware.org")
        return None
    table_end = html.find("</table>", idx)
    table = html[idx:table_end]
    # Parse rows: name, count, percent
    raw = {}
    for m in re.finditer(
        r"<a class='plink name'[^>]*>([^<]+)</a></td>\s*<td class='cnt[^']*'>([\d,]+)</td>",
        table,
    ):
        name = m.group(1).strip()
        count = int(m.group(2).replace(",", ""))
        raw[name] = count
    if not raw:
        return None
    # Sum into groups
    grouped = {}
    for key, names in LHW_GROUPS.items():
        grouped[key] = sum(raw.get(n, 0) for n in names)
    total = sum(grouped.values())
    if total == 0:
        return None
    return {k: (v / total) * 100 for k, v in grouped.items()}


def update_row(html: str, row_id: str, percentages: dict[str, float]) -> str:
    """Replace the 8 DE <td> cells in the given row."""
    # Match the row and its content
    pattern = rf'(<tr id="{row_id}">.*?</tr>)'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        print(f"Row {row_id} not found")
        return html
    row = m.group(1)
    # Find all <td ...>...</td> after the first (legend) td
    tds = list(re.finditer(r"<td[^>]*>.*?</td>", row, re.DOTALL))
    if len(tds) < 9:
        print(f"Row {row_id} has unexpected structure ({len(tds)} tds)")
        return html
    # Replace tds 1-8 (0 is the legend)
    new_row = row
    offset = 0
    for i, col in enumerate(COLUMNS):
        td = tds[i + 1]
        pct = percentages.get(col, 0)
        cls = mktshare_class(pct)
        text = f"{pct:.1f}%"
        new_td = f'<td class="{cls}">{text}</td>'
        start = td.start() + offset
        end = td.end() + offset
        new_row = new_row[:start] + new_td + new_row[end:]
        offset += len(new_td) - (td.end() - td.start())
    return html[:m.start()] + new_row + html[m.end():]


def main():
    html_path = Path("de_comparison.htm")
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("\r\n", "\n").replace("\r", "\n")

    changed = False

    # Arch
    arch = fetch_arch()
    if arch:
        print("Arch:", {k: f"{v:.1f}%" for k, v in arch.items()})
        html = update_row(html, "marketshare_arch", arch)
        changed = True
    else:
        print("Arch: skipped (fetch failed)")

    # GamingOnLinux
    gol = fetch_gol()
    if gol:
        print("GamingOnLinux:", {k: f"{v:.1f}%" for k, v in gol.items()})
        html = update_row(html, "marketshare_gamingonlinux", gol)
        changed = True
    else:
        print("GamingOnLinux: skipped (fetch failed)")

    # linux-hardware.org
    lhw = fetch_lhw()
    if lhw:
        print("linux-hardware.org:", {k: f"{v:.1f}%" for k, v in lhw.items()})
        html = update_row(html, "marketshare_linuxhardware", lhw)
        changed = True
    else:
        print("linux-hardware.org: skipped (fetch failed)")

    if changed:
        html_path.write_text(html, encoding="utf-8", newline="\n")
        print("Updated de_comparison.htm")
    else:
        print("No updates made")


if __name__ == "__main__":
    main()
