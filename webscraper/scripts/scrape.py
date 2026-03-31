#!/usr/bin/env python3
"""
Firecrawl scraping utility — reusable helper for common scraping operations.

Usage:
    python scrape.py <url> [--format markdown,html] [--json-prompt "..."] [--json-schema schema.json]
                           [--output results.json] [--actions actions.json] [--batch urls.txt]

Environment:
    FIRECRAWL_API_KEY — required Firecrawl API key
"""

import argparse
import json
import os
import sys

def get_client():
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: FIRECRAWL_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get your API key from https://firecrawl.dev and set it:", file=sys.stderr)
        print("  export FIRECRAWL_API_KEY='fc-YOUR-API-KEY'", file=sys.stderr)
        sys.exit(1)
    try:
        from firecrawl import Firecrawl
    except ImportError:
        print("Error: firecrawl-py is not installed. Run: pip install firecrawl-py", file=sys.stderr)
        sys.exit(1)
    return Firecrawl(api_key=api_key)


def scrape_url(url, formats=None, actions=None, location=None, max_age=None):
    """Scrape a single URL and return the result dict."""
    client = get_client()
    kwargs = {}
    if formats:
        kwargs["formats"] = formats
    else:
        kwargs["formats"] = ["markdown"]
    if actions:
        kwargs["actions"] = actions
    if location:
        kwargs["location"] = location
    if max_age is not None:
        kwargs["max_age"] = max_age
    return client.scrape(url, **kwargs)


def batch_scrape_urls(urls, formats=None, poll_interval=2, wait_timeout=120):
    """Batch scrape multiple URLs and return the result."""
    client = get_client()
    return client.batch_scrape(
        urls,
        formats=formats or ["markdown"],
        poll_interval=poll_interval,
        wait_timeout=wait_timeout,
    )


def extract_json(url, schema=None, prompt=None):
    """Extract structured JSON data from a URL."""
    client = get_client()
    json_format = {"type": "json"}
    if schema:
        json_format["schema"] = schema
    if prompt:
        json_format["prompt"] = prompt
    return client.scrape(url, formats=[json_format])


def save_result(result, output_path):
    """Save scrape result to a file."""
    with open(output_path, "w", encoding="utf-8") as f:
        if output_path.endswith(".md"):
            f.write(result.get("markdown", json.dumps(result, indent=2, default=str)))
        else:
            json.dump(result, f, indent=2, default=str)
    print(f"Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Scrape websites with Firecrawl")
    parser.add_argument("url", nargs="?", help="URL to scrape")
    parser.add_argument("--format", default="markdown", help="Comma-separated formats: markdown,html,links,screenshot,summary,images,branding")
    parser.add_argument("--json-prompt", help="Extract JSON using a natural language prompt")
    parser.add_argument("--json-schema", help="Path to JSON schema file for structured extraction")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--actions", help="Path to JSON file with page actions")
    parser.add_argument("--batch", help="Path to file with URLs (one per line) for batch scraping")
    parser.add_argument("--max-age", type=int, help="Cache max age in ms (0 = fresh scrape)")
    parser.add_argument("--country", help="Location country code (e.g., US, DE, JP)")
    parser.add_argument("--languages", help="Comma-separated language codes (e.g., en,es)")
    args = parser.parse_args()

    # Batch scrape mode
    if args.batch:
        with open(args.batch) as f:
            urls = [line.strip() for line in f if line.strip()]
        formats = args.format.split(",")
        print(f"Batch scraping {len(urls)} URLs...")
        result = batch_scrape_urls(urls, formats=formats)
        if args.output:
            save_result(result, args.output)
        else:
            print(json.dumps(result, indent=2, default=str))
        return

    if not args.url:
        parser.error("URL is required (or use --batch)")

    # JSON extraction mode
    if args.json_prompt or args.json_schema:
        schema = None
        if args.json_schema:
            with open(args.json_schema) as f:
                schema = json.load(f)
        result = extract_json(args.url, schema=schema, prompt=args.json_prompt)
        if args.output:
            save_result(result, args.output)
        else:
            print(json.dumps(result, indent=2, default=str))
        return

    # Standard scrape mode
    formats = args.format.split(",")
    actions = None
    if args.actions:
        with open(args.actions) as f:
            actions = json.load(f)

    location = None
    if args.country:
        location = {"country": args.country}
        if args.languages:
            location["languages"] = args.languages.split(",")

    result = scrape_url(
        args.url,
        formats=formats,
        actions=actions,
        location=location,
        max_age=args.max_age,
    )

    if args.output:
        save_result(result, args.output)
    else:
        # Print markdown if available, otherwise full JSON
        if "markdown" in result:
            print(result["markdown"])
        else:
            print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
