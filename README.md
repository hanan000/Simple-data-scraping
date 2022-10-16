# Simple-data-scraping

Selenium web scraping project 


### For this project, we scraped a website to get the information about the books. 

### In the first part, we scraped a web site.
The website is "https://www.idefix.com". We got the information from the books in the "Bilim" category. In short, we used "https://www.idefix.com/kategori/Kitap/Bilim/grupno=00052?Page=1" as a link. As I am preparing this project, there are 2531 books in 71 pages.

we found the links to the pages, then we got the book links from these pages. After getting the link of each book, we extracted the information, and we got the values for:

{"name," "author," "price," "number of reviewers," "rate given by the reviewers," "publication year," and "number of pages."}

and we stored the collected data in a json file.

<span style="background-color: red"> Note: Be careful, there may be missing values. </span>

## The libraries used in this project are:
<span style="background-color: #FFFF00"> Selenium, BeautifulSoup for scraping.</span>

#### In the second part, we used statistical and probability tools to understand the data. 

- found mean, median, and stdev values of the book prices. 
- draw the histogram of the reviewers' number. 
- Used discrete values such as 10,20 on the x-axis. 
- Find out if there is a relationship between the book price and the book rate. 
- found the distribution of the words and the most used word in the book names. 
- draw a histogram.
