#!/usr/bin/env python3
"""
Update desktop environment market share percentages in de_comparison.htm.
Sources: Arch pkgstats, GamingOnLinux, linux-hardware.org, Fedora Count Me, Debian PopCon.

Uses absolute percentages as shown on each site (not relative among the 8 DEs).
"""

import gzip
import json
import re
import sqlite3
import tempfile
import urllib.parse
import urllib.request
from datetime import date, timedelta
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

# linux-hardware.org name mapping (sum absolute percents of variants)
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

# Debian packages (task packages where available; GNOME includes flashback)
DEBIAN_PACKAGES = {
    "gnome": ["task-gnome-desktop", "task-gnome-flashback-desktop"],
    "plasma": ["task-kde-desktop"],
    "xfce": ["task-xfce-desktop"],
    "mate": ["task-mate-desktop"],
    "cinnamon": ["task-cinnamon-desktop"],
    "lxqt": ["task-lxqt-desktop"],
    "budgie": ["budgie-desktop"],
    "cosmic": ["cosmic-session"],  # may be 0 / not in repo
}
DEBIAN_TOTAL_PROXY = "task-desktop"
DEBIAN_POPCON_API = "https://qa.debian.org/cgi-bin/popcon-data"

# Fedora Count Me
FEDORA_URL = "https://data-analysis.fedoraproject.org/csv-reports/countme/totals.db.gz"
RECENT_WEEKS = 4  # recent weeks to consider


def fetch(url: str, timeout: int = 60) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "eylenburg-de-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None


def fetch_bytes(url: str, timeout: int = 120) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "eylenburg-de-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
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
    """Use the absolute popularity percentage from Arch pkgstats."""
    results = {}
    for key, pkg in ARCH_PACKAGES.items():
        data = fetch(f"https://pkgstats.archlinux.de/api/packages/{pkg}")
        if not data:
            return None
        try:
            j = json.loads(data)
            results[key] = float(j.get("popularity", 0))
        except Exception:
            return None
    return results


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
    spoiler_start = html.find('<details class="spoiler_container">', idx)
    if spoiler_start < 0:
        return None
    spoiler_end = html.find("</details>", spoiler_start)
    spoiler = html[spoiler_start:spoiler_end]
    results = {}
    for m in re.finditer(r"<strong>([^<]+)</strong>:\s*\d+\s*\(([\d.]+)%\)", spoiler):
        name, pct = m.group(1), float(m.group(2))
        key = GOL_NAMES.get(name)
        if key:
            results[key] = pct
    return results if results else None


def fetch_lhw() -> dict[str, float] | None:
    """Use absolute percents from linux-hardware.org and sum variants."""
    html = fetch("https://linux-hardware.org/?view=os_de&page_size=all")
    if not html:
        return None
    idx = html.find("<table class='tbl stats highlight'>")
    if idx < 0:
        print("Could not find stats table on linux-hardware.org")
        return None
    table_end = html.find("</table>", idx)
    table = html[idx:table_end]
    # Parse name and absolute percent
    raw = {}
    for m in re.finditer(
        r"<a class='plink name'[^>]*>([^<]+)</a></td>\s*<td class='cnt[^']*'>[\d,]+</td>\s*<td class='percent[^']*'>([\d.]+)%</td>",
        table,
    ):
        name = m.group(1).strip()
        pct = float(m.group(2))
        raw[name] = pct
    if not raw:
        return None
    # Sum absolute percents for grouped variants
    grouped = {}
    for key, names in LHW_GROUPS.items():
        grouped[key] = sum(raw.get(n, 0) for n in names)
    return grouped


def classify_fedora(os_variant: str) -> str | None:
    """Map Fedora os_variant to one of our DE keys, or None to exclude from both numerator and denominator."""
    v = (os_variant or "").lower()

    # Exclude Bazzite (no fixed default DE) and pure non-desktop variants
    if "bazzite" in v:
        return None
    if any(x in v for x in ("server", "iot", "cloud", "coreos", "container", "toolbox", "toolbx", "generic", "unknown")):
        return None

    # Main desktop / Atomic mappings
    if any(x in v for x in ("silverblue", "bluefin", "workstation")):
        return "gnome"
    if any(x in v for x in ("kinoite", "aurora", "kde", "plasma")):
        return "plasma"
    if "xfce" in v:
        return "xfce"
    if "mate" in v:
        return "mate"
    if "cinnamon" in v:
        return "cinnamon"
    if "lxqt" in v:
        return "lxqt"
    if "budgie" in v:
        return "budgie"
    if "cosmic" in v:
        return "cosmic"

    # Other known desktops count in the denominator
    if any(x in v for x in ("sway", "i3", "lxde", "phosh", "lomiri", "deepin", "pantheon", "onyx", "sericea")):
        return "other"

    # Anything else is excluded
    return None


def fetch_fedora() -> dict[str, float] | None:
    """Download Fedora Count Me totals.db.gz, compute DE percentages, discard data."""
    print("Downloading Fedora Count Me data...")
    raw = fetch_bytes(FEDORA_URL)
    if not raw:
        return None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            gz_path = Path(tmpdir) / "totals.db.gz"
            db_path = Path(tmpdir) / "totals.db"
            gz_path.write_bytes(raw)
            with gzip.open(gz_path, "rb") as f_in, open(db_path, "wb") as f_out:
                f_out.write(f_in.read())

            con = sqlite3.connect(db_path)
            cur = con.cursor()

            cur.execute("SELECT MAX(weeknum) FROM countme_totals")
            max_week = cur.fetchone()[0]
            if max_week is None:
                return None
            max_week = int(max_week)
            min_week = max_week - RECENT_WEEKS + 1

            # Approximate unique systems: max hits per (os_variant, os_arch, sys_age) over recent weeks
            # (each host reports once per week; max across repos approximates hosts)
            cur.execute(
                """
                SELECT os_variant, MAX(hits)
                FROM countme_totals
                WHERE weeknum >= ? AND weeknum <= ?
                  AND os_name LIKE '%Fedora%'
                GROUP BY os_variant, os_arch, sys_age
                """,
                (min_week, max_week),
            )
            rows = cur.fetchall()
            con.close()

            counts: dict[str, int] = {k: 0 for k in COLUMNS}
            other = 0
            for os_variant, hits in rows:
                cls = classify_fedora(os_variant or "")
                if cls is None:
                    continue
                if cls in counts:
                    counts[cls] += hits
                else:
                    other += hits

            total = sum(counts.values()) + other
            if total == 0:
                return None

            return {k: 100.0 * counts[k] / total for k in COLUMNS}
    except Exception as e:
        print(f"Fedora processing failed: {e}")
        return None
    # TemporaryDirectory is cleaned up automatically; no leftover files


def fetch_debian() -> dict[str, float | str] | None:
    """Query Debian PopCon for the relevant packages; use task-desktop as denominator."""
    print("Querying Debian PopCon...")
    all_pkgs = []
    for pkgs in DEBIAN_PACKAGES.values():
        all_pkgs.extend(pkgs)
    all_pkgs.append(DEBIAN_TOTAL_PROXY)

    today = date.today()
    from_date = (today - timedelta(days=30)).isoformat()
    to_date = today.isoformat()

    params = {
        "packages": " ".join(all_pkgs),
        "from_date": from_date,
        "to_date": to_date,
    }
    url = DEBIAN_POPCON_API + "?" + urllib.parse.urlencode(params)
    data_str = fetch(url)
    if not data_str:
        return None

    try:
        data = json.loads(data_str)
    except Exception:
        return None

    inst = {}
    for pkg in all_pkgs:
        series = data.get(pkg, {})
        if not series:
            inst[pkg] = 0
            continue
        latest_day = max(series.keys())
        entry = series[latest_day]
        inst[pkg] = (
            int(entry.get("vote", 0))
            + int(entry.get("old", 0))
            + int(entry.get("recent", 0))
            + int(entry.get("no_files", 0))
        )

    total = inst.get(DEBIAN_TOTAL_PROXY, 0)
    if total == 0:
        return None

    results: dict[str, float | str] = {}
    for de, pkgs in DEBIAN_PACKAGES.items():
        count = sum(inst.get(pkg, 0) for pkg in pkgs)
        if de == "cosmic" and count == 0:
            results[de] = "not in repo"
        else:
            results[de] = 100.0 * count / total
    return results


def update_row(html: str, row_id: str, percentages: dict[str, float | str]) -> str:
    """Replace the 8 DE <td> cells in the given row.
    Values may be floats (percentages) or special strings (e.g. 'not in repo').
    """
    pattern = rf'(<tr id="{row_id}">.*?</tr>)'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        print(f"Row {row_id} not found")
        return html
    row = m.group(1)
    tds = list(re.finditer(r"<td[^>]*>.*?</td>", row, re.DOTALL))
    if len(tds) < 9:
        print(f"Row {row_id} has unexpected structure ({len(tds)} tds)")
        return html
    new_row = row
    offset = 0
    for i, col in enumerate(COLUMNS):
        td = tds[i + 1]
        val = percentages.get(col, 0)
        if isinstance(val, str):
            new_td = f"<td>{val}</td>"
        else:
            pct = float(val)
            cls = mktshare_class(pct)
            text = f"{pct:.1f}%"
            new_td = f'<td class="{cls}">{text}</td>'
        start = td.start() + offset
        end = td.end() + offset
        new_row = new_row[:start] + new_td + new_row[end:]
        offset += len(new_td) - (td.end() - td.start())
    return html[:m.start()] + new_row + html[m.end():]


def main():
    html_path = Path(__file__).resolve().parent.parent / "de_comparison.htm"
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("\r\n", "\n").replace("\r", "\n")

    changed = False

    arch = fetch_arch()
    if arch:
        print("Arch:", {k: f"{v:.1f}%" for k, v in arch.items()})
        html = update_row(html, "marketshare_arch", arch)
        changed = True
    else:
        print("Arch: skipped (fetch failed)")

    gol = fetch_gol()
    if gol:
        print("GamingOnLinux:", {k: f"{v:.1f}%" for k, v in gol.items()})
        html = update_row(html, "marketshare_gamingonlinux", gol)
        changed = True
    else:
        print("GamingOnLinux: skipped (fetch failed)")

    lhw = fetch_lhw()
    if lhw:
        print("linux-hardware.org:", {k: f"{v:.1f}%" for k, v in lhw.items()})
        html = update_row(html, "marketshare_linuxhardware", lhw)
        changed = True
    else:
        print("linux-hardware.org: skipped (fetch failed)")

    fedora = fetch_fedora()
    if fedora:
        print("Fedora:", {k: f"{v:.1f}%" for k, v in fedora.items()})
        html = update_row(html, "marketshare_fedora", fedora)
        changed = True
    else:
        print("Fedora: skipped (fetch/processing failed)")

    debian = fetch_debian()
    if debian:
        print("Debian:", {k: (f"{v:.1f}%" if isinstance(v, float) else v) for k, v in debian.items()})
        html = update_row(html, "marketshare_debian", debian)
        changed = True
    else:
        print("Debian: skipped (fetch failed)")

    if changed:
        html_path.write_text(html, encoding="utf-8", newline="\n")
        print("Updated de_comparison.htm")
    else:
        print("No updates made")


if __name__ == "__main__":
    main()
