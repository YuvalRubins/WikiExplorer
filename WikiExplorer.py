import math
import networkx as nx
import heapq
from functools import cached_property
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, quote
import argparse
import colorama

from NLPModels import NLPModel, EnglishNLPModel, HebrewNLPModel

colorama.init(autoreset=True)

RANDOM_PAGE = '*'


class WikiExplorer:
    """
    Wiki explorer for path finding between pages
    """
    def __init__(self, start_page_name: str, end_page_name: str, nlp_model: NLPModel, max_path_length: float):
        self.start_page = start_page_name
        self.end_page = end_page_name
        self.explored_graph = nx.DiGraph()
        self.search_number = 0
        self.nlp_model = nlp_model
        self.max_path_length = max_path_length
        self.max_path_length_one_side = float("inf") if self.max_path_length == float("inf") else math.ceil(self.max_path_length / 2)

    def get_page_rank(self, page, dest_page):
        """
        Compute rank of `page` in relation to `dest_page` as it is the page going towards to
        (basically how similar is the current page to the dest page)
        Smaller rank is a better rank
        """
        return -self.nlp_model.get_nlp_similarity(page, dest_page)

    def get_outgoing_neighbors(self, node):
        return {page.name for page in Page(node).outgoing_pages}

    def get_incoming_neighbors(self, node):
        return {page.name for page in Page(node).incoming_pages}

    def is_valid_source(self, node):
        """
        Is the node a valid source, i.e. is it connected to the start
        """
        try:
            path = nx.shortest_path(self.explored_graph, self.start_page, node)
            return len(path) <= self.max_path_length_one_side
        except nx.NetworkXNoPath:
            return False

    def is_valid_target(self, node):
        """
        Is the node a valid target, i.e. is it connected to the end
        """
        try:
            path = nx.shortest_path(self.explored_graph, node, self.end_page)
            return len(path) <= self.max_path_length_one_side
        except nx.NetworkXNoPath:
            return False

    def print_current_path(self, source, target):
        begin_path = nx.shortest_path(self.explored_graph, self.start_page, source)
        end_path = nx.shortest_path(self.explored_graph, target, self.end_page)
        print(f"{self.search_number:3}) " +
              colorama.Fore.GREEN + Page.get_path_string(begin_path) +
              colorama.Style.RESET_ALL + "   ===>   " +
              colorama.Fore.RED + Page.get_path_string(end_path))

    def search_path(self):
        # Item in heap: [rank, node, dest_node that rank refers to]
        sources_heap = [[self.get_page_rank(self.start_page, self.end_page), self.start_page, self.end_page]]
        seen_sources = set([self.start_page])
        targets_heap = [[self.get_page_rank(self.end_page, self.start_page), self.end_page, self.start_page]]
        seen_targets = set([self.end_page])
        self.explored_graph.add_nodes_from([self.start_page, self.end_page])
        current_source = self.start_page
        current_target = self.end_page

        while sources_heap and targets_heap:
            if self.search_number % 2 == 0:
                # Advance forward
                current_target = targets_heap[0][1]
                while not self.is_valid_target(current_target):
                    heapq.heappop(targets_heap)
                    seen_targets.discard(current_target)
                    if not targets_heap:
                        print("No path exists")
                        return
                    current_target = targets_heap[0][1]

                _, current_source, from_target = heapq.heappop(sources_heap)
                while from_target != current_target or not self.is_valid_source(current_source):
                    if self.is_valid_source(current_source):
                        heapq.heappush(sources_heap, [self.get_page_rank(current_source, current_target), current_source, current_target])
                    else:
                        seen_sources.discard(current_source)
                    if sources_heap:
                        _, current_source, from_target = heapq.heappop(sources_heap)
                    else:
                        print("No path exists")
                        return

                neighbors = self.get_outgoing_neighbors(current_source)
                new_neighbors = neighbors.difference(seen_sources)
                seen_sources.update(new_neighbors)
                new_neighbors_with_ranks = [[self.get_page_rank(neighbor, current_target), neighbor, current_target] for neighbor in new_neighbors]
                heapq.heapify(new_neighbors_with_ranks)
                sources_heap = list(heapq.merge(sources_heap, new_neighbors_with_ranks))
                self.explored_graph.add_edges_from([(current_source, neighbor) for neighbor in neighbors])

            else:
                # Advance backwards
                current_source = sources_heap[0][1]
                while not self.is_valid_source(current_source) and sources_heap:
                    heapq.heappop(sources_heap)
                    seen_sources.discard(current_source)
                    if not sources_heap:
                        print("No path exists")
                        return
                    current_source = sources_heap[0][1]

                _, current_target, from_source = heapq.heappop(targets_heap)
                while from_source != current_source or not self.is_valid_target(current_target):
                    if self.is_valid_target(current_target):
                        heapq.heappush(targets_heap, [self.get_page_rank(current_target, current_source), current_target, current_source])
                    else:
                        seen_targets.discard(current_target)
                    if targets_heap:
                        _, current_target, from_source = heapq.heappop(targets_heap)
                    else:
                        print("No path exists")
                        return

                neighbors = self.get_incoming_neighbors(current_target)
                new_neighbors = neighbors.difference(seen_targets)
                seen_targets.update(new_neighbors)
                new_neighbors_with_ranks = [[self.get_page_rank(neighbor, current_source), neighbor, current_source] for neighbor in new_neighbors]
                heapq.heapify(new_neighbors_with_ranks)
                targets_heap = list(heapq.merge(targets_heap, new_neighbors_with_ranks))
                self.explored_graph.add_edges_from([(neighbor, current_target) for neighbor in neighbors])

            # Check current path
            self.print_current_path(current_source, current_target)
            self.search_number += 1
            while nx.has_path(self.explored_graph, self.start_page, self.end_page):
                path = nx.shortest_path(self.explored_graph, self.start_page, self.end_page)

                # Validate path, remove edges that aren't real
                is_valid_path = True
                for i in range(len(path)-1):
                    if Page(path[i+1]) not in Page(path[i]).outgoing_pages:
                        self.explored_graph.remove_edge(path[i], path[i+1])
                        Page(path[i+1]).incoming_pages.discard(path[i])
                        is_valid_path = False
                if is_valid_path:
                    if len(path) <= self.max_path_length:
                        print("Found path" + f" (len={len(path)}): " + Page.get_path_string(path))
                        return path
                    else:
                        break

        print("No path exists")


class NotWikiPage(Exception):
    pass


class Page:
    HEBREW_URL_PAGE_HEADER = "https://he.wikipedia.org/wiki/"
    ENGLISH_URL_PAGE_HEADER = "https://en.wikipedia.org/wiki/"
    NO_NAV_BOXES = False
    IS_HEBREW = False
    FORBIDDEN_PAGES = ["Main_Page", "עמוד_ראשי"]
    _pages = {}

    @staticmethod
    def get_url_page_header():
        return Page.HEBREW_URL_PAGE_HEADER if Page.IS_HEBREW else Page.ENGLISH_URL_PAGE_HEADER

    def __new__(cls, name):
        if name in cls._pages:
            return cls._pages[name]
        else:
            page = super().__new__(cls)
            cls._pages[name] = page
            return page

    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def name_to_url(name: str) -> str:
        if Page.IS_HEBREW:
            name = name[::-1]
        return Page.get_url_page_header() + quote(name)

    @staticmethod
    def is_url_of_wiki_page(url: str) -> bool:
        if not url.startswith(Page.get_url_page_header()):
            return False
        name = url[len(Page.get_url_page_header()):]
        name = unquote(name)
        return url.startswith(Page.get_url_page_header()) and \
            all(name != s for s in Page.FORBIDDEN_PAGES) and \
            all(not name.startswith(s + ":") for s in ["Talk", "Category", "Help", "File", "Wikipedia", "Special",
                                                       "User", "User_talk", "Template", "Template_talk", "Portal",
                                                       "Wikipedia_talk", "Draft", "Category_talk",
                                                       "שיחה", "מיוחד", "קטגוריה", "קובץ", "ויקיפדיה", "משתמש",
                                                       "שיחת_משתמש", "עזרה", "פורטל", "טיוטה", "משתמשת", "תבנית",
                                                       "שיחת_תבנית", "שיחת_קטגוריה", "שיחת_ויקיפדיה", "שיחת_טיוטה",
                                                       ])

    @staticmethod
    def url_to_name(url: str) -> str:
        if Page.is_url_of_wiki_page(url):
            name = url[len(Page.get_url_page_header()):].split('#')[0]
            name = unquote(name)
            if Page.IS_HEBREW:
                name = name[::-1]
            return name
        else:
            raise NotWikiPage(url)

    @staticmethod
    def get_random_page_name():
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            )
        }
        response = requests.get(f"{Page.get_url_page_header()}Special:Random", headers=headers)
        return Page.url_to_name(response.url)

    @staticmethod
    def get_links_from_html(url):
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
        if Page.NO_NAV_BOXES:
            for nav_tag in soup.find_all("div", attrs={'role': 'navigation'}) + soup.find_all("figcaption") + soup.find_all("table", attrs={'class': 'infobox'}) + soup.find_all("table", attrs={'class': 'navbox'}) + soup.find_all("div", attrs={'role': 'note'}) + soup.find_all("table", attrs={'class': 'wikitable'}) + soup.find_all("table", attrs={'class': 'sortable'}):
                nav_tag.decompose()
        return {urljoin(url, a["href"]) for a in soup.find_all("a", href=True)}

    @staticmethod
    def get_wikipedia_pages_from_url(url):
        pages = set()
        for link in Page.get_links_from_html(url):
            try:
                name = Page.url_to_name(link)
                pages.add(Page(name))
            except NotWikiPage:
                continue
        return pages

    @staticmethod
    def get_path_string(path):
        return " -> ".join(path)

    @cached_property
    def outgoing_pages(self):
        return self.get_wikipedia_pages_from_url(self.url).difference([self])

    @cached_property
    def incoming_pages(self):
        name = self.name[::-1] if self.IS_HEBREW else self.name
        incoming_pages = self.get_wikipedia_pages_from_url(f"{self.get_url_page_header()}Special:WhatLinksHere/{name}").difference([self])
        not_incoming_pages = set()
        # for page in incoming_pages:
        #     if self not in page.outgoing_pages:
        #         not_incoming_pages.add(page)
        return incoming_pages.difference(not_incoming_pages)

    @cached_property
    def url(self) -> str:
        return Page.name_to_url(self.name)

    @cached_property
    def rank(self) -> str:
        return len(self.outgoing_pages)

    def __str__(self):
        return self.name


def validate_path(path, start_page, end_page):
    assert path[0] == start_page
    assert path[-1] == end_page
    for i in range(len(path)-1):
        try:
            assert Page(path[i+1]) in Page(path[i]).outgoing_pages
        except AssertionError:
            print(f"{path[i+1]} not in {path[i]}")
            raise


def search_path_on_wikipedia(start_page_name, end_page_name, is_hebrew=False, max_path_length=float("inf"), no_nav_boxes=False, forbidden_pages: list=None):
    Page.NO_NAV_BOXES = no_nav_boxes
    Page.IS_HEBREW = is_hebrew

    if is_hebrew:
        start_page_name = start_page_name[::-1]
        end_page_name = end_page_name[::-1]

    if start_page_name == RANDOM_PAGE:
        start_page_name = Page.get_random_page_name()
    if end_page_name == RANDOM_PAGE:
        end_page_name = Page.get_random_page_name()

    if forbidden_pages:
        Page.FORBIDDEN_PAGES.extend(forbidden_pages)

    nlp_model = HebrewNLPModel() if is_hebrew else EnglishNLPModel()
    wiki_exp = WikiExplorer(start_page_name, end_page_name, nlp_model, max_path_length)
    path = wiki_exp.search_path()
    if path:
        validate_path(path, start_page_name, end_page_name)
    return path


def main():
    parser = argparse.ArgumentParser(description="Search a path from one Wikipedia page to another")
    parser.add_argument("--start-page", '-s', type=str, help="Start page (takes a random page is not set)", default=RANDOM_PAGE)
    parser.add_argument("--end-page", '-e', type=str, help="Target page (takes a random page is not set)", default=RANDOM_PAGE)
    parser.add_argument("--no-nav-boxes", '-nn', help="Don't use links in navigation boxes", action="store_true")
    parser.add_argument("--hebrew", '-he', help="In hebrew Wikipedia", action="store_true")
    parser.add_argument("--max-length", '-ml', type=int, help="Maximum allowed length of path (including start and end page)", default=float("inf"))
    parser.add_argument("--forbidden-page", '-fp', action='append', help="Forbidden pages to pass through", default=[])

    args = parser.parse_args()
    search_path_on_wikipedia(args.start_page, args.end_page, args.hebrew, args.max_length, args.no_nav_boxes, args.forbidden_page)


if __name__ == "__main__":
    main()
