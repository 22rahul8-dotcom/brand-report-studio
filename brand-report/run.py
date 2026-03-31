#!/usr/bin/env python3
"""
Brand-Aware Magazine Report Generator — unified entry point.

Runs the full pipeline in one command:
  Phase 1+2: Scrape brand identity from a company URL
  Phase 3+4: Generate a magazine-quality branded report

Usage:
    python run.py <url> --describe <text> [options]
    python run.py <url> --content <file> [options]

Examples:
    python run.py https://stripe.com --describe "Q1 2026: 40% revenue growth, Series C closed"
    python run.py https://linear.app --content brief.md --type investor --pdf --docx
    python run.py https://notion.so  --content data.md  --title "Annual Review 2025"
    python run.py https://stripe.com --content report.md --skip-scrape  # reuse cached brand
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Brand-Aware Magazine Report Generator — full pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Report types (--type):
  investor    Financial metrics, growth, market, team, outlook
  annual      Year in review: milestones, performance, priorities
  product     Feature launches, user metrics, roadmap
  case-study  Challenge → solution → results → learnings

Export formats:
  HTML is always generated (self-contained, print-ready)
  --pdf       PDF via WeasyPrint (pip install weasyprint) or Playwright
  --docx      Editable Word document (pip install python-docx)

Examples:
  python run.py https://stripe.com \\
      --describe "Q1 2026 investor update: 40%% YoY growth, Series C closed at $200M" \\
      --type investor --pdf --docx

  python run.py https://linear.app \\
      --content my-report.md --title "Product Update Q1 2026" --type product

  python run.py https://notion.so \\
      --content brief.md --skip-scrape  # reuse existing brand profile
        """,
    )

    # ── Positional ──
    parser.add_argument("url", help="Company website URL (e.g. https://stripe.com)")

    # ── Content source (mutually exclusive) ──
    content_group = parser.add_mutually_exclusive_group()
    content_group.add_argument("--content", metavar="FILE",
        help="Path to report content (markdown or plain text)")
    content_group.add_argument("--describe", metavar="TEXT",
        help='One-line description — AI generates the full report (e.g. "40%% growth Q1")')

    # ── Report options ──
    parser.add_argument("--title",  default="",
        help="Override report title (AI infers one if not set)")
    parser.add_argument("--type",   choices=["investor", "annual", "product", "case-study"],
        help="Report type preset — shapes AI structure and tone")

    # ── Export ──
    parser.add_argument("--pdf",    action="store_true", help="Export PDF")
    parser.add_argument("--docx",   action="store_true", help="Export Word document")
    parser.add_argument("--pdf-engine", choices=["weasyprint", "puppeteer"],
        default="weasyprint", help="PDF engine (default: weasyprint)")

    # ── Paths ──
    parser.add_argument("--brands-dir", default="./brands",
        help="Root directory for brand profiles (default: ./brands)")
    parser.add_argument("--output", default="",
        help="Custom output HTML path (default: brands/<slug>/reports/<title>/report.html)")

    # ── Scraper control ──
    parser.add_argument("--force-scrape", action="store_true",
        help="Re-scrape brand even if a cached profile exists (<30 days)")
    parser.add_argument("--skip-scrape",  action="store_true",
        help="Skip Phase 1+2, reuse existing brands/<slug>/brand.json")

    args = parser.parse_args()

    if not args.content and not args.describe:
        parser.error("Provide --content <file> or --describe <text>")

    # ── Import scripts as modules ──
    scripts_dir = Path(__file__).parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    try:
        from brand_scrape import scrape_brand, get_slug
        import generate_report as gr
    except ImportError as e:
        print(f"Error importing pipeline modules: {e}", file=sys.stderr)
        print(f"  Make sure you're running from the brand-report/ directory.", file=sys.stderr)
        sys.exit(1)

    slug      = get_slug(args.url)
    brand_dir = Path(args.brands_dir) / slug

    # ──────────────────────────────────────────────
    # Phase 1 + 2: Brand scraping
    # ──────────────────────────────────────────────
    if args.skip_scrape:
        if not (brand_dir / "brand.json").exists():
            print(f"Error: No brand profile at {brand_dir}/brand.json", file=sys.stderr)
            print("  Remove --skip-scrape to scrape the brand first.", file=sys.stderr)
            sys.exit(1)
        print(f"Skipping scrape — using existing profile for '{slug}'")
    else:
        scrape_brand(args.url, output_dir=args.brands_dir, force=args.force_scrape)

    print()

    # ──────────────────────────────────────────────
    # Phase 3 + 4: Report generation
    # ──────────────────────────────────────────────
    brand  = json.loads((brand_dir / "brand.json").read_text())
    client = gr.get_claude_client()

    print(f"Generating report for: {brand.get('company', slug)}")
    if args.type:
        print(f"  Report type: {args.type}")

    if args.describe:
        structured = gr.generate_content(client, args.describe, brand, report_type=args.type)
    else:
        content_path = Path(args.content)
        if not content_path.exists():
            print(f"Error: Content file not found: {content_path}", file=sys.stderr)
            sys.exit(1)
        raw = content_path.read_text(encoding="utf-8")
        structured = gr.structure_content(client, raw, brand, report_type=args.type)

    if args.title:
        structured["title"] = args.title

    report_title = structured.get("title", "Report")
    print(f"  Title    : {report_title}")
    print(f"  Sections : {len(structured.get('sections', []))}")

    # ── Determine output path ──
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        date_slug   = datetime.now().strftime("%Y-%m")
        title_slug  = re.sub(r"[^a-z0-9]+", "-", report_title.lower()).strip("-")
        report_dir  = brand_dir / "reports" / f"{title_slug}-{date_slug}"
        report_dir.mkdir(parents=True, exist_ok=True)
        output_path = report_dir / "report.html"

        # Save structured metadata alongside
        meta = {
            **structured,
            "brand_slug":   slug,
            "report_type":  args.type,
            "generated_at": datetime.now().isoformat(),
        }
        (report_dir / "report-metadata.json").write_text(json.dumps(meta, indent=2))

    # ── Render HTML ──
    print("  → Rendering HTML...")
    html = gr.generate_html(structured, brand, brand_dir, report_title)
    output_path.write_text(html, encoding="utf-8")

    print(f"\n{'='*56}")
    print(f"✓ Report complete!")
    print(f"  HTML  → {output_path}")
    print(f"  Open  : file://{output_path.absolute()}")

    # ── PDF ──
    if args.pdf:
        pdf_path = output_path.with_suffix(".pdf")
        print(f"  → Exporting PDF ({args.pdf_engine})...")
        if args.pdf_engine == "weasyprint":
            gr.export_pdf_weasyprint(output_path, pdf_path)
        else:
            gr.export_pdf_puppeteer(output_path, pdf_path)

    # ── DOCX ──
    if args.docx:
        docx_path = output_path.with_suffix(".docx")
        print("  → Exporting DOCX...")
        gr.export_docx(structured, brand, docx_path)

    print(f"{'='*56}")


if __name__ == "__main__":
    main()
