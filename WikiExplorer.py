import networkx as nx
import heapq
from functools import cached_property
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse
import colorama
import spacy
nlp = spacy.load("en_core_web_lg")  # python -m spacy download en_core_web_lg
colorama.init(autoreset=True)


class WikiExplorer:
    """
    Wiki explorer for path finding between pages
    """
    def __init__(self, start_page_name: str, end_page_name: str):
        self.start_page = start_page_name
        self.end_page = end_page_name
        self.explored_graph = nx.DiGraph()
        self.search_number = 0

    def get_page_rank(self, page, dest_page):
        """
        Compute rank of `page` in relation to `dest_page` as it is the page going towards to
        (basically how similar is the current page to the dest page)
        Smaller rank is a better rank
        """
        return -get_nlp_similarity(page, dest_page)

    def get_outgoing_neighbors(self, node):
        return {page.name for page in Page(node).outgoing_pages}

    def get_incoming_neighbors(self, node):
        return {page.name for page in Page(node).incoming_pages}

    def is_valid_source(self, node):
        """
        Is the node a valid source, i.e. is it connected to the start
        """
        return nx.has_path(self.explored_graph, self.start_page, node)

    def is_valid_target(self, node):
        """
        Is the node a valid target, i.e. is it connected to the end
        """
        return nx.has_path(self.explored_graph, node, self.end_page)

    def print_current_path(self, source, target):
        begin_path = nx.shortest_path(self.explored_graph, self.start_page, source)
        end_path = nx.shortest_path(self.explored_graph, target, self.end_page)
        print(f"{self.search_number:3}) " +
              colorama.Fore.GREEN + " -> ".join(begin_path) +
              colorama.Style.RESET_ALL + "   ===>   " +
              colorama.Fore.RED + " -> ".join(end_path))

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
                    current_target = targets_heap[0][1]

                _, current_source, from_target = heapq.heappop(sources_heap)
                while from_target != current_target or not self.is_valid_source(current_source):
                    if self.is_valid_source(current_source):
                        heapq.heappush(sources_heap, [self.get_page_rank(current_source, current_target), current_source, current_target])
                    else:
                        seen_sources.discard(current_source)
                    _, current_source, from_target = heapq.heappop(sources_heap)

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
                while not self.is_valid_source(current_source):
                    heapq.heappop(sources_heap)
                    current_source = sources_heap[0][1]

                _, current_target, from_source = heapq.heappop(targets_heap)
                while from_source != current_source or not self.is_valid_target(current_target):
                    if self.is_valid_target(current_target):
                        heapq.heappush(targets_heap, [self.get_page_rank(current_target, current_source), current_target, current_source])
                    else:
                        seen_targets.discard(current_target)
                    _, current_target, from_source = heapq.heappop(targets_heap)

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
                    print("Found path" + f" (len={len(path)}): " + " -> ".join(path))
                    return path

        print("No path exists")

    def validate_path(self, path):
        assert path[0] == self.start_page
        assert path[-1] == self.end_page
        for i in range(len(path)-1):
            try:
                assert Page(path[i+1]) in Page(path[i]).outgoing_pages
            except AssertionError:
                print(f"{path[i+1]} not in {path[i]}")
                raise


class NotWikiPage(Exception):
    pass


class Page:
    URL_PAGE_HEADER = "https://en.wikipedia.org/wiki/"
    NO_NAV_BOXES = False
    _pages = {}

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
        return Page.URL_PAGE_HEADER + name

    @staticmethod
    def is_url_of_wiki_page(url: str) -> bool:
        name = url.split('/')[-1]
        return url.startswith(Page.URL_PAGE_HEADER) and url.count('/') == Page.URL_PAGE_HEADER.count('/') and \
                ":" not in name and name != "Main_Page"

    @staticmethod
    def url_to_name(url: str) -> str:
        if Page.is_url_of_wiki_page(url):
            return url.split('/')[-1].split("#")[0]
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
        response = requests.get(f"{Page.URL_PAGE_HEADER}Special:Random", headers=headers)
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
        if Page.NO_NAV_BOXES:
            for nav_tag in soup.find_all("div", attrs={'role': 'navigation'}):
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

    @cached_property
    def outgoing_pages(self):
        return self.get_wikipedia_pages_from_url(self.url).difference([self])

    @cached_property
    def incoming_pages(self):
        incoming_pages = self.get_wikipedia_pages_from_url(f"{self.URL_PAGE_HEADER}Special:WhatLinksHere/{self.name}").difference([self])
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


def normalize_text_for_nlp(text: str) -> str:
    return text.lower().replace("_", " ").replace(",", " ").replace(".", " ")


def get_nlp_similarity(text1, text2):
    doc1 = nlp(normalize_text_for_nlp(text1))
    doc2 = nlp(normalize_text_for_nlp(text2))
    if not doc1.has_vector:
        return 0
    else:
        return doc1.similarity(doc2)


def search_path_on_wikipedia(start_page_name, end_page_name):
    wiki_exp = WikiExplorer(start_page_name, end_page_name)
    path = wiki_exp.search_path()
    wiki_exp.validate_path(path)


def main():
    parser = argparse.ArgumentParser(description="Search a path from one Wikipedia page to another")
    parser.add_argument("--start-page", '-s', type=str, help="Start page (takes a random page is not set)", default='*')
    parser.add_argument("--end-page", '-e', type=str, help="Target page (takes a random page is not set)", default='*')
    parser.add_argument("--no-nav-boxes", '-nn', help="Don't use links in navigation boxes", action="store_true")

    args = parser.parse_args()

    if args.start_page == '*':
        args.start_page = Page.get_random_page_name()
    if args.end_page == '*':
        args.end_page = Page.get_random_page_name()
    Page.NO_NAV_BOXES = args.no_nav_boxes

    search_path_on_wikipedia(args.start_page, args.end_page)


if __name__ == "__main__":
    main()
