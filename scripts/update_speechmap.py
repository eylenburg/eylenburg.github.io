#!/usr/bin/env python3
"""
Update SpeechMap Free Speech Index scores in ai_search_maps.htm.

Fetches the lab leaderboard from https://speechmap.ai/labs/ and writes each
tracked lab's Index (time-weighted average, not Peak) into the matching
speechmap_* cell.
"""

import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = REPO_ROOT / "ai_search_maps.htm"
LABS_URL = "https://speechmap.ai/labs/"
USER_AGENT = (
    "eylenburg.github.io speechmap updater "
    "(https://github.com/eylenburg/eylenburg.github.io)"
)

# HTML id suffix -> SpeechMap lab slugs and display-name aliases
# (case-insensitive). Slugs come from /labs/<slug>/ on speechmap.ai.
LAB_MAP = {
    "chatgpt": {"slugs": ["openai"], "names": ["OpenAI"]},
    "claude": {"slugs": ["anthropic"], "names": ["Anthropic"]},
    "gemini": {"slugs": ["google"], "names": ["Google DeepMind", "Google"]},
    "grok": {"slugs": ["x-ai"], "names": ["xAI"]},
    "meta": {"slugs": ["meta"], "names": ["Meta"]},
    "mistral": {"slugs": ["mistralai"], "names": ["Mistral AI", "Mistral"]},
    "deepseek": {"slugs": ["deepseek"], "names": ["DeepSeek"]},
    "kimi": {"slugs": ["moonshotai"], "names": ["Moonshot AI", "Moonshot", "Kimi"]},
    "ling": {"slugs": ["inclusionai"], "names": ["InclusionAI", "Ling"]},
    "mimo": {"slugs": ["xiaomi"], "names": ["Xiaomi", "MiMo"]},
    "minimax": {"slugs": ["minimax"], "names": ["MiniMax"]},
    "qwen": {"slugs": ["alibaba"], "names": ["Alibaba", "Qwen"]},
    "glm": {"slugs": ["z-ai"], "names": ["Zhipu AI", "Z.AI", "Z AI", "Zhipu"]},
}

# Main leaderboard rows include a Peak column; the off-board table does not.
LAB_ROW_RE = re.compile(
    r'<td class="lab-name">\s*'
    r'<a href="/labs/([^"/]+)/?"[^>]*>\s*([^<]+?)\s*</a>\s*'
    r'</td>\s*'
    r'<td class="trend">\s*([\d.]+)\s*</td>\s*'
    r'<td class="peak">',
    re.I | re.S,
)


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def fetch_labs_html() -> str:
    req = urllib.request.Request(
        LABS_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def parse_lab_indexes(html: str) -> list[tuple[str, str, float]]:
    """Return [(slug, display_name, index), ...] from the main leaderboard."""
    rows = []
    for slug, name, score_str in LAB_ROW_RE.findall(html):
        try:
            score = float(score_str)
        except ValueError:
            continue
        rows.append((slug.strip().lower(), name.strip(), score))
    return rows


def match_tracked_labs(rows: list[tuple[str, str, float]]) -> dict[str, float]:
    """Return {html_id_suffix: index} for each tracked lab found on the board."""
    slug_to_id: dict[str, str] = {}
    name_to_id: dict[str, str] = {}
    for html_id, aliases in LAB_MAP.items():
        for slug in aliases["slugs"]:
            slug_to_id[normalize(slug)] = html_id
        for name in aliases["names"]:
            name_to_id[normalize(name)] = html_id

    best: dict[str, float] = {}
    for slug, name, score in rows:
        html_id = slug_to_id.get(normalize(slug)) or name_to_id.get(normalize(name))
        if not html_id:
            continue
        # Keep the first (highest-ranked) match if a lab appears twice.
        if html_id not in best:
            best[html_id] = score
            print(f"Matched {html_id}: {name} ({slug}) = {score:.1f}")

    missing = [html_id for html_id in LAB_MAP if html_id not in best]
    for html_id in missing:
        print(f"Warning: no SpeechMap Index found for {html_id}.")

    return best


def compute_tiers(scores: list[float]) -> dict[float, int]:
    """Map each unique score to a tier 1–7 based on equal absolute ranges.
    Higher score = better = lower tier number.
    """
    if not scores:
        return {}
    min_s = min(scores)
    max_s = max(scores)
    if min_s == max_s:
        return {s: 1 for s in scores}

    span = max_s - min_s
    tier_map = {}
    for s in scores:
        # 0 = best (max), 1 = worst (min)
        ratio = (max_s - s) / span
        # 7 equal bands
        tier = int(ratio * 7) + 1
        tier = min(max(tier, 1), 7)
        tier_map[s] = tier
    return tier_map


def update_html(html: str, scores_by_id: dict[str, float]) -> str:
    today = date.today().isoformat().replace("-", ".")  # e.g. 2026.11.27

    html = re.sub(
        r'(<span\s+id="speechmap_date">)[^<]*(</span>)',
        rf"\g<1>{today}\g<2>",
        html,
        count=1,
    )

    if not scores_by_id:
        print("Warning: no matching labs found; only date was updated.")
        return html

    tier_by_score = compute_tiers(list(scores_by_id.values()))

    for html_id, score in scores_by_id.items():
        tier = tier_by_score[score]
        score_str = f"{score:.1f}"
        new_class = f"tier{tier}"

        pattern = rf'(<td\s+id="speechmap_{html_id}"\s+class=")[^"]*(">)[^<]*(</td>)'
        replacement = rf"\g<1>{new_class}\g<2>{score_str}\g<3>"
        html, n = re.subn(pattern, replacement, html, count=1)
        if n == 0:
            print(f'Warning: could not find <td id="speechmap_{html_id}"> to update.')
        else:
            print(f"Updated speechmap_{html_id}: {score_str} (tier {tier})")

    return html


def main() -> None:
    if not HTML_PATH.exists():
        print(f"Error: {HTML_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching lab leaderboard from {LABS_URL} ...")
    try:
        page = fetch_labs_html()
    except Exception as exc:
        print(f"Error: failed to fetch SpeechMap labs page: {exc}", file=sys.stderr)
        sys.exit(1)

    rows = parse_lab_indexes(page)
    print(f"Parsed {len(rows)} labs from the leaderboard.")
    if not rows:
        print("Error: could not parse any lab Index values from the page.", file=sys.stderr)
        sys.exit(1)

    scores_by_id = match_tracked_labs(rows)
    print(f"Found Index scores for {len(scores_by_id)} of {len(LAB_MAP)} tracked labs.")

    original = HTML_PATH.read_text(encoding="utf-8")
    updated = update_html(original, scores_by_id)

    if updated == original:
        print("No changes detected.")
        return

    HTML_PATH.write_text(updated, encoding="utf-8")
    print("Wrote updated ai_search_maps.htm")


if __name__ == "__main__":
    main()
