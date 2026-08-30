"""Convert docs/BUSINESS_PROPOSAL.md into a printable PDF."""
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent
src = ROOT / "docs" / "BUSINESS_PROPOSAL.md"
out = ROOT / "docs" / "ControlPlane_AI_Business_Proposal.pdf"

md = src.read_text(encoding="utf-8")
body = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br"])

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  @page {{
    size: A4;
    margin: 1.8cm 1.6cm 1.8cm 1.6cm;
  }}
  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1e293b;
  }}
  h1 {{
    font-size: 20pt;
    color: #1e2f6e;
    margin: 0 0 8px 0;
    border-bottom: 2px solid #3b5bdb;
    padding-bottom: 6px;
  }}
  h2 {{
    font-size: 13.5pt;
    color: #2a44a6;
    margin: 18px 0 8px 0;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 11.5pt;
    color: #3151c6;
    margin: 12px 0 6px 0;
    page-break-after: avoid;
  }}
  p, li {{
    margin: 0 0 6px 0;
  }}
  blockquote {{
    border-left: 3px solid #3b5bdb;
    margin: 8px 0;
    padding: 4px 0 4px 10px;
    color: #334155;
    font-style: italic;
  }}
  code {{
    font-family: Courier, monospace;
    font-size: 9pt;
    background: #f1f5f9;
  }}
  pre {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 8px;
    font-size: 8.5pt;
    font-family: Courier, monospace;
    white-space: pre-wrap;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 9.5pt;
  }}
  th {{
    background: #eef4ff;
    color: #1e2f6e;
    text-align: left;
    padding: 5px 6px;
    border: 1px solid #cbd5e1;
  }}
  td {{
    padding: 5px 6px;
    border: 1px solid #cbd5e1;
    vertical-align: top;
  }}
  hr {{
    border: none;
    border-top: 1px solid #cbd5e1;
    margin: 16px 0;
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

with out.open("wb") as f:
    result = pisa.CreatePDF(html, dest=f)

if result.err:
    raise SystemExit(f"PDF conversion failed: {result.err}")

print(f"Wrote {out} ({out.stat().st_size} bytes)")
