# The Polite Scraper

A scraping pipeline that collects book data from a practice sandbox site, cleans it, validates it, and stores it as JSON.
Built as part of the FlyRank AI Backend Internship — Week 5, Assignment A9.

## Target Classification

- **Site**: [books.toscrape.com](https://books.toscrape.com)
- **Why this site**: It is explicitly built as a sandbox for scraping practice. The homepage tagline reads "We love being scraped!" and includes a banner stating: "This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning."
- **Scope**: Only the first 3 catalogue pages (60 books total) are collected — not the full 1000-book catalogue.
- **Data collected**: Title, price, availability, star rating, and description for each book.
- **robots.txt result**: Requested `https://books.toscrape.com/robots.txt` — returned a 404 Not Found. No robots file exists for this site. This is not the same as explicit permission, but combined with the site's own stated purpose as a public scraping sandbox, scraping here is appropriate.

I will not reuse this code on another site without checking its rules and terms first.

## Tech Stack

- Python 3.10+
- `requests` — HTTP fetching
- `beautifulsoup4` — HTML parsing
- `pydantic` — schema validation

## How to Run

1. Clone this repo:

git clone https://github.com/YOUR-USERNAME/scraper.git
cd scraper

2. Create and activate a virtual environment:

python -m venv venv
venv\Scripts\Activate.ps1

3. Install dependencies:

pip install -r requirements.txt

4. Run the scraper:

python src/main.py

5. Output appears in `output/books.json`, `output/errors.json`, and `output/run-report.json`

## Record Schema

Each validated record in `books.json` has this shape:

```json
{
  "title": "string",
  "product_url": "string (URL)",
  "price_text": "string, e.g. £51.77",
  "price_gbp": "number, e.g. 51.77",
  "availability_text": "string",
  "rating_text": "string, e.g. Three",
  "description": "string or null",
  "source_page": "string (URL)",
  "fetched_at": "string (ISO 8601 timestamp)"
}
```

## Politeness Rules

- Every real request sends an identifying `User-Agent` header: `FlyRankInternshipA9/1.0 (+link-to-repo)`
- Every request has a 10-second timeout
- At least 500ms delay between real (non-cached) requests
- Server errors (5xx) are retried once; 404s and 403s are never retried
- All pages are cached locally in `cache/` during development, so repeated runs don't re-hit the site

## Sample Run Report

```json
{
  "start_time": "2026-08-26T11:10:14.360391+00:00",
  "duration_seconds": 1.22,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failed_page_details": []
}
```

## Why No Browser Was Needed

This site serves all its data directly in the HTML response — the book details, prices, and descriptions are all present in the raw page source. A browser (like Playwright or Selenium) would only add unnecessary cost (slower, more memory) since there's no JavaScript rendering needed to see the data.

## Limitations

- Data is scraped once per run and not automatically checked against previous runs for changes (no "diffing").
- Only the first 3 catalogue pages (60 books) are collected, not the full 1000-book catalogue, as scoped by the assignment.

## Ethics Note

This scraper only targets a site explicitly built for scraping practice. In general, I will always check for an official API before scraping, respect `robots.txt` and site terms, never bypass logins or paywalls, and only collect the data actually needed for the task.