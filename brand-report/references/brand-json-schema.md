# brand.json Schema Reference

Every scraped company gets a `brands/<slug>/brand.json` file. This is the master brand profile
consumed by the report generator. Below is the full schema with descriptions.

## Top-level fields

```json
{
  "company": "Stripe",           // Display name (title-cased from slug)
  "slug": "stripe",              // Filesystem-safe identifier from domain
  "url": "https://stripe.com",   // Original URL scraped
  "scraped_at": "2026-03-23T10:42:00Z",  // ISO 8601 UTC timestamp
  "colors": { ... },
  "fonts": { ... },
  "assets": { ... },
  "brand_voice": { ... },
  "design_language": { ... }
}
```

## colors

All color values are hex strings. Report-role keys are derived automatically:

```json
{
  // Raw extracted colors
  "primary":        "#635BFF",   // Main brand color (CTA, nav accent)
  "secondary":      "#0A2540",   // Supporting color (footers, headers)
  "accent":         "#00D4FF",   // Highlight / active states
  "background":     "#FFFFFF",   // Page background
  "surface":        "#F6F9FC",   // Card / panel backgrounds
  "text_primary":   "#0A2540",   // Main body text
  "text_secondary": "#425466",   // Captions, metadata

  // Derived report roles (used as CSS custom properties)
  "cover_bg":           "#635BFF",   // Cover page background
  "cover_text":         "#ffffff",   // Text on cover (auto light/dark)
  "section_accent":     "#00D4FF",   // Section numbers, rules, borders
  "pull_quote_bg":      "#f0eeff",   // Pull quote background tint
  "table_header_bg":    "#0A2540",   // Table header row background
  "sidebar_bg":         "#f8f8ff",   // Sidebar panel background
  "divider_color":      "#e0e0e0",   // Horizontal rules, table borders
  "footer_bg":          "#0A2540"    // Running footer background
}
```

## fonts

```json
{
  "heading": {
    "family": "Sohne",
    "fallback": "Inter, sans-serif",   // Used when web font unavailable
    "weights": [400, 600, 700]
  },
  "body": {
    "family": "Sohne",
    "fallback": "Inter, sans-serif",
    "weights": [400]
  }
}
```

The HTML report attempts to load fonts from Google Fonts if the family name is
not a generic stack. If the font can't be found, the fallback stack is used.

## assets

Local paths relative to the brand directory (`brands/<slug>/`):

```json
{
  "logo_svg": "assets/logo.svg",    // SVG preferred
  "logo_png": "assets/logo.png",    // Raster fallback
  "favicon":  "assets/favicon.ico",
  "hero_images": [
    "assets/hero-1.jpg",
    "assets/hero-2.jpg"
  ]
}
```

Empty string `""` means the asset was not found. The generator falls back gracefully.

## brand_voice

```json
{
  "tone": ["technical", "trustworthy", "modern"],  // Personality traits
  "tagline": "Financial infrastructure for the internet.",
  "description": "Full personality description from Firecrawl",
  "description_style": "concise"
}
```

The `tone` array informs Claude's writing style when generating AI content (`--describe` mode).

## design_language

```json
{
  "style": "clean_minimal",     // One of: clean_minimal | bold_editorial | corporate_formal
                                //          startup_playful | luxury_premium | technical_precise
  "corner_radius": "6px",       // Applied to cards, buttons, callout boxes
  "color_scheme": "light",      // "light" or "dark" (from page background)
  "shadow_style": "soft",       // Informs future shadow tokens
  "layout_density": "spacious"  // Affects margins: spacious=72px | standard=48px | dense=36px
}
```

## Style → Layout mapping

| style | CSS behavior |
|-------|-------------|
| `clean_minimal` | Large margins, thin dividers, generous whitespace |
| `bold_editorial` | Strong color blocks, heavy heading weights |
| `corporate_formal` | Ruled lines, classic two-column, navy/grey tones |
| `startup_playful` | Bright accent colors, rounded corners, colorful callouts |
| `luxury_premium` | Full-bleed imagery, elegant spacing, serif headings |
| `technical_precise` | Monospace elements, data-dense, dark affinity |
