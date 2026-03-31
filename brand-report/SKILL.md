---
name: brand-report
description: >
  Generate brand-aware, magazine-quality reports styled to a company's visual identity.
  Use this skill when the user wants to create a report for a company, scrape a company's
  brand identity, generate a PDF report, create an investor report, annual review, product
  update, or any branded document. Also trigger when the user pastes a company URL and asks
  for a report, or mentions brand scraping, brand identity extraction, or magazine layouts.
  This skill uses Firecrawl's branding format (Phase 1) and Claude API (Phase 3) to automate
  the full pipeline from URL → brand profile → styled HTML/PDF report.
---

# Brand-Aware Magazine Report Generator

This skill automates a 4-phase pipeline:
1. **Brand Scrape** — Extract colors, fonts, logo, and design language from a company's website
2. **Brand Processing** — Assign semantic color roles and classify design style
3. **Report Intelligence** — Use Claude to structure content into magazine sections
4. **Layout Engine** — Render a self-contained HTML report with embedded brand CSS

## Setup

```bash
pip install firecrawl-py anthropic
# Optional PDF export:
pip install weasyprint        # or use --pdf-engine puppeteer (requires playwright)
```

Set environment variables:
```bash
export FIRECRAWL_API_KEY='fc-YOUR-KEY'
export ANTHROPIC_API_KEY='sk-ant-YOUR-KEY'
```

## Core workflow

### Step 1 — Scrape brand identity

```bash
python brand-report/scripts/brand_scrape.py https://stripe.com
# → Creates: brands/stripe/brand.json + brands/stripe/assets/
```

Options:
- `--output-dir ./brands` — where to store brand profiles (default: `./brands`)
- `--force` — re-scrape even if a fresh profile exists (profiles are cached 30 days)

What gets extracted (via Firecrawl `branding` format):
- **Colors**: primary, secondary, accent, background, text — plus derived report roles
- **Fonts**: heading and body font families, weights
- **Logo**: downloaded as SVG or PNG
- **Images**: up to 3 hero images downloaded
- **Design style**: classified as `clean_minimal | bold_editorial | corporate_formal | startup_playful | luxury_premium | technical_precise`
- **Brand voice**: tone traits and tagline

### Step 2 — Generate the report

**From existing content (markdown or plain text):**
```bash
python brand-report/scripts/generate_report.py \
  --brand ./brands/stripe \
  --content my-report.md \
  --title "Q1 2026 Investor Report"
```

**AI-generated from a description:**
```bash
python brand-report/scripts/generate_report.py \
  --brand ./brands/stripe \
  --describe "Investor report: 40% YoY revenue growth, new enterprise tier launch, Series C fundraise"
```

**With PDF export:**
```bash
python brand-report/scripts/generate_report.py \
  --brand ./brands/linear \
  --content report.md \
  --pdf
  # or: --pdf --pdf-engine puppeteer
```

Output is saved to `brands/<slug>/reports/<title-slug>-<YYYY-MM>/report.html`

## Section types

Claude classifies content into these magazine section types:

| Type | Layout |
|------|--------|
| `executive_summary` | Large lead paragraph + body text |
| `key_metrics` | Stat cards grid (value + label) |
| `narrative` | Two-column body text with auto-extracted pull quote |
| `data_table` | Full-width styled table |
| `chart` | Chart.js bar/line/pie (brand-colored) |
| `pull_quote` | Full-bleed color spread with large quote |
| `recommendations` | Numbered list with brand-colored circles |
| `conclusion` | Centered single-column |
| `appendix` | Dense two-column |

## Brand storage structure

```
brands/
└── stripe/
    ├── brand.json          ← Master brand profile (colors, fonts, style, voice)
    ├── assets/
    │   ├── logo.svg
    │   ├── logo.png
    │   └── hero-1.jpg
    └── reports/
        └── q1-2026-investor-report-2026-03/
            ├── report.html
            ├── report.pdf
            └── report-metadata.json
```

## Full end-to-end example

```bash
# 1. Scrape Linear's brand
python brand-report/scripts/brand_scrape.py https://linear.app

# 2. Generate report from a description
python brand-report/scripts/generate_report.py \
  --brand ./brands/linear \
  --describe "Q1 2026 product update: shipped 12 features, 98.9% uptime, 150 enterprise clients" \
  --title "Q1 2026 Product Update" \
  --pdf
```

## Writing the script

When generating a report for the user:
1. Run `brand_scrape.py` first if no brand profile exists for the target company
2. Confirm brand extraction was successful (check brand.json for colors/fonts)
3. Run `generate_report.py` with the appropriate `--content` or `--describe` flag
4. Print the output path so the user can open it in a browser
5. If the user wants a PDF, add `--pdf`

When writing custom scrapers or extending the pipeline, follow the brand.json schema
from the spec (see `report-gen.md` at the project root) — the color role keys are
used directly as CSS custom properties in the HTML template.

## Edge cases & fallbacks

| Problem | What happens |
|---------|-------------|
| No logo found | Initials used as logomark in cover |
| No branding data from Firecrawl | Neutral grey palette used as default |
| Font is proprietary | Falls back to Google Fonts stack defined in brand.json |
| Single color extracted | Primary color used for all roles; tints derived automatically |
| `--describe` with no numbers | Claude generates illustrative placeholder data |
| WeasyPrint not installed | Skips PDF with warning; HTML output still generated |
