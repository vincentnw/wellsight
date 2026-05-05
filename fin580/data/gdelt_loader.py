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
    fetch_status = "ok"
    fetch_error: str | None = None
    # Retry-with-backoff on 429 / network errors.
    import time as _t
    backoffs = [5, 15, 45, 120]
    last_err: Exception | None = None
    for attempt in range(len(backoffs) + 1):
        try:
            req = Request(url, headers={"User-Agent": "FIN580/1.0"})
            with urlopen(req, timeout=30, context=_SSL_CTX) as r:
                payload = json.loads(r.read())
            for a in payload.get("articles", []):
                try:
                    pd_dt = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").date()
                except (KeyError, ValueError):
                    continue
                if pd_dt > T_minus_14:
                    continue  # Hard cutoff
                out.append(
                    GdeltArticle(
                        article_id=a.get("url", "")[-32:] or str(len(out)),
                        publish_date=pd_dt,
                        title=a.get("title", ""),
                        url=a.get("url", ""),
                    )
                )
            last_err = None
            break
        except Exception as e:
            last_err = e
            if attempt < len(backoffs):
                _t.sleep(backoffs[attempt])
                continue
    if last_err is not None:
        fetch_status = "error"
        fetch_error = f"{type(last_err).__name__}: {str(last_err)[:200]}"
        out = []

    # Persist articles array (legacy schema, list of article dicts).
    # Sidecar metadata file records fetch status so callers can distinguish
    # "API failed" (out=[] but error logged) from "API succeeded with zero hits".
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
    meta_file = cache_file.with_suffix(".meta.json")
    meta_file.write_text(json.dumps({
        "ticker": ticker,
        "prev_earnings_date": prev_earnings_date.isoformat(),
        "T_minus_14": T_minus_14.isoformat(),
        "n_articles": len(out),
        "fetch_status": fetch_status,
        "fetch_error": fetch_error,
        "query_term": query_term,
    }, indent=2))
    return out
