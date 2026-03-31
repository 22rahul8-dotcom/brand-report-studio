# Advanced Firecrawl Features

## Enhanced Mode

For complex websites that are hard to scrape (heavy JavaScript, bot detection), Firecrawl offers enhanced mode with better success rates. This uses enhanced proxies at additional credit cost (4 extra credits per page).

## Zero Data Retention (ZDR)

For teams with strict data handling requirements. Firecrawl won't persist any page content beyond the request lifetime.

```python
result = firecrawl.scrape("https://example.com",
    formats=["markdown"],
    zero_data_retention=True
)
```

- Available on Enterprise plans only
- Adds 1 credit per page
- Screenshots are NOT available in ZDR mode

## Caching

Firecrawl caches results for 2 days by default (`maxAge = 172800000` ms).

- **Force fresh**: `max_age=0` — bypasses cache, slower but always current
- **Custom window**: `max_age=600000` — 10-minute cache window
- **Don't store**: `store_in_cache=False` — don't cache this request's results
- **Cache-only lookup**: Use `min_age` to check cache without triggering a fresh scrape

## Branding Extraction

Extract comprehensive brand identity from a page — colors, fonts, typography, spacing, UI components.

```python
result = firecrawl.scrape("https://example.com", formats=["branding"])
brand = result["branding"]
# brand["colors"]["primary"], brand["fonts"], brand["typography"], etc.
```

Returns: `colorScheme`, `logo`, `colors` (primary/secondary/accent/background/text), `fonts`, `typography` (families/sizes/weights), `spacing`, `components` (button styles), `images`, `personality`.

## Screenshots

```python
result = firecrawl.scrape("https://example.com", formats=["screenshot"])
print(result["screenshot"])  # URL to screenshot image (expires in 24 hours)
```

Options: `fullPage`, `quality`, `viewport`.

## Location & Language

Get region-specific content by specifying country and language:

```python
result = firecrawl.scrape("https://example.com",
    formats=["markdown"],
    location={
        "country": "JP",        # ISO 3166-1 alpha-2
        "languages": ["ja", "en"]  # Priority order
    }
)
```

Firecrawl uses appropriate proxies and emulates the corresponding timezone/language settings.

## Credit Costs

| Operation | Credits |
|-----------|---------|
| Basic scrape | 1 per page |
| JSON extraction | +4 per page |
| Enhanced proxy | +4 per page |
| PDF parsing | 1 per PDF page |
| ZDR | +1 per page |
