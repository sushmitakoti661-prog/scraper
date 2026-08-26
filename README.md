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