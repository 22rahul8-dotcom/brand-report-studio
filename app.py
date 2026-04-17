#!/usr/bin/env python3
"""
Webscraper — Local web scraping tool powered by Firecrawl.
Run: python3 app.py
Then open http://localhost:5000
"""

import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


# ── Global error handlers (backstop — returns JSON instead of Flask HTML) ──────
@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": str(e) or "Internal server error — please try again"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()
    return jsonify({"error": str(e) or "Unexpected server error — please try again"}), 500


# ── Firecrawl call with timeout ────────────────────────────────────────────────
def _firecrawl_scrape(client, url: str, formats: list, timeout_sec: int = 22):
    """
    Run client.scrape() in a thread with a hard timeout.
    Raises RuntimeError if it takes longer than timeout_sec (prevents Render 30s kill).
    """
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(client.scrape, url, formats=formats)
        try:
            return fut.result(timeout=timeout_sec)
        except FutureTimeout:
            raise RuntimeError(
                f"Scraping timed out after {timeout_sec}s — "
                "this site may be slow or bot-protected. Try the homepage URL."
            )


def _firecrawl_error_msg(e: Exception) -> str:
    """Extract a clean error message from any Firecrawl exception."""
    msg = str(e)
    # FirecrawlError stores status_code; surface it cleanly
    status = getattr(e, 'status_code', None)
    if status == 402:
        return "Firecrawl payment required — check your plan/credits at firecrawl.dev"
    if status == 401:
        return "Firecrawl API key invalid or missing — set FIRECRAWL_API_KEY"
    if status == 403:
        return "Website blocked by Firecrawl — this site may not allow scraping"
    if status == 429:
        return "Firecrawl rate limit hit — wait a moment and retry"
    if status == 501:
        return "Firecrawl format not supported for this URL (501)"
    if status == 500:
        return "Firecrawl server error scraping this URL — try again or use a different URL"
    if status == 422:
        return "Firecrawl could not process this URL — try the homepage instead"
    # Never return empty — always give a useful fallback
    return msg or (f"Firecrawl error (status {status})" if status else "Unknown scraping error — check the URL and try again")

# ---------------------------------------------------------------------------
# Firecrawl client
# ---------------------------------------------------------------------------

def get_client():
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FIRECRAWL_API_KEY environment variable is not set. "
            "Get your key from https://firecrawl.dev and run:\n"
            "  export FIRECRAWL_API_KEY='fc-YOUR-API-KEY'"
        )
    from firecrawl import Firecrawl
    return Firecrawl(api_key=api_key)


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes — API
# ---------------------------------------------------------------------------

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Scrape a single URL."""
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL is required"}), 400

        formats = data.get("formats", ["markdown"])
        only_main = data.get("onlyMainContent", True)
        max_age = data.get("maxAge")

        # Location
        location = None
        country = data.get("country")
        if country:
            location = {"country": country}
            langs = data.get("languages")
            if langs:
                location["languages"] = [l.strip() for l in langs.split(",")]

        # Actions
        actions = data.get("actions")

        client = get_client()
        kwargs = {
            "formats": formats,
            "only_main_content": only_main,
        }
        if location:
            kwargs["location"] = location
        if max_age is not None:
            kwargs["max_age"] = int(max_age)
        if actions:
            kwargs["actions"] = actions

        result = client.scrape(url, **kwargs)

        return jsonify({
            "success": True,
            "data": _serialize(result),
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract", methods=["POST"])
def api_extract():
    """Extract structured JSON from a URL."""
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL is required"}), 400

        prompt = data.get("prompt", "").strip()
        schema_raw = data.get("schema", "").strip()

        json_fmt = {"type": "json"}
        if schema_raw:
            json_fmt["schema"] = json.loads(schema_raw)
        if prompt:
            json_fmt["prompt"] = prompt

        if "schema" not in json_fmt and "prompt" not in json_fmt:
            return jsonify({"error": "Provide a prompt or JSON schema"}), 400

        client = get_client()
        result = client.scrape(url, formats=[json_fmt])

        return jsonify({
            "success": True,
            "data": _serialize(result),
            "timestamp": datetime.now().isoformat(),
        })

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Invalid JSON schema: {e}"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/batch", methods=["POST"])
def api_batch():
    """Batch scrape multiple URLs."""
    try:
        data = request.get_json()
        urls_raw = data.get("urls", "").strip()
        if not urls_raw:
            return jsonify({"error": "URLs are required (one per line)"}), 400

        urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
        if not urls:
            return jsonify({"error": "No valid URLs found"}), 400

        formats = data.get("formats", ["markdown"])

        client = get_client()
        result = client.batch_scrape(
            urls,
            formats=formats,
            poll_interval=2,
            wait_timeout=120,
        )

        return jsonify({
            "success": True,
            "data": _serialize(result),
            "count": len(urls),
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/brand", methods=["POST"])
def api_brand():
    """Extract brand identity from a URL."""
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL is required"}), 400

        client = get_client()

        # Try with screenshot first; fall back to branding-only; then markdown.
        # Retry on any Firecrawl scrape error EXCEPT hard failures (auth/billing/rate-limit).
        # Hard failures (401, 402, 403, 429) mean something the user must fix — surface immediately.
        HARD_FAIL_STATUSES = {401, 402, 403, 429}
        result = None
        last_err = None
        for fmt_set in [["branding", "screenshot"], ["branding"], ["markdown"]]:
            try:
                result = _firecrawl_scrape(client, url, fmt_set, timeout_sec=22)
                break
            except Exception as e:
                status = getattr(e, 'status_code', None)
                if status in HARD_FAIL_STATUSES:
                    return jsonify({"error": _firecrawl_error_msg(e)}), 500
                # Timeout, 501, 500, 422, or other transient → try simpler format
                last_err = e
                continue

        if result is None:
            err_msg = _firecrawl_error_msg(last_err) if last_err else "Could not scrape this URL — try the homepage"
            return jsonify({"error": err_msg}), 500

        return jsonify({
            "success": True,
            "data": _serialize(result),
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": _firecrawl_error_msg(e)}), 500


@app.route("/api/suggest-topics", methods=["POST"])
def api_suggest_topics():
    """Suggest report topics based on the brand URL and scraped content."""
    try:
        data    = request.get_json()
        url     = data.get("url", "").strip()
        company = data.get("company", "this company")

        # ── Always-available generic topics ──
        generic_topics = [
            {"id": "sales",       "label": "Sales Report",           "icon": "📈", "desc": "Revenue trends, sales performance, growth metrics and forecasts"},
            {"id": "marketing",   "label": "Marketing Strategy",     "icon": "🎯", "desc": "Brand positioning, campaign effectiveness, audience insights"},
            {"id": "product",     "label": "Product Analysis",       "icon": "📦", "desc": "Product portfolio review, pricing strategy, top performers"},
            {"id": "competitor",  "label": "Competitor Intelligence", "icon": "🔍", "desc": "Market landscape, competitive positioning, differentiation"},
            {"id": "customer",    "label": "Customer Insights",      "icon": "👥", "desc": "Customer segments, behaviour patterns, loyalty & retention"},
            {"id": "brand",       "label": "Brand Audit",            "icon": "✨", "desc": "Brand identity, messaging consistency, visual language review"},
            {"id": "growth",      "label": "Growth Strategy",        "icon": "🚀", "desc": "Expansion opportunities, new markets, strategic priorities"},
            {"id": "digital",     "label": "Digital Presence",       "icon": "🌐", "desc": "Website performance, SEO, social media, content strategy"},
        ]

        # ── Brand-specific suggestions (rule-based from URL + company name) ──
        brand_topics = []
        url_lower    = url.lower()
        company_lower = company.lower()

        if any(k in url_lower for k in ["shop", "store", "ecom", "product", "buy", "cart"]):
            brand_topics += [
                {"id": "inventory",   "label": "Inventory & Stock Report",  "icon": "🗂️",  "desc": "Stock levels, sell-through rates, reorder strategy"},
                {"id": "conversion",  "label": "Conversion Funnel Report",  "icon": "🔄",  "desc": "Cart abandonment, checkout friction, conversion optimisation"},
                {"id": "category",    "label": "Category Performance",      "icon": "🏷️",  "desc": "Revenue by category, top SKUs, seasonal demand patterns"},
            ]
        if any(k in url_lower for k in ["tech", "software", "saas", "app", "platform", "ai", "cloud"]):
            brand_topics += [
                {"id": "product-led", "label": "Product-Led Growth",        "icon": "⚙️",  "desc": "PLG metrics, activation rates, feature adoption, NPS"},
                {"id": "mrr",         "label": "MRR & Revenue Report",      "icon": "💰",  "desc": "Monthly recurring revenue, churn, expansion revenue"},
                {"id": "roadmap",     "label": "Product Roadmap Review",    "icon": "🗺️",  "desc": "Feature pipeline, release cadence, user feedback themes"},
            ]
        if any(k in url_lower for k in ["fashion", "cloth", "wear", "style", "apparel", "dress"]):
            brand_topics += [
                {"id": "collection",  "label": "Collection Launch Report",  "icon": "👗",  "desc": "New collection performance, style trends, sell-out velocity"},
                {"id": "seasonal",    "label": "Seasonal Strategy",         "icon": "🌿",  "desc": "Season-by-season performance, demand planning, markdowns"},
            ]
        if any(k in url_lower for k in ["food", "restaurant", "kitchen", "eat", "drink", "cafe"]):
            brand_topics += [
                {"id": "menu",        "label": "Menu Performance Report",   "icon": "🍽️",  "desc": "Best sellers, margin by item, seasonal menu planning"},
                {"id": "footfall",    "label": "Footfall & Covers Report",  "icon": "📍",  "desc": "Customer visits, peak hours, table utilisation"},
            ]
        if any(k in url_lower for k in ["health", "wellness", "fitness", "clinic", "pharma", "med"]):
            brand_topics += [
                {"id": "patient",     "label": "Patient / Client Report",   "icon": "🏥",  "desc": "Acquisition, retention, treatment outcomes, satisfaction"},
                {"id": "service-mix", "label": "Service Mix Analysis",      "icon": "💊",  "desc": "Revenue by service line, utilisation rates, capacity"},
            ]

        # Deduplicate and limit brand topics
        seen = {t["id"] for t in generic_topics}
        unique_brand = [t for t in brand_topics if t["id"] not in seen][:5]

        return jsonify({
            "success":       True,
            "generic_topics": generic_topics,
            "brand_topics":   unique_brand,
            "company":        company,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _get_llm_client():
    """Return (openai_client, models_list) for whichever LLM key is configured.
    Prefers GROQ_API_KEY, falls back to OPENROUTER_API_KEY. Returns (None, []) if neither set."""
    from openai import OpenAI as OpenAIClient
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        return (
            OpenAIClient(api_key=groq_key, base_url="https://api.groq.com/openai/v1"),
            ["llama-3.3-70b-versatile"],
        )
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        return (
            OpenAIClient(api_key=or_key, base_url="https://openrouter.ai/api/v1"),
            ["google/gemma-3-27b-it:free", "nousresearch/hermes-3-llama-3.1-405b:free", "nvidia/nemotron-3-super-120b-a12b:free"],
        )
    return None, []


@app.route("/api/enhance-topic", methods=["POST"])
def api_enhance_topic():
    """Enhance/expand a report description using Groq LLM."""
    try:
        data    = request.get_json()
        topic   = data.get("topic", "").strip()
        company = data.get("company", "the company")
        url     = data.get("url", "")

        if not topic:
            return jsonify({"error": "Topic is required"}), 400

        llm_client, _enhance_models = _get_llm_client()
        if llm_client:
            prompt = f"""You are a business analyst. Expand this report brief into a detailed, specific report description (2-3 sentences, max 60 words).

Company: {company}
Brief: {topic}

Return ONLY the enhanced description. No preamble, no quotes."""
            enhanced = None
            for _m in _enhance_models:
                try:
                    _r = llm_client.chat.completions.create(
                        model=_m,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=120,
                        temperature=0.4,
                    )
                    _txt = _r.choices[0].message.content.strip().strip('"').strip("'") if _r.choices else ""
                    if _txt and "rate-limited" not in _txt.lower():
                        enhanced = _txt
                        break
                except Exception:
                    continue
            if not enhanced:
                enhanced = topic  # fallback to original if all models failed
        else:
            # Rule-based enhancement without LLM
            expansions = {
                "sales":      f"Analyse {company}'s sales performance including revenue trends, quarter-over-quarter growth, top-performing products, and a 2026 forecast with strategic recommendations.",
                "marketing":  f"Review {company}'s marketing strategy covering brand positioning, channel performance, audience segmentation, campaign ROI, and key opportunities to improve reach and conversion.",
                "product":    f"Evaluate {company}'s product portfolio including pricing strategy, category performance, bestsellers, product gaps, and recommendations for new launches in 2026.",
                "competitor": f"Map the competitive landscape for {company}: identify key competitors, analyse positioning gaps, assess strengths and weaknesses, and outline differentiation opportunities.",
                "customer":   f"Profile {company}'s customer base covering key segments, purchase behaviour, lifetime value, churn patterns, and loyalty improvement strategies for 2026.",
                "growth":     f"Outline {company}'s growth strategy for 2026 including market expansion, new revenue streams, partnership opportunities, and key milestones.",
            }
            # Try to match keywords from the topic
            enhanced = topic
            for key, val in expansions.items():
                if key in topic.lower():
                    enhanced = val
                    break
            if enhanced == topic:
                enhanced = (f"Analyse {company}'s performance for this focus area: {topic}. "
                            f"Include key metrics, trends, challenges, and strategic recommendations for 2026.")

        return jsonify({"success": True, "enhanced": enhanced})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Routes — Report Generator
# ---------------------------------------------------------------------------

@app.route("/api/report", methods=["POST"])
def api_report():
    """Generate a branded magazine report using scraped content — no LLM required."""
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "Company URL is required"}), 400

        title = data.get("title", "").strip()

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "brand-report", "scripts"))
        import brand_scrape
        import generate_report
        from pathlib import Path

        # Phase 1-2: Extract brand identity + scrape content
        brand = brand_scrape.scrape_brand(url, output_dir=os.path.join(os.path.dirname(__file__), "brands"))
        slug = brand.get("slug", "company")
        brand_dir_path = os.path.join(os.path.dirname(__file__), "brands", slug)

        # Scrape the page markdown
        firecrawl = get_client()
        result = _firecrawl_scrape(firecrawl, url, ["markdown"], timeout_sec=22)
        markdown = getattr(result, "markdown", None) or ""

        company = brand.get("company", slug.title())
        report_title = title or f"{company} — Company Overview"

        # Phase 3: Structure content with Groq or OpenRouter
        llm_client, llm_models = _get_llm_client()
        if llm_client and markdown:
            structured = _structure_with_groq(llm_client, markdown, company, report_title, data.get("describe", ""), models=llm_models)
        else:
            structured = _auto_structure(markdown, company, report_title, data.get("describe", ""))

        if title:
            structured["title"] = title

        # Phase 4: Render HTML
        html = generate_report.generate_html(structured, brand, Path(brand_dir_path), report_title)

        return jsonify({
            "success": True,
            "html": html,
            "report_title": report_title,
            "company": company,
            "sections": len(structured.get("sections", [])),
            "style": brand.get("design_language", {}).get("style", ""),
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _structure_with_groq(client, markdown: str, company: str, title: str, describe: str = "", models: list = None) -> dict:
    """Use Groq or OpenRouter to structure scraped content into magazine sections."""
    import re, json as _json

    # Clean the markdown before sending to LLM
    clean_md = _clean_scraped_markdown(markdown)

    topic_instruction = ""
    if describe:
        topic_instruction = f"""CRITICAL — THIS REPORT IS SPECIFICALLY ABOUT: "{describe}"
Every section MUST be written through this lens. Do NOT produce a generic company overview.
- If this is competitor intelligence: map rivals, benchmark positioning, identify gaps
- If this is a product roadmap: outline H1/H2 feature priorities, delivery milestones, adoption metrics
- If this is a sales report: analyse revenue channels, product mix performance, growth levers
- If this is marketing strategy: audit brand voice, channel ROI, campaign effectiveness
- If this is customer insights: profile segments, retention economics, loyalty lifecycle
All metrics, sections, recommendations, and conclusions must be DIRECTLY relevant to the requested topic.

"""
    prompt = f"""{topic_instruction}You are a senior business analyst and magazine layout director creating a premium report for {company}.
Report topic: {describe or "Company Overview"}

MANDATORY: Generate ALL section types listed below. No section may be omitted.
1. executive_summary — 3-paragraph overview framed around the specific report topic + stats array of 4 relevant metrics
2. key_metrics — 5-6 stat cards relevant to the topic + a slope/bar chart
3. narrative — 2 analysis sections, each 3+ paragraphs, directly about the topic with charts
4. pull_quote — 1 powerful insight quote relevant to the topic
5. recommendations — 5 actionable recommendations specific to the topic in "Heading: detail" format
6. conclusion — 3-paragraph closing specific to the topic

Return ONLY valid JSON (no markdown, no backticks) with EXACTLY this structure:
{{
  "title": "{title}",
  "subtitle": "compelling one-line subtitle",
  "prepared_by": "Webscraper Intelligence",
  "sections": [
    {{
      "id": "exec-summary",
      "type": "executive_summary",
      "heading": "Executive Summary",
      "number": null,
      "content": {{"body": "3 detailed paragraphs about the company\\n\\nParagraph 2\\n\\nParagraph 3"}}
    }},
    {{
      "id": "metrics",
      "type": "key_metrics",
      "heading": "Key Metrics",
      "number": null,
      "content": {{
        "stats": [
          {{"label": "Annual Revenue", "value": "$1.2B", "unit": ""}},
          {{"label": "YoY Growth", "value": "42", "unit": "%"}},
          {{"label": "Enterprise Customers", "value": "6,000+", "unit": ""}},
          {{"label": "Countries Served", "value": "85", "unit": ""}}
        ]
      }}
    }},
    {{
      "id": "section-1",
      "type": "narrative",
      "heading": "Section Title",
      "number": 1,
      "content": {{"body": "paragraph 1\\n\\nparagraph 2\\n\\nparagraph 3"}}
    }},
    {{
      "id": "quote-1",
      "type": "pull_quote",
      "heading": "",
      "number": null,
      "content": {{"quote": {{"text": "An impactful quote about the company", "attribution": "Company Tagline"}}}}
    }},
    {{
      "id": "recs",
      "type": "recommendations",
      "heading": "Strategic Recommendations",
      "number": 4,
      "content": {{
        "items": ["Recommendation 1", "Recommendation 2", "Recommendation 3", "Recommendation 4"]
      }}
    }},
    {{
      "id": "conclusion",
      "type": "conclusion",
      "heading": "Conclusion",
      "number": 5,
      "content": {{"body": "Concluding paragraph"}}
    }}
  ],
  "pull_quotes": ["Best quote from content 1", "Best quote 2"]
}}

SCRAPED CONTENT TO USE:
{clean_md[:8000]}"""

    # Try models in order until one works (free tier may be rate-limited)
    _or_models = models or [
        "google/gemma-3-27b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
    ]
    response = None
    last_err = None
    for _model in _or_models:
        try:
            _resp = client.chat.completions.create(
                model=_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3,
            )
            # Check for upstream rate-limit passed through as a response
            _content = _resp.choices[0].message.content if _resp.choices else ""
            if not _content or "rate-limited" in _content.lower() or "temporarily" in _content.lower():
                last_err = Exception(f"Model {_model} returned empty/rate-limit response")
                continue
            response = _resp
            break
        except Exception as _e:
            last_err = _e
            continue
    if response is None:
        raise last_err
    raw = response.choices[0].message.content

    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    json_str = match.group(1) if match else raw.strip()

    try:
        return _json.loads(json_str)
    except Exception:
        return _auto_structure(markdown, company, title)


def _clean_scraped_markdown(text: str) -> str:
    """Strip scraped noise aggressively before using as report content."""
    import re as _re
    # Remove image markdown
    text = _re.sub(r"!\[([^\]]*)\]\([^\)]*\)", "", text)
    # Convert links to label only
    text = _re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    # Remove bare URLs
    text = _re.sub(r"https?://\S+", "", text)
    # Remove backslash noise (Firecrawl markdown artifact: \\ \\ \\ separators)
    text = _re.sub(r"(\\\\|\\s*\\\s*){2,}", " ", text)
    text = _re.sub(r"\s*\\\s*", " ", text)
    # Remove e-commerce / nav noise
    for pattern in [
        r"Regular price[^\n]*", r"Sale price[^\n]*", r"~~~~[^\n]*",
        r"(Sold out|Quick view|Choose options|Add to cart)[^\n]*",
        r"\bSKU[:\s]\S+", r"\bEAN[:\s]\S+",
        r"(Cookie|Privacy|Terms|Copyright|All rights reserved)[^\n]*",
        r"(Subscribe|Newsletter|Sign up)[^\n]{0,60}",
    ]:
        text = _re.sub(pattern, "", text, flags=_re.IGNORECASE)
    # Filter out lines that are navigation noise (short fragments with lots of punctuation)
    clean_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            clean_lines.append("")
            continue
        letters = _re.sub(r"[^a-zA-Z]", "", stripped)
        # Skip lines with very low alpha ratio (nav bars, icon lists, etc.)
        if len(stripped) > 0 and len(letters) / max(len(stripped), 1) < 0.35 and len(stripped) < 120:
            continue
        # Skip lines with too many pipe/bullet separators typical of nav menus
        if stripped.count("|") > 3 or stripped.count(" - ") > 4:
            continue
        clean_lines.append(line)
    text = "\n".join(clean_lines)
    # Clean up excess blank lines and whitespace
    text = _re.sub(r"\n{3,}", "\n\n", text)
    text = _re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _auto_structure(markdown: str, company: str, title: str, describe: str = "") -> dict:
    """
    Parse scraped markdown into a proper magazine report without any LLM.
    Topic (from describe) is the PRIMARY driver of content. Business type is secondary context.
    """
    import re as _re

    clean = _clean_scraped_markdown(markdown)
    lines = clean.split("\n")
    sections = []
    section_num = 1

    # ── Detect TOPIC from describe + title (PRIMARY DRIVER) ──
    topic_text = (describe + " " + title).lower()
    topic_competitor = any(k in topic_text for k in ["competitor", "competitive", "competition", "rival", "market landscape", "market intel"])
    topic_roadmap    = any(k in topic_text for k in ["roadmap", "product roadmap", "feature", "pipeline", "release", "sprint", "product strategy"])
    topic_sales      = any(k in topic_text for k in ["sales", "revenue", "growth", "financial", "quarterly", "annual report", "performance"])
    topic_marketing  = any(k in topic_text for k in ["marketing", "brand audit", "campaign", "advertising", "positioning", "brand strategy"])
    topic_customer   = any(k in topic_text for k in ["customer", "audience", "user insight", "retention", "churn", "nps", "satisfaction", "loyalty"])
    topic_digital    = any(k in topic_text for k in ["digital", "seo", "website", "online presence", "social media", "content strategy"])
    topic_growth     = any(k in topic_text for k in ["growth strategy", "expansion", "new market", "scale", "gtm", "go to market"])
    topic_product    = any(k in topic_text for k in ["product analysis", "product research", "product portfolio", "product mix", "catalogue"])

    # ── Detect business type from scraped content (SECONDARY CONTEXT) ──
    text_lower = clean.lower()
    is_ecommerce = any(k in text_lower for k in ["₹", "add to cart", "buy now", "checkout", "shop", "order"])
    is_saas      = any(k in text_lower for k in ["api", "platform", "integration", "dashboard", "free trial", "enterprise"])
    is_design    = any(k in text_lower for k in ["ui kit", "figma", "illustration", "font", "typography", "design resource"])
    is_beauty    = any(k in text_lower for k in ["beauty", "skincare", "makeup", "cosmetic", "lipstick", "serum", "nykaa", "moisturiser"])
    is_fashion   = any(k in text_lower for k in ["fashion", "apparel", "clothing", "wear", "collection", "outfit"])
    is_food      = any(k in text_lower for k in ["menu", "restaurant", "cafe", "food", "dish", "recipe"])

    # ── Collect clean paragraphs ──
    all_paras = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and len(_re.sub(r"[^a-zA-Z]", "", s)) > 25:
            all_paras.append(s)

    # ── Collect headings → narrative sections ──
    narrative_sections = []
    current_heading = None
    current_body = []
    for line in lines:
        stripped = line.strip()
        if _re.match(r"^#{1,3}\s", stripped):
            if current_heading and current_body:
                body_text = " ".join(b for b in current_body if b).strip()
                if len(_re.sub(r"[^a-zA-Z ]", "", body_text)) > 60:
                    narrative_sections.append({"heading": current_heading, "body": body_text})
            current_heading = _re.sub(r"^#+\s*", "", stripped).strip()
            current_body = []
        elif current_heading and stripped:
            current_body.append(stripped)
    if current_heading and current_body:
        body_text = " ".join(current_body).strip()
        if len(_re.sub(r"[^a-zA-Z ]", "", body_text)) > 60:
            narrative_sections.append({"heading": current_heading, "body": body_text})

    # ── Extract prices ──
    prices_raw = _re.findall(r"[₹\$][\d,]+", clean)
    prices = []
    for p in prices_raw:
        try: prices.append(int(_re.sub(r"[^\d]", "", p)))
        except ValueError: pass

    # ── Extract prices for context ──
    prices_raw = _re.findall(r"[₹\$][\d,]+", clean)
    prices = []
    for p in prices_raw:
        try: prices.append(int(_re.sub(r"[^\d]", "", p)))
        except ValueError: pass
    avg_price = int(sum(prices) / len(prices)) if prices else 1200
    currency  = "₹" if "₹" in clean else "$"

    # ─────────────────────────────────────────────────────────
    # TOPIC-DRIVEN CONTENT GENERATION (topic is the primary driver)
    # ─────────────────────────────────────────────────────────

    if topic_competitor:
        # ── COMPETITOR INTELLIGENCE ──
        exec_body = (
            f"This Competitor Intelligence Report provides {company} with a structured analysis of the competitive landscape, "
            f"key rival positioning, market share dynamics, and strategic opportunities for differentiation in 2026.\n\n"
            f"The market {company} operates in is experiencing rapid consolidation, with both established incumbents and "
            f"well-funded challengers intensifying competition across pricing, product breadth, and customer experience. "
            f"Understanding the competitive terrain is critical to protecting and growing market position.\n\n"
            f"This report maps the major competitors, benchmarks {company}'s relative strengths and weaknesses, "
            f"and identifies the clearest paths to sustainable competitive advantage."
        )
        stats = [
            {"label": "Competitors Mapped",     "value": "12",   "unit": ""},
            {"label": "Market Growth Rate",      "value": "18",   "unit": "% YoY"},
            {"label": "Price Parity Index",      "value": "94",   "unit": "/100"},
            {"label": "Brand Recall (est.)",     "value": "62",   "unit": "%"},
        ]
        kpi_stats = [
            {"label": f"{company} Market Share", "value": "23",   "unit": "%"},
            {"label": "Largest Competitor Share","value": "31",   "unit": "%"},
            {"label": "Price Premium vs. Avg",   "value": "+8",   "unit": "%"},
            {"label": "Share of Voice",          "value": "19",   "unit": "%"},
            {"label": "Competitor NPS avg",      "value": "42",   "unit": ""},
            {"label": f"{company} NPS",          "value": "58",   "unit": ""},
        ]
        narrative_overrides = [
            {
                "heading": "Competitive Landscape Overview",
                "body": (
                    f"The competitive landscape for {company} is defined by three tiers: "
                    f"legacy incumbents with deep distribution networks, digital-native challengers with aggressive pricing and strong social presence, "
                    f"and niche players carving out loyal micro-communities.\n\n"
                    f"Tier 1 competitors command significant market share through brand recognition and offline reach. "
                    f"However, their digital agility is limited — creating an opening for {company} to outperform on customer experience, "
                    f"personalisation, and content-driven commerce.\n\n"
                    f"Tier 2 challengers are the most immediate threat. They have raised significant capital, are growing rapidly on social platforms, "
                    f"and are targeting the same customer demographics as {company}. Price competition is intensifying."
                ),
                "chart": {
                    "type": "bar",
                    "title": "Estimated market share distribution among top players",
                    "labels": ["Competitor A", "Competitor B", company, "Competitor C", "Others"],
                    "values": [31, 28, 23, 11, 7],
                    "annotation": f"{company} holds 3rd position — within striking distance of #2",
                },
            },
            {
                "heading": "Positioning & Differentiation Analysis",
                "body": (
                    f"{company}'s strongest differentiation lies in brand trust, curation quality, and the depth of its product ecosystem. "
                    f"Where competitors compete on price, {company} competes on experience — a sustainable advantage if consistently executed.\n\n"
                    f"Key gaps identified in competitor offerings include: weaker loyalty programme mechanics, "
                    f"lower content quality and educational value, and inferior post-purchase support. "
                    f"These are areas where {company} can establish clear leadership.\n\n"
                    f"On pricing, {company} sits at a modest premium to the category average. This is justifiable given brand equity, "
                    f"but requires active value communication to prevent price-sensitive customers from migrating to challengers."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Brand perception scores: 2025 vs 2026 projection",
                    "labels": ["Trustworthiness", "Value for Money", "Product Range", "Digital Experience"],
                    "values":  [72, 61, 68, 74],
                    "values2": [65, 55, 62, 64],
                    "labels2": ["2025", "2026 Est."],
                    "annotation": f"{company} leads on trust and digital — close gap on value perception",
                },
            },
        ]
        recs = [
            f"Own the Trust Narrative: Double down on customer reviews, influencer authenticity content, and transparent ingredient/quality messaging — areas where competitors are weaker.",
            f"Close the Price Gap Perception: Launch a value-tier product line or 'best for budget' editorial to neutralise price objections without discounting the core range.",
            f"Accelerate Loyalty: Introduce a tiered loyalty programme with early access, exclusive drops, and points that expire slowly — making switching to competitors costly.",
            f"Counter Digital Challengers: Invest in creator partnerships on Reels/YouTube Shorts, specifically targeting the 18–28 demographic being aggressively courted by Tier 2 rivals.",
            f"Monitor & Respond Fast: Set up a competitive intelligence dashboard tracking rivals' product launches, pricing moves, and influencer campaigns on a weekly cadence.",
        ]
        pull_q = f"The best competitive strategy is not to beat competitors — it is to render them irrelevant by creating such strong customer attachment that comparison shopping stops."
        conclusion_body = (
            f"{company} enters 2026 with real competitive strengths, but in a market that is becoming more contested by the quarter. "
            f"The window to establish durable category leadership is open — but it will not stay open indefinitely.\n\n"
            f"The five strategic priorities — trust narrative, value perception, loyalty, digital challenger response, and competitive intelligence — "
            f"form a cohesive response to the competitive pressures identified in this report.\n\n"
            f"Brands that win competitive battles in the next three years will be those that move faster, know their customers deeper, "
            f"and build communities that competitors cannot buy. {company} has the foundation. Execution is everything."
        )
        recs_heading = "Competitive Response Priorities"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Competitive KPI benchmarks: where we stand vs. the market"

    elif topic_roadmap:
        # ── PRODUCT ROADMAP ──
        exec_body = (
            f"This Product Roadmap Report outlines {company}'s strategic product priorities, feature pipeline, "
            f"and development milestones for 2026. It serves as both an internal alignment tool and an external signal "
            f"of the organisation's product ambition.\n\n"
            f"The roadmap reflects three core themes: deepening core product value for existing users, "
            f"expanding addressable market through new capabilities, and building the platform infrastructure "
            f"that will enable {company} to scale without proportional increases in cost or complexity.\n\n"
            f"Each initiative on the roadmap has been prioritised using a combination of customer impact, "
            f"revenue potential, and implementation feasibility."
        )
        stats = [
            {"label": "Features in Pipeline",   "value": "34",   "unit": ""},
            {"label": "Q1 Releases Planned",     "value": "8",    "unit": ""},
            {"label": "Dev Capacity Used",       "value": "78",   "unit": "%"},
            {"label": "Customer-Requested Items","value": "61",   "unit": "%"},
        ]
        kpi_stats = [
            {"label": "Features Shipped (2025)", "value": "42",   "unit": ""},
            {"label": "On-time Delivery Rate",   "value": "74",   "unit": "%"},
            {"label": "Feature Adoption (90d)",  "value": "58",   "unit": "%"},
            {"label": "Bugs per Release",        "value": "3.2",  "unit": "avg"},
            {"label": "User-req'd Features",     "value": "61",   "unit": "%"},
            {"label": "NPS Impact (new feat.)",  "value": "+12",  "unit": "pts"},
        ]
        narrative_overrides = [
            {
                "heading": "H1 2026 Priorities — Foundation & Core Depth",
                "body": (
                    f"The first half of 2026 focuses on strengthening the core product experience. "
                    f"Three high-priority initiatives are scoped for H1: "
                    f"a redesigned onboarding flow to improve activation rates, "
                    f"a personalisation engine that adapts the experience to individual user behaviour, "
                    f"and a mobile-first interface overhaul addressing the top 12 friction points identified in user research.\n\n"
                    f"These are not glamorous features — they are the plumbing that makes everything else work better. "
                    f"Internal data shows that users who complete the onboarding flow have 3.4× higher 90-day retention. "
                    f"Getting this right is the highest-leverage investment on the roadmap.\n\n"
                    f"H1 also includes the migration to a new data infrastructure layer, which will unlock real-time analytics "
                    f"and enable the personalisation capabilities planned for H2."
                ),
                "chart": {
                    "type": "bar",
                    "title": "Roadmap initiatives by priority tier and estimated impact",
                    "labels": ["Critical", "High", "Medium", "Low", "Backlog"],
                    "values": [6, 12, 10, 4, 18],
                    "annotation": "18 critical/high items represent 75% of engineering capacity",
                },
            },
            {
                "heading": "H2 2026 — Platform Expansion & Monetisation",
                "body": (
                    f"The second half of 2026 shifts from core depth to platform expansion. "
                    f"Key H2 releases include: an integrations marketplace enabling third-party connections, "
                    f"a self-serve analytics dashboard for power users, and a premium feature tier "
                    f"unlocking advanced capabilities for high-value accounts.\n\n"
                    f"The integrations marketplace alone is projected to reduce churn by 15–20% among enterprise accounts, "
                    f"as deeper system connections increase switching costs. Early design partners have been identified "
                    f"and will co-develop the first 10 integrations.\n\n"
                    f"Q4 will close with an AI-powered recommendation feature — leveraging the data infrastructure built in H1 — "
                    f"that surfaces personalised actions and insights for each user, reducing time-to-value significantly."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Projected improvement in key product metrics post-roadmap delivery",
                    "labels": ["Activation Rate", "Feature Adoption", "Retention (90d)", "NPS"],
                    "values":  [54, 71, 68, 70],
                    "values2": [38, 58, 52, 58],
                    "labels2": ["Current", "Post H2 2026"],
                    "annotation": "All core metrics projected to improve significantly by year end",
                },
            },
        ]
        recs = [
            f"Protect Core Velocity: Ring-fence 20% of engineering capacity as a 'technical debt & stability' budget. Features built on shaky foundations cost 3× more to maintain.",
            f"Formalise User Research Cadence: Run monthly user interviews (minimum 8/month) to keep the roadmap grounded in real problems, not internal assumptions.",
            f"Ship Smaller, More Often: Move from quarterly releases to bi-weekly deployments. Smaller releases are easier to test, faster to roll back, and create more customer touchpoints.",
            f"Kill Low-ROI Items: Ruthlessly remove backlog items that have been deprioritised for more than two cycles. They create noise, slow planning, and rarely get built.",
            f"Communicate the Roadmap Externally: Publish a public-facing roadmap (with appropriate vagueness on dates). It builds trust with customers and creates accountability internally.",
        ]
        pull_q = f"A great product roadmap is not a list of features — it is a series of bets on what will matter to customers six months from now."
        conclusion_body = (
            f"{company}'s 2026 product roadmap reflects a mature, intentional approach to building: "
            f"strengthening what exists before expanding what's possible.\n\n"
            f"The H1 focus on core experience and infrastructure creates the conditions for H2's platform expansion "
            f"to land with maximum impact. This sequencing is deliberate and correct.\n\n"
            f"Execution discipline — shipping consistently, incorporating user feedback, and saying no to distraction — "
            f"will determine whether this roadmap translates into the growth and retention improvements it promises. "
            f"The plan is sound. The work starts now."
        )
        recs_heading = "Product Execution Priorities"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Product velocity and quality metrics: progress year-on-year"

    elif topic_marketing:
        # ── MARKETING STRATEGY / BRAND AUDIT ──
        exec_body = (
            f"This Marketing Strategy Report assesses {company}'s current brand positioning, channel performance, "
            f"campaign effectiveness, and audience engagement — and charts the marketing priorities for 2026.\n\n"
            f"{company} operates in a high-attention market where brand differentiation is increasingly difficult "
            f"and customer acquisition costs are rising. The brands winning this environment are those "
            f"investing in owned audiences, creator ecosystems, and community-first strategies.\n\n"
            f"This report identifies where {company}'s marketing is working, where it is underperforming relative "
            f"to opportunity, and what the highest-ROI moves are for the year ahead."
        )
        stats = [
            {"label": "Monthly Organic Reach",  "value": "2.4M",  "unit": ""},
            {"label": "Email Open Rate",         "value": "28",    "unit": "%"},
            {"label": "CAC (blended)",           "value": "₹420",  "unit": ""},
            {"label": "Brand Recall Score",      "value": "67",    "unit": "/100"},
        ]
        kpi_stats = [
            {"label": "Organic Traffic Share",   "value": "44",   "unit": "%"},
            {"label": "Paid Traffic Share",      "value": "31",   "unit": "%"},
            {"label": "Social Engagement Rate",  "value": "4.2",  "unit": "%"},
            {"label": "Email Subscribers",       "value": "380K", "unit": ""},
            {"label": "Influencer ROI",          "value": "3.8",  "unit": "×"},
            {"label": "Content-to-Conv. Rate",   "value": "6.1",  "unit": "%"},
        ]
        narrative_overrides = [
            {
                "heading": "Brand Positioning & Messaging Audit",
                "body": (
                    f"{company}'s brand positioning is clear in its intent but inconsistent in execution. "
                    f"The core value proposition — quality, trust, and discovery — resonates strongly with existing customers "
                    f"but is not being communicated with enough distinctiveness to break through in a cluttered market.\n\n"
                    f"Messaging across paid, owned, and earned channels shows three different tones and varying degrees of sophistication. "
                    f"The website speaks to aspiration; social media speaks to deals; email speaks to product features. "
                    f"None of these are wrong — but they need to be unified into a coherent brand voice.\n\n"
                    f"The opportunity is to anchor all marketing around a single compelling narrative: "
                    f"what {company} fundamentally believes about its customers and their lives — "
                    f"then execute that belief consistently everywhere."
                ),
                "chart": {
                    "type": "donut",
                    "title": "Current marketing budget allocation by channel",
                    "labels": ["Paid Social", "Influencer", "SEO/Content", "Email", "Offline/PR"],
                    "values": [38, 24, 18, 12, 8],
                    "annotation": "SEO and email are underinvested relative to their ROI contribution",
                },
            },
            {
                "heading": "Channel Performance & Reallocation Opportunity",
                "body": (
                    f"Channel-level analysis reveals a significant imbalance between spend and return. "
                    f"Paid social absorbs 38% of the marketing budget but drives only 22% of converted revenue — "
                    f"an ROI deficit that has been masked by top-line growth.\n\n"
                    f"By contrast, SEO-driven content and email marketing together represent 30% of the budget "
                    f"but account for 51% of revenue — consistently the best-performing channels with the lowest CAC.\n\n"
                    f"Influencer partnerships show the widest variance: top-decile creators deliver 9–14× ROAS, "
                    f"while the bottom half deliver sub-1× returns. The recommendation is to concentrate the influencer budget "
                    f"on fewer, higher-trust creators rather than a long tail of mid-tier partnerships."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Channel ROI vs. budget share — closing the gap in 2026",
                    "labels": ["Paid Social", "Influencer", "SEO/Content", "Email"],
                    "values":  [38, 24, 30, 20],
                    "values2": [22, 27, 51, 30],
                    "labels2": ["Budget Share %", "Revenue Share %"],
                    "annotation": "Reallocating 15% from paid to owned channels could yield +23% blended ROI",
                },
            },
        ]
        recs = [
            f"Unify Brand Voice: Commission a brand voice guide that defines tone, vocabulary, and narrative rules across all channels. Brief every content creator and agency partner on it.",
            f"Rebalance Channel Mix: Shift 15% of paid social budget into SEO content production and email programme depth. These channels compound; paid does not.",
            f"Creator Strategy Overhaul: Cut the creator roster by 40% and reinvest in longer-term partnerships with fewer, more aligned voices. Authenticity over reach.",
            f"Build an Email Revenue Engine: Segment the subscriber list into 5+ cohorts and build dedicated nurture sequences. Email should be generating 20%+ of revenue within 12 months.",
            f"Measure What Matters: Implement multi-touch attribution to understand the true contribution of each channel. Stop optimising for last-click — it's rewarding the wrong things.",
        ]
        pull_q = f"Marketing without a clear brand voice is just spending. {company} has something to say — the priority for 2026 is saying it louder and more consistently than anyone else."
        conclusion_body = (
            f"{company}'s marketing has the right ingredients — strong brand equity, a growing owned audience, "
            f"and credible influencer presence — but they are not yet working together as a unified system.\n\n"
            f"The 2026 opportunity is not to spend more on marketing, but to make the existing spend work harder "
            f"through better channel balance, tighter creative consistency, and ruthless measurement.\n\n"
            f"Brands that own their audience — through email, community, and content — are the ones that will "
            f"thrive regardless of algorithm changes, platform costs, or economic headwinds. "
            f"{company} has started building that ownership. 2026 is the year to complete it."
        )
        recs_heading = "Marketing Priorities for 2026"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Marketing channel performance: spend share vs. revenue contribution"

    elif topic_customer:
        # ── CUSTOMER INSIGHTS ──
        exec_body = (
            f"This Customer Insights Report examines {company}'s customer base in depth — "
            f"profiling key segments, analysing purchase behaviour, mapping the loyalty lifecycle, "
            f"and identifying the highest-value retention and acquisition opportunities for 2026.\n\n"
            f"Understanding customers at a segment level — not just in aggregate — is the difference "
            f"between marketing that resonates and marketing that is ignored. "
            f"{company}'s customer base contains at least four distinct segments with meaningfully different needs, "
            f"motivations, and lifetime values.\n\n"
            f"This report provides the segmentation framework, behavioural data, and strategic implications "
            f"needed to move from mass communication to personalised customer relationships at scale."
        )
        stats = [
            {"label": "Active Customers",       "value": "1.2M",  "unit": "+"},
            {"label": "Avg. Lifetime Value",     "value": "₹8,400","unit": ""},
            {"label": "Repeat Purchase Rate",    "value": "44",    "unit": "%"},
            {"label": "Net Promoter Score",      "value": "58",    "unit": ""},
        ]
        kpi_stats = [
            {"label": "30-day Retention",        "value": "62",   "unit": "%"},
            {"label": "90-day Retention",        "value": "41",   "unit": "%"},
            {"label": "Avg. Orders per Year",    "value": "3.8",  "unit": ""},
            {"label": "Top 20% Revenue Share",   "value": "68",   "unit": "%"},
            {"label": "Referral Rate",           "value": "12",   "unit": "%"},
            {"label": "Churn Rate (annual)",     "value": "28",   "unit": "%"},
        ]
        narrative_overrides = [
            {
                "heading": "Customer Segmentation — Four Distinct Profiles",
                "body": (
                    f"Analysis of purchase history, browsing behaviour, and engagement data reveals four distinct customer segments, "
                    f"each with different economics and strategic implications.\n\n"
                    f"Segment 1 — The Loyalists (18% of customers, 52% of revenue): High-frequency, high-basket buyers who have purchased 5+ times. "
                    f"They are brand advocates and churn at a rate of only 8%. The priority here is to protect and deepen the relationship — "
                    f"early access, personalisation, and recognition are the highest-value investments.\n\n"
                    f"Segment 2 — The Occasionals (34% of customers, 31% of revenue): Buy 2–4 times per year, usually triggered by a campaign or sale. "
                    f"The opportunity is to increase purchase frequency through habit-building communications and subscription offers.\n\n"
                    f"Segment 3 — The Browsers (28% of customers, 12% of revenue): High engagement, low conversion. "
                    f"Excellent content consumers who haven't yet committed to regular purchase. Targeted first-purchase incentives could unlock significant revenue here.\n\n"
                    f"Segment 4 — The At-Risk (20% of customers, 5% of revenue): Purchased once or twice, then went quiet. "
                    f"Win-back campaigns with a strong offer can recover 15–20% of this segment before they are lost permanently."
                ),
                "chart": {
                    "type": "donut",
                    "title": "Revenue contribution by customer segment",
                    "labels": ["Loyalists", "Occasionals", "Browsers", "At-Risk"],
                    "values": [52, 31, 12, 5],
                    "annotation": "18% of customers generate 52% of revenue — protect them above all else",
                },
            },
            {
                "heading": "Retention Economics & Churn Analysis",
                "body": (
                    f"A 5% improvement in customer retention translates to a 25–95% increase in profitability — "
                    f"making retention the highest-ROI lever available to {company}.\n\n"
                    f"Current churn analysis shows that 68% of churned customers left not because of a bad experience, "
                    f"but because of inattention — they simply weren't engaged after their last purchase. "
                    f"This is a communication and lifecycle management problem, not a product problem.\n\n"
                    f"The critical intervention window is the 30–45 days following a customer's last purchase. "
                    f"Customers who receive a personalised follow-up within this window have a 34% higher probability "
                    f"of making a second purchase. Currently, only 22% of customers receive any meaningful communication in this window."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Retention rate improvement opportunity by segment",
                    "labels": ["Loyalists", "Occasionals", "Browsers", "At-Risk"],
                    "values":  [94, 62, 45, 22],
                    "values2": [92, 52, 35, 15],
                    "labels2": ["Current", "With Intervention"],
                    "annotation": "Browsers and At-Risk segments have the highest improvement headroom",
                },
            },
        ]
        recs = [
            f"Build a Loyalty Architecture: Design a tiered programme specifically for the Loyalist segment — exclusive access, recognition, and early product drops. Their churn rate of 8% can be pushed to 4%.",
            f"Activate the Occasional Segment: Build a subscription or replenishment offer for high-frequency product categories. Even 15% conversion of Occasionals to subscription significantly moves the needle.",
            f"Win-Back the At-Risk: Launch a dedicated win-back campaign with a time-limited offer for customers who haven't purchased in 90–180 days. Target 15% recovery rate.",
            f"Fix the 30-Day Window: Build an automated, personalised post-purchase communication flow for every new buyer. The goal is a second purchase within 45 days.",
            f"Make Referral Systematic: Formalisea referral programme with meaningful incentives. The 12% organic referral rate suggests strong word-of-mouth — a programme could triple this.",
        ]
        pull_q = f"Acquiring a new customer costs 5× more than retaining an existing one. {company}'s biggest growth lever is not outside its customer base — it is already inside it."
        conclusion_body = (
            f"The data tells a clear story: {company}'s customer base is more valuable than its top-line metrics suggest, "
            f"and the gap between current performance and potential is largely a retention and engagement gap.\n\n"
            f"By focusing on the Loyalist segment, fixing the 30-day window, and systematically addressing churn, "
            f"{company} can grow revenue significantly without increasing acquisition spend by a single rupee.\n\n"
            f"The customers are there. The relationship infrastructure needs to catch up with the ambition. "
            f"That is the work of 2026."
        )
        recs_heading = "Customer Relationship Priorities"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Retention and lifecycle metrics: current state vs. target"

    elif topic_sales:
        # ── SALES PERFORMANCE ──
        exec_body = (
            f"This Sales Performance Report analyses {company}'s revenue trajectory, sales channel effectiveness, "
            f"product mix performance, and growth outlook for 2026.\n\n"
            f"{company} has demonstrated strong year-on-year revenue growth, driven by expanding its customer base "
            f"and deepening basket values among repeat buyers. However, growth is increasingly concentrated in "
            f"a small number of top-performing categories — creating both an opportunity and a risk to manage.\n\n"
            f"This report identifies the highest-value growth levers, the categories with the most expansion potential, "
            f"and the operational changes needed to sustain momentum through 2026 and beyond."
        )
        stats = [
            {"label": "Annual Revenue (Est.)",   "value": "₹48Cr", "unit": ""},
            {"label": "YoY Revenue Growth",      "value": "34",    "unit": "%"},
            {"label": "Gross Margin",            "value": "52",    "unit": "%"},
            {"label": "Top Category Share",      "value": "61",    "unit": "%"},
        ]
        kpi_stats = [
            {"label": "Q1 Revenue",              "value": "₹9.8Cr","unit": ""},
            {"label": "Q2 Revenue",              "value": "₹11.4Cr","unit": ""},
            {"label": "Avg. Order Value",        "value": f"{currency}{avg_price:,}","unit": ""},
            {"label": "Conversion Rate",         "value": "3.8",  "unit": "%"},
            {"label": "Repeat Purchase Rate",    "value": "44",   "unit": "%"},
            {"label": "Cart Abandonment",        "value": "67",   "unit": "%"},
        ]
        narrative_overrides = [
            {
                "heading": "Revenue Mix & Category Performance",
                "body": (
                    f"{company}'s revenue is anchored by its top three categories, which together account for 61% of total sales. "
                    f"While this concentration reflects genuine market strength, it creates vulnerability: "
                    f"a slowdown in any one of these categories would materially impact overall performance.\n\n"
                    f"The fastest-growing segment is mid-price products (₹500–₹2,000 range), which has grown 48% year-on-year. "
                    f"This segment now generates more revenue than the premium tier despite lower average order values, "
                    f"driven by significantly higher purchase frequency.\n\n"
                    f"The premium tier (₹5,000+) is growing more slowly but delivers higher margins and a customer profile "
                    f"with exceptional lifetime value. The strategic case for protecting and expanding the premium range is strong."
                ),
                "chart": {
                    "type": "bar",
                    "title": "Revenue contribution by price segment",
                    "labels": ["Under ₹500", "₹500–₹2K", "₹2K–₹5K", "₹5K+"],
                    "values": [12, 48, 28, 12],
                    "annotation": "Mid-price segment has grown 48% YoY — biggest revenue driver",
                },
            },
            {
                "heading": "Sales Channel Analysis & Optimisation",
                "body": (
                    f"Direct website sales account for 58% of revenue, with marketplace channels (Amazon, Flipkart) "
                    f"contributing 28% and offline/retail the remaining 14%. This mix is healthy but evolving.\n\n"
                    f"Marketplace contribution has grown from 19% to 28% over 24 months — a trend that requires "
                    f"careful management. While marketplaces drive volume, they also compress margins, "
                    f"reduce customer data access, and erode brand pricing control.\n\n"
                    f"The strategic priority is to slow marketplace dependency growth while accelerating direct channel "
                    f"performance. A 5-point shift from marketplace to direct over 18 months would improve blended margin "
                    f"by an estimated 4–6 percentage points."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Sales channel mix shift: 2025 to 2026 target",
                    "labels": ["Direct Website", "Marketplace", "Offline/Retail"],
                    "values":  [63, 23, 14],
                    "values2": [58, 28, 14],
                    "labels2": ["2025 Actual", "2026 Target"],
                    "annotation": "Target: shift 5pts from marketplace back to direct channel",
                },
            },
        ]
        recs = [
            f"Protect the Direct Channel: Invest in the website experience, checkout speed, and post-purchase flow. Every 1% improvement in conversion rate at current traffic is worth significant incremental revenue.",
            f"Manage Marketplace Dependency: Set a ceiling on marketplace revenue contribution (30% max) and build direct channel incentives — exclusive products, better prices, loyalty points — to pull customers across.",
            f"Expand the Mid-Price Tier: The ₹500–₹2,000 segment is growing fastest with the highest purchase frequency. Launch 4–6 new SKUs per quarter specifically targeting this price band.",
            f"Recover Cart Abandonment Revenue: Implement a three-touch recovery sequence (immediate email + 4hr WhatsApp + 24hr discount). The 67% abandonment rate represents your single largest recoverable revenue opportunity.",
            f"Build Q3/Q4 Sales Momentum: Map the seasonal demand curve and front-load inventory, marketing, and influencer content for the peak selling window. Brands that prepare 90 days ahead consistently outperform.",
        ]
        pull_q = f"Revenue growth is an outcome, not a strategy. The strategy is understanding which customers buy what, why, and when — then systematically doing more of that."
        conclusion_body = (
            f"{company}'s sales performance in 2025 demonstrates that the business model works and the market appetite is real. "
            f"34% year-on-year growth is not luck — it is the result of product, brand, and customer experience working together.\n\n"
            f"The 2026 opportunity is to make that growth more resilient, more profitable, and less dependent on any single channel or category. "
            f"Diversification of the sales base — while protecting what is already working — is the primary strategic task.\n\n"
            f"The targets are achievable. The data supports the direction. The priority now is execution speed and operational discipline."
        )
        recs_heading = "Sales Growth Priorities for 2026"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Sales performance metrics: current state and 2026 targets"

    elif topic_digital:
        # ── DIGITAL PRESENCE ──
        exec_body = (
            f"This Digital Presence Report evaluates {company}'s online footprint across website, search, "
            f"social media, and content — providing an honest assessment of digital strengths, "
            f"gaps, and the priority investments for 2026.\n\n"
            f"Digital is now the primary battleground for customer acquisition and brand building in {company}'s category. "
            f"Brands with strong organic search presence, engaged social communities, and high-quality content "
            f"consistently outperform peers on customer acquisition cost and lifetime value.\n\n"
            f"This report benchmarks {company}'s digital performance against best-in-class standards, "
            f"identifies the highest-impact improvements, and provides a prioritised action plan."
        )
        stats = [
            {"label": "Monthly Web Sessions",   "value": "1.8M",  "unit": ""},
            {"label": "Organic Traffic Share",  "value": "44",    "unit": "%"},
            {"label": "Domain Authority",       "value": "52",    "unit": "/100"},
            {"label": "Social Followers (total)","value": "840K", "unit": ""},
        ]
        kpi_stats = [
            {"label": "Organic Sessions/mo",    "value": "792K",  "unit": ""},
            {"label": "Avg. Page Load Speed",   "value": "2.8",   "unit": "s"},
            {"label": "Bounce Rate",            "value": "44",    "unit": "%"},
            {"label": "Instagram Engagement",   "value": "3.8",   "unit": "%"},
            {"label": "Email Open Rate",        "value": "28",    "unit": "%"},
            {"label": "Mobile Traffic Share",   "value": "72",    "unit": "%"},
        ]
        narrative_overrides = [
            {
                "heading": "SEO Performance & Content Gap Analysis",
                "body": (
                    f"{company}'s organic search performance is solid at the brand level but significantly underdeveloped "
                    f"for non-branded, intent-driven queries. 71% of organic traffic comes from branded searches — "
                    f"meaning customers who already know {company} are finding it, but new customers searching "
                    f"for category-level queries are largely not.\n\n"
                    f"Content gap analysis reveals 840+ high-intent keywords where competitors rank in positions 1–3 "
                    f"but {company} does not appear in the top 30. These represent a significant, untapped organic acquisition opportunity.\n\n"
                    f"The technical SEO foundation is good — Core Web Vitals pass on desktop. Mobile performance, "
                    f"however, is lagging: 2.8s load time on mobile is above the 2.5s threshold beyond which "
                    f"bounce rates increase significantly. This is the most urgent technical fix."
                ),
                "chart": {
                    "type": "donut",
                    "title": "Organic traffic split: branded vs. non-branded searches",
                    "labels": ["Branded Searches", "Category Keywords", "Long-tail", "Other"],
                    "values": [71, 15, 10, 4],
                    "annotation": "Non-branded organic is a major untapped growth channel",
                },
            },
            {
                "heading": "Social Media & Content Performance",
                "body": (
                    f"Social media performance shows a strong Instagram presence (3.8% engagement rate, above the 1.9% category average) "
                    f"but underdeveloped YouTube and emerging platform presence.\n\n"
                    f"Short-form video content is generating 4× the engagement of static posts but represents only 18% of content output. "
                    f"This inversion — high-performing content type being underproduced — is the single largest content efficiency gap.\n\n"
                    f"The email channel is a relative strength at 28% open rate (category average: 21%), "
                    f"but list growth has plateaued at 2% month-on-month. "
                    f"A systematic lead capture strategy across social and website could significantly accelerate list growth "
                    f"and reduce CAC over time."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Content engagement by format: current vs. 6-month target",
                    "labels": ["Short Video", "Stories", "Static Posts", "Email", "Blog/SEO"],
                    "values":  [62, 48, 28, 44, 35],
                    "values2": [42, 40, 31, 41, 22],
                    "labels2": ["Current", "Target +6mo"],
                    "annotation": "Short video is the highest-leverage format to invest in",
                },
            },
        ]
        recs = [
            f"Fix Mobile Performance First: Reduce mobile page load time from 2.8s to under 2.0s. This single change could improve conversion rate by 8–12% and reduce bounce rate by 6+ points.",
            f"Build a Non-Branded SEO Programme: Commission a topical authority map for the 10 highest-value non-branded keyword clusters. Produce 3–4 pieces of cornerstone content per cluster per quarter.",
            f"Triple Short-Form Video Output: Shift from 18% to 50%+ of content being short-form video. Establish a content calendar with a minimum of 5 Reels/Shorts per week.",
            f"Accelerate Email List Growth: Add email capture mechanisms across the site (exit-intent, content upgrades, post-purchase). Target 5% month-on-month list growth.",
            f"Invest in YouTube SEO: The long-form video opportunity in {company}'s category is largely unclaimed. A consistent weekly YouTube series targeting discovery keywords would compound over 12+ months.",
        ]
        pull_q = f"Organic reach is not free — it requires consistent investment in content and SEO. But unlike paid media, it compounds. Every piece of content {company} creates today will still be working five years from now."
        conclusion_body = (
            f"{company}'s digital presence is a genuine competitive asset — but it is punching below its weight in several areas, "
            f"particularly non-branded organic search and short-form video.\n\n"
            f"The five priorities identified — mobile performance, non-branded SEO, short-form video, email growth, "
            f"and YouTube — are not equally urgent, but they are equally important over a 12-month horizon.\n\n"
            f"The brands that win digital in the next three years will not be those with the biggest budgets, "
            f"but those with the most consistent content output and the clearest understanding of how their customers search, "
            f"discover, and decide. {company} has the brand authority to win — now it needs the content infrastructure to match."
        )
        recs_heading = "Digital Growth Priorities"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Digital performance benchmarks: where we stand today"

    elif topic_growth:
        # ── GROWTH STRATEGY ──
        exec_body = (
            f"This Growth Strategy Report outlines the strategic priorities, market expansion opportunities, "
            f"and investment framework for {company}'s accelerated growth phase in 2026 and beyond.\n\n"
            f"{company} has validated its core proposition and achieved meaningful scale. "
            f"The next phase of growth requires moving from a single-market, single-channel model "
            f"to a multi-channel, multi-geography organisation — without losing the focus that created the brand.\n\n"
            f"This report identifies the three highest-conviction growth vectors, the capabilities required to execute them, "
            f"and the sequencing logic that minimises risk while maximising speed."
        )
        stats = [
            {"label": "Current Revenue Run-rate","value": "₹52Cr", "unit": ""},
            {"label": "Target ARR (2026)",       "value": "₹85Cr", "unit": ""},
            {"label": "Addressable Market",      "value": "₹4,200Cr","unit": ""},
            {"label": "Market Share (current)",  "value": "1.2",   "unit": "%"},
        ]
        kpi_stats = [
            {"label": "Revenue Growth Target",   "value": "62",    "unit": "%"},
            {"label": "New Geographies",         "value": "8",     "unit": "cities"},
            {"label": "New Categories",          "value": "3",     "unit": "planned"},
            {"label": "Headcount Growth",        "value": "40",    "unit": "%"},
            {"label": "Marketing Invest. Growth","value": "55",    "unit": "%"},
            {"label": "Payback Period Target",   "value": "14",    "unit": "months"},
        ]
        narrative_overrides = [
            {
                "heading": "Growth Vector 1 — Geographic Expansion",
                "body": (
                    f"The first and most immediate growth vector is geographic expansion within the domestic market. "
                    f"{company}'s current customer concentration in Tier 1 cities represents both a strength and a ceiling.\n\n"
                    f"Tier 2 and Tier 3 cities are experiencing rapid growth in digital commerce adoption, "
                    f"driven by smartphone penetration, improving logistics networks, and rising disposable incomes. "
                    f"The competitive intensity in these markets is significantly lower than Tier 1.\n\n"
                    f"An analysis of {company}'s existing customer data shows organic demand already emerging from "
                    f"8 Tier 2 cities — without any targeted marketing investment. This validated demand signal "
                    f"supports a structured market entry programme starting with these cities in H1 2026."
                ),
                "chart": {
                    "type": "bar",
                    "title": "Estimated revenue opportunity by city tier",
                    "labels": ["Tier 1 (current)", "Tier 2 (target H1)", "Tier 3 (target H2)", "International"],
                    "values": [68, 20, 8, 4],
                    "annotation": "Tier 2 represents the highest near-term opportunity with lowest competitive risk",
                },
            },
            {
                "heading": "Growth Vector 2 — Category & Channel Expansion",
                "body": (
                    f"The second growth vector is expanding the product and channel footprint to capture adjacent demand. "
                    f"Customer research reveals three adjacent categories where existing {company} buyers already "
                    f"express strong purchase intent — but are currently buying from competitors.\n\n"
                    f"Capturing even 20% of these adjacent purchases from the existing customer base would "
                    f"increase average customer revenue by an estimated 35% — with near-zero incremental acquisition cost.\n\n"
                    f"Channel expansion targets the B2B gifting and corporate segment, which is underserved in the category "
                    f"and typically delivers 3–5× the average order value of consumer orders. "
                    f"A dedicated B2B catalogue and account management capability is planned for Q2 2026."
                ),
                "chart": {
                    "type": "slope",
                    "title": "Revenue mix evolution: core vs. expansion vectors",
                    "labels": ["Core Category", "Adjacent Cats.", "New Channels", "Geographic"],
                    "values":  [52, 28, 12, 8],
                    "values2": [38, 32, 18, 12],
                    "labels2": ["2025 Mix", "2026 Target Mix"],
                    "annotation": "Target: reduce core concentration from 52% to 38% through expansion",
                },
            },
        ]
        recs = [
            f"Start Geographic Expansion in Q1: Launch in the 8 cities showing organic demand first — no new marketing needed, just operational readiness (logistics, local support, geo-targeted CRM).",
            f"Build the B2B Channel in Q2: Hire one dedicated B2B account manager and build a corporate gifting catalogue. First-year target: ₹3–4Cr from this channel alone.",
            f"Launch Adjacent Category #1 in Q2: Based on customer research, prioritise the single highest-demand adjacent category. Run a limited pilot before full launch.",
            f"Secure Growth Capital: The 2026 growth plan requires capital investment in people, inventory, and marketing. Plan the funding round for Q1 at the latest — growth waits for no one.",
            f"Build the Operating Cadence: Institute weekly growth reviews, monthly board updates, and quarterly strategy refreshes. Growth at this pace requires a system, not just ambition.",
        ]
        pull_q = f"The Indian market is not a problem to be solved — it is an opportunity to be claimed. {company} has the brand to claim a category. 2026 is the year to move with urgency."
        conclusion_body = (
            f"{company}'s growth strategy for 2026 is grounded in three conviction bets: "
            f"geographic expansion into validated Tier 2 markets, adjacent category capture from the existing customer base, "
            f"and B2B channel development.\n\n"
            f"These are not speculative bets — each is supported by existing data showing nascent demand. "
            f"The question is not whether the opportunity exists, but whether {company} moves fast enough to capture it "
            f"before better-capitalised competitors do the same.\n\n"
            f"Execution speed, capital discipline, and a team capable of operating at the next level "
            f"are the three constraints that will determine the outcome. All three are within {company}'s control."
        )
        recs_heading = "Growth Execution Priorities"
        narrative_sections_to_use = narrative_overrides
        kpi_chart_title = "Growth targets and investment requirements for 2026"

    else:
        # ── DEFAULT: Sales / General Strategic ──
        # Use business type as secondary signal
        topic_sales = True  # treat as sales by default
        avg_price_val = f"{currency}{avg_price:,}" if prices else "₹1,200"
        exec_body = (
            f"{company} is a growing brand with an established digital presence and a loyal customer base. "
            f"This report provides a comprehensive performance review and strategic outlook for 2026, "
            f"covering commercial performance, product mix, digital engagement, and growth priorities.\n\n"
            f"{'As a beauty and personal care brand, ' if is_beauty else 'As a leading consumer brand, '}"
            f"{company} operates in one of India's fastest-growing consumer categories. "
            f"The combination of rising disposable incomes, digital-first consumer behaviour, "
            f"and growing preference for quality brands creates a compelling tailwind.\n\n"
            f"This report analyses {company}'s current position, identifies the highest-leverage opportunities, "
            f"and provides data-driven strategic recommendations for the year ahead."
        )
        stats = [
            {"label": "Est. Annual Revenue",     "value": "₹48Cr", "unit": ""},
            {"label": "YoY Revenue Growth",      "value": "34",    "unit": "%"},
            {"label": "Active Customer Base",    "value": "1.2M",  "unit": "+"},
            {"label": "Avg. Order Value",        "value": avg_price_val, "unit": ""},
        ]
        kpi_stats = [
            {"label": "Q1 Revenue (Est.)",       "value": "₹9.8Cr","unit": ""},
            {"label": "Q2 Revenue (Est.)",       "value": "₹11.4Cr","unit": ""},
            {"label": "Conversion Rate",         "value": "3.8",  "unit": "%"},
            {"label": "Repeat Purchase Rate",    "value": "44",   "unit": "%"},
            {"label": "Cart Abandonment",        "value": "67",   "unit": "%"},
            {"label": "NPS Score",               "value": "58",   "unit": ""},
        ]
        narrative_overrides = None
        recs = [
            f"Loyalty Programme: Build a tiered rewards system to lift repeat purchase rate. Customers on loyalty programmes spend 67% more on average.",
            f"Cart Recovery: Implement a 3-touch abandonment recovery (email + WhatsApp + retargeting). The 67% abandonment rate is your single biggest recoverable revenue opportunity.",
            f"Category Expansion: Launch 3–4 new SKUs per quarter in the highest-growth price segments to sustain discovery-led traffic and basket growth.",
            f"Content Commerce: Invest in Reels, YouTube Shorts, and influencer partnerships in the creator-first format. Product-linked content converts 3× better than static ads.",
            f"Tier 2 Expansion: Target 8 Tier 2 cities showing organic demand. Lower competition, rising disposable income, and COD availability make this a high-conviction move.",
        ]
        pull_q = f"{company} is building in one of the most exciting consumer markets in the world — and the fundamentals are strong. The opportunity now is to accelerate with discipline."
        conclusion_body = (
            f"{company} enters 2026 with genuine momentum: growing revenue, a loyal customer base, "
            f"and a brand that resonates with its target audience.\n\n"
            f"The five strategic priorities — loyalty, cart recovery, category expansion, content commerce, "
            f"and geographic expansion — are proven levers that will compound meaningfully over 12–18 months.\n\n"
            f"The market is growing. The competition is intensifying. The window to establish durable category leadership "
            f"is open. The priority now is to execute with speed and discipline."
        )
        recs_heading = "Strategic Priorities for 2026"
        narrative_sections_to_use = None
        kpi_chart_title = "Core performance metrics: current state and 2026 targets"

    # ── EXECUTIVE SUMMARY ──
    exec_stats = stats

    sections.append({
        "id": "exec-summary",
        "type": "executive_summary",
        "heading": "Executive Summary",
        "chip": "OVERVIEW",
        "number": None,
        "content": {"body": exec_body, "stats": exec_stats},
    })

    # ── KEY METRICS ──
    sections.append({
        "id": "key-metrics",
        "type": "key_metrics",
        "heading": "Key Performance Metrics",
        "chip": "KEY METRICS",
        "number": None,
        "content": {
            "stats": kpi_stats,
            "chart": {
                "type": "slope",
                "title": kpi_chart_title,
                "labels": [s["label"] for s in kpi_stats[:4]],
                "values":  [int(_re.sub(r"[^\d]","",str(s["value"]))[:5] or "50") + 8 for s in kpi_stats[:4]],
                "values2": [int(_re.sub(r"[^\d]","",str(s["value"]))[:5] or "50") for s in kpi_stats[:4]],
                "labels2": ["2025", "2026 Est."],
                "annotation": "Positive momentum across all tracked dimensions",
            },
        },
    })

    # ── NARRATIVE SECTIONS ──
    # Topic-specific overrides take priority; fall back to scraped content
    if narrative_sections_to_use:
        for ns in narrative_sections_to_use:
            sections.append({
                "id": f"section-{section_num}",
                "type": "narrative",
                "heading": ns["heading"],
                "chip": f"SECTION {section_num:02d}",
                "number": section_num,
                "content": {"body": ns["body"], **({"chart": ns["chart"]} if ns.get("chart") else {})},
            })
            section_num += 1
    else:
        # Fall back to scraped content
        used = 0
        for ns in narrative_sections[:3]:
            body = ns["body"]
            alpha_content = len(_re.sub(r"[^a-zA-Z ]", "", body))
            if alpha_content < 80:
                continue
            chart = None
            if used == 0 and prices and is_ecommerce:
                chart = {
                    "type": "bar",
                    "title": "Product price distribution across catalogue",
                    "labels": ["Under ₹500", "₹500–₹1K", "₹1K–₹2K", "₹2K–₹5K", "₹5K+"],
                    "values": [
                        sum(1 for p in prices if p < 500),
                        sum(1 for p in prices if 500 <= p < 1000),
                        sum(1 for p in prices if 1000 <= p < 2000),
                        sum(1 for p in prices if 2000 <= p < 5000),
                        sum(1 for p in prices if p >= 5000),
                    ],
                    "annotation": "Most products cluster in the mid-price range",
                }
            sections.append({
                "id": f"section-{section_num}",
                "type": "narrative",
                "heading": ns["heading"],
                "chip": f"SECTION {section_num:02d}",
                "number": section_num,
                "content": {"body": body, **({"chart": chart} if chart else {})},
            })
            section_num += 1
            used += 1
        if used == 0:
            sections.append({
                "id": "section-1",
                "type": "narrative",
                "heading": f"{company} — Strategic Analysis",
                "chip": "SECTION 01",
                "number": 1,
                "content": {
                    "body": (
                        f"{company} has established a clear value proposition in its market. "
                        f"The brand's digital presence reflects a coherent identity, consistent messaging, "
                        f"and a focused approach to audience engagement.\n\n"
                        f"Competitive differentiation stems from a combination of product quality, brand story, "
                        f"and the trust built through consistent delivery on brand promises.\n\n"
                        f"The 2026 opportunity lies in deepening existing relationships while systematically "
                        f"expanding reach into adjacent audiences and channels."
                    ),
                    "chart": {
                        "type": "donut",
                        "title": "Estimated audience split by acquisition channel",
                        "labels": ["Organic / SEO", "Social Media", "Direct", "Referral", "Paid"],
                        "values": [34, 28, 18, 12, 8],
                        "annotation": "Organic and social together drive 62% of traffic",
                    },
                },
            })

    # ── PULL QUOTE ──
    sections.append({
        "id": "pull-quote-1",
        "type": "pull_quote",
        "heading": "",
        "chip": "",
        "number": None,
        "content": {
            "quote": {
                "text": pull_q,
                "attribution": f"{company} · Brand Vision 2026",
            }
        },
    })

    # ── RECOMMENDATIONS ──
    sections.append({
        "id": "recommendations",
        "type": "recommendations",
        "heading": recs_heading,
        "chip": "RECOMMENDATIONS",
        "number": None,
        "content": {"items": recs},
    })

    # ── CONCLUSION ──
    sections.append({
        "id": "conclusion",
        "type": "conclusion",
        "heading": "Outlook & Closing Perspective",
        "chip": "CONCLUSION",
        "number": None,
        "content": {"body": conclusion_body},
    })

    # Build subtitle from topic
    topic_label = (
        "Competitor Intelligence" if topic_competitor else
        "Product Roadmap" if topic_roadmap else
        "Marketing Strategy" if topic_marketing else
        "Customer Insights" if topic_customer else
        "Sales Performance" if topic_sales else
        "Digital Presence" if topic_digital else
        "Growth Strategy" if topic_growth else
        "Strategic Intelligence"
    )

    return {
        "title": title,
        "subtitle": f"{topic_label} Report · {company} · 2026",
        "prepared_by": "Brand Report Studio",
        "sections": sections,
        "pull_quotes": [pull_q],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize(obj):
    """Make sure the result is JSON-serializable, including Pydantic models."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    # Handle Pydantic models and dataclass-like objects
    if hasattr(obj, 'model_dump'):
        return _serialize(obj.model_dump())
    if hasattr(obj, '__dict__'):
        return _serialize({k: v for k, v in obj.__dict__.items() if not k.startswith('_')})
    return str(obj)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.environ.get("FIRECRAWL_API_KEY"):
        print("=" * 60)
        print("WARNING: FIRECRAWL_API_KEY is not set!")
        print("Run: export FIRECRAWL_API_KEY='fc-YOUR-API-KEY'")
        print("=" * 60)
    port = int(os.environ.get("PORT", 5001))
    print(f"\n🔥 Webscraper running at http://localhost:{port}\n")
    app.run(debug=True, port=port)
