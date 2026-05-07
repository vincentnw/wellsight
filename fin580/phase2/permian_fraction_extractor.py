"""
Permian production-share extractor (10-K segment data via SEC EDGAR).

Per Pre-Code Action Item 15: per company per fiscal year, extract trailing-12-
month Permian production fraction from segment-reporting and operational-
highlights sections of the 10-K. Required input to:

    - The point-in-time equity-universe constructor's >= 30% Permian threshold
      (DL #44).
    - The drilling-to-revenue forecast model's Permian-revenue-share scaling
      (DL #47, code/phase2/revenue_forecast.py DEFAULT_PERMIAN_REVENUE_SHARE).

This is a reference / spec implementation: it locates the most recent 10-K per
company per fiscal year via the SEC EDGAR submissions API, downloads the filing
index, and parses the operational-highlights table where possible. For
narrative-style segment disclosures (most pure-play and integrated names),
extraction needs an LLM pass; for table-style, a regex pass is enough. The full
50-extraction job is left as user-side homework or a downstream LLM-driven
batch — for the design demonstration we provide:

    1. The deterministic SEC EDGAR fetch and 10-K resolution function.
    2. A simple regex extractor for table-style operational highlights.
    3. A scaffolded LLM-extraction interface (not wired to a live API in this
       file; the prompt is documented).
    4. A merged output schema and CSV writer.

Per the project-goal alignment (DL #48), the design demonstrates an end-to-end
extraction path. Production hardening would tighten the regexes, add LLM
batch-extraction, and verify each value manually.
"""

from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import ssl

try:
    import certifi  # type: ignore
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl._create_unverified_context()

PHASE1_OUTPUT = Path(__file__).resolve().parents[2] / "phase1" / "output"

# SEC EDGAR rate limit: 10 req/sec, identify with email per fair-access policy.
SEC_USER_AGENT = "FIN580-Project Vincent Wibowo vincentnw24@gmail.com"

# Universe to extract for. CIKs come from SEC EDGAR ticker-to-CIK lookup.
TICKER_CIK = {
    "FANG": "0001539838",
    "EOG":  "0000821189",
    "DVN":  "0001090012",
    "CTRA": "0000858470",  # Coterra Energy (formerly Cabot Oil & Gas)
    "OXY":  "0000797468",
    "MTDR": "0001520006",
    "PR":   "0001658566",  # Permian Resources (formerly Centennial Resource Dev)
    "OVV":  "0001792580",  # Ovintiv (formerly Encana)
    "SM":   "0000893538",
    "CRGY": "0001866175",
}


# ---------------------------------------------------------------------------
# SEC EDGAR fetch helpers
# ---------------------------------------------------------------------------


def _http_get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": SEC_USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=30, context=_SSL_CTX) as r:
        return r.read()


def list_10k_filings(cik: str) -> list[dict]:
    """Return list of {accession_number, filing_date, primary_document} for
    all 10-K filings of `cik`, sorted newest first."""
    cik_no_pad = str(int(cik))
    url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    data = json.loads(_http_get(url))
    out: list[dict] = []
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accs = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    docs = recent.get("primaryDocument", [])
    for form, acc, fdate, doc in zip(forms, accs, dates, docs):
        if form != "10-K":
            continue
        out.append({"accession_number": acc, "filing_date": fdate, "primary_document": doc})
    return out


def fetch_10k_text(cik: str, accession_number: str, primary_document: str) -> str:
    """Download the primary document of a 10-K filing as plain text."""
    acc_no_dashes = accession_number.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dashes}/"
    raw = _http_get(urljoin(base, primary_document))
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


# ---------------------------------------------------------------------------
# Permian production-share extractors
# ---------------------------------------------------------------------------


@dataclass
class PermianFractionRecord:
    ticker: str
    fiscal_year: int
    permian_production_fraction_ttm: float | None
    method: str  # 'regex_table' | 'llm_narrative' | 'manual' | 'pure_play_default'
    source_filing_date: str
    notes: str = ""


PURE_PLAY_DEFAULT = {"FANG": 1.00, "MTDR": 1.00, "PR": 1.00}


def regex_extract_permian_fraction(text: str) -> float | None:
    """Look for a stated Permian percentage of production in the operational
    highlights or segment-reporting section. Returns None if no clean match."""
    candidates = re.findall(
        r"Permian[^\.]{0,200}?(\d{1,3}(?:\.\d+)?)\s*%[^\.]{0,80}?(?:production|output|barrels|boe)",
        text, flags=re.IGNORECASE,
    )
    for c in candidates:
        try:
            f = float(c) / 100.0
            if 0.05 <= f <= 1.0:
                return f
        except ValueError:
            continue
    return None


def llm_extract_permian_fraction_prompt(filing_year_label: str, snippet: str) -> str:
    """Documented prompt template for an LLM-driven extraction pass.

    Wire to your preferred provider (Gemini 2.5 Flash, Llama 70B via Groq,
    DeepSeek R1 via Cerebras) at temperature 0; require structured output."""
    return f"""You are a financial data extractor. Given the following excerpt
from a US oil and gas company's 10-K for fiscal year {filing_year_label},
identify the share of trailing-12-month total production attributable to the
Permian Basin (Delaware + Midland sub-basins).

Return a single JSON object with keys:
  - "permian_production_fraction_ttm": a number between 0 and 1, or null if
    not stated.
  - "supporting_quote": the verbatim sentence(s) that support the number.

EXCERPT:
{snippet[:6000]}

Respond with the JSON object only.
"""


# ---------------------------------------------------------------------------
# Per-company extraction
# ---------------------------------------------------------------------------


def extract_for_ticker(
    ticker: str,
    target_fiscal_years: Iterable[int] = (2020, 2021, 2022, 2023, 2024),
) -> list[PermianFractionRecord]:
    out: list[PermianFractionRecord] = []
    cik = TICKER_CIK.get(ticker)
    if cik is None:
        return out

    if ticker in PURE_PLAY_DEFAULT:
        for fy in target_fiscal_years:
            out.append(PermianFractionRecord(
                ticker=ticker, fiscal_year=fy,
                permian_production_fraction_ttm=PURE_PLAY_DEFAULT[ticker],
                method="pure_play_default",
                source_filing_date="",
                notes="Pure-play Permian operator; assumed 100% Permian.",
            ))
        return out

    try:
        filings = list_10k_filings(cik)
    except Exception as e:  # noqa: BLE001
        for fy in target_fiscal_years:
            out.append(PermianFractionRecord(
                ticker=ticker, fiscal_year=fy,
                permian_production_fraction_ttm=None,
                method="manual",
                source_filing_date="",
                notes=f"EDGAR fetch failed: {e!r}. Hand-populate from 10-K.",
            ))
        return out

    for fy in target_fiscal_years:
        match = next(
            (f for f in filings if f["filing_date"][:4] == str(fy + 1)),
            None,
        )
        if match is None:
            out.append(PermianFractionRecord(
                ticker=ticker, fiscal_year=fy,
                permian_production_fraction_ttm=None,
                method="manual",
                source_filing_date="",
                notes=f"No 10-K filed in CY {fy + 1}.",
            ))
            continue
        try:
            text = fetch_10k_text(cik, match["accession_number"], match["primary_document"])
            time.sleep(0.15)  # SEC fair-access throttle
        except Exception as e:  # noqa: BLE001
            out.append(PermianFractionRecord(
                ticker=ticker, fiscal_year=fy,
                permian_production_fraction_ttm=None,
                method="manual",
                source_filing_date=match["filing_date"],
                notes=f"Document fetch failed: {e!r}.",
            ))
            continue
        pf = regex_extract_permian_fraction(text)
        if pf is not None:
            out.append(PermianFractionRecord(
                ticker=ticker, fiscal_year=fy,
                permian_production_fraction_ttm=pf,
                method="regex_table",
                source_filing_date=match["filing_date"],
                notes="Regex match on '<X>% ... production'.",
            ))
        else:
            out.append(PermianFractionRecord(
                ticker=ticker, fiscal_year=fy,
                permian_production_fraction_ttm=None,
                method="llm_narrative",
                source_filing_date=match["filing_date"],
                notes="Regex did not match; pass excerpt to LLM "
                      "with `llm_extract_permian_fraction_prompt`.",
            ))
    return out


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_csv(records: list[PermianFractionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "ticker", "fiscal_year", "permian_production_fraction_ttm",
            "method", "source_filing_date", "notes",
        ])
        for r in records:
            w.writerow([
                r.ticker, r.fiscal_year,
                "" if r.permian_production_fraction_ttm is None else f"{r.permian_production_fraction_ttm:.4f}",
                r.method, r.source_filing_date, r.notes,
            ])


def main(tickers: Iterable[str] = TICKER_CIK.keys()) -> None:
    records: list[PermianFractionRecord] = []
    for t in tickers:
        records.extend(extract_for_ticker(t))
    out = PHASE1_OUTPUT / "permian_fraction.csv"
    write_csv(records, out)
    print(f"Wrote {out} with {len(records)} rows")
    methods: dict[str, int] = {}
    for r in records:
        methods[r.method] = methods.get(r.method, 0) + 1
    for m, n in methods.items():
        print(f"  method={m}: {n}")


if __name__ == "__main__":
    main()
