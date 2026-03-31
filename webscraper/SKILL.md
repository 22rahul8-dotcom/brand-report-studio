---
name: webscraper
description: >
  Scrape websites and extract data using the Firecrawl API. Use this skill whenever the user wants to
  scrape a webpage, extract content from a URL, convert a website to markdown or HTML, pull structured
  data from a site, batch scrape multiple URLs, or interact with a page before scraping (clicking buttons,
  filling forms, taking screenshots). Also trigger when the user mentions Firecrawl, web scraping,
  web extraction, or wants to get clean text/data from any URL — even if they just paste a URL and say
  "get me the content" or "what's on this page". If the user wants to crawl, harvest, or mine data from
  websites, this is the right skill.
---

# Webscraper — Firecrawl-powered web scraping

This skill uses the [Firecrawl](https://firecrawl.dev) Python SDK (`firecrawl-py`) to scrape websites
and extract clean, structured data. Firecrawl handles the hard parts — proxies, JavaScript rendering,
rate limits, dynamic content, PDFs — so you can focus on what to extract.

## Setup

The Firecrawl API key must be available as the environment variable `FIRECRAWL_API_KEY`.

Install the SDK if not already present:

```bash
pip install firecrawl-py
```

## Core operations

### 1. Scrape a single URL

The most common operation. Returns clean markdown, HTML, or both.

```python
import os
from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])

# Get markdown (most common)
result = firecrawl.scrape("https://example.com", formats=["markdown"])
print(result["markdown"])

# Get multiple formats
result = firecrawl.scrape("https://example.com", formats=["markdown", "html", "links"])
```

**Available formats:** `markdown`, `html`, `rawHtml`, `links`, `screenshot`, `summary`, `json`, `images`, `branding`

### 2. Extract structured JSON data

Pull specific fields from a page using a JSON schema or a natural language prompt.

**With a schema** (precise control over output structure):

```python
from pydantic import BaseModel

class ProductInfo(BaseModel):
    name: str
    price: float
    in_stock: bool
    description: str

result = firecrawl.scrape(
    "https://example.com/product",
    formats=[{"type": "json", "schema": ProductInfo.model_json_schema()}]
)
print(result["json"])
```

**With just a prompt** (let the LLM decide the structure):

```python
result = firecrawl.scrape(
    "https://example.com",
    formats=[{"type": "json", "prompt": "Extract all product names and prices"}]
)
print(result["json"])
```

You can combine a schema with a prompt for guided extraction — the schema defines the shape, and the prompt gives additional instructions.

### 3. Batch scrape multiple URLs

For scraping many pages at once. Firecrawl handles them in parallel on the server side.

```python
result = firecrawl.batch_scrape(
    [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
    ],
    formats=["markdown"],
    poll_interval=2,
    wait_timeout=120,
)

for page in result["data"]:
    print(page["metadata"]["sourceURL"])
    print(page["markdown"][:200])
    print("---")
```

### 4. Page interactions (actions)

Interact with a page before scraping — click buttons, fill forms, wait for content to load, take screenshots. This is essential for pages behind logins, pagination, or dynamic content.

```python
result = firecrawl.scrape(
    url="https://example.com/login",
    formats=["markdown"],
    actions=[
        {"type": "wait", "milliseconds": 1000},
        {"type": "click", "selector": "#accept-cookies"},
        {"type": "wait", "milliseconds": 500},
        {"type": "write", "selector": "#email", "text": "user@example.com"},
        {"type": "press", "key": "Tab"},
        {"type": "write", "text": "password123"},
        {"type": "click", "selector": "button[type='submit']"},
        {"type": "wait", "milliseconds": 2000},
        {"type": "screenshot", "full_page": True},
    ],
)
print(result["markdown"])
```

**Action types:**
- `wait` — pause for content to load (`milliseconds` param). Use before/after other actions.
- `click` — click an element (`selector` param, CSS selector)
- `write` — type text (`text` param, optional `selector` to focus first)
- `press` — press a key (`key` param, e.g. "Tab", "Enter")
- `screenshot` — capture the page (`full_page` optional boolean)
- `scrape` — capture HTML at that point in the action sequence

Always include `wait` actions to give the page time to respond — pages don't update instantly after clicks or form submissions.

## Important options

**Location/language** — get region-specific content:
```python
result = firecrawl.scrape("https://example.com",
    formats=["markdown"],
    location={"country": "US", "languages": ["en"]}
)
```

**Cache control** — force a fresh scrape (bypass cache):
```python
result = firecrawl.scrape("https://example.com", formats=["markdown"], max_age=0)
```

**Main content only** — skip headers/footers/nav:
```python
result = firecrawl.scrape("https://example.com",
    formats=["markdown"],
    only_main_content=True  # default is True
)
```

## Choosing the right approach

| Goal | Method |
|------|--------|
| Get page content as text | `formats=["markdown"]` |
| Get raw page structure | `formats=["html"]` or `formats=["rawHtml"]` |
| Extract specific fields | `formats=[{"type": "json", "schema": ...}]` |
| Explore what's on a page | `formats=[{"type": "json", "prompt": "..."}]` |
| Scrape many pages | `batch_scrape([urls], ...)` |
| Page requires interaction | Use `actions=[...]` |
| Get a visual snapshot | `formats=["screenshot"]` |
| Extract brand/design info | `formats=["branding"]` |

## Tips

- Each scrape costs 1 Firecrawl credit. JSON extraction adds 4 credits per page.
- Screenshot URLs expire after 24 hours — download or process them promptly.
- For advanced features (enhanced mode, zero data retention, change tracking), see `references/advanced.md`.

## Writing the script

When building a scraper for the user, write a self-contained Python script that:
1. Imports `os` and `firecrawl`
2. Reads `FIRECRAWL_API_KEY` from the environment
3. Performs the scraping operation
4. Saves results to a file (JSON, markdown, CSV — whatever suits the use case)
5. Prints a summary of what was scraped

Handle errors gracefully — check that the API key is set, wrap the scrape call in try/except, and give clear error messages.
