#!/usr/bin/env python3
"""
Brand identity extractor — Phase 1 & 2 of the Brand-Aware Magazine Report Generator.

Scrapes a company's website using Firecrawl's branding extraction, downloads assets,
runs multi-page crawl for richer data, generates logo variants, downloads fonts,
and writes a complete brand.json profile to brands/<slug>/.

Usage:
    python brand_scrape.py <url> [--output-dir ./brands] [--force]

Environment:
    FIRECRAWL_API_KEY — required
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ── Utilities ──────────────────────────────────────────────────────────────────

def _to_dict(obj):
    """Convert Pydantic models / dataclass-like objects to plain dicts recursively."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return _to_dict(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return _to_dict({k: v for k, v in obj.__dict__.items() if not k.startswith("_")})
    return str(obj)


def get_slug(url: str) -> str:
    """Derive a filesystem-safe slug from a URL (e.g. https://stripe.com → stripe)."""
    parsed = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    domain = parsed.netloc.lower().lstrip("www.")
    return domain.split(".")[0]


def download_asset(url: str, path: Path) -> bool:
    """Download a remote asset to a local path. Returns True on success."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BrandScraper/1.0)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            path.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"    ⚠ Could not download {url}: {e}")
        return False


def get_firecrawl_client():
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: FIRECRAWL_API_KEY is not set.", file=sys.stderr)
        print("  export FIRECRAWL_API_KEY='fc-YOUR-API-KEY'", file=sys.stderr)
        sys.exit(1)
    try:
        from firecrawl import Firecrawl
        return Firecrawl(api_key=api_key)
    except ImportError:
        print("Error: pip install firecrawl-py", file=sys.stderr)
        sys.exit(1)


# ── Color processing ───────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple:
    c = hex_color.lstrip("#")
    if len(c) == 3:
        c = c[0]*2 + c[1]*2 + c[2]*2
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _rgb_to_hex(r, g, b) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _is_dark(hex_color: str) -> bool:
    try:
        r, g, b = _hex_to_rgb(hex_color)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 128
    except Exception:
        return True


def _tint(hex_color: str, opacity: float) -> str:
    """Blend hex color toward white at given opacity (0=full white, 1=original)."""
    try:
        r, g, b = _hex_to_rgb(hex_color)
        return _rgb_to_hex(
            r + (255 - r) * (1 - opacity),
            g + (255 - g) * (1 - opacity),
            b + (255 - b) * (1 - opacity),
        )
    except Exception:
        return "#f0f0f0"


def _linearize(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    try:
        r, g, b = _hex_to_rgb(hex_color)
        return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)
    except Exception:
        return 0.0


def wcag_contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2.1 contrast ratio between two hex colors. AA requires >= 4.5."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def fix_cover_contrast(primary: str) -> str:
    """Return #ffffff or #111111 — whichever achieves higher contrast on primary."""
    return "#ffffff" if wcag_contrast_ratio("#ffffff", primary) >= wcag_contrast_ratio("#111111", primary) else "#111111"


# Colors that are browser/platform defaults — NOT real brand choices
_GENERIC_COLORS = {
    # Browser default link blues
    "#0000ee", "#0000ff", "#0000cc", "#0033cc",
    # Bootstrap / Material blues
    "#007bff", "#0d6efd", "#1a73e8", "#4285f4", "#2196f3",
    # Shopify defaults
    "#008060", "#004c3f", "#00a862", "#006e52",
    # Tailwind / other framework colors that slip through
    "#3b82f6", "#6366f1", "#8b5cf6",
    # Generic browser blacks / grays that aren't brand choices
    "#808080", "#999999",
}


def _is_generic_color(hex_color: str) -> bool:
    """Return True if this looks like a browser/framework default, not a deliberate brand color."""
    if not hex_color or not hex_color.startswith("#"):
        return False
    c = hex_color.lower().strip()
    if c in _GENERIC_COLORS:
        return True
    # Pure primary colors (exactly #ff0000, #00ff00, #0000ff) are never brand accents
    try:
        r, g, b = _hex_to_rgb(c)
        if (r == 255 and g == 0  and b == 0) or \
           (r == 0   and g == 255 and b == 0) or \
           (r == 0   and g == 0  and b == 255) or \
           (r == 0   and g == 0  and b == 238):   # browser default link blue
            return True
    except Exception:
        pass
    return False


def _color_saturation(hex_color: str) -> float:
    """Return HSL saturation 0–1."""
    try:
        r, g, b = [x / 255.0 for x in _hex_to_rgb(hex_color)]
        mx, mn = max(r, g, b), min(r, g, b)
        l = (mx + mn) / 2
        if mx == mn:
            return 0.0
        d = mx - mn
        return d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    except Exception:
        return 0.0


def _pick_best_accent(raw_colors: dict, bg: str, text: str) -> str:
    """
    Choose the best accent color from Firecrawl's raw data.
    Priority:
      1. button/CTA background color (most intentional brand color)
      2. any non-generic non-neutral color with saturation > 0.3
      3. the text color itself (for monochromatic brands)
    """
    dark_bg = _is_dark(bg)

    # 1. Button / CTA color — most intentional signal
    cta_candidates = [
        raw_colors.get("buttonBackground"),
        raw_colors.get("buttonPrimary"),
        raw_colors.get("ctaBackground"),
        raw_colors.get("button"),
        raw_colors.get("link"),        # link color before falling to browser default
    ]
    for c in cta_candidates:
        if c and isinstance(c, str) and c.startswith("#") and not _is_generic_color(c):
            r2, g2, b2 = _hex_to_rgb(c)
            # Must contrast adequately with background
            if wcag_contrast_ratio(c, bg) >= 3.0:
                return c

    # 2. Scan all raw values for a distinctive brand color
    all_vals = [v for v in raw_colors.values() if isinstance(v, str) and v.startswith("#")]
    scored = []
    for c in all_vals:
        if _is_generic_color(c):
            continue
        sat = _color_saturation(c)
        lum = _relative_luminance(c)
        contrast = wcag_contrast_ratio(c, bg)
        # Prefer: high saturation, good contrast, not too close to pure black/white
        r2, g2, b2 = _hex_to_rgb(c)
        brightness = (0.299*r2 + 0.587*g2 + 0.114*b2)
        if contrast >= 2.5 and 10 < brightness < 245 and sat > 0.15:
            scored.append((sat * contrast, c))
    if scored:
        scored.sort(reverse=True)
        return scored[0][1]

    # 3. Fall back to text color for monochromatic brands (B&W)
    return text


def assign_color_roles(raw_colors: dict) -> dict:
    """
    Map Firecrawl raw color keys to semantic report roles.
    Filters out browser/platform default colors (e.g. #0000EE link blue, Shopify greens)
    and correctly identifies monochromatic (B&W) brands.
    """
    bg       = raw_colors.get("background", "#ffffff") or "#ffffff"
    dark_bg  = _is_dark(bg)

    # Text — usually reliable from Firecrawl
    text     = raw_colors.get("textPrimary", raw_colors.get("text",
               "#ffffff" if dark_bg else "#111111")) or ("#ffffff" if dark_bg else "#111111")
    text_sec = raw_colors.get("textSecondary", "#aaaaaa" if dark_bg else "#555555")

    # Primary — reject browser defaults
    raw_primary = raw_colors.get("primary", "#333333") or "#333333"
    primary = raw_primary if not _is_generic_color(raw_primary) else text

    # Accent — smart selection
    accent = _pick_best_accent(raw_colors, bg, text)

    # Secondary — use raw or derive from primary
    raw_secondary = raw_colors.get("secondary", "#666666") or "#666666"
    secondary = raw_secondary if not _is_generic_color(raw_secondary) else \
                _tint(primary, 0.5) if not _is_dark(_tint(primary, 0.5)) else "#555555"

    surface  = raw_colors.get("surface", "#1a1a1a" if dark_bg else "#f5f5f5")
    cover_text = fix_cover_contrast(primary)

    return {
        "primary":         primary,
        "secondary":       secondary,
        "accent":          accent,
        "background":      bg,
        "surface":         surface,
        "text_primary":    text,
        "text_secondary":  text_sec,
        "cover_bg":        primary,
        "cover_text":      cover_text,
        "section_accent":  accent,
        "pull_quote_bg":   _tint(primary, 0.08),
        "table_header_bg": secondary,
        "sidebar_bg":      _tint(primary, 0.05),
        "divider_color":   _tint(text, 0.2),
        "footer_bg":       secondary,
        "_contrast_cover": round(wcag_contrast_ratio(cover_text, primary), 2),
    }


def extract_image_colors(img_path: Path, n_colors: int = 6) -> list:
    """
    Extract dominant colors from an image using Pillow palette quantization.
    Returns list of hex strings. Returns [] if Pillow not installed.
    """
    try:
        from PIL import Image
        img = Image.open(img_path).convert("RGB").resize((100, 100))
        quantized = img.quantize(colors=n_colors, method=1)  # MEDIANCUT=1
        palette = quantized.getpalette()
        colors = []
        for i in range(n_colors):
            r, g, b = palette[i*3], palette[i*3+1], palette[i*3+2]
            if (r + g + b) > 720 or (r + g + b) < 30:
                continue
            colors.append(_rgb_to_hex(r, g, b))
        return colors[:n_colors]
    except Exception:
        return []


# ── Design language classifier ─────────────────────────────────────────────────

STYLE_RULES = [
    (["luxury", "premium", "elegant", "exclusive", "sophisticat"], "luxury_premium"),
    (["technical", "developer", "precise", "engineering", "data", "code"], "technical_precise"),
    (["playful", "fun", "creative", "vibrant", "energetic", "colorful"],   "startup_playful"),
    (["corporate", "formal", "enterprise", "professional", "conservative"],"corporate_formal"),
    (["bold", "editorial", "strong", "impactful", "powerful"],             "bold_editorial"),
]

def classify_style(brand_data: dict) -> str:
    personality = brand_data.get("personality") or {}
    traits      = personality.get("traits") or []
    description = str(personality.get("description") or "")
    text = " ".join(str(t).lower() for t in traits) + " " + description.lower()
    for keywords, style in STYLE_RULES:
        if any(k in text for k in keywords):
            return style

    # Fallback: infer from dominant brand color
    colors = brand_data.get("colors") or {}
    primary = str(colors.get("primary") or colors.get("background") or "#888888")
    accent  = str(colors.get("accent") or colors.get("cta") or "#888888")
    try:
        # Use accent if it's more vivid
        for color in [accent, primary]:
            color = color.strip().lstrip("#")
            if len(color) < 6:
                continue
            r2, g2, b2 = int(color[0:2],16), int(color[2:4],16), int(color[4:6],16)
            mx = max(r2, g2, b2); mn = min(r2, g2, b2)
            sat = (mx - mn) / mx if mx else 0
            lum = (0.299 * r2 + 0.587 * g2 + 0.114 * b2) / 255
            if sat < 0.15:  # grayscale/achromatic
                return "corporate_formal"
            if sat > 0.7 and lum < 0.25:
                return "bold_editorial"
            delta = mx - mn
            if delta == 0: continue
            hue = 0.0
            if mx == r2: hue = 60 * (((g2-b2)/delta) % 6)
            elif mx == g2: hue = 60 * ((b2-r2)/delta + 2)
            else: hue = 60 * ((r2-g2)/delta + 4)
            if hue < 0: hue += 360
            if (hue < 20 or hue > 340) and sat > 0.5:
                return "bold_editorial"
            if 20 <= hue < 70:
                return "startup_playful"
            if 165 <= hue < 255 and sat > 0.4:
                return "technical_precise"
            if 255 <= hue < 330 and sat > 0.4:
                return "luxury_premium"
    except Exception:
        pass
    return "clean_minimal"


# ── Font processing & downloading ──────────────────────────────────────────────

def process_fonts(brand_data: dict) -> dict:
    typography = brand_data.get("typography") or {}
    fonts_list = brand_data.get("fonts") or []

    families = typography.get("families") or []
    if not families:
        families = [f.get("family", "") for f in fonts_list if isinstance(f, dict) and f.get("family")]
    # Filter out generic CSS stacks
    families = [f for f in families if f and f.lower() not in
                ("sans-serif", "serif", "monospace", "system-ui", "inherit", "")]
    if not families:
        families = ["Inter"]

    heading = families[0]
    body    = families[1] if len(families) > 1 else heading

    is_serif = any(w in heading.lower() for w in ["serif", "georgia", "times", "garamond", "playfair"])
    fallback = "Georgia, serif" if is_serif else "Inter, system-ui, sans-serif"

    weights = typography.get("weights") or [400, 600, 700]
    if not isinstance(weights, list):
        weights = [400, 600, 700]

    return {
        "heading": {"family": heading, "fallback": fallback, "weights": weights},
        "body":    {"family": body,    "fallback": fallback, "weights": [400]},
    }


def download_fonts(font_families: list, fonts_dir: Path) -> list:
    """
    Download woff2 files from Google Fonts for each font family.
    Returns list of relative paths to downloaded font files.
    """
    downloaded = []
    fonts_dir.mkdir(exist_ok=True)
    generic = {"sans-serif", "serif", "monospace", "system-ui", "inherit", "inter"}

    for family in font_families:
        if not family or family.lower() in generic:
            continue

        gf_name = family.replace(" ", "+")
        css_url = f"https://fonts.googleapis.com/css2?family={gf_name}:wght@400;600;700&display=swap"

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(css_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                css_text = resp.read().decode("utf-8")

            woff2_urls = re.findall(r"url\((https://[^)]+\.woff2[^)]*)\)", css_text)
            weights    = re.findall(r"font-weight:\s*(\d+)", css_text)

            for i, woff2_url in enumerate(woff2_urls[:3]):
                weight    = weights[i] if i < len(weights) else "400"
                safe_name = re.sub(r"[^a-z0-9]", "-", family.lower())
                filename  = f"{safe_name}-{weight}.woff2"
                font_path = fonts_dir / filename

                if not font_path.exists():
                    freq = urllib.request.Request(woff2_url, headers=headers)
                    with urllib.request.urlopen(freq, timeout=10) as fr:
                        font_path.write_bytes(fr.read())

                downloaded.append(f"fonts/{filename}")
                print(f"    ✓ Font: {family} w{weight}")

        except Exception as e:
            print(f"    ⚠ Font download failed ({family}): {e}")

    return downloaded


# ── Favicon downloading ────────────────────────────────────────────────────────

def download_favicon(base_url: str, assets_dir: Path) -> str:
    """Try common favicon paths. Returns relative asset path on success, else ''."""
    parsed = urllib.parse.urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    for url in [f"{origin}/favicon.ico", f"{origin}/favicon-32x32.png",
                f"{origin}/favicon-16x16.png", f"{origin}/apple-touch-icon.png"]:
        ext  = url.rsplit(".", 1)[-1].split("?")[0]
        path = assets_dir / f"favicon.{ext}"
        if download_asset(url, path) and path.stat().st_size > 100:
            print(f"    ✓ Favicon ({ext})")
            return f"assets/favicon.{ext}"

    return ""


# ── Logo variant generation ────────────────────────────────────────────────────

def generate_logo_variants(logo_path: Path, assets_dir: Path, primary_color: str) -> dict:
    """
    Generate light (white) and dark (primary color) logo variants.
    SVG: regex-based fill rewriting. PNG/WebP: Pillow pixel manipulation.
    Returns dict of variant asset paths created.
    """
    variants = {}
    suffix   = logo_path.suffix.lower()

    if suffix == ".svg":
        try:
            svg = logo_path.read_text(encoding="utf-8", errors="replace")

            def _recolor_fill(m, target):
                val = m.group(2).strip()
                try:
                    return m.group(1) + target + m.group(3) if _is_dark(val) else m.group(0)
                except Exception:
                    return m.group(0)

            light = re.sub(r'(fill\s*=\s*["\'])(?!none|url)([^"\']+)(["\'])',
                           lambda m: _recolor_fill(m, "#ffffff"), svg)
            dark  = re.sub(r'(fill\s*=\s*["\'])(?!none|url)([^"\']+)(["\'])',
                           lambda m: m.group(1) + primary_color + m.group(3)
                           if not _is_dark(m.group(2).strip()) else m.group(0), svg)

            (assets_dir / "logo-light.svg").write_text(light, encoding="utf-8")
            (assets_dir / "logo-dark.svg").write_text(dark,  encoding="utf-8")
            variants["logo_light"] = "assets/logo-light.svg"
            variants["logo_dark"]  = "assets/logo-dark.svg"
            print("    ✓ Logo variants (SVG light/dark)")
        except Exception as e:
            print(f"    ⚠ SVG variant error: {e}")

    elif suffix in (".png", ".webp"):
        try:
            from PIL import Image
            img    = Image.open(logo_path).convert("RGBA")
            w, h   = img.size
            pixels = img.load()
            pr, pg, pb = _hex_to_rgb(primary_color)

            light_img = img.copy(); lp = light_img.load()
            dark_img  = img.copy(); dp = dark_img.load()

            for y in range(h):
                for x in range(w):
                    r, g, b, a = pixels[x, y]
                    if a < 20:
                        continue
                    lum = 0.299*r + 0.587*g + 0.114*b
                    if lum < 100:   # dark pixel → white in light variant
                        lp[x, y] = (255, 255, 255, a)
                    if lum > 200:   # light pixel → primary in dark variant
                        dp[x, y] = (pr, pg, pb, a)

            light_img.save(assets_dir / "logo-light.png", "PNG")
            dark_img.save( assets_dir / "logo-dark.png",  "PNG")
            variants["logo_light"] = "assets/logo-light.png"
            variants["logo_dark"]  = "assets/logo-dark.png"
            print("    ✓ Logo variants (PNG light/dark)")
        except ImportError:
            print("    ⚠ Pillow not installed — skipping logo variants. pip install Pillow")
        except Exception as e:
            print(f"    ⚠ PNG variant error: {e}")

    return variants


# ── Cache management ───────────────────────────────────────────────────────────

def update_scrape_cache(brands_dir: Path, slug: str, url: str):
    cache_dir  = brands_dir / "_cache"
    cache_file = cache_dir  / "scrape-cache.json"
    cache_dir.mkdir(exist_ok=True)
    cache = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except Exception:
            pass
    cache[url] = {"slug": slug, "scraped_at": datetime.now(timezone.utc).isoformat()}
    cache_file.write_text(json.dumps(cache, indent=2))


# ── Multi-page crawl ───────────────────────────────────────────────────────────

KEY_PAGE_PATTERNS = [
    r"/about\b", r"/company\b", r"/story\b", r"/mission\b",
    r"/product\b", r"/features\b", r"/solutions\b",
    r"/blog\b",   r"/news\b",    r"/press\b",
]

def find_key_pages(links: list, base_url: str, max_pages: int = 3) -> list:
    """Pick up to max_pages internal links matching About/Product/Blog patterns."""
    parsed_base = urllib.parse.urlparse(base_url)
    base_netloc = parsed_base.netloc.lower()
    found, seen = [], set()

    for link in (links or []):
        href = (link.get("url") or link.get("href") or "") if isinstance(link, dict) else str(link)
        if not href or href in seen:
            continue
        if href.startswith("/"):
            href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        elif not href.startswith("http"):
            continue
        parsed = urllib.parse.urlparse(href)
        if parsed.netloc.lower() != base_netloc:
            continue
        path = parsed.path.rstrip("/").lower()
        if any(re.search(p, path) for p in KEY_PAGE_PATTERNS):
            seen.add(href)
            found.append(href)
            if len(found) >= max_pages:
                break

    return found


def merge_brand_data(primary: dict, extras: list) -> dict:
    """Merge color + personality data from extra pages into the primary brand dict."""
    merged = dict(primary)
    for extra in extras:
        if not isinstance(extra, dict):
            continue
        for key, val in (extra.get("colors") or {}).items():
            if key not in merged.get("colors", {}):
                merged.setdefault("colors", {})[key] = val
        ep = extra.get("personality") or {}
        mp = merged.setdefault("personality", {})
        if ep.get("traits") and not mp.get("traits"):
            mp["traits"] = ep["traits"]
        if ep.get("tagline") and not mp.get("tagline"):
            mp["tagline"] = ep["tagline"]
    return merged


# ── Main pipeline ──────────────────────────────────────────────────────────────

def scrape_brand(url: str, output_dir: str = "./brands", force: bool = False) -> dict:
    """
    Full Phase 1 + 2 pipeline:
      1. Firecrawl branding extraction (homepage)
      2. Multi-page crawl (About / Product / Blog)
      3. Color roles + WCAG contrast check
      4. Logo download + light/dark variant generation
      5. Favicon download
      6. Hero image download + k-means palette extraction
      7. Font download from Google Fonts
      8. Cache management
    Returns the complete brand profile dict.
    """
    slug       = get_slug(url)
    brands_dir = Path(output_dir)
    brand_dir  = brands_dir / slug
    assets_dir = brand_dir / "assets"
    fonts_dir  = brand_dir / "fonts"
    brand_json = brand_dir / "brand.json"

    # ── Freshness check ──
    if brand_json.exists() and not force:
        existing = json.loads(brand_json.read_text())
        try:
            age = (datetime.now(timezone.utc) -
                   datetime.fromisoformat(existing.get("scraped_at", ""))).days
            if age < 30:
                print(f"✓ Using cached brand profile for '{slug}' ({age}d old). --force to refresh.")
                return existing
        except Exception:
            pass

    brand_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(exist_ok=True)
    fonts_dir.mkdir(exist_ok=True)
    (brand_dir / "reports").mkdir(exist_ok=True)

    print(f"\nScraping brand identity: {url}")
    client = get_firecrawl_client()

    # ── Step 1: Homepage branding ──
    print("  → Extracting branding data (homepage)...")
    try:
        result     = client.scrape(url, formats=["branding", "links"])
        brand_data = _to_dict(
            getattr(result, "branding", None) or
            (result.get("branding") if isinstance(result, dict) else None) or {}
        )
        raw_links = _to_dict(
            getattr(result, "links", None) or
            (result.get("links") if isinstance(result, dict) else None) or []
        )
    except Exception as e:
        print(f"  ⚠ Scrape error: {e}. Continuing with defaults.", file=sys.stderr)
        brand_data, raw_links = {}, []

    if not brand_data:
        print("  ⚠ No branding data returned — defaults will be used.")

    # ── Step 2: Multi-page crawl ──
    key_pages = find_key_pages(raw_links, url, max_pages=3)
    if key_pages:
        labels = [p.rstrip("/").rsplit("/", 1)[-1] or p for p in key_pages]
        print(f"  → Crawling additional pages: {', '.join(labels)}")
        try:
            batch       = client.batch_scrape(key_pages, formats=["branding"],
                                              poll_interval=2, wait_timeout=60)
            extra_pages = _to_dict(
                getattr(batch, "data", None) or
                (batch.get("data") if isinstance(batch, dict) else None) or []
            )
            extra_brands = [p.get("branding", {}) for p in extra_pages if isinstance(p, dict)]
            brand_data   = merge_brand_data(brand_data, extra_brands)
        except Exception as e:
            print(f"    ⚠ Multi-page crawl error: {e}")

    # ── Step 3: Process brand identity ──
    raw_colors  = brand_data.get("colors") or {}
    colors      = assign_color_roles(raw_colors)
    fonts       = process_fonts(brand_data)
    style       = classify_style(brand_data)
    personality = brand_data.get("personality") or {}
    components  = brand_data.get("components") or {}

    logo_raw  = brand_data.get("logo")
    logo_info = logo_raw if isinstance(logo_raw, dict) else {"url": str(logo_raw or "")}
    images_raw = brand_data.get("images") or {}
    images     = list(images_raw.values()) if isinstance(images_raw, dict) else \
                 (images_raw if isinstance(images_raw, list) else [])

    # ── Build profile skeleton ──
    profile = {
        "company":     slug.replace("-", " ").title(),
        "slug":        slug,
        "url":         url,
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
        "colors":      colors,
        "fonts":       fonts,
        "assets": {
            "logo_svg":    "",
            "logo_png":    "",
            "logo_light":  "",
            "logo_dark":   "",
            "favicon":     "",
            "hero_images": [],
            "fonts":       [],
        },
        "brand_voice": {
            "tone":              personality.get("traits", ["professional"]),
            "tagline":           personality.get("tagline", ""),
            "description":       personality.get("description", ""),
            "description_style": "concise",
        },
        "design_language": {
            "style":          style,
            "corner_radius":  str(components.get("borderRadius") or "4px"),
            "color_scheme":   brand_data.get("colorScheme", "light"),
            "shadow_style":   str(components.get("shadowStyle") or "soft"),
            "layout_density": "spacious",
        },
    }

    # ── Step 4: Logo + variants ──
    print("  → Downloading assets...")
    logo_url = logo_info.get("url", "") if isinstance(logo_info, dict) else str(logo_info or "")
    if logo_url and logo_url.startswith("http"):
        ext = "svg" if ".svg" in logo_url.lower() else "png"
        logo_path = assets_dir / f"logo.{ext}"
        if download_asset(logo_url, logo_path):
            profile["assets"][f"logo_{ext}"] = f"assets/logo.{ext}"
            print(f"    ✓ Logo ({ext})")
            variants = generate_logo_variants(logo_path, assets_dir, colors["primary"])
            profile["assets"].update(variants)

    # ── Step 5: Favicon ──
    profile["assets"]["favicon"] = download_favicon(url, assets_dir)

    # ── Step 6: Hero images + k-means palette ──
    hero_paths    = []
    image_palette = []
    for i, img_url in enumerate(images[:3]):
        if not img_url or not img_url.startswith("http"):
            continue
        raw_ext  = img_url.split("?")[0].rsplit(".", 1)[-1][:4].lower()
        ext      = raw_ext if raw_ext in ("jpg", "jpeg", "png", "webp") else "jpg"
        img_path = assets_dir / f"hero-{i+1}.{ext}"
        if download_asset(img_url, img_path):
            hero_paths.append(f"assets/hero-{i+1}.{ext}")
            print(f"    ✓ Hero image {i+1}")
            image_palette.extend(extract_image_colors(img_path))

    profile["assets"]["hero_images"] = hero_paths
    if image_palette:
        profile["colors"]["image_palette"] = list(dict.fromkeys(image_palette))[:8]

    # ── Step 7: Font download ──
    font_families = list(dict.fromkeys([fonts["heading"]["family"], fonts["body"]["family"]]))
    downloaded_fonts = download_fonts(font_families, fonts_dir)
    profile["assets"]["fonts"] = downloaded_fonts

    # ── Step 8: Save + cache ──
    brand_json.write_text(json.dumps(profile, indent=2))
    update_scrape_cache(brands_dir, slug, url)

    contrast    = colors["_contrast_cover"]
    wcag_status = "✓ WCAG AA" if contrast >= 4.5 else "⚠ below AA"
    print(f"\n✓ Brand profile saved → {brand_json}")
    print(f"  Colors    : primary={colors['primary']}  accent={colors['accent']}")
    print(f"  Contrast  : {contrast}:1 cover text  {wcag_status}")
    print(f"  Fonts     : {fonts['heading']['family']} / {fonts['body']['family']}")
    print(f"  Style     : {style}  |  color_scheme={brand_data.get('colorScheme','light')}")
    print(f"  Assets    : logo={bool(profile['assets']['logo_svg'] or profile['assets']['logo_png'])}  "
          f"favicon={bool(profile['assets']['favicon'])}  "
          f"heroes={len(hero_paths)}  fonts={len(downloaded_fonts)}")

    return profile


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract brand identity from a company website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python brand_scrape.py https://stripe.com
  python brand_scrape.py https://linear.app --output-dir ./brands
  python brand_scrape.py https://notion.so --force
        """,
    )
    parser.add_argument("url",          help="Company website URL")
    parser.add_argument("--output-dir", default="./brands",
                        help="Root directory for brand profiles (default: ./brands)")
    parser.add_argument("--force",      action="store_true",
                        help="Re-scrape even if a recent profile exists (<30 days)")
    args = parser.parse_args()
    scrape_brand(args.url, output_dir=args.output_dir, force=args.force)


if __name__ == "__main__":
    main()
