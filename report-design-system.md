# Report Design System
### Visual Intelligence Extracted from Industry-Grade Research Reports

> Sourced from: Autodesk 2025 State of Design & Make · BCG AI Radar 2025 · CrowdStrike LATAM Threat Report · Splunk Predictions 2025 · McKinsey Superagency in the Workplace

---

## 1. Core Design Philosophy

Every high-quality professional report follows the same underlying rules:

- **One accent color does all the work.** Yellow (Autodesk), BCG green, CrowdStrike red, Splunk orange, McKinsey blue — each report picks a single high-saturation accent and uses it exclusively to signal "the most important thing on this page." It never decorates. It points.
- **Extreme scale contrast replaces decoration.** Big stat = 72–120pt. Body text = 10–11pt. The gulf between them is the design. Nothing in between.
- **White space is active, not passive.** Margins are wide. Sections breathe. A page that feels "empty" is doing its job.
- **One signature visual asset.** Autodesk: abstract 3D renders. BCG: the green orb. CrowdStrike: the wave column. Splunk: swooping arc lines. McKinsey: the fiber stream. One motif, repeated consistently, creates a report identity.
- **Data-first, decoration-second.** Charts are plain — no gradients on bars, no 3D effects, no unnecessary gridlines. The data speaks; the design only amplifies it.

---

## 2. Page Layout Architecture

### 2.1 The Two Dominant Structural Templates

**A. Split-Panel Layout (40/60 or 35/65)**
The most common pattern across all five reports.
- Left panel: image, color block, or dark background with title text
- Right panel: body content, chart, or dominant stat
- Used for: hero sections, pull-quote pages, chapter openers

```
┌─────────────┬──────────────────────┐
│  IMAGE or   │                      │
│  COLOR      │   CONTENT / CHART    │
│  BLOCK      │                      │
│  (35–40%)   │   (60–65%)           │
└─────────────┴──────────────────────┘
```

**B. Full-Width Content with Top Header Band**
Used for dense data pages.
- Narrow top band: breadcrumb / section chip / chapter label
- Full-width content below
- No decorative column; data uses 100% of horizontal space

### 2.2 Chapter Dividers / Section Breaks

The chapter break page is the highest-drama moment in a report. Consistent techniques across all five sources:

| Technique | How it works |
|-----------|--------------|
| Full-bleed dark background | Entire page in black or deep brand color. Single bold headline, white, centered or left-aligned. |
| Oversized chapter number | The numeral rendered at 150–200pt, nearly filling the page, in light gray or accent color. Chapter title overlaid or placed beneath it. |
| Abstract art crop | The signature visual asset (render, fiber stream, illustration) fills the full spread, with the chapter title reversed out in white over the image. |
| Color gradient panel | Top 30–40% of the page is the dark/accent band; content fills the lower 60–70%. |

### 2.3 Grid System for Body Pages

- **Margins:** 48–64px equivalent on all sides
- **Columns:** Single-column for charts/stats pages; two-column for text-heavy pages
- **Gutter:** 24–32px between columns
- **Breadcrumb row:** 28–32px height at top, separated by a 1px horizontal rule
- **Logo lockup:** Always bottom-right, 8–10pt, never changes position

---

## 3. Typography System

### 3.1 Type Hierarchy (6 Levels)

| Level | Role | Size | Weight | Treatment |
|-------|------|------|--------|-----------|
| T1 | Cover / Chapter title | 60–80pt | Black/Heavy | Mixed case or uppercase, accent color on key word |
| T2 | Section heading | 36–48pt | Bold | Mixed case, brand color or white-on-dark |
| T3 | Sub-heading | 18–24pt | Semi-bold | Mixed case, primary text color |
| T4 | Pull quote / Stat label | 14–18pt | Medium-italic | Generous line-height (1.6x), accent color or contrasting color |
| T5 | Body text | 10–11pt | Regular | 1.4–1.5 line-height, high legibility sans-serif |
| T6 | Caption / Source / Footnote | 8–9pt | Regular | Light gray, tracked slightly wide |

### 3.2 Signature Typography Techniques

**The two-color headline split (Splunk method)**
Split the headline at its conceptual hinge. First clause in primary text color; key term or payload word in accent color.
```
"The organizations that         ← body color (black)
 will lead are those            ← body color
 who invest now"               ← accent color on key word
```

**The oversize stat display (all five reports)**
A single metric rendered at extreme scale. Format:
- Number: 72–120pt, bold, accent color
- Unit or descriptor: 16–18pt, regular weight, below or beside the number
- Supporting context: 11pt, gray, below the descriptor

```
  ┌─────────────┐
  │    76%      │  ← 80pt bold, accent color
  │             │
  │ of companies│  ← 14pt, bold black
  │ plan to     │
  │ increase    │
  │ AI budgets  │
  └─────────────┘
```

**The section locator chip**
A small filled pill or rectangle — always in the accent color — containing a short uppercase label ("INSIGHT 4", "CHAPTER 2", "KEY FINDING"). Appears top-left on every content page. Creates instant wayfinding.

**The drop cap opener**
On the first paragraph of a major section, set the initial letter at 3–4× the body text size, floated left, in the accent color or dark gray.

**Pull quote treatment (BCG / McKinsey method)**
- Opening quotation mark: 48–60pt solid, accent color
- Quote text: 16–20pt semi-bold, generous line-height
- Attribution: 10pt, all-caps tracked, lighter weight
- Separator: 1–2px horizontal rule in accent color above attribution

---

## 4. Color System

### 4.1 The Universal Color Architecture (3-Color Rule)

Every report uses exactly three functional colors:

1. **Background dark** — Black or deep brand color. Used for: covers, divider pages, pull-quote cards, section chips.
2. **Background light** — White or off-white (never pure white in Splunk — a barely perceptible warm cream tint). Used for: all body/content pages.
3. **Accent** — One high-saturation brand color. Used exclusively to mark the single most important element per composition.

Secondary colors appear only in data (chart fills) or in photography. They never appear in the layout chrome.

### 4.2 Accent Color Roles

| Role | Usage |
|------|-------|
| Current section / active locator | Section chip, chapter number highlight |
| Single most important stat on a page | The large display number gets the accent |
| One key word in each headline | Never color more than 3–4 words |
| Hyperlinks / interactive references | Consistent, never decorative |
| Primary data fill in charts | All bars, rings, lines use the accent (or a tonal variant) |
| The brand's visual motif | The decorative element (arc lines, wave column, etc.) |

### 4.3 Background Treatment for Dark Sections

Dark pages use one of three techniques:
- **Pure black** (#0A0A0A): Autodesk, BCG. Creates maximum contrast and luxury.
- **Deep brand color** (#2B0D5E purple-black for Splunk, dark forest green for BCG section dividers): More editorial warmth.
- **Dark gradient** (top-left black to bottom-right brand color): CrowdStrike cover. Creates depth without multiple fills.

### 4.4 Data Color Palette

Charts use a disciplined system:
- **Primary series:** Accent color at 100%
- **Secondary series / comparison year:** Accent color at 50–60% opacity or a lighter tonal variant
- **Baseline / "low value" / "not yet" segment:** Light gray (#C8C8D0 equivalent) — never a competing hue
- **Negative / risk / warning:** Warm red only if it contrasts with the accent; otherwise dark gray
- **Geographic fills:** Use a single-hue diverging scale (light tint → full accent) so the most important region is most saturated

---

## 5. Data Visualization

### 5.1 Chart Type Selection Matrix

Choose the chart type based on what the data is showing:

| Data story | Chart type | Notes |
|------------|-----------|-------|
| Comparison of a value over time (2 points) | Slope chart | Show change as direction and magnitude; annotate delta inline |
| Comparison of a value over time (3+ points) | Line chart (minimal) | No background fill; accent-color line; circle endpoint markers |
| Distribution across categories (single year) | Horizontal bar chart | Bars horizontal for readability; labels flush-left; values at bar end |
| Distribution across categories (two years) | Grouped or slope panel | Pair 2024/2025 bars in same accent family |
| Part-of-whole (single metric) | Thick donut/ring | Ring width ~30% of radius; fill accent color; big bold % inside ring |
| Part-of-whole (small N, human-scale) | Waffle / unit dot grid | 10×10 grid; accent-filled dots for the proportion; gray for remainder |
| Multi-variable categorical comparison | Vertical thin-bar cluster | Descending order; single accent fill; no legend (label bars directly) |
| Geographic distribution | Choropleth map + horizontal bar | Map for geography intuition; bar for precise ranking; connect with color |
| Framework / hierarchy | Bordered box diagram | Use accent-colored top bar + white column boxes; no gradients, no icons unless necessary |
| Key stats summary | Stat card grid | 2- or 3-column; each card: oversized number + short descriptor |

### 5.2 Chart Styling Rules (Applies to All Types)

- **No chart background fill.** The page background is the chart background.
- **No 3D effects, no drop shadows on data elements.**
- **No legend if bars/lines can be labeled directly.** Direct labels are always preferred over legend lookups.
- **Horizontal reference grid lines:** Thin, light gray (#E0E0E8), 1px. Maximum 4–5 lines. No vertical grid lines.
- **Axis labels:** 9–10pt, regular, gray. Y-axis label can be omitted if the chart title describes the metric.
- **Data labels on bars:** Bold, same color as bar fill (darker) or white if bar is dark. Inside bar when bar is wide enough; outside (right-aligned) when narrow.
- **Annotations:** Use only to highlight the key story (e.g., "↑ 14pp year-over-year"). Small callout box in accent color with white text. Not more than 1–2 annotations per chart.
- **Chart title format:** Describe the finding, not the variable. "AI investment intent rises sharply in APAC" not "AI Investment by Region."

### 5.3 Slope Chart Specification (Autodesk Signature)

```
  2024          2025
   ○────────────●   "Expanding AI use cases"    +9pp
   ○──────────●     "Increasing AI budget"      +7pp
   ○────●           "Cutting legacy spend"      +3pp
   ○●              "Moving to cloud"            +1pp
```
- Open circle (hollow): previous year endpoint
- Filled circle: current year endpoint
- Line in accent color with a soft fill band beneath (20% opacity) for visual weight
- Delta annotation midway on the slope, in a small accent-colored pill label
- Multiple slopes in a single panel, stacked vertically with consistent row height

### 5.4 Stat Card / "By the Numbers" Panel Specification

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│              │  │              │  │              │
│    76%       │  │    3×        │  │   $2.4T      │
│              │  │              │  │              │
│ of companies │  │ more likely  │  │ projected    │
│ are adopting │  │ to retain    │  │ AI market    │
│ AI agents    │  │ top talent   │  │ by 2030      │
└──────────────┘  └──────────────┘  └──────────────┘
```
- Number: 64–80pt, bold, accent color
- Descriptor: 12–13pt, regular, body text color
- Card border: 1px light gray rule, or a 3px left accent-color border
- Cards in a 2–4 column grid
- Optional hairline rule beneath the number, before the descriptor

### 5.5 Charts That Must Be Generated Dynamically (Based on Data Type)

When the report content contains the following patterns, auto-generate the corresponding chart:

| Content pattern detected | Auto-generate |
|--------------------------|---------------|
| Numbers with % signs across multiple items | Horizontal bar chart or donut |
| Year-over-year or before/after comparison | Slope chart |
| Dollar amounts / revenue / market size | Vertical bar chart + stat card |
| Distribution across named categories (5+) | Horizontal ranked bar chart |
| Single key percentage or ratio | Large donut ring with stat overlay |
| A list of 3–6 parallel items with equal importance | Stat card grid |
| Geographic / country references with counts | Choropleth note (if map SVG available) + ranked bars |
| A ranked top-N list | Horizontal lollipop or thin bar, descending |

---

## 6. Visual Motifs & Decorative Elements

These are the "signature" elements that give each report its identity. When building a branded report, choose ONE and apply it consistently.

### 6.1 Motif Types and HTML Implementation

**The Color-Block Decorative Column (CrowdStrike method)**
A vertical strip (30–35% page width) on the right or left side of every interior page. Filled with the brand color, no content. Pure visual identity marker. In HTML:
```css
.page-decoration {
  position: absolute;
  right: 0; top: 0; bottom: 0;
  width: 32%;
  background: var(--brand-primary);
  opacity: 0.08;  /* subtle on light pages; 1.0 on dark pages */
}
```

**The Geometric Background Shape (all reports)**
Large, low-opacity geometric forms positioned behind content:
- Circle at 20% opacity, 400px diameter, accent color, positioned at top-right corner
- Overlapping circles or squares at 8–12% opacity
- Diagonal slash or ruled lines at 5% opacity

**The Section Number Device (Autodesk method)**
A very large chapter/section number (200–300px, extra-bold) rendered at 6–8% opacity as a background watermark behind the section content. The readable section number (20–24px) is overlaid at full opacity in the accent color.

**The Accent Rule**
A 3–4px horizontal rule in the exact accent color, used to open a major section. Spans the full content width. Placed above the section heading, with 32px space above and 16px space below.

**The Pull Quote Card (BCG / Autodesk method)**
A filled rectangle (black or dark brand color) containing the pull quote, absolutely positioned over a photography element or set as a standalone card.
```css
.pull-quote-card {
  background: #0a0a0f;
  border-left: 4px solid var(--accent);
  padding: 28px 32px;
  border-radius: 4px;
}
.pull-quote-card blockquote {
  font-size: 18px;
  font-style: italic;
  line-height: 1.65;
  color: #ffffff;
}
.pull-quote-card cite {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
  font-style: normal;
}
```

---

## 7. Cover Page Architecture

The cover is the only page where all visual energy is deployed simultaneously. Consistent techniques:

### 7.1 Cover Layout Template

```
┌─────────────────────────────────────────────────────┐
│  [LOGO / BRAND IDENTIFIER]              [YEAR]      │  ← 48px top band
│                                                     │
│                                                     │
│     [SIGNATURE VISUAL ASSET]                        │  ← 55–65% height
│     (abstract render / illustration /               │
│      B&W photo + overlay / glowing orb)             │
│                                                     │
│  ─────────────────────────────────────────────────  │  ← 3px accent rule
│                                                     │
│  REPORT TITLE                                       │  ← 60–80pt bold
│  In accent color on key word / second line          │
│                                                     │
│  Subtitle or short descriptor                       │  ← 14–16pt, gray
│  Date · Publisher                                   │  ← 11pt, gray
└─────────────────────────────────────────────────────┘
```

### 7.2 Cover Color Treatments

- **Dark cover:** Black or very dark brand color as full-bleed background. All text white. Accent color on title key word only. (Autodesk, BCG, CrowdStrike)
- **Split cover:** Left dark panel (40%) with title text; right panel occupied by visual asset. (BCG split-panel style)
- **Full-bleed image cover:** Photographic or illustrated image edge-to-edge, with a gradient overlay (dark at bottom) allowing white title text to read. Color graded in brand palette. (Splunk, McKinsey)

---

## 8. Section Templates for Report Generator

### 8.1 Executive Summary
- **Layout:** Single column, white background
- **Opening stat cards:** 3–4 key numbers in a horizontal row at top
- **Body text:** 2–3 paragraphs at standard body size
- **Right-side pull quote card:** Most important sentence from the summary, styled as a pull-quote card (dark background, accent border-left)
- **Section locator chip:** "EXECUTIVE SUMMARY" in accent-filled pill, top-left

### 8.2 Key Metrics / Data Section
- **Layout:** Full-width content page
- **Stat card grid:** 2×2 or 4-column row for headline metrics
- **Primary chart:** Full-width, with chart title (finding-oriented), source below
- **Secondary chart:** Placed beside body text in a 60/40 split
- **Rule:** Begin with an accent rule across full width

### 8.3 Narrative / Analysis Section
- **Layout:** Two-column body text (60/40) — text left, pull quote right
- **Sub-header:** Bold, 18–20pt, preceded by the accent rule
- **Pull quote card:** Floated to the right column, 3–4 sentences from body text
- **Body text:** 2–4 paragraphs, 10–11pt, 1.45 line-height
- **Supporting chart:** If data is referenced, embed the relevant chart inline below the paragraph

### 8.4 Recommendations Section
- **Layout:** Full-width with numbered list treatment
- **Recommendation label:** Large recommendation number (64px) in accent color at 15% opacity as background watermark; readable small number (24px) in accent color overlaid
- **Heading:** Bold, 22–24pt, accent color
- **Body:** 2–3 sentences, body text
- **Visual separator:** 1px rule between each recommendation

### 8.5 Conclusion / Summary
- **Layout:** Dark background page (chapter-divider style)
- **Opening stat or key takeaway:** Single large stat (if applicable) at 80pt in accent color, white background panel
- **Body text:** White on dark, 14–16pt (slightly larger than body for readability on dark)
- **Closing visual:** The signature visual motif at reduced opacity as background

---

## 9. Chart-to-Content Mapping (Implementation Guide)

When generating a report section, use this logic to decide whether and what chart to generate:

```
IF section contains:
  → percentage stats about categories        → horizontal bar chart
  → year-over-year change                   → slope chart panel
  → single headline stat (%, $, ×)          → stat card + donut if part-of-whole
  → ranked list (top 5, top 10)             → lollipop bar chart
  → multiple stats of equal weight          → 3-column stat card grid
  → geographic distribution                 → ranked bar (choropleth optional)
  → framework / model / stages              → box diagram
  → quote / testimonial                     → pull-quote card (no chart)
  → text-only analysis                      → decorative section divider + body text only
```

Chart dimensions:
- **Full-width chart:** max-width 100%, height ~320–400px
- **Half-width chart (inline):** max-width 48%, height ~240–280px
- **Stat card:** 160–200px wide, auto height

---

## 10. HTML Implementation Patterns

### 10.1 The Stat Card (HTML)
```html
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-number">76%</div>
    <div class="stat-label">of companies are adopting AI agents</div>
  </div>
  <!-- repeat -->
</div>
```
```css
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.stat-card { padding: 24px 20px; background: var(--surface); border: 1px solid var(--border); border-top: 3px solid var(--accent); border-radius: 8px; }
.stat-number { font-size: 56px; font-weight: 800; color: var(--accent); line-height: 1; margin-bottom: 8px; }
.stat-label { font-size: 13px; color: var(--text2); line-height: 1.5; }
```

### 10.2 The Section Locator Chip (HTML)
```html
<div class="section-chip">INSIGHT 3</div>
```
```css
.section-chip {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  font-size: 10px; font-weight: 800;
  letter-spacing: 0.12em; text-transform: uppercase;
  padding: 4px 12px; border-radius: 20px;
  margin-bottom: 12px;
}
```

### 10.3 The Accent Rule Section Opener (HTML)
```html
<div class="section-opener">
  <div class="accent-rule"></div>
  <h2 class="section-heading">Market Expansion Strategy</h2>
</div>
```
```css
.accent-rule { height: 3px; background: var(--accent); width: 100%; margin-bottom: 16px; }
.section-heading { font-size: 32px; font-weight: 800; letter-spacing: -0.5px; }
```

### 10.4 Dark Chapter Divider (HTML)
```html
<div class="chapter-divider">
  <div class="chapter-bg-number">03</div>
  <div class="chapter-content">
    <div class="section-chip">CHAPTER 3</div>
    <h2>Strategic Outlook</h2>
    <p>Key themes and recommendations for the year ahead.</p>
  </div>
</div>
```
```css
.chapter-divider {
  background: #0a0a0f;
  min-height: 320px;
  position: relative;
  display: flex; align-items: center;
  padding: 48px 64px;
  overflow: hidden;
  border-radius: 12px;
  margin: 40px 0;
}
.chapter-bg-number {
  position: absolute; right: 48px;
  font-size: 240px; font-weight: 900;
  color: rgba(255,255,255,0.04);
  line-height: 1; user-select: none;
}
.chapter-divider h2 { font-size: 48px; font-weight: 800; color: #fff; margin: 12px 0; }
.chapter-divider p { font-size: 16px; color: rgba(255,255,255,0.5); }
```

### 10.5 Split Panel Section (HTML)
```html
<div class="split-panel">
  <div class="split-left">
    <!-- Image, color block, or pull quote -->
  </div>
  <div class="split-right">
    <!-- Chart or body content -->
  </div>
</div>
```
```css
.split-panel { display: grid; grid-template-columns: 38% 62%; gap: 0; min-height: 280px; border-radius: 12px; overflow: hidden; }
.split-left { background: var(--accent); padding: 40px 32px; display: flex; flex-direction: column; justify-content: flex-end; }
.split-right { background: var(--surface); padding: 40px 40px; }
```

### 10.6 Slope Chart (SVG-based, JavaScript)
Generate in-browser using SVG + inline data. Each slope is:
- Two x-positions (2024, 2025) as fixed pixel columns
- Y-position proportional to value within the panel height
- `<circle r="5" fill="none" stroke="var(--accent)" stroke-width="2">` for start point
- `<circle r="5" fill="var(--accent)">` for end point
- `<line>` or `<path>` connecting them, stroke = accent, stroke-width = 2
- Delta annotation: `<rect>` filled accent + `<text>` white, positioned at midpoint

### 10.7 Horizontal Ranked Bar Chart (SVG)
```
For each item (sorted descending by value):
  - Label: left-aligned text, 13px, body color
  - Bar: rect, height=24px, width proportional to max value, fill=accent
  - Value label: text at end of bar, bold, 13px, same color as fill or body
  - Grid lines: horizontal lines at 25%, 50%, 75%, 100% of max — 1px, light gray
```

---

## 11. Anti-Patterns (Never Do These)

These were absent from every high-quality sample, for good reason:

| Anti-pattern | Why it fails |
|--------------|-------------|
| Gradient fills on bar charts | Adds noise; makes value estimation harder |
| 3D pie / donut charts | Distorts proportion; unreadable angles |
| More than 3 accent colors in body layout | Destroys hierarchy; everything competes |
| Small multiples with different scales | Forces false comparisons |
| Tables with alternating striped rows in strong colors | Distracts from the data |
| Icons on every stat card | Over-decorates; icons rarely add meaning |
| Full-bleed photography behind body text (no overlay) | Destroys text legibility |
| Centered body text (more than 2 lines) | Harder to read; academic-amateur signal |
| Dark background throughout the entire report (not just accents) | Fatiguing; reserved for covers and dividers only |
| Typography at more than 3 size levels per page | Creates visual noise; no clear hierarchy |

---

## 12. Imagery Generation Guidelines

When the report generator creates or suggests imagery:

### 12.1 Cover / Chapter Opener Images
- **Abstract 3D renders** (Autodesk style): organic wave forms, sphere clusters, low-poly meshes, cylinder terrains. Generate with: single dominant hue matching brand accent, soft directional lighting, shallow depth of field, no recognizable objects.
- **Data glow orbs** (BCG style): single glowing sphere, radiating particle lines in brand color, dark background. Communicate energy and connectivity.
- **Abstract fiber / ribbon streams** (McKinsey style): fine fiber strands or light traces, flowing directionally, in blues / purples / accents. Suggest intelligence, flow, transformation.
- **Illustrative diagrams** (CrowdStrike style): flat vector illustrations, geometric forms, brand palette.

### 12.2 Photography Treatment Rules
- Desaturate human subject photos to B&W
- Apply brand color grade to background / environment only
- Never use full-color photography in the body; reserve for covers only
- Crop tightly — head-and-shoulders for portraits, dramatic close-up for environments
- Never use stock photo clichés (handshakes, lightbulbs, puzzle pieces)

### 12.3 Decorative Shape Generation
For each section, generate an SVG background shape:
```
TYPE A: Large low-opacity circle
  - diameter: 400–600px
  - fill: accent color
  - opacity: 0.06–0.09
  - position: top-right or bottom-left of section container

TYPE B: Diagonal ruled lines
  - 3–5 parallel lines, 1px, accent color, 15° angle
  - opacity: 0.12
  - positioned at corner of section

TYPE C: Dot grid
  - 8×8 or 10×10 array of 3px circles
  - fill: accent color
  - opacity: 0.15
  - positioned at one corner of the page
```

---

## 13. Brand Color → Report Theme Mapping

When Brand Discovery extracts a company's colors, apply them as follows:

| Brand asset | Maps to report role |
|-------------|---------------------|
| Primary brand color | `--accent` (section chips, stat numbers, chart fills, accent rule) |
| Secondary brand color | Chart secondary fill, decorative background opacity shapes |
| Background dark (if brand uses dark) | Chapter divider background, cover background |
| Background light (brand site body BG) | Report body page background |
| Body text color | `--text` |

If the brand accent color is very light (< 50% lightness), darken it 20–30% for use on white backgrounds. If it is very dark, lighten it 20–30% for use on dark backgrounds.

Always test: the accent color must pass WCAG AA contrast ratio against both white (#fff) and the report's dark background.

---

*This design system document is a living reference. Add new patterns from additional sample reports as they are analyzed.*
