"""GDELT article loader with strict T-14 cutoff (spec DL #7, project_overview.md
Agent 4 description).

Uses GDELT 2.0 DOC API with a per-ticker query. Results cached as JSON per
(ticker, prev_earnings_date, T-14)."""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"
GDELT_CACHE_DIR = PHASE1_OUTPUT / "gdelt_cache"
GDELT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    import certifi  # type: ignore

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl._create_unverified_context()


TICKER_QUERY_TERMS = {
    "FANG": "Diamondback Energy",
    "EOG": "EOG Resources",
    "DVN": "Devon Energy",
    "CTRA": "Coterra Energy",
    "OXY": "Occidental Petroleum",
    "MTDR": "Matador Resources",
    "PR": "Permian Resources",
    "OVV": "Ovintiv",
    "SM": "SM Energy",
    "CRGY": "Crescent Energy",
}


@dataclass(frozen=True)
class GdeltArticle:
    article_id: str
    publish_date: date
    title: str
    url: str


def fetch_articles(
    ticker: str,
    prev_earnings_date: date,
    T_minus_14: date,
    max_records: int = 75,
) -> list[GdeltArticle]:
    """Fetch GDELT articles for ticker between prev_earnings_date and T_minus_14.
    Strictly excludes any article with publish_date > T_minus_14."""
    cache_file = (
        GDELT_CACHE_DIR
        / f"{ticker}_{prev_earnings_date.isoformat()}_{T_minus_14.isoformat()}.json"
    )
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        # Codex Audit Round-2 fix: even when reading from cache, defensively
        # re-apply the T-14 cutoff so a manually-edited or wrong-date cache
        # cannot leak post-T articles through the PIT discipline.
        return [
            GdeltArticle(
                a["article_id"],
                date.fromisoformat(a["publish_date"]),
                a["title"],
                a["url"],
            )
            for a in data
            if date.fromisoformat(a["publish_date"]) <= T_minus_14
        ]

    query_term = TICKER_QUERY_TERMS.get(ticker, ticker)
    params = {
        "query": f'"{query_term}" oil drilling',
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max_records,
        "startdatetime": prev_earnings_date.strftime("%Y%m%d") + "000000",
        "enddatetime": T_minus_14.strftime("%Y%m%d") + "235959",
    }
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{urlencode(params)}"
    out: list[GdeltArticle] = []
    try:
        req = Request(url, headers={"User-Agent": "FIN580/1.0"})
        with urlopen(req, timeout=30, context=_SSL_CTX) as r:
            payload = json.loads(r.read())
        for a in payload.get("articles", []):
            try:
                pd = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").date()
            except (KeyError, ValueError):
                continue
            if pd > T_minus_14:
                continue  # Hard cutoff
            out.append(
                GdeltArticle(
                    article_id=a.get("url", "")[-32:] or str(len(out)),
                    publish_date=pd,
                    title=a.get("title", ""),
                    url=a.get("url", ""),
                )
            )
    except Exception:
        # Synthetic fallback: empty list if network fails
        out = []

    cache_file.write_text(
        json.dumps(
            [
                {
                    "article_id": a.article_id,
                    "publish_date": a.publish_date.isoformat(),
                    "title": a.title,
                    "url": a.url,
                }
                for a in out
            ],
            indent=2,
        )
    )
    return out
