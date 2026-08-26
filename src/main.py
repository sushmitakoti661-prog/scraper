import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

# Global counters for the run report
stats = {"fetched": 0, "cache_hits": 0}

from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR-USERNAME/scraper)"
TIMEOUT = 10  # seconds
CACHE_DIR = Path("cache")

import re

def clean_price(price_text):
    """
    Turns "£51.77" into 51.77 (a float).
    """
    # Remove everything except digits and the decimal point
    cleaned = re.sub(r"[^\d.]", "", price_text)
    return float(cleaned)

def fetch_page(url, cache_filename, retry=True):
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        print(f"CACHE HIT: {cache_filename}")
        stats["cache_hits"] += 1
        html = cache_path.read_text(encoding="utf-8")
        return html, None

    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        if retry:
            print(f"  error: {e} - retrying once...")
            time.sleep(1)
            return fetch_page(url, cache_filename, retry=False)
        return None, f"Request failed: {e}"

    if response.status_code == 200:
        response.encoding = "utf-8"
        html = response.text
        CACHE_DIR.mkdir(exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")
        stats["fetched"] += 1
        time.sleep(0.5)
        return html, None

    if response.status_code >= 500 and retry:
        print(f"  status {response.status_code} - retrying once...")
        time.sleep(1)
        return fetch_page(url, cache_filename, retry=False)

    return None, f"status code {response.status_code}"


def get_book_links(html, page_url):
    """
    Given a catalogue page's HTML, return a list of absolute URLs
    to every book on that page.
    """
    soup = BeautifulSoup(html, "html.parser")
    book_links = []

    # Each book is inside an <article class="product_pod">, with a link inside <h3><a>
    for article in soup.select("article.product_pod"):
        link_tag = article.select_one("h3 a")
        relative_url = link_tag["href"]
        absolute_url = urljoin(page_url, relative_url)
        book_links.append(absolute_url)

    return book_links


def get_next_page_url(html, page_url):
    """
    Given a catalogue page's HTML, return the absolute URL of the
    "next" page, or None if there isn't one.
    """
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("li.next a")

    if next_link is None:
        return None

    return urljoin(page_url, next_link["href"])

def extract_book_details(html, product_url, source_page):
    """
    Given a single book page's HTML, extract the raw fields we care about.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = soup.select_one("div.product_main h1").get_text(strip=True)

    # Price (raw text, e.g. "£51.77")
    price_text = soup.select_one("p.price_color").get_text(strip=True)

    # Availability (raw text, e.g. "In stock (22 available)")
    availability_text = soup.select_one("p.availability").get_text(strip=True)

    # Rating - stored as a CSS class like "star-rating Three"
    rating_tag = soup.select_one("p.star-rating")
    rating_classes = rating_tag.get("class", [])
    # rating_classes looks like ["star-rating", "Three"] - we want the second word
    rating_text = rating_classes[1] if len(rating_classes) > 1 else None

    # Description - not every book has one, so we check first
    description_tag = soup.select_one("#product_description ~ p")
    description = description_tag.get_text(strip=True) if description_tag else None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

import json

def clean_and_validate(raw_records):
    """
    Cleans each raw record (adds price_gbp), then validates it against
    the BookRecord schema. Good records and bad records are separated.
    """
    valid_records = []
    error_records = []

    for raw in raw_records:
        try:
            # Add the cleaned price field
            raw["price_gbp"] = clean_price(raw["price_text"])

            # Validate against our schema
            validated = BookRecord(**raw)

            # Convert back to a plain dict for JSON storage
            valid_records.append(json.loads(validated.model_dump_json()))

        except (ValidationError, ValueError) as e:
            error_records.append({
                "record": raw,
                "reason": str(e)
            })

    return valid_records, error_records

def discover_all_book_links():
    MAX_PAGES = 3
    all_links = []
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    page_number = 1

    while current_url and page_number <= MAX_PAGES:
        cache_filename = f"catalogue-page-{page_number}.html"
        html, error = fetch_page(current_url, cache_filename)

        if error:
            raise Exception(f"Could not fetch catalogue page {page_number}: {error}")

        links = get_book_links(html, current_url)
        for link in links:
            all_links.append((link, current_url))

        current_url = get_next_page_url(html, current_url)
        page_number += 1

    seen = set()
    unique_links = []
    for book_url, source_page in all_links:
        if book_url not in seen:
            seen.add(book_url)
            unique_links.append((book_url, source_page))

        
    print(f"catalogue_pages={min(page_number - 1, MAX_PAGES)}")
    print(f"discovered={len(all_links)}")
    print(f"unique_urls={len(unique_links)}")

    return unique_links


def scrape_all_books():
    """
    Discovers all book links, then visits each one to extract details.
    Returns (records, failed_pages) - failed_pages logs any pages that
    could not be fetched.
    """
    book_links = discover_all_book_links()
    all_records = []
    failed_pages = []

    for i, (product_url, source_page) in enumerate(book_links, start=1):
        cache_filename = f"book-{i}.html"
        html, error = fetch_page(product_url, cache_filename)

        if error:
            print(f"  SKIPPED: {product_url} - {error}")
            failed_pages.append({"url": product_url, "reason": error})
            continue

        record = extract_book_details(html, product_url, source_page=source_page)
        all_records.append(record)

    print(f"detail_pages={len(all_records)}")
    print(f"failed_pages={len(failed_pages)}")
    return all_records, failed_pages

def save_output(valid_records, error_records):
    """
    Writes valid records to output/books.json and any bad ones to
    output/errors.json.
    """
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "books.json", "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(output_dir / "errors.json", "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2, ensure_ascii=False)

    print(f"valid_records={len(valid_records)}")
    print(f"error_records={len(error_records)}")

def save_run_report(start_time, pages_fetched, cache_hits, valid_count, error_count, failed_pages):
    """
    Writes an honest summary of what happened during this run.
    """
    duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

    report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": round(duration_seconds, 2),
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits,
        "valid_records": valid_count,
        "invalid_records": error_count,
        "failed_pages": len(failed_pages),
        "failed_page_details": failed_pages
    }

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "run-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"run report saved - duration: {report['duration_seconds']}s, failed_pages: {report['failed_pages']}")

if __name__ == "__main__":
    start_time = datetime.now(timezone.utc)

    raw_records, failed_pages = scrape_all_books()
    valid_records, error_records = clean_and_validate(raw_records)
    save_output(valid_records, error_records)

    save_run_report(
        start_time=start_time,
        pages_fetched=stats["fetched"],
        cache_hits=stats["cache_hits"],
        valid_count=len(valid_records),
        error_count=len(error_records),
        failed_pages=failed_pages
    )