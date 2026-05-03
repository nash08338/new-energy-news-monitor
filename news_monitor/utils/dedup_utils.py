# utils/dedup_utils.py
"""
Cross-run title deduplication based on normalized Jaccard similarity.

Flow: load_unused_news → filter_by_fingerprints → DeepSeek
      DeepSeek output  → save_fingerprints

Only stores raw titles + dates in a JSONL file.
Tokens are computed on-the-fly so rules can evolve without migration.
"""

import os
import json
import re
import logging

from .time_utils import now_cst

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop words – common English function words that carry no dedup signal
# ---------------------------------------------------------------------------
STOP_WORDS = frozenset({
    # Common function words
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'been', 'being', 'has', 'have', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'shall', 'can', 'not',
    'its', 'their', 'his', 'her', 'our', 'this', 'that', 'these', 'those',
    'into', 'over', 'after', 'before', 'between', 'under', 'through',
    'up', 'down', 'out', 'off', 'more', 'also', 'just', 'than',
    # News-generic verbs / filler words
    'announces', 'announced', 'announce', 'says', 'said', 'reports',
    'reported', 'report', 'reveals', 'revealed', 'plans', 'planned',
    'aims', 'aimed', 'launches', 'launched', 'launch', 'unveils',
    'unveiled', 'set', 'sets', 'new', 'first', 'latest',
    # Verbs common in financial / energy headlines (noise for dedup)
    'secures', 'secured', 'securing', 'secures',
    'invests', 'invested', 'investing', 'invests',
    'expands', 'expanded', 'expanding', 'expands',
    'develops', 'developed', 'developing', 'develops',
    'builds', 'building', 'built', 'builds',
    'installs', 'installed', 'installing', 'installs',
    'powers', 'powered', 'powering', 'powers',
    'backs', 'backed', 'backing',
    'signs', 'signed', 'signing',
    'wins', 'winning', 'won',
    'gets', 'getting', 'got', 'get',
    'starts', 'starting', 'started',
    'opens', 'opened', 'opening',
    'closes', 'closed', 'closing',
    'seeks', 'seeking', 'sought',
    'moves', 'moving', 'moved',
    'raises', 'raising', 'raised',
    'funds', 'funded', 'funding',
    'leads', 'leading', 'led',
    'drives', 'driving', 'drove', 'driven',
    'supports', 'supported', 'supporting',
    'approves', 'approved', 'approving',
    'adds', 'added', 'adding',
    'cuts', 'cutting', 'cut',
    'hits', 'hitting', 'hit',
    'marks', 'marking', 'marked',
    'boosts', 'boosting', 'boosted',
    'steps', 'stepping', 'stepped',
    'takes', 'taking', 'took', 'taken',
    'makes', 'making', 'made',
    'gives', 'giving', 'gave', 'given',
    'goes', 'going', 'went', 'gone',
    'comes', 'coming', 'came',
    # Filler nouns / adjectives in headlines
    'deal', 'project', 'program', 'programme',
    'initiative', 'effort', 'move', 'step',
    'major', 'big', 'large', 'huge', 'massive',
    'global', 'world', 'worldwide',
    'year', 'years', 'day', 'days', 'week', 'weeks',
    'time', 'times', 'way', 'ways',
    'expansion', 'expand', 'expanded', 'expanding',
})

# ---------------------------------------------------------------------------
# Number normalisation patterns
# ---------------------------------------------------------------------------
# Group 1: leading $ optional, digits with commas
# Group 2: word-scale unit (million / billion / M / B)
_NUM_SCALE_RE = re.compile(
    r'\$?([\d,]+(?:\.\d+)?)\s*(million|billion|[mb])\b', re.I
)
# Large bare numbers (>= 5 digits) – likely money / capacity
_NUM_BARE_RE = re.compile(r'\$?([\d,]{5,})')

_SCALE = {
    'million': 1_000_000, 'm': 1_000_000,
    'billion': 1_000_000_000, 'b': 1_000_000_000,
}

# Capacity units: MW, GW, kW
_CAP_UNIT_RE = re.compile(
    r'(\d+(?:\.\d+)?)(?:\s*)(mw|gw|kw)\b', re.I
)
_CAP_SCALE = {'mw': 1, 'gw': 1000, 'kw': 0.001}



def _normalize_number_match(m):
    """Return a canonical token like N:65000000."""
    num = float(m.group(1).replace(',', ''))
    unit = m.group(2).lower()
    num *= _SCALE.get(unit, 1)
    return f"N:{int(num)}"


def normalize_title(title: str) -> set:
    """
    Convert a news title into a set of dedup tokens.

    Steps: lowercase -> number normalisation -> punctuation strip -> stop-word
    removal -> tokenize.
    """
    text = title.lower()

    # 1) Normalise scaled numbers: "$65M" / "$65 million" -> N:65000000
    text = _NUM_SCALE_RE.sub(_normalize_number_match, text)

    # 2) Normalise large bare numbers: "$65,000,000" -> N:65000000
    text = _NUM_BARE_RE.sub(
        lambda m: f"N:{m.group(1).replace(',', '')}", text
    )

    # 3) Normalise capacity units: "500MW" / "500 MW" / "1GW" -> C:500 / C:1000
    text = _CAP_UNIT_RE.sub(
        lambda m: f"C:{int(float(m.group(1)) * _CAP_SCALE[m.group(2).lower()])}",
        text,
    )

    # 4) Strip non-alphanumeric (keep spaces and N: C: prefixes)
    text = re.sub(r'[^a-z0-9\s:]', ' ', text)

    # 5) Tokenise & remove stop words / single chars
    tokens = set()
    for word in text.split():
        if len(word) > 1 and word not in STOP_WORDS:
            tokens.add(word)

    return tokens


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def jaccard_similarity(tokens_a: set, tokens_b: set) -> float:
    """Standard Jaccard index on two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ---------------------------------------------------------------------------
# Fingerprint file (JSONL)
# ---------------------------------------------------------------------------

# Same directory as used_news.csv
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FINGERPRINT_FILE = os.path.join(_ROOT_DIR, "docs", "used_fingerprints.jsonl")


def load_fingerprints(path=None):
    """
    Load all fingerprint records from JSONL.

    Each line: {"t": "<title>", "d": "YYYY-MM-DD"}

    Returns a list of dicts.
    """
    path = path or FINGERPRINT_FILE
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    logger.info(f"  fingerprint history: {len(records)} records loaded")
    return records


def save_fingerprints(titles, path=None):
    """
    Append new title records to the JSONL file.

    Args:
        titles: list of title strings to persist.
        path: override file path (for testing).
    """
    path = path or FINGERPRINT_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    today = now_cst().strftime("%Y-%m-%d")
    with open(path, "a", encoding="utf-8") as f:
        for title in titles:
            f.write(json.dumps({"t": title, "d": today}, ensure_ascii=False) + "\n")
    logger.info(f"  saved {len(titles)} new fingerprint records")


# ---------------------------------------------------------------------------
# Public API -- filter + save
# ---------------------------------------------------------------------------

def filter_duplicate_news(news_rows, threshold=0.55):
    """
    Remove news rows whose titles are too similar to previously selected ones.

    Args:
        news_rows: list of CSV rows from load_unused_news().
                   Each row is expected to have the title at index 2.
        threshold: Jaccard similarity threshold (default 0.55).

    Returns:
        (filtered_rows, removed_count)
    """
    history = load_fingerprints()
    if not history:
        return news_rows, 0

    # Pre-compute normalised tokens for history (avoid repeated work)
    history_tokens = [
        normalize_title(rec["t"]) for rec in history
    ]

    kept = []
    removed = 0
    for row in news_rows:
        title = row[2]  # title field in news_master.csv
        tokens = normalize_title(title)
        max_sim = 0.0
        for h_tokens in history_tokens:
            sim = jaccard_similarity(tokens, h_tokens)
            if sim > max_sim:
                max_sim = sim
                if max_sim >= threshold:  # early exit
                    break
        if max_sim >= threshold:
            logger.debug(f"  duplicate removed (sim={max_sim:.2f}): {title}")
            removed += 1
        else:
            kept.append(row)

    if removed > 0:
        logger.info(f"  fingerprint dedup: removed {removed}, kept {len(kept)}")
    else:
        logger.info(f"  fingerprint dedup: no duplicates, all {len(kept)} kept")
    return kept, removed
