#!/usr/bin/env python3
"""
Update Artificial Analysis Intelligence Index scores in ai_search_maps.htm.

Requires AA_API_KEY environment variable (set as a GitHub Actions secret).
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

import requests

HTML_PATH = Path("ai_search_maps.htm")
API_URL = "https://artificialanalysis.ai/api/v2/language/models/free"

# HTML id suffix -> list of creator name aliases (case-insensitive match)
CREATOR_MAP = {
    "chatgpt": ["OpenAI"],
    "claude": ["Anthropic"],
    "gemini": ["Google", "Google DeepMind"],
    "grok": ["xAI", "SpaceXAI", "xAI (SpaceXAI)"],
    "meta": ["Meta", "Meta Superintelligence Labs", "Meta AI"],
    "mistral": ["Mistral", "Mistral AI"],
    "deepseek": ["DeepSeek"],
    "kimi": ["Moonshot AI", "Kimi", "Moonshot"],
    "mimo": ["Xiaomi", "MiMo"],
    "minimax": ["MiniMax"],
    "qwen": ["Alibaba", "Qwen", "Alibaba (Qwen)"],
    "glm": ["Z AI", "Z.ai", "Zhipu", "Zhipu AI", "Z AI (Zhipu)"],
}


def get_api_key() -> str:
    key = os.environ.get("AA_API_KEY")
    if not key:
        print("Error: AA_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return key


def fetch_models(api_key: str) -> list[dict]:
    headers = {"x-api-key": api_key}
    all_models = []
    page = 1
    while True:
        resp = requests.get(API_URL, headers=headers, params={"page": page}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data") or []
        all_models.extend(models)
        pagination = data.get("pagination") or {}
        if not pagination.get("has_more"):
            break
        page += 1
        if page > 20:  # safety
            break
    return all_models


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def find_top_models(models: list[dict]) -> dict[str, tuple[str, float]]:
    """Return {html_id_suffix: (model_name, score)} for each tracked creator."""
    # Build reverse lookup: normalized alias -> html id
    alias_to_id = {}
    for html_id, aliases in CREATOR_MAP.items():
        for alias in aliases:
            alias_to_id[normalize(alias)] = html_id

    best: dict[str, tuple[str, float]] = {}

    for model in models:
        creator_obj = model.get("model_creator") or {}
        creator_name = creator_obj.get("name") or ""
        if not creator_name:
            continue

        html_id = alias_to_id.get(normalize(creator_name))
        if not html_id:
            continue

        evaluations = model.get("evaluations") or {}
        score = evaluations.get("artificial_analysis_intelligence_index")
        if score is None:
            continue

        try:
            score = float(score)
        except (TypeError, ValueError):
            continue

        name = model.get("name") or model.get("slug") or "Unknown"
        current = best.get(html_id)
        if current is None or score > current[1]:
            best[html_id] = (name, score)

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


def update_html(html: str, tops: dict[str, tuple[str, float]]) -> str:
    today = date.today().isoformat().replace("-", ".")  # e.g. 2026.11.24

    # Update date
    html = re.sub(
        r'(<span\s+id="aaii_date">)[^<]*(</span>)',
        rf"\g<1>{today}\g<2>",
        html,
        count=1,
    )

    if not tops:
        print("Warning: no matching models found; only date was updated.")
        return html

    scores = [score for _, score in tops.values()]
    tier_by_score = compute_tiers(scores)

    for html_id, (model_name, score) in tops.items():
        tier = tier_by_score[score]
        # Format score cleanly
        score_str = f"{score:.1f}".rstrip("0").rstrip(".")
        new_content = f"{model_name}: {score_str}"
        new_class = f"tier{tier}"

        # Replace the <td id="aaii_xxx" class="...">...</td>
        pattern = rf'(<td\s+id="aaii_{html_id}"\s+class=")[^"]*(">)[^<]*(</td>)'
        replacement = rf"\g<1>{new_class}\g<2>{new_content}\g<3>"
        html, n = re.subn(pattern, replacement, html, count=1)
        if n == 0:
            print(f'Warning: could not find <td id="aaii_{html_id}"> to update.')
        else:
            print(f"Updated aaii_{html_id}: {new_content} (tier {tier})")

    return html


def main() -> None:
    if not HTML_PATH.exists():
        print(f"Error: {HTML_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()
    print("Fetching models from Artificial Analysis...")
    models = fetch_models(api_key)
    print(f"Received {len(models)} models.")

    tops = find_top_models(models)
    print(f"Found top models for {len(tops)} creators.")

    original = HTML_PATH.read_text(encoding="utf-8")
    updated = update_html(original, tops)

    if updated == original:
        print("No changes detected.")
        return

    HTML_PATH.write_text(updated, encoding="utf-8")
    print("Wrote updated ai_search_maps.htm")


if __name__ == "__main__":
    main()
