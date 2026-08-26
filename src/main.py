import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone

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

def fetch_page(url, cache_filename):
    """
    Fetches a page, using a cached copy if available.
    Otherwise downloads it politely and saves it to cache.
    """
    cache_path = CACHE_DIR / cache_filename

    if cache_path.exists():
        print(f"CACHE HIT: {cache_filename}")
        html = cache_path.read_text(encoding="utf-8")
        return html

    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url} - status code: {response.status_code}")
    response.encoding = "utf-8"  # <-- ADD THIS LINE: fixes £ symbol and other special characters
    html = response.text
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    time.sleep(0.5)  # be polite - wait half a second after a real request

    return html


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
    """
    Starts at catalogue page 1, follows "next" links, and collects
    every unique book URL — but only across the first 3 catalogue pages.
    Returns a list of (book_url, source_page) tuples.
    """
    MAX_PAGES = 3
    all_links = []  # will hold (book_url, source_page) tuples
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    page_number = 1

    while current_url and page_number <= MAX_PAGES:
        cache_filename = f"catalogue-page-{page_number}.html"
        html = fetch_page(current_url, cache_filename)

        links = get_book_links(html, current_url)
        for link in links:
            all_links.append((link, current_url))  # pair each book with its source page

        current_url = get_next_page_url(html, current_url)
        page_number += 1

    # Remove duplicates based on the book URL only, keep first occurrence
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
    """
    book_links = discover_all_book_links()  # now a list of (book_url, source_page) tuples
    all_records = []

    for i, (product_url, source_page) in enumerate(book_links, start=1):
        cache_filename = f"book-{i}.html"
        html = fetch_page(product_url, cache_filename)

        record = extract_book_details(html, product_url, source_page=source_page)
        all_records.append(record)

    print(f"detail_pages={len(all_records)}")
    return all_records

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

if __name__ == "__main__":
    raw_records = scrape_all_books()
    valid_records, error_records = clean_and_validate(raw_records)
    save_output(valid_records, error_records)