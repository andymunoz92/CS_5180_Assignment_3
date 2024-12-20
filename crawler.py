from urllib.parse import urljoin
from urllib.request import urlopen, Request
import ssl
from bs4 import BeautifulSoup
import pymongo
import certifi


class Frontier:
    def __init__(self, seed_url):
        self.queue = [seed_url]
        self.visited = set()

    def nextURL(self):
        if not self.queue:
            return None
        url = self.queue.pop(0)
        self.visited.add(url)
        return url

    def addURL(self, url):
        if url not in self.visited and url not in self.queue:
            self.queue.append(url)

    def done(self):
        return len(self.queue) == 0

    def clear_frontier(self):
        self.queue.clear()


def retrieveHTML(url):
    try:
        # Create SSL context using certifi certificates
        context = ssl.create_default_context(cafile=certifi.where())

        # Create a Request object with headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = Request(url, headers=headers)

        # Open URL with SSL context
        with urlopen(req, context=context) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error retrieving {url}: {e}")
        return None


def storePage(url, html, db):
    try:
        db.pages.insert_one({
            "url": url,
            "html": html,
            "is_target": False
        })
    except Exception as e:
        print(f"Error storing page {url}: {e}")


def flagTargetPage(url, db):
    try:
        db.pages.update_one(
            {"url": url},
            {"$set": {"is_target": True}}
        )
    except Exception as e:
        print(f"Error flagging target page {url}: {e}")


def target_page(html):
    if not html:
        return False
    soup = BeautifulSoup(html, 'html.parser')
    target_heading = soup.find('h1', class_='cpp-h1')
    return target_heading and 'Permanent Faculty' in target_heading.text


def parse(html, base_url):
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    urls = []

    for link in soup.find_all('a', href=True):
        url = link['href']
        # Convert relative URLs to absolute URLs
        absolute_url = urljoin(base_url, url)

        # Only include HTML or SHTML pages from the CS department
        if (absolute_url.endswith(('.html', '.shtml')) and
                'cpp.edu/sci/computer-science' in absolute_url):
            urls.append(absolute_url)

    return urls


def crawlerThread(frontier, db):
    while not frontier.done():
        url = frontier.nextURL()
        if not url:
            continue

        print(f"Crawling: {url}")
        html = retrieveHTML(url)

        if html:
            storePage(url, html, db)

            if target_page(html):
                print(f"Found target page: {url}")
                flagTargetPage(url, db)
                frontier.clear_frontier()
            else:
                linked_urls = parse(html, url)
                for linked_url in linked_urls:
                    frontier.addURL(linked_url)


def main():
    # MongoDB connection
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["cs_faculty"]

    # Clear previous crawl data
    db.pages.drop()

    # Initialize frontier with seed URL
    seed_url = "https://www.cpp.edu/sci/computer-science/"
    frontier = Frontier(seed_url)

    # Start crawling
    crawlerThread(frontier, db)

    print("Crawling completed")


if __name__ == "__main__":
    main()
