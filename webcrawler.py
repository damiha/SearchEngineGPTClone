import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from queue import Queue
import queue
import json
from datetime import datetime
import threading
import time
import pickle
import dill
from concurrent.futures import ThreadPoolExecutor, as_completed

class WebCrawler:
    def __init__(self, start_url, uses_threadpool=True, max_workers=20):
        self.start_url = start_url
        self.index = {}  # Maps URLs to filenames
        self.folder = "webpages"

        self.index_file = "webpages/index.json"

        # Create the 'webpages' directory if it doesn't exist
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as file:
                self.index = json.load(file)
        else:
            self.index = {}

        self.counter = len(self.index) + 1

        # for threading
        self.crawl_thread = None

        # for stopping
        self.is_crawling = False

        # for statistics
        self.start_time = None
        self.pages_crawled = 0

        # for continuing crawling
        self.queue_file = os.path.join(self.folder, "queue.pickle")

        # Load the queue if it exists, otherwise initialize with start_url
        if os.path.exists(self.queue_file):
            with open(self.queue_file, 'rb') as file:
                self.queue = dill.load(file)
        else:
            self.queue = Queue(maxsize=10_000)
        
        self.nonblocking_put(start_url)

        # sending requests in a thread pool
        self.uses_threadpool = uses_threadpool
        self.max_workers = max_workers

        self.pending_futures = 0

    def nonblocking_put(self, item):
        try:
            self.queue.put_nowait(item)
        except queue.Full:
            pass

    def _valid_url(self, url):
        """ Check if a URL is valid """
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    def _save_content(self, url, content):
        """ Save content to a file and update index """
        filename = f"{self.counter}.txt"
        self.counter += 1
        with open(os.path.join(self.folder, filename), 'w', encoding='utf-8') as file:
            file.write(content)
        
        current_date = datetime.now().strftime("%Y-%m-%d")  # Date in 'YYYY-MM-DD' format
        self.index[filename] = {"url": url, "date": current_date}

        # Write the updated index to 'index.json'
        with open(self.index_file, 'w', encoding='utf-8') as file:
            json.dump(self.index, file, indent=4)

    def _extract_text(self, html_content):
        """ Extract text content from HTML """
        soup = BeautifulSoup(html_content, 'html.parser')
        paragraphs = soup.find_all('p')
        return '\n'.join([p.get_text() for p in paragraphs])
    
    def _was_indexed(self, url):
        """Check if the URL was indexed and if the dates match."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        for file_info in self.index.values():
            if file_info['url'] == url and file_info['date'] == current_date:
                return True
        return False
    
    def _get_info(self):
        """ Returns statistics about the crawling process """
        total_time = time.time() - self.start_time if self.start_time else 0
        pages_per_second = self.pages_crawled / total_time if total_time > 0 else 0
        return {
            "webpages_per_second": pages_per_second,
            "total_webpages": self.pages_crawled,
            "queue_size": self.queue.qsize(),
            "pending_futures": self.pending_futures
        }

    def _fetch_url(self, url):
        # The function to fetch a single URL.
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return None
    
    def _process_page(self, url, response_text):
        """ Process the page: Extract text, save content, and find links """
        # Extract and save text content
        text_content = self._extract_text(response_text)
        self._save_content(url, text_content)

        # Parse for links and add to queue
        soup = BeautifulSoup(response_text, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href:
                abs_url = urljoin(url, href)
                if self._valid_url(abs_url):
                    self.nonblocking_put(abs_url)

        # add counter
        self.pages_crawled += 1
    
    def crawl(self):

        self.is_crawling = True
        self.start_time = time.time()
        self.pages_crawled = 0

        self.executor = ThreadPoolExecutor(max_workers=self.max_workers) if self.uses_threadpool else None

        # the queue should already be initialized
        if self.uses_threadpool:
            while self.is_crawling and (not self.queue.empty() or self.pending_futures == 0):
                
                future_to_url = {}
                # Take a batch of URLs from the queue
                while not self.queue.empty() and len(future_to_url) < self.max_workers:

                    url = self.queue.get()

                    if self._was_indexed(url):
                        continue
                    
                    future = self.executor.submit(self._fetch_url, url)
                    future_to_url[future] = url
                    self.pending_futures += 1

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    response_text = future.result()
                    if response_text:
                        self.executor.submit(self._process_page, url, response_text)

                    # remove completed futures
                    del future_to_url[future]
                    self.pending_futures -= 1
            
            self.executor.shutdown()

        else:
            # ... existing single-threaded crawl logic ...
            while self.queue and self.is_crawling:

                url = self.queue.get()

                if self._was_indexed(url):
                    continue

                # Fetching URL without thread pool.
                response_text = self._fetch_url(url)

                if response_text:
                    self._process_page(url, response_text)

        self.finish_crawl()

    def finish_crawl(self):

        self.is_crawling = False

        # Pickle the queue
        with open(self.queue_file, 'wb') as file:
            dill.dump(self.queue, file)

    def stop(self):

        self.finish_crawl()

        if self.crawl_thread and self.crawl_thread.is_alive():
            self.crawl_thread.join()  # Wait for the crawling thread to finish

    def start_crawl(self):
        """ Start the crawl in a separate thread """
        self.crawl_thread = threading.Thread(target=self.crawl)
        self.crawl_thread.start()
