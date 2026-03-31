#!/usr/bin/env python3
"""
Magazine Report Generator — Full Design System
Implements: Autodesk / BCG / McKinsey / CrowdStrike / Splunk visual intelligence.

Design system: report-design-system.md
Charts: slope · waffle · lollipop · bar · donut · line (all SVG-native or Chart.js)
Layout: split-panel · chapter dividers · stat grids · pull-quote cards
Typography: two-color headline split · drop cap · section chips · accent rules
"""

import argparse
import base64
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ── LLM helpers ───────────────────────────────────────────────────────────────

def claude(client, prompt: str, system: str = "") -> str:
    kwargs = {"model": "claude-sonnet-4-6", "max_tokens": 8192,
              "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    return client.messages.create(**kwargs).content[0].text


def groq_complete(client, prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages, max_tokens=6000, temperature=0.3,
    ).choices[0].message.content


# ── Content structuring ───────────────────────────────────────────────────────

STRUCTURE_SYSTEM = """\
You are a senior business intelligence analyst and magazine layout director.
Structure web content into a professional report following McKinsey/BCG/Autodesk design standards.

Return ONLY valid JSON — no markdown fences, no backticks, no explanation.

Full schema:
{
  "title": "Full descriptive report title",
  "subtitle": "One-line descriptor",
  "prepared_by": "Brand Report Studio",
  "chapter_intro": "One compelling paragraph opening",
  "sections": [
    {
      "id": "unique-kebab-id",
      "type": "executive_summary|key_metrics|chapter_divider|narrative|pull_quote|recommendations|data_table|conclusion",
      "heading": "Section heading",
      "chip": "SHORT LABEL (3 words max)",
      "number": null,
      "content": {
        "body": "Paragraphs separated by \\n\\n",
        "stats": [{"label": "...", "value": "...", "unit": "..."}],
        "table": {"headers": ["Col"], "rows": [["val"]]},
        "chart": {
          "type": "bar|line|donut|slope|waffle|lollipop",
          "title": "Finding-oriented title (describe the insight, not the variable)",
          "subtitle": "Optional metric definition",
          "labels": ["..."],
          "values": [0],
          "values2": [0],
          "labels2": ["2024", "2025"],
          "annotation": "Key insight to call out"
        },
        "items": ["item 1", "item 2"],
        "quote": {"text": "...", "attribution": "..."}
      }
    }
  ],
  "pull_quotes": ["Standalone quote 1", "Standalone quote 2"]
}

CHART TYPE RULES — choose the right chart:
- slope: year-over-year or before/after comparisons (values = current, values2 = previous, labels = categories)
- waffle: single percentage shown as unit grid (values = [percentage_number], labels = ["metric name"])
- lollipop: ranked list of 5-10 items (values descending)
- donut: part-of-whole, single or multi-segment
- bar: multi-category comparison
- line: time series with 4+ data points

MANDATORY SECTIONS:
1. executive_summary — first; stats array with 3-4 headline metrics
2. key_metrics — 4-6 stat cards + a chart (slope or bar preferred)
3. Two or more narrative sections — 3+ paragraph body each; include chart when data exists
4. At least one pull_quote
5. recommendations — 4-5 items
6. conclusion — dark closing section

RULES:
- chip labels: SHORT UPPERCASE max 3 words ("KEY FINDING", "CHAPTER 1", "INSIGHT")
- Chart titles describe the finding: "AI investment rises sharply" not "AI Investment by Year"
- Stats should be large & bold-worthy: percentages, $ amounts, multipliers (2×), growth rates
- For slope charts: labels = category names, values = current year %, values2 = prior year %
"""


def structure_content(client_fn, raw_content: str, brand: dict) -> dict:
    company = brand.get("company", "Company")
    tone = brand.get("brand_voice", {}).get("tone", ["professional"])
    prompt = f"""Company: {company}
Brand tone: {', '.join(tone) if isinstance(tone, list) else tone}

CONTENT TO STRUCTURE:
---
{raw_content[:8000]}
---

Structure this into a professional magazine report. Generate ALL required section types.
For key_metrics, always include a slope or bar chart."""
    raw = client_fn(prompt, STRUCTURE_SYSTEM)
    return _parse_json(raw, company, raw_content)


def generate_content(client_fn, description: str, brand: dict, markdown: str = "") -> dict:
    company = brand.get("company", "Company")
    tone = brand.get("brand_voice", {}).get("tone", ["professional"])
    tagline = brand.get("brand_voice", {}).get("tagline", "")
    system = f"""{STRUCTURE_SYSTEM}

You are writing a premium business report for {company}.
Brand tone: {', '.join(tone) if isinstance(tone, list) else tone}.
{f'Company tagline: {tagline}' if tagline else ''}
Use the scraped website content as context. Invent plausible illustrative data for metrics."""
    context = f"\n\nSCRAPED WEBSITE CONTENT:\n{markdown[:5000]}" if markdown else ""
    prompt = f"Create a detailed professional report for: {description}{context}"
    raw = client_fn(prompt, system)
    return _parse_json(raw, company, description)


def _parse_json(raw: str, company: str, fallback_content: str) -> dict:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    json_str = match.group(1) if match else raw.strip()
    json_str = re.sub(r'^[^{\[]*', '', json_str)
    json_str = re.sub(r'[^}\]]*$', '', json_str)
    try:
        return json.loads(json_str)
    except Exception:
        return {
            "title": f"{company} Report", "subtitle": "Company Overview",
            "prepared_by": "Brand Report Studio", "chapter_intro": "",
            "sections": [{"id": "exec", "type": "executive_summary",
                          "heading": "Executive Summary", "chip": "SUMMARY", "number": None,
                          "content": {"body": fallback_content[:2000], "stats": []}}],
            "pull_quotes": [],
        }


# ── Asset helpers ─────────────────────────────────────────────────────────────

def load_asset_b64(path) -> str:
    if not path or not Path(path).is_file():
        return ""
    ext = Path(path).suffix.lower().lstrip(".")
    mime_map = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg",
                "jpeg": "image/jpeg", "ico": "image/x-icon", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/png")
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:{mime};base64,{data}"


# ── Color helpers ─────────────────────────────────────────────────────────────

def _is_dark(hex_color: str) -> bool:
    try:
        c = hex_color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 128
    except Exception:
        return True


def _ensure_contrast(hex_color: str, on_dark: bool = False) -> str:
    try:
        c = hex_color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if on_dark and lum < 0.35:
            f = 1.6
            r, g, b = min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f))
        elif not on_dark and lum > 0.8:
            f = 0.55
            r, g, b = int(r * f), int(g * f), int(b * f)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def _hex_to_rgb(hex_color: str) -> tuple:
    c = hex_color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _lighten(hex_color: str, factor: float = 0.4) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── CSS builder ───────────────────────────────────────────────────────────────

def build_css(brand: dict) -> str:
    c  = brand.get("colors", {})
    f  = brand.get("fonts", {})

    accent      = _ensure_contrast(c.get("accent", c.get("primary", "#0066cc")))
    accent_dark = _ensure_contrast(accent, on_dark=True)
    accent_lite = _lighten(accent, 0.72)
    primary     = c.get("primary", "#0a0a0f")
    text        = c.get("text_primary", "#111111")
    text2       = c.get("text_secondary", "#555555")
    # Cover bg: must be dark. If primary is dark use it, otherwise fall back.
    # But also reject very saturated bright colors (like pure #0000ff) — darken them hard.
    def _is_too_saturated(hex_color: str) -> bool:
        try:
            r2, g2, b2 = _hex_to_rgb(hex_color)
            mx = max(r2, g2, b2); mn = min(r2, g2, b2)
            sat = (mx - mn) / mx if mx else 0
            lum = (0.299 * r2 + 0.587 * g2 + 0.114 * b2) / 255
            return sat > 0.85 and lum < 0.4  # vivid dark color → darken more
        except Exception:
            return False

    if _is_dark(primary) and not _is_too_saturated(primary):
        cover_bg = primary
    elif _is_too_saturated(primary):
        # Very saturated dark color (e.g. pure blue #0000ff) → crush to near-black tinted
        r2, g2, b2 = _hex_to_rgb(primary)
        cover_bg = f"#{max(0,r2//6):02x}{max(0,g2//6):02x}{max(0,b2//6):02x}"
    else:
        cover_bg = "#0a0a0f"

    heading_family = (f.get("heading", {}).get("family", "Inter")
                      if isinstance(f, dict) else "Inter")
    body_family    = (f.get("body", {}).get("family", "Inter")
                      if isinstance(f, dict) else "Inter")

    google_url = ""
    safe = ("sans-serif", "serif", "monospace", "system-ui", "inter")
    if heading_family.lower() not in safe:
        fams = [heading_family.replace(" ", "+")]
        if body_family.lower() not in safe and body_family != heading_family:
            fams.append(body_family.replace(" ", "+"))
        google_url = (f"https://fonts.googleapis.com/css2?family="
                      f"{'&family='.join(fams)}:wght@300;400;600;700;800;900&display=swap")

    return f"""
{'@import url("' + google_url + '");' if google_url else ''}

:root {{
  --accent:       {accent};
  --accent-dark:  {accent_dark};
  --accent-lite:  {accent_lite};
  --primary:      {primary};
  --cover-bg:     {cover_bg};
  --bg:           #ffffff;
  --surface:      #f6f6f9;
  --border:       #e2e2ec;
  --text:         {text if not _is_dark(text) else '#111111'};
  --text2:        {text2};
  --font-head:    "{heading_family}", Inter, system-ui, sans-serif;
  --font-body:    "{body_family}", Inter, system-ui, sans-serif;
  --radius:       8px;
  --page-width:   794px;
  --margin:       52px;
  --gutter:       28px;
}}

@page {{ size: A4 portrait; margin: 0; }}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 15px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font-family: var(--font-body); background: #d0d0da; -webkit-font-smoothing: antialiased; }}

/* ── Page wrapper ── */
.rp {{ width: var(--page-width); margin: 40px auto; background: var(--bg); box-shadow: 0 8px 80px rgba(0,0,0,.28); border-radius: 2px; overflow: hidden; }}
@media print {{
  body {{ background: white; }}
  .rp {{ width: 794px; margin: 0 auto; box-shadow: none; border-radius: 0; }}
}}
@media (max-width: 840px) {{ .rp {{ width: 100%; margin: 0; box-shadow: none; }} :root {{ --margin: 28px; }} }}

/* ══════════════════════════════════════════════
   COVER
══════════════════════════════════════════════ */
.cover {{
  background: var(--cover-bg);
  min-height: 1060px;
  display: grid;
  grid-template-rows: 56px 1fr auto;
  position: relative;
  overflow: hidden;
}}
.cover-art {{
  position: absolute; inset: 0;
  pointer-events: none; z-index: 0;
  overflow: hidden;
}}
.cover-nav {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--margin);
  border-bottom: 1px solid rgba(255,255,255,.07);
  position: relative; z-index: 2;
}}
.cover-brand {{
  font-family: var(--font-head); font-size: 13px; font-weight: 700;
  color: rgba(255,255,255,.6); letter-spacing: .12em; text-transform: uppercase;
}}
.cover-year {{ font-size: 12px; color: rgba(255,255,255,.28); letter-spacing: .08em; }}
.cover-body {{
  padding: 48px var(--margin) 40px;
  display: flex; flex-direction: column; justify-content: flex-end;
  position: relative; z-index: 2;
}}
.cover-eyebrow {{
  font-size: 10px; font-weight: 800; letter-spacing: .2em; text-transform: uppercase;
  color: var(--accent-dark); margin-bottom: 18px;
}}
.cover-rule {{ height: 3px; width: 56px; background: var(--accent); margin-bottom: 22px; border-radius: 2px; }}
.cover-title {{
  font-family: var(--font-head);
  font-size: clamp(38px, 5.5vw, 70px);
  font-weight: 900; line-height: 1.06; letter-spacing: -1.5px;
  color: #fff; margin-bottom: 18px; max-width: 600px;
}}
.cover-title .hw {{ color: var(--accent-dark); }}
.cover-subtitle {{
  font-size: 16px; color: rgba(255,255,255,.45);
  font-weight: 400; line-height: 1.5; max-width: 520px; margin-bottom: 8px;
}}
.cover-meta {{ font-size: 11px; color: rgba(255,255,255,.22); letter-spacing: .06em; margin-top: 6px; }}
.cover-footer {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px var(--margin);
  border-top: 1px solid rgba(255,255,255,.05);
  font-size: 10px; color: rgba(255,255,255,.22);
  letter-spacing: .08em; text-transform: uppercase;
  position: relative; z-index: 2;
}}

/* ══════════════════════════════════════════════
   RUNNING HEADER / FOOTER
══════════════════════════════════════════════ */
.page-header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px var(--margin);
  border-bottom: 1px solid var(--border);
  font-size: 10px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase;
  color: var(--text2); background: var(--bg);
}}
.page-header .logo-mark {{
  font-family: var(--font-head); font-weight: 800; color: var(--accent); font-size: 13px;
}}
.page-footer {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px var(--margin);
  border-top: 1px solid var(--border);
  font-size: 10px; color: var(--text2);
  letter-spacing: .08em; text-transform: uppercase; background: var(--bg);
}}
.page-num {{ font-weight: 800; color: var(--accent); }}

/* ══════════════════════════════════════════════
   SECTION PRIMITIVES
══════════════════════════════════════════════ */
.sec-chip {{
  display: inline-block;
  background: var(--accent); color: #fff;
  font-size: 9px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase;
  padding: 3px 11px; border-radius: 20px; margin-bottom: 14px;
}}
.accent-rule {{ height: 3px; background: var(--accent); width: 100%; margin-bottom: 20px; border-radius: 2px; }}
.accent-rule-short {{ height: 3px; background: var(--accent); width: 48px; margin-bottom: 16px; border-radius: 2px; }}
.sec-num {{
  font-size: 11px; font-weight: 700; color: var(--accent);
  letter-spacing: .14em; text-transform: uppercase; margin-bottom: 8px;
}}
.sec-heading {{
  font-family: var(--font-head);
  font-size: clamp(26px, 3.8vw, 44px);
  font-weight: 800; line-height: 1.12; letter-spacing: -.4px;
  color: var(--text); margin-bottom: 8px;
}}
.sec-heading .hw {{ color: var(--accent); }}

/* Section container */
.section {{
  padding: 52px var(--margin) 0;
  position: relative; background: var(--bg); overflow: hidden;
}}
.section-dark {{
  background: var(--cover-bg);
  padding: 52px var(--margin) 0; position: relative; overflow: hidden;
}}
.section-end {{ height: 56px; background: var(--bg); }}
.section-end-dark {{ height: 56px; background: var(--cover-bg); }}

/* ── Background watermark number ── */
.bg-num {{
  position: absolute; right: var(--margin);
  font-size: 240px; font-weight: 900;
  color: var(--accent); opacity: .05;
  line-height: 1; pointer-events: none; user-select: none;
  top: 0;
}}
.bg-num-dark {{
  position: absolute; right: var(--margin);
  font-size: 240px; font-weight: 900;
  color: rgba(255,255,255,.04);
  line-height: 1; pointer-events: none; user-select: none;
  top: 0;
}}

/* ── Decorative corner dot grid ── */
.dot-grid {{
  position: absolute; pointer-events: none; user-select: none;
  display: grid; grid-template-columns: repeat(8, 8px); gap: 7px;
  opacity: .14;
}}
.dot-grid span {{ width: 3px; height: 3px; border-radius: 50%; background: var(--accent); display: block; }}
.dot-grid-br {{ bottom: 32px; right: 40px; }}
.dot-grid-tr {{ top: 32px; right: 40px; }}

/* ── Decorative bg circle ── */
.bg-circle {{
  position: absolute; border-radius: 50%;
  background: var(--accent); pointer-events: none;
}}

/* ══════════════════════════════════════════════
   STAT GRID
══════════════════════════════════════════════ */
.stat-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
  gap: 16px; margin: 26px 0;
}}
.stat-card {{
  padding: 22px 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent);
  border-radius: var(--radius);
  position: relative; overflow: visible; min-height: 110px;
}}
.stat-card::after {{
  content: '';
  position: absolute; bottom: -20px; right: -20px;
  width: 80px; height: 80px; border-radius: 50%;
  background: var(--accent); opacity: .05;
}}
.stat-num {{
  font-family: var(--font-head);
  font-size: clamp(18px, 2.4vw, 34px);
  font-weight: 900; line-height: 1.1; color: var(--accent);
  margin-bottom: 10px;
  word-break: break-word; overflow-wrap: anywhere;
  min-width: 0;
  overflow: visible;
}}
.stat-unit {{ font-size: 22px; font-weight: 400; color: var(--text2); }}
.stat-lbl {{
  font-size: 12px; color: var(--text2); line-height: 1.5;
  font-weight: 600; letter-spacing: .02em;
}}

/* ══════════════════════════════════════════════
   TYPOGRAPHY
══════════════════════════════════════════════ */
.body-text {{ max-width: 72ch; }}
.body-text p {{
  font-size: 15px; line-height: 1.75; color: var(--text);
  margin-bottom: 18px;
}}
.body-text p:last-child {{ margin-bottom: 0; }}
.body-text-white p {{ color: rgba(255,255,255,.72); font-size: 16px; line-height: 1.75; margin-bottom: 18px; }}

/* Drop cap */
.drop-cap::first-letter {{
  float: left;
  font-family: var(--font-head);
  font-size: 4em; font-weight: 900;
  line-height: 0.82; color: var(--accent);
  margin-right: 8px; margin-top: 6px;
}}

/* Exec lead */
.exec-lead {{
  font-family: var(--font-head);
  font-size: clamp(16px, 2vw, 20px);
  font-weight: 400; line-height: 1.6; color: var(--text);
  padding-bottom: 26px; margin-bottom: 26px;
  border-bottom: 1px solid var(--border);
  max-width: 68ch;
}}

/* ══════════════════════════════════════════════
   PULL QUOTE
══════════════════════════════════════════════ */
.pull-quote {{
  background: #0a0a0f;
  border-left: 4px solid var(--accent);
  border-radius: 0 var(--radius) var(--radius) 0;
  padding: 26px 28px; margin: 8px 0;
  position: relative;
}}
.pq-mark {{
  font-size: 56px; line-height: 1; font-weight: 900; font-style: normal;
  color: var(--accent); display: block; margin-bottom: -16px;
  font-family: var(--font-head);
}}
.pull-quote-text {{
  font-family: var(--font-head);
  font-size: 16px; font-weight: 500; font-style: italic;
  line-height: 1.6; color: #fff; margin-bottom: 14px; margin-top: 8px;
}}
.pull-quote-attr {{
  font-size: 10px; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; color: var(--accent);
  border-top: 1px solid rgba(255,255,255,.1); padding-top: 10px;
}}

/* Full-bleed pull quote page */
.section-quote {{
  background: var(--cover-bg); padding: 72px var(--margin);
  text-align: center; position: relative; overflow: hidden;
}}
.section-quote .q-bg-mark {{
  position: absolute; font-size: 320px; font-weight: 900;
  color: rgba(255,255,255,.025); top: -60px; left: 50%;
  transform: translateX(-50%); line-height: 1;
  pointer-events: none; user-select: none;
}}
.section-quote .pq-mark {{ color: var(--accent-dark); margin-bottom: -24px; font-size: 64px; }}
.section-quote .pull-quote-text {{
  font-size: clamp(20px, 2.8vw, 30px); max-width: 680px;
  margin: 0 auto 20px; color: #fff; font-style: italic;
}}
.section-quote .pull-quote-attr {{
  color: rgba(255,255,255,.4); border-color: rgba(255,255,255,.08);
  display: inline-block;
}}

/* ══════════════════════════════════════════════
   CHAPTER DIVIDER
══════════════════════════════════════════════ */
.chapter-div {{
  background: var(--cover-bg);
  min-height: 320px; position: relative; overflow: hidden;
  display: flex; align-items: center;
  padding: 56px var(--margin);
}}
.chapter-div .ch-num-bg {{
  position: absolute; right: calc(var(--margin) - 20px);
  font-size: 260px; font-weight: 900;
  color: rgba(255,255,255,.04); line-height: 1;
  pointer-events: none; user-select: none; top: 10px;
}}
.chapter-div .ch-accent-bar {{
  position: absolute; left: 0; top: 0; bottom: 0;
  width: 5px; background: var(--accent);
}}
.chapter-div .ch-content {{ position: relative; z-index: 1; }}
.chapter-div h2 {{
  font-family: var(--font-head);
  font-size: clamp(32px, 5.5vw, 56px);
  font-weight: 900; color: #fff; line-height: 1.08;
  margin: 12px 0 14px; letter-spacing: -.5px;
}}
.chapter-div h2 .hw {{ color: var(--accent-dark); }}
.chapter-div p {{ font-size: 15px; color: rgba(255,255,255,.4); max-width: 480px; line-height: 1.6; }}

/* ══════════════════════════════════════════════
   SPLIT PANEL
══════════════════════════════════════════════ */
.split-panel {{
  display: grid; grid-template-columns: 40% 60%; min-height: 280px;
}}
.split-dark {{
  background: var(--cover-bg); padding: 40px 36px;
  display: flex; flex-direction: column; justify-content: flex-end;
  position: relative; overflow: hidden;
}}
.split-dark .sd-bg {{
  position: absolute; top: -40px; right: -40px;
  width: 200px; height: 200px; border-radius: 50%;
  background: var(--accent); opacity: .08;
}}
.split-light {{
  background: var(--surface); padding: 40px 36px;
  display: flex; flex-direction: column; justify-content: center;
}}
.split-dark .split-stat-big {{
  font-family: var(--font-head);
  font-size: clamp(52px, 8vw, 88px);
  font-weight: 900; line-height: 1; color: var(--accent-dark);
  margin-bottom: 8px;
}}
.split-dark .split-stat-label {{
  font-size: 13px; color: rgba(255,255,255,.45); line-height: 1.5;
}}
@media (max-width: 680px) {{
  .split-panel {{ grid-template-columns: 1fr; }}
}}

/* ══════════════════════════════════════════════
   TWO-COLUMN BODY
══════════════════════════════════════════════ */
.body-two-col {{
  display: grid; grid-template-columns: 60% 40%;
  gap: var(--gutter); align-items: start;
}}
.body-two-col .body-text {{ max-width: none; }}
@media (max-width: 680px) {{ .body-two-col {{ grid-template-columns: 1fr; }} }}

/* ══════════════════════════════════════════════
   RECOMMENDATIONS
══════════════════════════════════════════════ */
.rec-list {{ list-style: none; }}
.rec-item {{
  display: grid; grid-template-columns: 60px 1fr;
  gap: 20px; align-items: start;
  padding: 22px 0; border-bottom: 1px solid var(--border);
}}
.rec-item:last-child {{ border-bottom: none; }}
.rec-num-wrap {{
  position: relative; height: 52px;
  display: flex; align-items: center; justify-content: center;
}}
.rec-num-bg {{
  position: absolute; font-size: 72px; font-weight: 900;
  color: var(--accent); opacity: .1; line-height: 1; top: -12px; left: -6px;
}}
.rec-num {{
  position: relative; font-family: var(--font-head);
  font-size: 22px; font-weight: 900; color: var(--accent); z-index: 1;
}}
.rec-heading {{
  font-family: var(--font-head); font-size: 15px; font-weight: 700;
  color: var(--text); margin-bottom: 4px;
}}
.rec-text {{ font-size: 14px; line-height: 1.65; color: var(--text2); }}

/* ══════════════════════════════════════════════
   DATA TABLE
══════════════════════════════════════════════ */
.data-table-wrapper {{ overflow-x: auto; margin: 16px 0; }}
.data-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
.data-table th {{
  background: var(--cover-bg); color: #fff;
  font-family: var(--font-head); font-size: 10px; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase;
  padding: 12px 14px; text-align: left;
}}
.data-table td {{ padding: 11px 14px; border-bottom: 1px solid var(--border); color: var(--text); line-height: 1.5; }}
.data-table tr:nth-child(even) td {{ background: var(--surface); }}

/* ══════════════════════════════════════════════
   CHARTS
══════════════════════════════════════════════ */
.chart-wrap {{ position: relative; width: 100%; margin: 22px 0; }}
.chart-finding {{
  font-family: var(--font-head); font-size: 15px; font-weight: 700;
  color: var(--text); margin-bottom: 4px; line-height: 1.3;
}}
.chart-subtitle {{ font-size: 12px; color: var(--text2); margin-bottom: 14px; }}
.chart-source {{ font-size: 10px; color: var(--text2); margin-top: 10px; letter-spacing: .04em; }}
.chart-annotation {{
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--accent); color: #fff;
  font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px;
  margin-bottom: 12px;
}}

/* SVG chart containers */
.svg-chart {{ width: 100%; overflow: visible; display: block; }}
.slope-wrap {{ padding: 8px 0; }}
.waffle-wrap {{ display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }}
.waffle-legend {{ font-size: 13px; color: var(--text2); }}
.waffle-legend strong {{ font-family: var(--font-head); font-size: 28px; font-weight: 900; color: var(--accent); display: block; margin-bottom: 4px; }}

/* ══════════════════════════════════════════════
   CONCLUSION
══════════════════════════════════════════════ */
.conclusion {{
  background: var(--cover-bg);
  padding: 56px var(--margin);
  position: relative; overflow: hidden;
}}
.conclusion .sec-heading {{ color: #fff; }}
.conclusion .sec-chip {{ background: var(--accent); }}
.conclusion .accent-rule {{ background: var(--accent); opacity: .6; }}

/* ══════════════════════════════════════════════
   PRINT
══════════════════════════════════════════════ */
@media print {{
  body {{ background: white; }}
  .rp {{ width: 100%; margin: 0; box-shadow: none; }}
  .cover {{ min-height: 100vh; page-break-after: always; }}
  .chapter-div, .section-quote {{ page-break-before: always; }}
  .stat-grid, .pull-quote, .rec-item {{ break-inside: avoid; }}
  .data-table tr {{ break-inside: avoid; }}
}}
"""


# ══════════════════════════════════════════════
# TYPOGRAPHY HELPERS
# ══════════════════════════════════════════════

def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _stat_font_size(value: str) -> str:
    """Return an inline font-size style based on value string length."""
    n = len(str(value))
    if n <= 3:  return "font-size:54px"
    if n <= 5:  return "font-size:44px"
    if n <= 7:  return "font-size:34px"
    if n <= 9:  return "font-size:26px"
    return "font-size:20px"


def _clean_markdown(text: str) -> str:
    """Strip raw markdown syntax that should never appear in rendered output."""
    if not text:
        return ""
    # Remove image syntax entirely  ![](...) or ![alt](...)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", "", text)
    # Convert hyperlinks to plain text [label](url) → label
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    # Remove bare URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove repeated price noise patterns (e-commerce scraped content)
    text = re.sub(r"Regular price[^\n]*", "", text)
    text = re.sub(r"Sale price[^\n]*", "", text)
    text = re.sub(r"(Sold out|Quick view|Choose options)\s*", "", text)
    # Remove lines that are just dashes/tildes (markdown table/hr artifacts)
    text = re.sub(r"^[-~]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Collapse excess whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _md_to_html(text: str, drop_cap: bool = False) -> str:
    if not text:
        return ""
    text = _clean_markdown(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*",     r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`",       r"<code>\1</code>", text)
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    paras = [re.sub(r"\n", " ", p) for p in paras]
    paras = [p for p in paras if not re.match(r"^#{1,6}\s", p)]
    # Drop paragraphs that are just noise after cleaning (too short or all punctuation)
    paras = [p for p in paras if len(re.sub(r"[^a-zA-Z]", "", p)) > 12]
    html_parts = []
    for i, p in enumerate(paras):
        cls = ' class="drop-cap"' if drop_cap and i == 0 else ''
        html_parts.append(f"<p{cls}>{p}</p>")
    return "".join(html_parts)


def _accent_headline(title: str) -> str:
    """Two-color headline split: accent the last 2 words."""
    words = title.split()
    if len(words) <= 2:
        return _esc(title)
    split = max(1, len(words) - 2)
    plain = _esc(" ".join(words[:split]))
    bold  = _esc(" ".join(words[split:]))
    return f'{plain} <span class="hw">{bold}</span>'


def _dot_grid(n: int = 64, extra_class: str = "dot-grid-br") -> str:
    dots = '<span></span>' * n
    return f'<div class="dot-grid {extra_class}">{dots}</div>'


def _best_pull_quote(body: str) -> str:
    """Extract the most stat-rich sentence from body text."""
    sentences = re.split(r'(?<=[.!?])\s+', body.replace("\n", " "))
    candidates = sorted(
        [s.strip() for s in sentences if 50 < len(s.strip()) < 220],
        key=lambda s: len(re.findall(r'\d+[%×xX]?|\$[\d.,]+[BMKbmk]?', s)) * 3 + len(s),
        reverse=True
    )
    return candidates[0] if candidates else ""


# ══════════════════════════════════════════════
# SVG CHART RENDERERS
# ══════════════════════════════════════════════

def _slope_svg(chart_spec: dict, accent: str, chart_id: str) -> str:
    """Slope chart: show year-over-year change per category."""
    labels  = chart_spec.get("labels", [])
    vals    = chart_spec.get("values", [])     # current year
    vals2   = chart_spec.get("values2", [])    # prior year
    year_labels = chart_spec.get("labels2", ["Before", "After"])
    annotation  = chart_spec.get("annotation", "")

    if not labels or not vals:
        return ""

    n        = len(labels)
    row_h    = 52
    pad_top  = 40
    pad_bot  = 28
    pad_l    = 180
    pad_r    = 80
    W        = 620
    H        = pad_top + n * row_h + pad_bot

    x0 = pad_l          # left column (before/prior)
    x1 = W - pad_r      # right column (after/current)

    # Normalise: map 0–100 range within each row to y-position
    all_v = [v for v in (vals + (vals2 or [])) if isinstance(v, (int, float))]
    mn    = min(all_v) if all_v else 0
    mx    = max(all_v) if all_v else 100
    span  = mx - mn or 1

    def row_y(i):
        return pad_top + i * row_h + row_h // 2

    lines_svg  = []
    circles_svg = []
    labels_svg = []
    delta_svg  = []

    lite = _lighten(accent, 0.72)

    for i, (label, v) in enumerate(zip(labels, vals)):
        y_cur = row_y(i)
        v2    = vals2[i] if vals2 and i < len(vals2) else v
        # position within band (optional; here we keep same y per row for clarity)
        # Show delta pill
        try:
            delta = float(v) - float(v2)
        except (TypeError, ValueError):
            delta = 0

        delta_str = f"+{delta:.0f}pp" if delta >= 0 else f"{delta:.0f}pp"
        delta_col = accent if delta >= 0 else "#ef4444"

        # Line
        lines_svg.append(
            f'<line x1="{x0}" y1="{y_cur}" x2="{x1}" y2="{y_cur}" '
            f'stroke="{accent}" stroke-width="2" stroke-opacity="0.9"/>'
        )
        # Fill band
        lines_svg.append(
            f'<rect x="{x0}" y="{y_cur - 10}" width="{x1 - x0}" height="20" '
            f'fill="{accent}" fill-opacity="0.05" rx="4"/>'
        )
        # Before circle (open)
        circles_svg.append(
            f'<circle cx="{x0}" cy="{y_cur}" r="6" fill="#fff" '
            f'stroke="{accent}" stroke-width="2"/>'
        )
        # After circle (filled)
        circles_svg.append(
            f'<circle cx="{x1}" cy="{y_cur}" r="7" fill="{accent}"/>'
        )
        # Label (left)
        labels_svg.append(
            f'<text x="{x0 - 10}" y="{y_cur + 5}" text-anchor="end" '
            f'font-size="13" fill="#444" font-weight="500">{_esc(str(label))}</text>'
        )
        # Before value
        labels_svg.append(
            f'<text x="{x0}" y="{y_cur - 14}" text-anchor="middle" '
            f'font-size="11" fill="#999">{_esc(str(v2))}</text>'
        )
        # After value
        labels_svg.append(
            f'<text x="{x1}" y="{y_cur - 14}" text-anchor="middle" '
            f'font-size="12" fill="{accent}" font-weight="700">{_esc(str(v))}</text>'
        )
        # Delta pill (midpoint)
        mx_mid = (x0 + x1) // 2
        delta_svg.append(
            f'<rect x="{mx_mid - 22}" y="{y_cur - 10}" width="44" height="20" '
            f'rx="10" fill="{delta_col}" fill-opacity="0.15"/>'
        )
        delta_svg.append(
            f'<text x="{mx_mid}" y="{y_cur + 5}" text-anchor="middle" '
            f'font-size="10" fill="{delta_col}" font-weight="700">{_esc(delta_str)}</text>'
        )

    # Year labels at top
    year_svg = [
        f'<text x="{x0}" y="24" text-anchor="middle" font-size="11" '
        f'fill="#999" font-weight="600" letter-spacing="1">{_esc(str(year_labels[0] if year_labels else "Before"))}</text>',
        f'<text x="{x1}" y="24" text-anchor="middle" font-size="11" '
        f'fill="{accent}" font-weight="700" letter-spacing="1">{_esc(str(year_labels[-1] if year_labels else "After"))}</text>',
    ]

    annotation_html = ""
    if annotation:
        annotation_html = f'<div class="chart-annotation">↑ {_esc(annotation)}</div>'

    svg = (
        f'<svg class="svg-chart slope-wrap" viewBox="0 0 {W} {H}" '
        f'style="max-height:{H}px">'
        + "".join(year_svg)
        + "".join(lines_svg)
        + "".join(delta_svg)
        + "".join(circles_svg)
        + "".join(labels_svg)
        + "</svg>"
    )
    return annotation_html + svg


def _waffle_svg(chart_spec: dict, accent: str, chart_id: str) -> str:
    """Waffle / unit dot grid for single-percentage stats."""
    vals   = chart_spec.get("values", [50])
    labels = chart_spec.get("labels", [""])
    try:
        pct = max(0, min(100, float(vals[0])))
    except (TypeError, ValueError, IndexError):
        pct = 50
    label = str(labels[0]) if labels else ""

    cols, rows = 10, 10
    r    = 6
    gap  = 16
    W    = cols * gap + 4
    H    = rows * gap + 4
    lite = _lighten(accent, 0.8)

    filled = round(pct)
    dots   = []
    idx    = 0
    for row in range(rows - 1, -1, -1):  # bottom-to-top fill
        for col in range(cols):
            cx = col * gap + gap // 2 + 2
            cy = row * gap + gap // 2 + 2
            color = accent if idx < filled else "#e0e0e8"
            dots.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
            idx += 1

    svg = (
        f'<svg class="svg-chart" viewBox="0 0 {W} {H}" '
        f'style="width:{W}px;max-width:100%">'
        + "".join(dots)
        + "</svg>"
    )
    legend = f"""<div class="waffle-legend">
      <strong>{int(pct)}%</strong>{_esc(label)}
    </div>"""
    return f'<div class="waffle-wrap">{svg}{legend}</div>'


def _lollipop_svg(chart_spec: dict, accent: str, chart_id: str) -> str:
    """Horizontal lollipop / ranked bar chart."""
    labels = chart_spec.get("labels", [])
    vals   = chart_spec.get("values", [])
    title  = chart_spec.get("title", "")

    if not labels or not vals:
        return ""

    pad_l   = 200
    pad_r   = 60
    pad_top = 8
    row_h   = 44
    W       = 660
    H       = pad_top + len(labels) * row_h + 16
    mx      = max((float(v) for v in vals if isinstance(v, (int, float))), default=100)
    bar_w   = W - pad_l - pad_r

    items = []
    for i, (label, val) in enumerate(zip(labels, vals)):
        try:
            fval = float(val)
        except (TypeError, ValueError):
            fval = 0
        bw   = int(bar_w * fval / mx)
        y    = pad_top + i * row_h + row_h // 2
        col  = accent if i == 0 else _lighten(accent, i * 0.12)
        items.append(
            # label
            f'<text x="{pad_l - 10}" y="{y + 5}" text-anchor="end" '
            f'font-size="13" fill="#444">{_esc(str(label))}</text>'
            # track line
            f'<line x1="{pad_l}" y1="{y}" x2="{pad_l + bar_w}" y2="{y}" '
            f'stroke="#e8e8f0" stroke-width="1"/>'
            # bar
            f'<line x1="{pad_l}" y1="{y}" x2="{pad_l + bw}" y2="{y}" '
            f'stroke="{accent}" stroke-width="3" stroke-linecap="round"/>'
            # dot
            f'<circle cx="{pad_l + bw}" cy="{y}" r="6" fill="{accent}"/>'
            # value
            f'<text x="{pad_l + bw + 10}" y="{y + 5}" '
            f'font-size="12" fill="{accent}" font-weight="700">{_esc(str(val))}</text>'
        )

    return (
        f'<svg class="svg-chart" viewBox="0 0 {W} {H}" '
        f'style="max-height:{H}px">'
        + "".join(items)
        + "</svg>"
    )


def _chart_js(chart_spec: dict, brand: dict, chart_id: str) -> str:
    """Chart.js charts: bar · line · donut. SVG charts handled separately."""
    if not chart_spec:
        return ""
    ctype  = chart_spec.get("type", "bar")
    title  = _esc(chart_spec.get("title", ""))
    sub    = _esc(chart_spec.get("subtitle", ""))
    annot  = chart_spec.get("annotation", "")
    labels = json.dumps(chart_spec.get("labels", []))
    values = json.dumps(chart_spec.get("values", []))
    accent = _ensure_contrast(
        brand.get("colors", {}).get("accent",
        brand.get("colors", {}).get("primary", "#0066cc"))
    )
    lite   = _lighten(accent, 0.72)

    title_html = f'<div class="chart-finding">{title}</div>' if title else ""
    sub_html   = f'<div class="chart-subtitle">{sub}</div>' if sub else ""
    annot_html = f'<div class="chart-annotation">↑ {_esc(annot)}</div>' if annot else ""

    # ── Slope → SVG ──
    if ctype == "slope":
        svg = _slope_svg(chart_spec, accent, chart_id)
        return f'<div class="chart-wrap">{title_html}{sub_html}{annot_html}{svg}</div>'

    # ── Waffle → SVG ──
    if ctype == "waffle":
        svg = _waffle_svg(chart_spec, accent, chart_id)
        return f'<div class="chart-wrap">{title_html}{sub_html}{svg}</div>'

    # ── Lollipop → SVG ──
    if ctype == "lollipop":
        svg = _lollipop_svg(chart_spec, accent, chart_id)
        return f'<div class="chart-wrap">{title_html}{sub_html}{annot_html}{svg}</div>'

    # ── Donut ──
    if ctype == "donut":
        bg_list = json.dumps([accent, lite, "#d0d0dc", "#b0b0c0"])
        cfg = f"""{{
  type:'doughnut',
  data:{{
    labels:{labels},
    datasets:[{{data:{values},
      backgroundColor:{bg_list},
      borderWidth:0, hoverOffset:6}}]
  }},
  options:{{
    cutout:'68%', responsive:true, maintainAspectRatio:true,
    plugins:{{
      legend:{{position:'right',labels:{{font:{{size:12}},color:'#555',padding:14}}}},
      tooltip:{{callbacks:{{label:ctx=>ctx.label+': '+ctx.raw+'%'}}}}
    }}
  }}
}}"""
        return f"""<div class="chart-wrap">{title_html}{sub_html}{annot_html}
<canvas id="{chart_id}" height="200"></canvas></div>
<script>(function(){{new Chart(document.getElementById('{chart_id}').getContext('2d'),{cfg});}})()</script>"""

    # ── Line ──
    if ctype == "line":
        cfg = f"""{{
  type:'line',
  data:{{
    labels:{labels},
    datasets:[{{data:{values},
      borderColor:'{accent}',backgroundColor:'transparent',
      borderWidth:2.5,pointRadius:5,
      pointBackgroundColor:'{accent}',tension:0.35}}]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{display:false}},ticks:{{color:'#888',font:{{size:12}}}}}},
      y:{{grid:{{color:'#e8e8f0',drawBorder:false}},ticks:{{color:'#888',font:{{size:12}}}}}}
    }}
  }}
}}"""
        return f"""<div class="chart-wrap" style="height:260px">{title_html}{sub_html}
<canvas id="{chart_id}"></canvas></div>
<script>(function(){{new Chart(document.getElementById('{chart_id}').getContext('2d'),{cfg});}})()</script>"""

    # ── Bar (horizontal if many categories) ──
    is_horiz = len(chart_spec.get("labels", [])) >= 4
    bg_arr   = json.dumps([accent] * 20)
    cfg = f"""{{
  type:'bar',
  data:{{
    labels:{labels},
    datasets:[{{data:{values},
      backgroundColor:{bg_arr},
      borderRadius:4, borderSkipped:false}}]
  }},
  options:{{
    indexAxis:'{'y' if is_horiz else 'x'}',
    responsive:true, maintainAspectRatio:false,
    plugins:{{
      legend:{{display:false}},
      tooltip:{{callbacks:{{label:ctx=>' '+ctx.raw}}}}
    }},
    scales:{{
      x:{{grid:{{color:'{'transparent' if is_horiz else '#e8e8f0'}',drawBorder:false}},
          ticks:{{color:'#888',font:{{size:12}}}}}},
      y:{{grid:{{color:'{'#e8e8f0' if is_horiz else 'transparent'}',drawBorder:false}},
          ticks:{{color:'#888',font:{{size:12}}}}}}
    }}
  }}
}}"""
    h = max(220, len(chart_spec.get("labels", [])) * 40) if is_horiz else 260
    return f"""<div class="chart-wrap" style="height:{h}px">{title_html}{sub_html}{annot_html}
<canvas id="{chart_id}"></canvas></div>
<script>(function(){{new Chart(document.getElementById('{chart_id}').getContext('2d'),{cfg});}})()</script>"""


# ══════════════════════════════════════════════
# COVER ART — Abstract SVG generator
# ══════════════════════════════════════════════

def _cover_art_svg(accent: str, style: str = "clean_minimal", seed: int = 0) -> str:
    """
    Abstract geometric cover art. 6 style variants + seed variation.
    The art_type is selected from style name, seed breaks ties so same-style brands differ.
    """
    import math as _m

    style_map = {
        "clean_minimal":    0,
        "technical_precise":1,
        "startup_playful":  2,
        "bold_editorial":   3,
        "luxury_premium":   4,
        "corporate_formal": 5,
    }
    art_type = style_map.get(style, seed % 6)  # unknown style → pure seed
    W, H = 794, 1060
    s = seed  # shorthand

    if art_type == 0:
        # ── Diagonal prism slices (clean/minimal) ──
        cx = 580 + (s % 5) * 22
        cy = 320 + (s % 6) * 18
        items = []
        for i in range(5):
            x1 = W * i // 4
            x2 = W * (i+1) // 4
            y_off = 80 + (s % 4) * 20 + i * 40
            op = round(0.06 + i * 0.012 + (s % 3) * 0.008, 3)
            items.append(f'<polygon points="{x1},{y_off} {x2},{y_off-30} {x2},{y_off+60} {x1},{y_off+90}" '
                         f'fill="white" fill-opacity="{op}"/>')
        glow = (f'<circle cx="{cx}" cy="{cy}" r="260" fill="{accent}" fill-opacity="0.13"/>'
                f'<circle cx="{cx}" cy="{cy}" r="140" fill="{accent}" fill-opacity="0.18"/>'
                f'<circle cx="{cx}" cy="{cy}" r="55" fill="white" fill-opacity="0.07"/>')
        # Fine grid lines
        grid = ""
        for i in range(0, W, 40):
            grid += f'<line x1="{i}" y1="0" x2="{i}" y2="{H}" stroke="white" stroke-width="0.4" stroke-opacity="0.04"/>'
        for i in range(0, H, 40):
            grid += f'<line x1="0" y1="{i}" x2="{W}" y2="{i}" stroke="white" stroke-width="0.4" stroke-opacity="0.03"/>'
        dots = "".join(
            f'<circle cx="{W-80-col*18}" cy="{H-80-row*18}" r="2.5" fill="white" fill-opacity="{round(0.07+(row+col)%4*0.04,2)}"/>'
            for row in range(6) for col in range(8))
        return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
                f'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
                + grid + "".join(items) + glow + dots + "</svg>")

    elif art_type == 1:
        # ── Perspective grid / data mesh (technical) ──
        items = []
        vp_x = 680 + (s % 6) * 18
        vp_y = -60
        for i in range(14):
            y_start = 80 + i * 70
            op = round(0.03 + i * 0.007, 3)
            items.append(f'<line x1="0" y1="{y_start}" x2="{vp_x}" y2="{vp_y}" '
                         f'stroke="white" stroke-width="0.7" stroke-opacity="{op}"/>')
        for i in range(10):
            x = 60 + i * 80
            items.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" '
                         f'stroke="white" stroke-width="0.4" stroke-opacity="0.04"/>')
        # Data nodes
        nodes = [(620,220,55,0.22),(560,300,32,0.16),(670,350,20,0.12),(710,240,16,0.1),(590,390,12,0.09)]
        for nx, ny, nr, nop in nodes:
            nx += (s % 4) * 8
            items.append(f'<circle cx="{nx}" cy="{ny}" r="{nr}" fill="{accent}" fill-opacity="{nop}"/>')
            items.append(f'<circle cx="{nx}" cy="{ny}" r="{nr}" fill="none" stroke="white" stroke-width="0.8" stroke-opacity="0.14"/>')
        # Connect nodes
        for (ax,ay,_,__),(bx,by,___,____) in zip(nodes, nodes[1:]):
            ax+=(s%4)*8; bx+=(s%4)*8
            items.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="white" stroke-width="0.7" stroke-opacity="0.1"/>')
        return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
                f'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
                + "".join(items) + "</svg>")

    elif art_type == 2:
        # ── Flowing waves (startup/playful) ──
        items = []
        amp_base = 28 + (s % 8) * 6
        for i in range(10):
            y_base = 180 + i * 90
            op = round(0.035 + i * 0.009, 3)
            amp = amp_base + i * 7
            freq = 0.007 - i * 0.0004
            phase = (s % 5) * 0.4
            pts = " ".join(f"{x},{y_base + amp * _m.sin(freq * x + i + phase):.1f}" for x in range(0, W+1, 12))
            items.append(f'<polyline points="{pts}" fill="none" stroke="white" stroke-width="1" stroke-opacity="{op}"/>')
        for cx2, cy2, r2, off in [(680, 160, 90, 0),(640, 260, 50, 1),(700, 330, 28, 2)]:
            cx2 += (s % 4) * 10
            items.append(f'<circle cx="{cx2}" cy="{cy2}" r="{r2}" fill="{accent}" fill-opacity="0.2"/>')
        dots = "".join(
            f'<circle cx="{50+col*22}" cy="{H-80-row*18}" r="2" fill="white" fill-opacity="{round(0.06+(row+col)%3*0.04,2)}"/>'
            for row in range(5) for col in range(10))
        return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
                f'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
                + "".join(items) + dots + "</svg>")

    elif art_type == 3:
        # ── Polygon shatter (bold/editorial) ──
        items = []
        ox = (s % 4) * 15
        oy = (s % 5) * 12
        polygons = [
            ([(620+ox,40+oy),(780+ox,130+oy),(690+ox,250+oy),(550+ox,180+oy)], 0.14),
            ([(690+ox,250+oy),(800+ox,320+oy),(760+ox,440+oy),(630+ox,390+oy)], 0.09),
            ([(550+ox,180+oy),(690+ox,250+oy),(630+ox,390+oy),(510+ox,340+oy)], 0.07),
            ([(480+ox,70+oy),(620+ox,40+oy),(550+ox,180+oy),(430+ox,160+oy)], 0.08),
            ([(760+ox,440+oy),(W,500+oy),(W-30+ox,620+oy),(700+ox,560+oy)], 0.06),
        ]
        for pts_raw, op in polygons:
            # clamp to SVG bounds
            pts = [(min(W,max(0,x)), min(H,max(0,y))) for x,y in pts_raw]
            pt_str = " ".join(f"{x},{y}" for x,y in pts)
            items.append(f'<polygon points="{pt_str}" fill="white" fill-opacity="{op}"/>')
            items.append(f'<polygon points="{pt_str}" fill="none" stroke="white" stroke-width="0.8" stroke-opacity="0.2"/>')
        # Accent glow
        gcx = 660 + (s % 5) * 14
        items.append(f'<circle cx="{gcx}" cy="200" r="150" fill="{accent}" fill-opacity="0.22"/>')
        items.append(f'<circle cx="{gcx}" cy="200" r="70" fill="{accent}" fill-opacity="0.18"/>')
        return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
                f'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
                + "".join(items) + "</svg>")

    elif art_type == 4:
        # ── Concentric elegant rings (luxury/premium) ──
        items = []
        cx = 680 + (s % 5) * 16
        cy = 300 + (s % 6) * 14
        for i, (r, op, sw) in enumerate([(320,0.06,1.2),(240,0.09,0.9),(170,0.12,0.7),(110,0.16,0.5),(60,0.22,0.4),(25,0.3,0.3)]):
            items.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                         f'stroke="white" stroke-width="{sw}" stroke-opacity="{op}" '
                         f'stroke-dasharray="{4+i*2} {8+i*3}"/>')
        items.append(f'<circle cx="{cx}" cy="{cy}" r="220" fill="{accent}" fill-opacity="0.12"/>')
        items.append(f'<circle cx="{cx}" cy="{cy}" r="90" fill="{accent}" fill-opacity="0.18"/>')
        items.append(f'<circle cx="{cx}" cy="{cy}" r="25" fill="white" fill-opacity="0.1"/>')
        # Bottom-left accent arc
        bx, by = 60 + (s%3)*20, H-80
        for r2 in [200, 140, 90, 50]:
            items.append(f'<circle cx="{bx}" cy="{by}" r="{r2}" fill="none" '
                         f'stroke="white" stroke-width="0.6" stroke-opacity="0.06"/>')
        items.append(f'<circle cx="{bx}" cy="{by}" r="28" fill="{accent}" fill-opacity="0.28"/>')
        # Sparse dot grid
        dots = "".join(
            f'<circle cx="{W-60-col*16}" cy="{H-60-row*16}" r="1.8" fill="white" fill-opacity="{round(0.06+(row+col)%3*0.03,2)}"/>'
            for row in range(8) for col in range(10))
        return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
                f'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
                + "".join(items) + dots + "</svg>")

    else:
        # ── Structured column bars (corporate/formal) ──
        items = []
        bar_w = 60 + (s % 4) * 8
        bar_gap = 22 + (s % 3) * 4
        x_start = W - 200 + (s % 5) * 10
        for i, (bh, op) in enumerate([(420,0.09),(300,0.07),(500,0.11),(240,0.06),(360,0.08)]):
            bh += (s % 4) * 20
            bx = x_start + i * (bar_w + bar_gap)
            if bx + bar_w < W + 100:
                items.append(f'<rect x="{bx}" y="{H-bh}" width="{bar_w}" height="{bh}" '
                             f'fill="white" fill-opacity="{op}" rx="2"/>')
        # Horizontal rule lines
        for i in range(6):
            y2 = 80 + i * 120
            items.append(f'<line x1="0" y1="{y2}" x2="{W}" y2="{y2}" '
                         f'stroke="white" stroke-width="0.5" stroke-opacity="0.05"/>')
        # Accent block top-right
        items.append(f'<rect x="{W-180}" y="0" width="180" height="8" fill="{accent}" fill-opacity="0.6"/>')
        items.append(f'<circle cx="{W-90}" cy="60" r="80" fill="{accent}" fill-opacity="0.15"/>')
        return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
                f'style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none">'
                + "".join(items) + "</svg>")


# ══════════════════════════════════════════════
# SECTION RENDERERS
# ══════════════════════════════════════════════

def render_page_header(company: str, section_name: str, page_num: int, logo_b64: str) -> str:
    logo_html = (
        f'<img class="logo-mark" src="{logo_b64}" '
        f'style="height:18px;object-fit:contain" alt="{_esc(company)}">'
        if logo_b64 else
        f'<span class="logo-mark">{_esc(company[:2].upper())}</span>'
    )
    return (
        f'<div class="page-header">'
        f'{logo_html}'
        f'<span>{_esc(company)} · {_esc(section_name)}</span>'
        f'<span>Page {page_num}</span></div>'
    )


def render_page_footer(company: str, section_name: str, page_num: int, logo_b64: str) -> str:
    logo_html = (
        f'<img src="{logo_b64}" '
        f'style="height:13px;object-fit:contain;opacity:.4;filter:brightness(0)" alt="">'
        if logo_b64 else
        f'<span style="font-weight:800;font-size:12px;color:var(--accent)">'
        f'{_esc(company[:1])}</span>'
    )
    return (
        f'<div class="page-footer">'
        f'{logo_html}'
        f'<span>{_esc(section_name)}</span>'
        f'<span class="page-num">{page_num}</span></div>'
    )


def render_section(section: dict, brand: dict, page_num: int, logo_b64: str, company: str) -> str:
    stype   = section.get("type", "narrative")
    heading = section.get("heading", "")
    chip    = section.get("chip", "")
    num     = section.get("number")
    content = section.get("content", {})
    body    = content.get("body", "")
    sid     = section.get("id", f"s{page_num}")
    chart_id = f"chart-{sid}-{page_num}"

    accent = _ensure_contrast(
        brand.get("colors", {}).get("accent",
        brand.get("colors", {}).get("primary", "#0066cc"))
    )

    header = render_page_header(company, heading, page_num, logo_b64)
    footer = render_page_footer(company, heading, page_num, logo_b64)

    chip_html = f'<div class="sec-chip">{_esc(chip)}</div>' if chip else ""
    num_html  = (f'<div class="sec-num">{"0"+str(num) if num and num < 10 else str(num)}'
                 f' / {_esc(company)}</div>') if num else ""
    dots_br   = _dot_grid(64, "dot-grid dot-grid-br")

    # ── CHAPTER DIVIDER ──────────────────────────────────────────────
    if stype == "chapter_divider":
        ch_num = f"0{num}" if num and num < 10 else str(num or "")
        return f"""{header}
<div class="chapter-div">
  <div class="ch-accent-bar"></div>
  <div class="ch-num-bg">{ch_num}</div>
  <div class="ch-content">
    {chip_html}
    <h2>{_accent_headline(heading)}</h2>
    <p>{_esc((body or "")[:240])}</p>
  </div>
  {dots_br}
</div>
{footer}"""

    # ── FULL-BLEED PULL QUOTE ─────────────────────────────────────────
    if stype == "pull_quote":
        quote = content.get("quote", {})
        qt   = (quote.get("text", body) if quote else body) or ""
        attr = (quote.get("attribution", "") if quote else "") or ""
        attr_html = f'<div class="pull-quote-attr">{_esc(attr)}</div>' if attr else ""
        return f"""{header}
<div class="section-quote">
  <div class="q-bg-mark">"</div>
  <span class="pq-mark">"</span>
  <div class="pull-quote-text">{_esc(qt)}</div>
  {attr_html}
  {dots_br}
</div>
{footer}"""

    # ── CONCLUSION ────────────────────────────────────────────────────
    if stype == "conclusion":
        body_html = _md_to_html(body, drop_cap=True)
        return f"""{header}
<div class="conclusion">
  <div class="bg-num-dark">✦</div>
  {chip_html}
  <div class="accent-rule-short"></div>
  <h2 class="sec-heading" style="color:#fff">{_accent_headline(heading)}</h2>
  <div style="height:22px"></div>
  <div class="body-text body-text-white">{body_html}</div>
  {dots_br}
</div>
<div class="section-end-dark"></div>
{footer}"""

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────────
    if stype == "executive_summary":
        stats = content.get("stats", [])
        paras = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
        lead  = paras[0] if paras else ""
        rest  = _md_to_html("\n\n".join(paras[1:]), drop_cap=False)

        stat_cards = ""
        if stats:
            cards = ""
            for s in stats:
                val   = _esc(str(s.get("value", "")))
                unit  = _esc(str(s.get("unit", "")))
                label = _esc(str(s.get("label", "")))
                cards += (f'<div class="stat-card">'
                          f'<div class="stat-num" style="{_stat_font_size(val)}">{val}'
                          f'<span class="stat-unit">{unit}</span></div>'
                          f'<div class="stat-lbl">{label}</div></div>')
            stat_cards = f'<div class="stat-grid">{cards}</div>'

        chart_spec = content.get("chart")
        chart_html = _chart_js(chart_spec, brand, chart_id) if chart_spec else ""

        return f"""{header}
<div class="section">
  <div class="bg-num" style="top:0;opacity:.04">01</div>
  {dots_br}
  {chip_html}
  <div class="accent-rule"></div>
  <h2 class="sec-heading">{_accent_headline(heading)}</h2>
  <div style="height:26px"></div>
  {stat_cards}
  <div class="exec-lead">{_esc(lead)}</div>
  <div class="body-text">{rest}</div>
  {chart_html}
</div>
<div class="section-end"></div>
{footer}"""

    # ── KEY METRICS ───────────────────────────────────────────────────
    if stype == "key_metrics":
        stats = content.get("stats", [])
        cards = ""
        for s in stats:
            val   = _esc(str(s.get("value", "")))
            unit  = _esc(str(s.get("unit", "")))
            label = _esc(str(s.get("label", "")))
            cards += (f'<div class="stat-card">'
                      f'<div class="stat-num" style="{_stat_font_size(val)}">{val}'
                      f'<span class="stat-unit">{unit}</span></div>'
                      f'<div class="stat-lbl">{label}</div></div>')

        chart_spec = content.get("chart")
        chart_html = _chart_js(chart_spec, brand, chart_id) if chart_spec else ""
        body_html  = _md_to_html(body) if body else ""

        return f"""{header}
<div class="section">
  <div class="bg-num" style="opacity:.04">02</div>
  {dots_br}
  {chip_html}
  <div class="accent-rule"></div>
  <h2 class="sec-heading">{_accent_headline(heading)}</h2>
  <div class="stat-grid">{cards}</div>
  {chart_html}
  {f'<div class="body-text" style="margin-top:20px">{body_html}</div>' if body_html else ''}
</div>
<div class="section-end"></div>
{footer}"""

    # ── RECOMMENDATIONS ───────────────────────────────────────────────
    if stype == "recommendations":
        items     = content.get("items", [])
        items_html = ""
        for i, item in enumerate(items, 1):
            # Try to split "Heading: detail" format
            text = str(item)
            if ": " in text:
                h_part, d_part = text.split(": ", 1)
                item_inner = (f'<div class="rec-heading">{_esc(h_part)}</div>'
                              f'<div class="rec-text">{_esc(d_part)}</div>')
            else:
                item_inner = f'<div class="rec-text">{_esc(text)}</div>'

            items_html += f"""<li class="rec-item">
  <div class="rec-num-wrap">
    <div class="rec-num-bg">{i}</div>
    <div class="rec-num">{i:02d}</div>
  </div>
  <div>{item_inner}</div>
</li>"""

        body_html = _md_to_html(body) if body else ""
        return f"""{header}
<div class="section">
  {dots_br}
  {chip_html}
  <div class="accent-rule"></div>
  <h2 class="sec-heading">{_accent_headline(heading)}</h2>
  {f'<div class="body-text" style="margin-bottom:26px">{body_html}</div>' if body_html else ''}
  <ul class="rec-list">{items_html}</ul>
</div>
<div class="section-end"></div>
{footer}"""

    # ── DATA TABLE ────────────────────────────────────────────────────
    if stype == "data_table":
        table   = content.get("table", {})
        headers = table.get("headers", [])
        rows    = table.get("rows", [])
        thead   = "<tr>" + "".join(f"<th>{_esc(h)}</th>" for h in headers) + "</tr>"
        tbody   = "".join(
            "<tr>" + "".join(f"<td>{_esc(str(cell))}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        body_html = _md_to_html(body) if body else ""
        return f"""{header}
<div class="section">
  {dots_br}
  {chip_html}
  <div class="accent-rule"></div>
  <h2 class="sec-heading">{_accent_headline(heading)}</h2>
  {f'<div class="body-text" style="margin-bottom:20px">{body_html}</div>' if body_html else ''}
  <div class="data-table-wrapper">
    <table class="data-table"><thead>{thead}</thead><tbody>{tbody}</tbody></table>
  </div>
</div>
<div class="section-end"></div>
{footer}"""

    # ── NARRATIVE (default) ───────────────────────────────────────────
    paras = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    chart_spec = content.get("chart")
    chart_html = _chart_js(chart_spec, brand, chart_id) if chart_spec else ""

    pq_candidate = _best_pull_quote(body)
    pq_html = ""
    if pq_candidate and len(paras) >= 3:
        pq_html = f"""<div class="pull-quote">
  <span class="pq-mark">"</span>
  <div class="pull-quote-text">{_esc(pq_candidate)}</div>
</div>"""

    mid = max(len(paras) // 2, 1)
    left_paras  = paras[:mid]
    right_paras = paras[mid:]

    left_html  = _md_to_html("\n\n".join(left_paras), drop_cap=True)
    right_html = _md_to_html("\n\n".join(right_paras))

    right_col = f"{pq_html}{right_html or ''}{chart_html}"

    if len(paras) > 2 and (pq_html or chart_html):
        body_block = f"""<div class="body-two-col">
  <div class="body-text">{left_html}</div>
  <div>{right_col}</div>
</div>"""
    else:
        all_html = _md_to_html(body, drop_cap=True)
        body_block = f'<div class="body-text">{all_html}</div>'
        if chart_html:
            body_block += f'<div style="margin-top:20px">{chart_html}</div>'

    return f"""{header}
<div class="section">
  {dots_br}
  {chip_html}
  {num_html}
  <div class="accent-rule"></div>
  <h2 class="sec-heading">{_accent_headline(heading)}</h2>
  <div style="height:22px"></div>
  {body_block}
</div>
<div class="section-end"></div>
{footer}"""


# ══════════════════════════════════════════════
# COVER RENDERER
# ══════════════════════════════════════════════

def render_cover(structured: dict, brand: dict, logo_b64: str) -> str:
    company  = brand.get("company", "Company")
    title    = structured.get("title", "Report")
    subtitle = structured.get("subtitle", "")
    prepared = structured.get("prepared_by", "Brand Report Studio")
    date_str = datetime.now().strftime("%B %Y")
    accent   = _ensure_contrast(
        brand.get("colors", {}).get("accent",
        brand.get("colors", {}).get("primary", "#0066cc")),
        on_dark=True
    )

    logo_html = (
        f'<img src="{logo_b64}" '
        f'style="height:26px;object-fit:contain;filter:brightness(10);opacity:.65" '
        f'alt="{_esc(company)}">'
        if logo_b64 else
        f'<span class="cover-brand">{_esc(company)}</span>'
    )

    # Abstract SVG cover art — derive style from brand, then hue-based fallback
    dl    = brand.get("design_language", {})
    style = dl.get("style", "clean_minimal")

    # Hue-based fallback: if still clean_minimal, infer from accent color
    if style == "clean_minimal":
        try:
            r2, g2, b2 = _hex_to_rgb(accent)
            mx = max(r2, g2, b2); mn = min(r2, g2, b2)
            delta = mx - mn
            lum = (0.299 * r2 + 0.587 * g2 + 0.114 * b2) / 255
            sat = delta / mx if mx else 0
            if sat < 0.18:
                style = "corporate_formal"
            elif sat > 0.65 and lum < 0.28:
                style = "bold_editorial"
            else:
                hue = 0.0
                if delta > 0:
                    if mx == r2: hue = 60 * (((g2 - b2) / delta) % 6)
                    elif mx == g2: hue = 60 * ((b2 - r2) / delta + 2)
                    else: hue = 60 * ((r2 - g2) / delta + 4)
                if hue < 0: hue += 360
                if (hue < 25 or hue > 335) and sat > 0.45:
                    style = "bold_editorial"
                elif 25 <= hue < 75 and sat > 0.4:
                    style = "startup_playful"
                elif 160 <= hue < 260 and sat > 0.4:
                    style = "technical_precise"
                elif 260 <= hue < 335 and sat > 0.35:
                    style = "luxury_premium"
        except Exception:
            pass

    seed = sum(ord(c) for c in company) % 100
    art   = _cover_art_svg(accent, style, seed)

    return f"""<div class="cover">
  <div class="cover-art">{art}</div>
  <div class="cover-nav">
    {logo_html}
    <span class="cover-year">{date_str}</span>
  </div>
  <div class="cover-body">
    <div class="cover-eyebrow">Intelligence Report · {_esc(company)}</div>
    <div class="cover-rule"></div>
    <div class="cover-title">{_accent_headline(title)}</div>
    {f'<div class="cover-subtitle">{_esc(subtitle)}</div>' if subtitle else ''}
    <div class="cover-meta">{_esc(prepared)} · {date_str}</div>
  </div>
  <div class="cover-footer">
    <span>Prepared by Brand Report Studio</span>
    <span>Confidential · {date_str}</span>
  </div>
</div>"""


# ══════════════════════════════════════════════
# MAIN HTML ASSEMBLER
# ══════════════════════════════════════════════

def generate_html(structured: dict, brand: dict, brand_dir: Path, report_title: str) -> str:
    company  = brand.get("company", "Company")
    assets   = brand.get("assets", {})
    logo_rel = assets.get("logo_svg") or assets.get("logo_png") or ""
    logo_path = brand_dir / logo_rel if logo_rel else None
    logo_b64  = load_asset_b64(logo_path) if logo_path and Path(logo_path).is_file() else ""

    css    = build_css(brand)
    cover  = render_cover(structured, brand, logo_b64)

    sections_html = []
    for i, section in enumerate(structured.get("sections", [])):
        sections_html.append(
            render_section(section, brand, i + 2, logo_b64, company)
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(report_title)} — {_esc(company)}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
  <style>{css}</style>
</head>
<body>
<div class="rp">
  {cover}
  {''.join(sections_html)}
</div>
</body>
</html>"""


# ══════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate a branded magazine report")
    parser.add_argument("--brand",    required=True, help="Path to brands/<slug> directory")
    parser.add_argument("--describe", help="Describe the report you want")
    parser.add_argument("--content",  help="Path to raw content file")
    parser.add_argument("--title",    help="Report title")
    parser.add_argument("--out",      help="Output HTML path")
    args = parser.parse_args()

    brand_dir  = Path(args.brand)
    brand_json = brand_dir / "brand.json"
    if not brand_json.exists():
        print(f"Error: {brand_json} not found. Run brand_scrape.py first.", file=sys.stderr)
        sys.exit(1)

    brand = json.loads(brand_json.read_text())
    report_title = args.title or f"{brand.get('company', 'Company')} Report"

    noop = lambda p, s: ""
    structured = (
        structure_content(noop, Path(args.content).read_text(), brand) if args.content
        else generate_content(noop, args.describe, brand) if args.describe
        else (print("Error: provide --describe or --content", file=sys.stderr) or sys.exit(1))
    )

    html      = generate_html(structured, brand, brand_dir, report_title)
    out_path  = args.out or str(brand_dir / "reports" / f"{report_title.replace(' ','_')}.html")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html)
    print(f"✓ Report saved → {out_path}")


if __name__ == "__main__":
    main()
