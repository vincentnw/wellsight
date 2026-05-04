"""Build paper_pdf/paper.pdf from docs/paper/*.md.

Concatenates the 14 numbered sections in order, renders Markdown to HTML,
then converts the HTML to PDF via xhtml2pdf (pure-Python, no system deps).
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SECTIONS_DIR = ROOT / "docs" / "paper"
OUT_PDF = ROOT / "paper_pdf" / "paper.pdf"


def _ordered_sections() -> list[Path]:
    files = sorted(SECTIONS_DIR.glob("*.md"))
    return [
        f for f in files
        if re.match(r"^\d{2}-", f.name) and not f.name.startswith("00-")
    ]


def _md_to_html(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )


CSS = """
@page { size: letter; margin: 0.85in 0.75in; }
body { font-family: 'Times New Roman', Times, serif; font-size: 10.5pt; line-height: 1.4; }
h1 { font-size: 18pt; margin-top: 22pt; margin-bottom: 8pt; page-break-before: always; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 13pt; margin-top: 14pt; margin-bottom: 5pt; }
h3 { font-size: 11.5pt; margin-top: 10pt; margin-bottom: 4pt; }
p { margin: 5pt 0; text-align: justify; }
table { border-collapse: collapse; margin: 8pt 0; font-size: 9.5pt; width: 100%; }
th, td { border: 1px solid #888; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background-color: #eee; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 9.5pt; background: #f3f3f3; padding: 0 2pt; }
pre { background: #f3f3f3; padding: 6pt; font-size: 9pt; white-space: pre-wrap; }
ul, ol { margin: 4pt 0 4pt 18pt; }
li { margin: 2pt 0; }
hr { border: none; border-top: 1px solid #aaa; margin: 12pt 0; }
"""


def main() -> None:
    sections = _ordered_sections()
    if not sections:
        raise SystemExit(f"No section files found in {SECTIONS_DIR}")

    parts = []
    for f in sections:
        parts.append(_md_to_html(f.read_text(encoding="utf-8")))
    body_html = "\n<hr/>\n".join(parts)

    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{body_html}</body></html>"""

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    from xhtml2pdf import pisa
    with open(OUT_PDF, "wb") as out:
        result = pisa.CreatePDF(src=html_doc, dest=out, encoding="utf-8")
    if result.err:
        raise SystemExit(f"PDF build failed with {result.err} errors")
    print(f"Wrote {OUT_PDF} ({OUT_PDF.stat().st_size/1024:.1f} KB) "
          f"from {len(sections)} sections")


if __name__ == "__main__":
    main()
