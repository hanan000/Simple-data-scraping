import csv
from pathlib import Path

import pytest

import scraper

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- value helpers ---------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("34,30 TL ", 34.3),
        ("34,30", 34.3),
        ("1.234,50 TL", 1234.5),
        ("3,5", 3.5),
        ("4", 4.0),
        ("", None),
        (None, None),
        ("Fiyat yok", None),
    ],
)
def test_parse_decimal(text, expected):
    assert scraper.parse_decimal(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [("19", 19), ("19 Kişi", 19), ("", None), (None, None), ("Türkçe", None)],
)
def test_parse_int(text, expected):
    assert scraper.parse_int(text) == expected


# --- listing page ----------------------------------------------------------

def test_parse_listing_page_reads_every_card():
    items = scraper.parse_listing_page(load("listing_page.html"))

    assert [item.name for item in items] == [
        "Arachnoid Mater",
        "Zamanın Kısa Tarihi",
        "Doğanın İşaretlerini Okumanın Kaybolmuş Sanatı",
        "Beyinde Ararken Bağırsakta Buldum",
    ]
    assert [item.price for item in items] == [34.3, 17.4, 18.0, 25.2]


def test_parse_listing_page_uses_untruncated_author_and_book_url():
    first = scraper.parse_listing_page(load("listing_page.html"))[0]

    assert first.author == "Serkan Karaismailoğlu"  # visible text is "Serkan Karaisma..."
    assert first.url == (
        "https://www.idefix.com/Kitap/Arachnoid-Mater/Bilim/Populer-Bilim/urunno=0001878105001"
    )


def test_parse_listing_page_keeps_fields_aligned_when_one_is_missing():
    page = """
    <html><body>
      <div class="product-box">
        <div class="box-title"><a href="/a" title="Book A">Book A</a></div>
        <a class="who" title="Author A">Author A</a>
      </div>
      <div class="product-box">
        <div class="box-title"><a href="/b" title="Book B">Book B</a></div>
        <a class="who" title="Author B">Author B</a>
        <span class="price price" data-price="12,50">12,50 TL</span>
      </div>
    </body></html>
    """
    items = scraper.parse_listing_page(page)

    assert [(i.name, i.price) for i in items] == [("Book A", None), ("Book B", 12.5)]


def test_parse_listing_page_without_cards_returns_empty_list():
    assert scraper.parse_listing_page("<html><body><p>Ürün bulunamadı</p></body></html>") == []


# --- book page -------------------------------------------------------------

def test_parse_book_page():
    details = scraper.parse_book_page(load("book_page.html"))

    assert details == scraper.BookDetails(
        rating=3.5, reviewers=19, first_edition_year=2020, pages=488
    )


def test_parse_book_page_missing_fields_are_none():
    details = scraper.parse_book_page(
        "<html><body><ul><li><span>Dil:</span> <a class='bold'>Türkçe</a></li></ul></body></html>"
    )

    assert details == scraper.BookDetails(
        rating=None, reviewers=None, first_edition_year=None, pages=None
    )


def test_parse_book_page_does_not_borrow_value_from_next_attribute():
    # No first-edition year: must not pick up the page count from the next row.
    page = load("book_page.html").replace(
        '<li><span>İlk Baskı Yılı:</span> <a class="bold" href="#">2020</a></li>', ""
    )
    details = scraper.parse_book_page(page)

    assert details.first_edition_year is None
    assert details.pages == 488


# --- output ----------------------------------------------------------------

def test_merge_and_write_csv(tmp_path):
    item = scraper.parse_listing_page(load("listing_page.html"))[0]
    book = scraper.merge(item, scraper.parse_book_page(load("book_page.html")))
    missing = scraper.Book(
        name="Book B", author=None, price=None, rating=None,
        reviewers=None, first_edition_year=None, pages=None, url=None,
    )
    out = tmp_path / "books.csv"

    assert scraper.write_csv([book, missing], str(out)) == 2

    with out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == scraper.CSV_FIELDS
    assert rows[0] == {
        "name": "Arachnoid Mater",
        "author": "Serkan Karaismailoğlu",
        "price": "34.3",
        "rating": "3.5",
        "reviewers": "19",
        "first_edition_year": "2020",
        "pages": "488",
        "url": item.url,
    }
    assert rows[1]["name"] == "Book B"
    assert rows[1]["price"] == ""


# --- driver loop (fake driver, no browser) ---------------------------------

class FakeDriver:
    def __init__(self, pages):
        self.pages = pages
        self.visited = []
        self.page_source = ""

    def get(self, url):
        self.visited.append(url)
        self.page_source = self.pages[url]


def test_scrape_visits_listing_then_each_book():
    listing_url = scraper.CATEGORY_URL.format(page=1)
    listing_html = load("listing_page.html")
    book_urls = [i.url for i in scraper.parse_listing_page(listing_html)]
    pages = {listing_url: listing_html, **{url: load("book_page.html") for url in book_urls}}
    driver = FakeDriver(pages)

    books = list(scraper.scrape(driver, max_pages=1, delay=0))

    assert driver.visited == [listing_url, *book_urls]
    assert len(books) == 4
    assert books[1].name == "Zamanın Kısa Tarihi"
    assert books[1].reviewers == 19
