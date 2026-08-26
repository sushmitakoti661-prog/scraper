import requests
import time
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Politeness settings
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR-USERNAME/scraper)"
TIMEOUT = 10  # seconds
CACHE_DIR = Path("cache")


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


def discover_all_book_links():
    """
    Starts at catalogue page 1, follows "next" links, and collects
    every unique book URL — but only across the first 3 catalogue pages.
    """
    MAX_PAGES = 3
    all_links = []
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    page_number = 1

    while current_url and page_number <= MAX_PAGES:
        cache_filename = f"catalogue-page-{page_number}.html"
        html = fetch_page(current_url, cache_filename)

        links = get_book_links(html, current_url)
        all_links.extend(links)

        current_url = get_next_page_url(html, current_url)
        page_number += 1

    unique_links = list(dict.fromkeys(all_links))  # removes duplicates, keeps order

    print(f"catalogue_pages={min(page_number - 1, MAX_PAGES)}")
    print(f"discovered={len(all_links)}")
    print(f"unique_urls={len(unique_links)}")

    return unique_links


if __name__ == "__main__":
    book_links = discover_all_book_links()