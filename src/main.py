import requests
import os
from pathlib import Path

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/sushmitakoti661-prog/scraper.git)"
TIMEOUT = 10  # seconds
CACHE_DIR = Path("cache")

def fetch_page(url, cache_filename):
    """
    Fetches a page, using a cached copy if available.
    Otherwise downloads it politely and saves it to cache.
    """
    cache_path = CACHE_DIR / cache_filename

    # If we already have this page cached, just read it
    if cache_path.exists():
        print(f"CACHE HIT: {cache_filename}")
        html = cache_path.read_text(encoding="utf-8")
        print(f"  size: {len(html)} bytes")
        return html

    # Otherwise, fetch it from the real site
    print(f"FETCH: {url}")
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url} - status code: {response.status_code}")

    html = response.text

    # Make sure the cache folder exists, then save the page
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    print(f"  size: {len(html)} bytes")
    return html


if __name__ == "__main__":
    url = "https://books.toscrape.com/catalogue/page-1.html"
    html = fetch_page(url, "catalogue-page-1.html")