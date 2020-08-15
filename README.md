# Simple-data-scraping
web scraping simple project using selenium 

#### In this project, you will scrape a web site to get the information of the books.

In the first part, you will scrape a web site.
The web site is "https://www.idefix.com". You will get the information of the books in "Bilim" category. In short, you can use "https://www.idefix.com/kategori/Kitap/Bilim/grupno=00052?Page=1" as a link. In the "Bilim" category, there are 2531 books in 71 pages as I am preparing this project.

First you need to find the links of the pages, then you can get the book links from these pages.After getting the link of each book, you can extract the information.You should get the values of "name", "author", "price", "number of reviwers", "rate given by the reviewers", "publication year" and "number of pages". Be careful, there may be missing values. After collecting the data, you need to store them in a file, preferably json.

You need to use Selenium, BeautifulSoup for scraping.

#### In the second part, you will use statistical and probability tools to understand data..

You need the find mean and median and stdev values of the book prices. You need to draw the histogram of the reviewers' number. Use discrete values such as 10,20 on the x-axis. You need to find out if there is a relationship between between the book price and the book rate. You need to find the distribution of the words and the most used word in the book names. You can draw a histogram.
