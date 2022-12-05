from selenium import webdriver
import bs4, csv

browser = webdriver.Chrome()
with open('file.csv', 'r') as f:
    with open('file2.csv', 'w') as f2:
        fieldnames = ['placename', 'url', 'address']
        writer = csv.DictWriter(f2, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(300):
            first_line = f.readline()
            url = first_line
            browser.get(url)
            html = browser.page_source
            # ----------------------------------
            soup = bs4.BeautifulSoup(html, "html.parser")
            placename = soup.find("h1", {"class": "normal"}).get_text()
            addy = soup.find("div", {"class": "address-wrapper"}).get_text()
            writer.writerow({'placename': placename, 'url': url, 'address': addy})
