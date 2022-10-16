"""Scrape book data from the "Bilim" (science) category on idefix.com.

The module is split in two layers:

* **Parsing** (``parse_listing_page``, ``parse_book_page`` and the small
  ``parse_*`` helpers) works on plain HTML strings, so it can be tested
  offline against saved pages.
* **Browser driving** (``create_driver``, ``scrape``) uses Selenium + Firefox
  to load pages, then hands ``driver.page_source`` to the parsers.

Run ``python scraper.py --help`` for the command-line interface.
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from dataclasses import asdict, dataclass, fields
from typing import Iterable, Iterator, Optional

from lxml import html

CATEGORY_URL = "https://www.idefix.com/kategori/Kitap/Bilim/grupno=00052?Page={page}"

# Rating widget on a book page ("3,5/5 - 19 Kişi"). The site exposes no
# stable class names here, so these are the positional paths that worked
# against the live page when the project was built.
_RATING_SPAN = (
    "/html/body/div[1]/section/div/div[2]/section[2]/div[1]/div/div"
    "/div[3]/div[2]/div[1]/div[2]/span"
)
RATING_XPATH = _RATING_SPAN + "/span[1]"
REVIEWERS_XPATH = _RATING_SPAN + "/span[3]"

FIRST_EDITION_LABEL = "İlk Baskı Yılı:"
PAGE_COUNT_LABEL = "Sayfa Sayısı:"


@dataclass
class ListingItem:
    """A book as it appears on a category listing page."""

    name: Optional[str]
    author: Optional[str]
    price: Optional[float]
    url: Optional[str]


@dataclass
class BookDetails:
    """Fields that are only available on a book's own page."""

    rating: Optional[float]
    reviewers: Optional[int]
    first_edition_year: Optional[int]
    pages: Optional[int]


@dataclass
class Book:
    """One CSV row: listing fields plus book-page fields."""

    name: Optional[str]
    author: Optional[str]
    price: Optional[float]
    rating: Optional[float]
    reviewers: Optional[int]
    first_edition_year: Optional[int]
    pages: Optional[int]
    url: Optional[str]


CSV_FIELDS = [f.name for f in fields(Book)]


# --------------------------------------------------------------------------
# Value parsing
# --------------------------------------------------------------------------

def parse_decimal(text: Optional[str]) -> Optional[float]:
    """Parse a Turkish-formatted number such as ``"1.234,50 TL"`` or ``"3,5"``.

    ``.`` is the thousands separator and ``,`` the decimal separator.
    Returns ``None`` when no number is present.
    """
    if not text:
        return None
    match = re.search(r"\d[\d.]*(?:,\d+)?", text)
    if not match:
        return None
    return float(match.group().replace(".", "").replace(",", "."))


def parse_int(text: Optional[str]) -> Optional[int]:
    """Return the first whole number in ``text`` (``"19 Kişi"`` -> 19), else ``None``."""
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _first_text(node, xpath: str) -> Optional[str]:
    found = node.xpath(xpath)
    if not found:
        return None
    value = found[0] if isinstance(found[0], str) else found[0].text_content()
    value = value.strip()
    return value or None


# --------------------------------------------------------------------------
# Page parsing
# --------------------------------------------------------------------------

def parse_listing_page(page_html: str) -> list[ListingItem]:
    """Extract every book card from a category listing page.

    Each card is parsed on its own, so a card with a missing field yields
    ``None`` for that field instead of shifting values between books.
    The full title and author come from the ``title`` attributes; the visible
    text is truncated by the site (e.g. ``"Serkan Karaisma..."``).
    """
    tree = html.fromstring(page_html)
    cards = tree.xpath(
        '//div[contains(concat(" ", normalize-space(@class), " "), " product-box ")]'
    )
    items = []
    for card in cards:
        title_link = card.xpath('.//div[contains(@class, "box-title")]//a')
        name = url = None
        if title_link:
            link = title_link[0]
            name = (link.get("title") or link.text_content()).strip() or None
            url = link.get("href")

        author = _first_text(card, './/a[@class="who"]/@title') or _first_text(
            card, './/a[@class="who"]'
        )

        price_text = _first_text(card, './/span[@class="price price"]/@data-price') or _first_text(
            card, './/span[@class="price price"]'
        )

        items.append(
            ListingItem(name=name, author=author, price=parse_decimal(price_text), url=url)
        )
    return items


def _labelled_value(tree, label: str) -> Optional[int]:
    """Return the number in the ``a.bold`` that sits in the same ``<li>`` as ``label``."""
    rows = tree.xpath(f'//li[.//span[normalize-space()="{label}"]]')
    for row in rows:
        value = parse_int(_first_text(row, './/a[contains(@class, "bold")]'))
        if value is not None:
            return value
    return None


def parse_book_page(page_html: str) -> BookDetails:
    """Extract rating, reviewer count, first-edition year and page count from a book page.

    Any field that is missing on the page is returned as ``None``.
    """
    tree = html.fromstring(page_html)
    return BookDetails(
        rating=parse_decimal(_first_text(tree, RATING_XPATH)),
        reviewers=parse_int(_first_text(tree, REVIEWERS_XPATH)),
        first_edition_year=_labelled_value(tree, FIRST_EDITION_LABEL),
        pages=_labelled_value(tree, PAGE_COUNT_LABEL),
    )


def merge(item: ListingItem, details: BookDetails) -> Book:
    """Combine a listing entry with the details scraped from its book page."""
    return Book(
        name=item.name,
        author=item.author,
        price=item.price,
        rating=details.rating,
        reviewers=details.reviewers,
        first_edition_year=details.first_edition_year,
        pages=details.pages,
        url=item.url,
    )


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def write_csv(books: Iterable[Book], path: str) -> int:
    """Write ``books`` to ``path`` as UTF-8 CSV. Missing values become empty cells.

    Returns the number of rows written.
    """
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for book in books:
            writer.writerow(asdict(book))
            count += 1
    return count


# --------------------------------------------------------------------------
# Browser driving
# --------------------------------------------------------------------------

def create_driver(driver_path: Optional[str] = None, headless: bool = False):
    """Start a Firefox WebDriver.

    With Selenium >= 4.6, geckodriver is located or downloaded automatically
    when ``driver_path`` is not given.
    """
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    options = Options()
    if headless:
        options.add_argument("-headless")
    service = Service(executable_path=driver_path) if driver_path else Service()
    return webdriver.Firefox(service=service, options=options)


def scrape(driver, max_pages: int = 1, delay: float = 3.0) -> Iterator[Book]:
    """Yield a :class:`Book` for every book on the first ``max_pages`` listing pages.

    ``delay`` seconds are waited after each page load so the page can finish
    rendering (and to keep the request rate polite).
    """
    for page in range(1, max_pages + 1):
        driver.get(CATEGORY_URL.format(page=page))
        time.sleep(delay)
        listing = parse_listing_page(driver.page_source)
        for item in listing:
            if not item.url:
                continue
            driver.get(item.url)
            time.sleep(delay)
            yield merge(item, parse_book_page(driver.page_source))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Scrape books from the idefix.com 'Bilim' category into a CSV file."
    )
    parser.add_argument("-p", "--pages", type=int, default=1,
                        help="number of listing pages to scrape (default: 1)")
    parser.add_argument("-o", "--output", default="books.csv",
                        help="output CSV path (default: books.csv)")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="seconds to wait after each page load (default: 3)")
    parser.add_argument("--driver-path",
                        help="path to geckodriver (optional with Selenium >= 4.6)")
    parser.add_argument("--headless", action="store_true",
                        help="run Firefox without a visible window")
    args = parser.parse_args(argv)

    driver = create_driver(args.driver_path, headless=args.headless)
    try:
        count = write_csv(scrape(driver, args.pages, args.delay), args.output)
    finally:
        driver.quit()
    print(f"Wrote {count} books to {args.output}")


if __name__ == "__main__":
    main()
