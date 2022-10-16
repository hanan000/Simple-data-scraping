# Simple Data Scraping

A small Selenium web scraper that collects book data from the **"Bilim" (science)** category of
[idefix.com](https://www.idefix.com), a Turkish online bookstore, and saves it as CSV. The repository
also contains the original Jupyter notebook in which the data was scraped and explored.

> **Note:** the scraper was written against idefix.com as it was in 2020. The site has since been
> redesigned, so the selectors may no longer match the live pages. The parsing logic is covered by
> tests that run against saved HTML, so it can be checked and updated without hitting the site.

## How it works

1. Open the category listing page
   `https://www.idefix.com/kategori/Kitap/Bilim/grupno=00052?Page=N` for pages `1..N`.
2. Read every book card on the page: name, author, price and the link to the book's own page.
3. Visit each book page and read the rating, number of reviewers, first-edition year and page count.
4. Write one CSV row per book.

Selenium (Firefox) only loads the pages; the HTML is then parsed with `lxml` by plain functions
in `scraper.py`, which is what makes the parsing testable offline.

## Fields

| Column               | Source       | Example                 |
|----------------------|--------------|-------------------------|
| `name`               | listing page | `Arachnoid Mater`       |
| `author`             | listing page | `Serkan Karaismailoğlu` |
| `price`              | listing page | `34.3` (TL)             |
| `rating`             | book page    | `3.5` (out of 5)        |
| `reviewers`          | book page    | `19`                    |
| `first_edition_year` | book page    | `2020`                  |
| `pages`              | book page    | `488`                   |
| `url`                | listing page | link to the book page   |

A value that is missing on the site is written as an empty cell.

## Setup

Requires Python 3.9+ and Firefox.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Browser driver:** Selenium drives Firefox through
[geckodriver](https://github.com/mozilla/geckodriver/releases). With Selenium 4.6 or newer (the
minimum in `requirements.txt`), Selenium Manager finds or downloads a matching geckodriver
automatically. To use your own binary instead, download it and pass its path with `--driver-path`.

## Usage

```bash
# Scrape the first listing page into books.csv
python scraper.py

# Scrape three pages into a custom file without opening a browser window
python scraper.py --pages 3 --output bilim_books.csv --headless
```

| Option          | Default     | Description                                |
|-----------------|-------------|--------------------------------------------|
| `-p, --pages`   | `1`         | Number of listing pages to scrape          |
| `-o, --output`  | `books.csv` | Output CSV path                            |
| `--delay`       | `3`         | Seconds to wait after each page load       |
| `--driver-path` | –           | Path to geckodriver (optional, see above)  |
| `--headless`    | off         | Run Firefox without a visible window       |

The functions can also be used from Python:

```python
from scraper import create_driver, scrape, write_csv

driver = create_driver(headless=True)
try:
    write_csv(scrape(driver, max_pages=1), "books.csv")
finally:
    driver.quit()
```

### Sample output

Values from the 2020 run:

```csv
name,author,price,rating,reviewers,first_edition_year,pages,url
Arachnoid Mater,Serkan Karaismailoğlu,34.3,3.5,19,2020,488,https://www.idefix.com/Kitap/Arachnoid-Mater/Bilim/Populer-Bilim/urunno=0001878105001
Doğanın İşaretlerini Okumanın Kaybolmuş Sanatı,Tristan Gooley,23.4,4.0,26,2018,,https://www.idefix.com/Kitap/Doganin-Isaretlerini-Okumanin-Kaybolmus-Sanati/Bilim/Populer-Bilim/urunno=0001785184001
```

## The notebook

`BookScraping.ipynb` is the original exploration, kept with its outputs. Besides scraping one page
of books, it looks at the data:

- mean, median and standard deviation of the book prices,
- covariance between price and rating,
- a bar chart of the number of reviewers per book,
- the most frequent words in the book titles.

Its cells use the Selenium 3 API and won't run unchanged on Selenium 4; use `scraper.py` for
scraping. The analysis cells also need `pandas`, `numpy`, `matplotlib` and `jupyter`.

## Project structure

```
.
├── scraper.py              # parsing functions, Selenium driver loop and CLI
├── BookScraping.ipynb      # original exploration notebook (with outputs)
├── Images/                 # screenshots of the listing and a book page
├── tests/
│   ├── test_scraper.py     # tests for parsing, CSV output and the scrape loop
│   └── fixtures/           # saved HTML used by the tests
├── requirements.txt
└── pytest.ini
```

## Tests

The tests use saved HTML fixtures and a fake driver, so they need neither a browser nor a network
connection:

```bash
pytest
```

## Author

Hanan Abbas
