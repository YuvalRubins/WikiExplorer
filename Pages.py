from functools import cached_property
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, quote


class NotWikiPage(Exception):
    pass


class PageManager:
    FORBIDDEN_PAGES = ["Main_Page", "עמוד_ראשי"]
    FORBIDDEN_PREFIXES = ["Talk", "Category", "Help", "File", "Wikipedia", "Special",
                          "User", "User_talk", "Template", "Template_talk", "Portal",
                          "Wikipedia_talk", "Draft", "Category_talk",
                          "שיחה", "מיוחד", "קטגוריה", "קובץ", "ויקיפדיה", "משתמש",
                          "שיחת_משתמש", "עזרה", "פורטל", "טיוטה", "משתמשת", "תבנית",
                          "שיחת_תבנית", "שיחת_קטגוריה", "שיחת_ויקיפדיה", "שיחת_טיוטה",
                          ]
    BASE_URL_PAGE_HEADER = "https://{}.wikipedia.org/wiki/"
    ENGLISH_PREFIX = "en"
    HEBREW_PREFIX = "he"

    def __init__(self, is_hebrew: bool=False, forbidden_pages: list=None, no_nav_boxes: bool=False):
        self.is_hebrew = is_hebrew
        self.no_nav_boxes=no_nav_boxes
        self.forbidden_pages = forbidden_pages or []
        self.forbidden_pages.extend(PageManager.FORBIDDEN_PAGES)
        self.pages = {}

    @cached_property
    def url_page_header(self):
        return PageManager.BASE_URL_PAGE_HEADER.format(PageManager.HEBREW_PREFIX if self.is_hebrew else PageManager.ENGLISH_PREFIX)

    def get_page(self, page_name: str):
        if page_name not in self.pages:
            self.pages[page_name] = Page(page_name, self)
        return self.pages[page_name]

    def name_to_url(self, name: str) -> str:
        if self.is_hebrew:
            name = name[::-1]
        return self.url_page_header + quote(name)

    def is_url_of_wiki_page(self, url: str) -> bool:
        if not url.startswith(self.url_page_header):
            return False
        name = url[len(self.url_page_header):].split('#')[0]
        name = unquote(name)
        return url.startswith(self.url_page_header) and \
            name not in self.forbidden_pages and \
            all(not name.startswith(s + ":") for s in PageManager.FORBIDDEN_PREFIXES)

    def url_to_name(self, url: str) -> str:
        if self.is_url_of_wiki_page(url):
            name = url[len(self.url_page_header):].split('#')[0]
            name = unquote(name)
            if self.is_hebrew:
                name = name[::-1]
            return name
        else:
            raise NotWikiPage(url)

    def get_random_page_name(self):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            )
        }
        response = requests.get(f"{self.url_page_header}Special:Random", headers=headers, timeout=30)
        return self.url_to_name(response.url)

    def get_links_from_html(self, url):
        """
        Return all links from a html page
        If NO_NAV_BOXES is true, it doesn't return links from navigation boxes
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup.find_all("footer"):
            tag.decompose()
        if self.no_nav_boxes:
            for nav_tag in soup.find_all("div", attrs={'role': 'navigation'}) + soup.find_all("figcaption") + soup.find_all("table", attrs={'class': 'infobox'}) + soup.find_all("table", attrs={'class': 'navbox'}) + soup.find_all("div", attrs={'role': 'note'}) + soup.find_all("table", attrs={'class': 'wikitable'}) + soup.find_all("table", attrs={'class': 'sortable'}):
                nav_tag.decompose()
        return {urljoin(url, a["href"]) for a in soup.find_all("a", href=True)}

    def get_wikipedia_pages_from_url(self, url):
        pages = set()
        for link in self.get_links_from_html(url):
            try:
                name = self.url_to_name(link)
                pages.add(self.get_page(name))
            except NotWikiPage:
                continue
        return pages

    def validate_path(self, path, start_page, end_page):
        assert path[0] == start_page
        assert path[-1] == end_page
        for i in range(len(path)-1):
            try:
                assert self.get_page(path[i+1]) in self.get_page(path[i]).outgoing_pages
            except AssertionError:
                print(f"{path[i+1]} not in {path[i]}")
                raise


class Page:
    HEBREW_URL_PAGE_HEADER = "https://he.wikipedia.org/wiki/"
    ENGLISH_URL_PAGE_HEADER = "https://en.wikipedia.org/wiki/"

    def __init__(self, name: str, page_manager: PageManager):
        self.name = name
        self.page_manager = page_manager

    @staticmethod
    def get_path_string(path):
        return " -> ".join(path)

    @cached_property
    def outgoing_pages(self):
        return self.page_manager.get_wikipedia_pages_from_url(self.url).difference([self])

    @cached_property
    def incoming_pages(self):
        name = self.name[::-1] if self.page_manager.is_hebrew else self.name
        incoming_pages = self.page_manager.get_wikipedia_pages_from_url(f"{self.page_manager.url_page_header}Special:WhatLinksHere/{name}").difference([self])
        not_incoming_pages = set()
        # for page in incoming_pages:
        #     if self not in page.outgoing_pages:
        #         not_incoming_pages.add(page)
        return incoming_pages.difference(not_incoming_pages)

    @cached_property
    def url(self) -> str:
        return self.page_manager.name_to_url(self.name)

    @cached_property
    def rank(self) -> str:
        return len(self.outgoing_pages)

    def __str__(self):
        return self.name
