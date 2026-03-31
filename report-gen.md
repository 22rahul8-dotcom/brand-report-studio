# Brand-Aware Magazine Report Generator
### *Intelligent, Auto-Generated Reports Styled to a Company's Identity*

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Phase 1 — Brand Scraping & Asset Extraction](#3-phase-1--brand-scraping--asset-extraction)
4. [Phase 2 — Brand Identity Processing](#4-phase-2--brand-identity-processing)
5. [Phase 3 — Report Intelligence Layer](#5-phase-3--report-intelligence-layer)
6. [Phase 4 — Magazine Layout Engine](#6-phase-4--magazine-layout-engine)
7. [Local Storage Structure](#7-local-storage-structure)
8. [Tech Stack](#8-tech-stack)
9. [User Flow](#9-user-flow)
10. [Report Layout Specifications](#10-report-layout-specifications)
11. [Output Formats](#11-output-formats)
12. [Edge Cases & Fallbacks](#12-edge-cases--fallbacks)
13. [Extensibility & Roadmap](#13-extensibility--roadmap)

---

## 1. Overview

The **Brand-Aware Magazine Report Generator** is an automated pipeline that accepts a company's website URL, intelligently scrapes its visual identity (colors, fonts, logos, imagery, favicons, and design language), and uses that identity to produce publication-quality, magazine-style reports. Every report feels native to the company — as if their own design team created it.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Brand Fidelity** | Every design decision is derived from the company's actual visual identity, not a generic template |
| **Magazine Quality** | Layouts follow editorial design standards — grids, hierarchy, pull quotes, sidebars, spreads |
| **Offline-First Assets** | All scraped brand assets are stored locally per company for fast, consistent regeneration |
| **Intelligent Fallbacks** | When assets are incomplete, the system infers design decisions from available data |
| **Multi-Format Output** | Reports are exported as HTML, PDF, and optionally DOCX |

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│              "Paste company website URL"                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   PHASE 1: BRAND SCRAPER                         │
│  • Headless browser crawl (Playwright)                           │
│  • Logo, favicon, font, color, image extraction                  │
│  • CSS variable & stylesheet parsing                             │
│  • OG / meta tag reading                                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                PHASE 2: BRAND IDENTITY PROCESSOR                 │
│  • Color palette clustering & role assignment                    │
│  • Font pairing analysis                                         │
│  • Logo format normalization (SVG / PNG)                         │
│  • Brand voice inference (from tagline, headlines)               │
│  • Brand profile JSON creation                                   │
│  • Asset storage: /brands/<company-slug>/                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│               PHASE 3: REPORT INTELLIGENCE LAYER                 │
│  • Report content ingestion (user-provided data / AI-generated)  │
│  • Section classification & hierarchy planning                   │
│  • Pull quote & callout extraction                               │
│  • Chart & data visualization specs                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              PHASE 4: MAGAZINE LAYOUT ENGINE                     │
│  • Grid system construction from brand tokens                    │
│  • Section-by-section layout assignment                          │
│  • Cover page, spreads, sidebars, footers                        │
│  • Brand-styled charts, tables, callout boxes                    │
│  • HTML → PDF rendering (Puppeteer / WeasyPrint)                 │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      OUTPUT                                      │
│              HTML · PDF · DOCX · Preview                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 1 — Brand Scraping & Asset Extraction

### 3.1 Trigger

The user pastes a URL (e.g., `https://stripe.com`) into the interface. The scraper is invoked automatically.

### 3.2 Crawl Strategy

The scraper uses a **headless Playwright browser** so JavaScript-rendered pages, lazy-loaded images, and dynamic styles are all captured correctly.

```
Step 1  →  Load homepage (full render, wait for network idle)
Step 2  →  Follow 2–3 key internal pages (About, Product, Blog)
Step 3  →  Extract all asset references
Step 4  →  Download and store assets locally
Step 5  →  Parse all CSS for design tokens
Step 6  →  Write brand profile JSON
```

### 3.3 What Gets Scraped

#### Logos & Favicons
- `<link rel="icon">` and `<link rel="apple-touch-icon">` — favicon in multiple sizes
- `<img>` tags in `<header>` containing "logo" in `class`, `id`, `alt`, or `src`
- SVG inline logos embedded in the DOM
- OG image (`<meta property="og:image">`) as fallback hero asset

#### Color Palette
- CSS custom properties (`--color-*`, `--brand-*`, `--primary`, `--accent`, etc.)
- Computed `background-color` and `color` values from key DOM elements: `<header>`, `<nav>`, `<footer>`, hero sections, CTA buttons
- Hex codes extracted from inline styles and `<style>` tags
- Color frequency analysis across the full DOM to surface dominant hues

#### Typography
- `@font-face` declarations from stylesheets
- Google Fonts / Adobe Fonts `<link>` tags → font names and weights extracted
- Computed `font-family` of `<h1>`, `<h2>`, `<p>`, `<nav>`, `<footer>`
- Font size scale values extracted as a type ramp

#### Imagery & Textures
- Hero background images from CSS `background-image` properties
- High-resolution images from `<picture>` and `<img srcset>` elements
- Pattern or texture assets detected via low-entropy image analysis
- Photography style tags (lifestyle, product, abstract, illustration) inferred via image classification

#### Brand Voice & Tone
- Homepage `<h1>` and `<h2>` headline text (used to infer tone: bold, technical, friendly, premium, etc.)
- `<meta name="description">` and OG description
- Tagline or slogan text near the logo

### 3.4 Scraper Output

All data is assembled into a `brand.json` file and written to the local storage directory:

```json
{
  "company": "Stripe",
  "slug": "stripe",
  "url": "https://stripe.com",
  "scraped_at": "2026-03-23T10:42:00Z",
  "colors": {
    "primary": "#635BFF",
    "secondary": "#0A2540",
    "accent": "#00D4FF",
    "background": "#FFFFFF",
    "surface": "#F6F9FC",
    "text_primary": "#0A2540",
    "text_secondary": "#425466",
    "roles": {
      "cta_bg": "#635BFF",
      "nav_bg": "#FFFFFF",
      "footer_bg": "#0A2540"
    }
  },
  "fonts": {
    "heading": { "family": "Sohne", "fallback": "Inter, sans-serif", "weights": [400, 600, 700] },
    "body": { "family": "Sohne", "fallback": "Inter, sans-serif", "weights": [400] },
    "mono": { "family": "Sohne Mono", "fallback": "monospace", "weights": [400] }
  },
  "assets": {
    "logo_svg": "assets/logo.svg",
    "logo_png": "assets/logo.png",
    "favicon": "assets/favicon.ico",
    "favicon_32": "assets/favicon-32x32.png",
    "og_image": "assets/og-image.jpg",
    "hero_images": ["assets/hero-1.jpg", "assets/hero-2.jpg"],
    "textures": []
  },
  "brand_voice": {
    "tone": ["technical", "trustworthy", "modern"],
    "tagline": "Financial infrastructure for the internet.",
    "description_style": "concise"
  },
  "design_language": {
    "style": "clean_minimal",
    "corner_radius": "6px",
    "shadow_style": "soft",
    "layout_density": "spacious",
    "uses_gradients": true,
    "uses_illustrations": true
  }
}
```

---

## 4. Phase 2 — Brand Identity Processing

### 4.1 Color Role Assignment

The processor takes raw extracted colors and assigns semantic roles for the report layout:

| Report Role | Assignment Logic |
|-------------|-----------------|
| `cover_bg` | Primary brand color or darkest extracted color |
| `cover_text` | Highest contrast color against `cover_bg` |
| `section_accent` | Accent or secondary color |
| `body_text` | Primary text color from homepage |
| `pull_quote_bg` | Light tint (15% opacity) of primary color |
| `table_header_bg` | Secondary color |
| `sidebar_bg` | Surface color or light tint of primary |
| `link_color` | Accent color |
| `divider_color` | 20% opacity of text color |

### 4.2 Typography Pairing

If the brand uses a single font family, the system generates a hierarchical type scale:

```
Display / Cover Title  →  64–80px  |  weight: 700  |  line-height: 1.1
Section Heading (H1)   →  36–44px  |  weight: 600  |  line-height: 1.2
Sub-heading (H2)       →  24–28px  |  weight: 600  |  line-height: 1.3
Pull Quote             →  22–26px  |  weight: 400  |  italic
Body Copy              →  15–17px  |  weight: 400  |  line-height: 1.65
Caption / Label        →  11–12px  |  weight: 500  |  uppercase, tracked
```

If web fonts cannot be downloaded (licensing restrictions), the system maps to the closest Google Fonts alternative and flags the substitution in the brand profile.

### 4.3 Logo Normalization

- SVG logos are preferred and stored as-is
- Raster logos (PNG/JPG) are processed to extract a transparent-background version
- A dark variant and light variant are derived (for use on light and dark report sections respectively)
- Minimum dimensions enforced: 200px width for inline use; original resolution preserved for cover

### 4.4 Design Language Classification

The processor classifies the brand's design language into one of these buckets to inform layout decisions:

| Style Class | Characteristics | Layout Behavior |
|-------------|-----------------|-----------------|
| `clean_minimal` | Lots of white space, thin type, muted palette | Generous margins, understated dividers |
| `bold_editorial` | Strong color blocks, heavy type | Full-bleed color sections, large headings |
| `corporate_formal` | Navy/grey palette, serif fonts, structured grids | Classic two-column layout, ruled lines |
| `startup_playful` | Bright gradients, rounded corners, illustrations | Asymmetric layouts, colorful callouts |
| `luxury_premium` | Black/gold/white, serif headings, photography | Full-bleed imagery, elegant spacing |
| `technical_precise` | Monospace elements, dark mode affinity, data-dense | Code-like grid, dense information design |

---

## 5. Phase 3 — Report Intelligence Layer

### 5.1 Content Ingestion

The user provides the report content in one of three ways:

1. **Paste raw text** — The AI structures it into sections automatically
2. **Upload a document** (DOCX / PDF / Markdown) — The system extracts and restructures
3. **Describe the report** — The AI generates the content using the company's scraped brand voice

### 5.2 Section Classification

The AI analyzes the content and classifies each block into a section type, which determines how it will be laid out:

| Section Type | Layout Assigned |
|--------------|----------------|
| Executive Summary | Full-width intro spread with large lead text |
| Key Metrics / Numbers | Stat cards in a 3 or 4-column grid |
| Narrative / Analysis | Two-column body text with sidebar |
| Data Table | Full-width styled table |
| Chart / Visualization | Full-width or half-width chart section |
| Quote / Testimonial | Full-bleed pull quote spread |
| Recommendations | Numbered list with icon accents |
| Conclusion | Single-column centered layout |
| Appendix | Dense two-column format |

### 5.3 Pull Quote & Callout Extraction

The system automatically identifies compelling sentences (high information density, quotable length, declarative structure) and promotes them to pull quotes or callout boxes, visually styled to the brand.

---

## 6. Phase 4 — Magazine Layout Engine

### 6.1 Grid System

Every report uses a **12-column grid** built from the brand's `layout_density` and `corner_radius` values. Margins, gutters, and column widths are derived from the brand profile.

```
Spacious brands  →  outer margin: 72px  |  gutter: 24px
Standard brands  →  outer margin: 48px  |  gutter: 18px
Dense brands     →  outer margin: 36px  |  gutter: 12px
```

### 6.2 Cover Page

The cover is the most brand-expressive page:

- **Full-bleed background**: primary brand color, gradient, or hero image
- **Logo**: positioned top-left or top-center, light variant on dark backgrounds
- **Report title**: display font, maximum weight, color-contrasted against background
- **Subtitle / date / company name**: smaller, secondary weight
- **Decorative element**: derived from brand (geometric shape, texture, illustration style)
- **Bottom bar**: footer color with report metadata

### 6.3 Section Spreads

Each major section opens with a branded section header:
- Left-aligned section number in accent color
- Section title in heading font
- Thin horizontal rule in brand accent color
- Optional hero image or color block for visual separation

### 6.4 Body Layout Variants

The engine selects from these layout templates per section type:

```
[ FULL SPREAD ]                [ TWO-COLUMN ]              [ SIDEBAR ]
┌──────────────────────┐       ┌──────────┬──────────┐     ┌────────────┬────┐
│                      │       │          │          │     │            │    │
│   Large headline     │       │  Body    │  Body    │     │  Body      │Tip │
│   + lead paragraph   │       │  copy    │  copy    │     │  copy      │box │
│                      │       │          │          │     │            │    │
└──────────────────────┘       └──────────┴──────────┘     └────────────┴────┘

[ STAT CARDS ]                 [ PULL QUOTE ]
┌──────┐ ┌──────┐ ┌──────┐    ┌──────────────────────┐
│  42% │ │  $2M │ │  18x │    │                      │
│      │ │      │ │      │    │  " Pull quote text "  │
│ desc │ │ desc │ │ desc │    │      — Attribution   │
└──────┘ └──────┘ └──────┘    └──────────────────────┘
```

### 6.5 Brand-Styled Components

Every component in the report is rendered using brand tokens:

**Tables**
- Header row: `table_header_bg` color, white or contrasted text, heading font
- Alternating rows: white / light surface tint
- Border: 1px `divider_color`
- Corner radius from brand profile

**Charts & Data Visualizations**
- Bar/line colors use the brand's primary, secondary, and accent colors
- Axis labels in body font, caption size
- Grid lines in `divider_color`
- Chart title in sub-heading style

**Callout Boxes**
- Left border: 4px solid accent color
- Background: `pull_quote_bg` (light primary tint)
- Icon: derived from brand tone (ℹ️ for informational, ⚡ for highlight, etc.)

**Page Footer**
- Footer background: `footer_bg` color from brand
- Logo mark (small) on the left
- Page number centered or right-aligned
- Report title in caption style

---

## 7. Local Storage Structure

All brand assets and profiles are stored locally using a consistent directory convention:

```
brands/
├── stripe/
│   ├── brand.json               ← Master brand profile
│   ├── assets/
│   │   ├── logo.svg
│   │   ├── logo-light.svg       ← Auto-generated light variant
│   │   ├── logo-dark.svg        ← Auto-generated dark variant
│   │   ├── favicon.ico
│   │   ├── favicon-32x32.png
│   │   ├── og-image.jpg
│   │   ├── hero-1.jpg
│   │   └── hero-2.jpg
│   ├── fonts/
│   │   ├── Sohne-Regular.woff2
│   │   └── Sohne-Bold.woff2
│   └── reports/
│       ├── q1-2026-report/
│       │   ├── report.html
│       │   ├── report.pdf
│       │   └── report-metadata.json
│       └── annual-review-2025/
│           ├── report.html
│           └── report.pdf
│
├── notion/
│   ├── brand.json
│   ├── assets/
│   ├── fonts/
│   └── reports/
│
└── _cache/
    └── scrape-cache.json        ← URL → slug mapping + scrape timestamps
```

### Naming Convention

Company slugs are derived from the domain name:
- `https://stripe.com` → `stripe`
- `https://www.notion.so` → `notion`
- `https://linear.app` → `linear`
- `https://www.mckinsey.com` → `mckinsey`

If a slug already exists, the scraper checks the `scraped_at` timestamp. If it's older than 30 days (configurable), it re-scrapes and updates the brand profile. Existing reports are preserved.

---

## 8. Tech Stack

### Core Pipeline

| Component | Tool / Library | Purpose |
|-----------|---------------|---------|
| Headless Browser | **Playwright** (Node.js) | Full-page rendering, JS execution, screenshot capture |
| CSS Parser | **PostCSS** + **css-tree** | Extract design tokens from stylesheets |
| Color Processing | **Chroma.js** | Color role assignment, contrast calculation, tinting |
| Font Detection | **FontFaceObserver** + fetch intercept | Identify and download web fonts |
| Image Processing | **Sharp** | Logo variant generation, background removal |
| Color Clustering | **k-means** (ml-kmeans) | Dominant palette extraction from imagery |
| AI / LLM | **Claude API (claude-sonnet-4)** | Content structuring, brand voice inference, section layout decisions |

### Report Rendering

| Component | Tool / Library | Purpose |
|-----------|---------------|---------|
| Template Engine | **Nunjucks** or **Handlebars** | HTML template rendering with brand tokens |
| CSS Framework | Custom CSS (no Tailwind) | Pixel-precise magazine layouts |
| PDF Export | **Puppeteer** or **WeasyPrint** | High-fidelity HTML-to-PDF with print CSS |
| Chart Generation | **Chart.js** or **D3.js** | Brand-colored data visualizations |
| DOCX Export | **docx** (npm) | Word document output for editable reports |

### Storage & Config

| Component | Tool | Purpose |
|-----------|------|---------|
| Local Storage | File system (`/brands/`) | Asset and profile persistence |
| Config | `.env` + `config.json` | Paths, API keys, scrape intervals |
| CLI Interface | **Commander.js** | Command-line report generation |
| Web UI (optional) | **Next.js** | Browser-based interface for URL input and preview |

---

## 9. User Flow

### Step-by-Step

```
1.  User opens the app (CLI or web interface)

2.  User pastes: https://linear.app

3.  System checks /brands/linear/ → not found → initiates scrape
        [Loading: Scraping Linear's brand identity...]

4.  Playwright opens linear.app, renders fully, extracts:
        ✓ Logo (SVG detected)
        ✓ Favicon (32px, 64px)
        ✓ Colors: 7 unique hex values extracted
        ✓ Fonts: "Inter" via Google Fonts link
        ✓ Hero images: 3 found
        ✓ Design language: clean_minimal
        ✓ Brand voice: technical, precise, modern
        → Brand profile saved to /brands/linear/brand.json

5.  User is prompted:
        "Brand identity for Linear captured. 
         What type of report would you like to create?"
        [ Product Update ] [ Investor Report ] [ Annual Review ] [ Custom ]

6.  User selects "Investor Report" and pastes their report content
    (or types a description and lets AI generate it)

7.  AI processes content:
        → Identifies 6 sections: Executive Summary, Key Metrics, 
          Growth Analysis, Product Milestones, Team, Outlook
        → Selects layout per section
        → Extracts 2 pull quotes
        → Specs 3 charts

8.  Layout engine assembles the report:
        → Builds cover page with Linear's purple + dark theme
        → Renders each section with Inter font, brand colors
        → Generates charts in Linear's color palette
        → Applies styled tables, callout boxes
        → Inserts logo, page numbers, footer

9.  Preview renders in browser (HTML)
        User can: [ Download PDF ] [ Download DOCX ] [ Edit Content ] [ Re-style ]

10. Report saved to /brands/linear/reports/investor-report-2026-03/
```

---

## 10. Report Layout Specifications

### Cover Page

```
┌─────────────────────────────────────────────────────────┐
│  [LOGO]                                      [FAVICON]  │  ← header bar (brand color)
├─────────────────────────────────────────────────────────┤
│                                                         │
│                                                         │
│   ████████████████████████████████████████             │
│   ██  COMPANY NAME  ██████████████████████             │
│   ████████████████████████████████████████             │
│                                                         │  ← full-bleed brand bg
│   Report Title in Display Font                          │
│   Bold, oversized, high contrast                        │
│                                                         │
│   Subtitle or Report Type                               │
│   Month Year                                            │
│                                                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Prepared by: [Name]    |    Confidential    |  Page 1  │  ← footer bar
└─────────────────────────────────────────────────────────┘
```

### Interior Spread (Two-Column)

```
┌─────────────────────────────────────────────────────────┐
│  [logo mark]  Report Title                   Page  04   │  ← running header
├──────────────────────────────────┬──────────────────────┤
│                                  │                      │
│  02 / Section Heading            │  Body copy continues │
│  ─────────────────               │  here across the     │
│                                  │  right column with   │
│  Body copy flows here in the     │  consistent line     │
│  left column using brand body    │  height and brand    │
│  font at 16px / 1.65 line-height │  typography.         │
│                                  │                      │
│  ┌────────────────────────────┐  │  ╔════════════════╗  │
│  │  " Pull quote in larger   │  │  ║  KEY STAT       ║  │
│  │    italic brand type "    │  │  ║   $4.2B         ║  │
│  └────────────────────────────┘  │  ║  Annual ARR    ║  │
│                                  │  ╚════════════════╝  │
├─────────────────────────────────────────────────────────┤
│  [logo mark]  Section Name                   Page  04   │  ← running footer
└─────────────────────────────────────────────────────────┘
```

### Full-Bleed Stat Page

```
┌─────────────────────────────────────────────────────────┐
│                  [brand color background]                │
│                                                         │
│         BY THE NUMBERS                                  │
│         ─────────────────────────────                   │
│                                                         │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐        │
│   │    42%    │   │   $2.1M   │   │    18x    │        │
│   │  YoY      │   │  MRR      │   │  ROI      │        │
│   │  Growth   │   │           │   │           │        │
│   └───────────┘   └───────────┘   └───────────┘        │
│                                                         │
│   ┌───────────┐   ┌───────────┐                        │
│   │   98.9%   │   │   150+    │                        │
│   │  Uptime   │   │  Enterprise│                        │
│   │           │   │  Clients  │                        │
│   └───────────┘   └───────────┘                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 11. Output Formats

### HTML Report
- Self-contained single-file HTML with embedded CSS and base64 assets
- Print CSS included for direct browser-print to PDF
- Responsive preview for desktop screen
- Shareable without dependencies

### PDF Report
- Generated via Puppeteer headless Chrome print
- A4 or Letter size (configurable)
- Embedded fonts, full color fidelity
- Bleed-safe margins
- Metadata: title, author, company, creation date

### DOCX Report
- Editable Word document using `docx` npm package
- Brand fonts embedded where licensing permits (fallback to system fonts)
- Styles mapped: Heading1 → section title, Heading2 → sub-heading, etc.
- Tables, images, and callout boxes rendered as close to brand spec as possible
- Suitable for client handoff requiring editable versions

---

## 12. Edge Cases & Fallbacks

| Scenario | Fallback Behavior |
|----------|-------------------|
| No logo found | Use company initials in brand color as logomark |
| Fonts are proprietary / cannot download | Map to closest Google Fonts alternative; log substitution |
| Only one color extracted | Generate a full palette using hue rotation and tint/shade steps |
| JavaScript-heavy SPA fails to render | Retry with extended wait; fall back to static HTML parse |
| OG image is low resolution | Skip; use color block with brand primary instead |
| No hero images found | Generate abstract geometric pattern from brand colors |
| Website is behind auth / paywall | Prompt user to upload brand assets manually |
| Brand colors fail WCAG contrast on report | Auto-adjust lightness while preserving hue |
| Multiple brand variants detected | Prompt user to select: "We found 2 logo variants — which should we use?" |

---

## 13. Extensibility & Roadmap

### Immediate Extensions
- **Brand comparison reports**: Generate a single report comparing two companies using a split-design system
- **Dark mode reports**: Full dark theme variant derived from the brand palette
- **Template library**: Pre-built magazine layout archetypes (Startup Annual, Investor Deck, Product Launch, Case Study)
- **Multi-language support**: RTL layout support for Arabic/Hebrew brands

### AI Enhancements
- **Auto-rescrape triggers**: Detect brand updates (logo/color changes) and flag users to regenerate
- **Brand voice writing**: AI-generated report body content that matches the scraped brand tone
- **Smart image curation**: Select the most on-brand hero images from the scraped library for each section
- **Competitor benchmarking**: Generate a report that places the company's metrics alongside industry benchmarks

### Integration Targets
- **Figma plugin**: Push generated report layouts directly into Figma frames for designer editing
- **Notion export**: Structured content exported to a Notion database with brand styling metadata
- **Google Slides**: Magazine-layout slides generated from the same pipeline
- **CMS webhooks**: Trigger report generation automatically when new data is published

---

*Document version 1.0 — March 2026*
*This specification covers the full system design for the Brand-Aware Magazine Report Generator pipeline.*
