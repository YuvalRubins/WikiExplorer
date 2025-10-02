import networkx as nx
import heapq
from functools import cached_property
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse
import colorama
import spacy
nlp = spacy.load("en_core_web_lg")
colorama.init(autoreset=True)


class WikiExplorer:
    TOO_FAR_RANK = -0.4
    RETRACTION_PERIOD = 10
    def __init__(self, start_page_name: str, end_page_name: str, get_neighbors: callable, get_node_rank: callable):
        self.start_page = start_page_name
        self.end_page = end_page_name
        self.target_page = end_page_name
        self.get_neighbors = get_neighbors
        self.get_node_rank = get_node_rank
        self.explored_graph = nx.DiGraph()

    def get_page_rank(self, page, dest_page=None):
        """
        Smaller - more similar
        """
        dest_page = dest_page or self.target_page
        return -get_nlp_similarity(page, dest_page) - len(Page(page).sub_pages) / 10_000

    def print_current_path(self, page):
        begin_path = nx.shortest_path(self.explored_graph, self.start_page, page)
        end_path = nx.shortest_path(self.explored_graph, self.target_page, self.end_page)
        print(f"{self.search_number:3}) " +
              colorama.Fore.GREEN + " -> ".join(begin_path) +
              colorama.Style.RESET_ALL + "   ===>   " +
              colorama.Fore.RED + " -> ".join(end_path))

    def search_path(self):
        self.current_nodes = [[self.get_page_rank(self.start_page), self.start_page]]
        heapq.heapify(self.current_nodes)
        self.explored_graph.add_nodes_from([self.start_page, self.end_page])
        explored_nodes = set([self.start_page])
        seen_targets = set([self.end_page])
        self.search_number = 0

        while self.current_nodes:
            page_rank, closest_node = self.current_nodes[0]
            self.print_current_path(closest_node)
            print(f"Page rank: {page_rank}")

            if (page_rank > self.TOO_FAR_RANK or self.search_number % self.RETRACTION_PERIOD == 0) and \
               self.search_number % (self.RETRACTION_PERIOD+1) != 0:
                best_rank = float("inf")
                for bi_neighbor_page in Page(self.target_page).bidirectional_links_iterator:
                    bi_neighbor = bi_neighbor_page.name
                    # if bi_neighbor in seen_targets:
                    #     continue

                    self.explored_graph.add_edge(bi_neighbor, self.target_page)
                    self.explored_graph.add_edge(self.target_page, bi_neighbor)
                    bi_neighbor_rank = self.get_page_rank(bi_neighbor, closest_node)
                    if bi_neighbor_rank < self.TOO_FAR_RANK:
                        best_bi_neighbor = bi_neighbor
                        break

                    if best_rank > bi_neighbor_rank:
                        best_rank = bi_neighbor_rank
                        best_bi_neighbor = bi_neighbor

                self.target_page = best_bi_neighbor
                seen_targets.add(self.target_page)
                for node in self.current_nodes:
                    node[0] = self.get_page_rank(node[1])
                heapq.heapify(self.current_nodes)
                if nx.has_path(self.explored_graph, self.start_page, self.end_page):
                    break

            else:
                heapq.heappop(self.current_nodes)
                neighbors = set(self.get_neighbors(closest_node))
                new_neighbors = neighbors.difference(explored_nodes)
                explored_nodes.update(new_neighbors)
                new_neighbors_with_ranks = [[self.get_page_rank(neighbor), neighbor] for neighbor in new_neighbors]
                heapq.heapify(new_neighbors_with_ranks)
                self.current_nodes = list(heapq.merge(self.current_nodes, new_neighbors_with_ranks))
                self.explored_graph.add_nodes_from(new_neighbors)
                self.explored_graph.add_edges_from([(closest_node, neighbor) for neighbor in neighbors])
                if self.target_page in explored_nodes:
                    break

            self.search_number += 1

        path = nx.shortest_path(self.explored_graph, self.start_page, self.end_page)
        print("Found path: " + " -> ".join(path))
        return path


class NotWikiPage(Exception):
    pass


class Page:
    URL_PAGE_HEADER = "https://en.wikipedia.org/wiki/"

    @staticmethod
    def name_to_url(name: str) -> str:
        return Page.URL_PAGE_HEADER + name

    @staticmethod
    def is_url_of_wiki_page(url: str) -> bool:
        return url.startswith(Page.URL_PAGE_HEADER) and url.count('/') == Page.URL_PAGE_HEADER.count('/') and \
            '.' not in url.split('/')[-1] and ":" not in url.split('/')[-1]

    @staticmethod
    def url_to_name(url: str) -> str:
        if Page.is_url_of_wiki_page(url):
            return url.split('/')[-1].split("#")[0]
        else:
            raise NotWikiPage(url)

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

    @cached_property
    def content(self) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            )
        }
        response = requests.get(self.url, headers=headers)
        return response.text

    @cached_property
    def sub_pages(self):
        soup = BeautifulSoup(self.content, "html.parser")
        links = {urljoin(self.url, a["href"]) for a in soup.find_all("a", href=True)}
        sub_pages = set()
        for link in links:
            try:
                name = Page.url_to_name(link)
                sub_pages.add(Page(name))
            except NotWikiPage:
                continue
        return sub_pages

    @cached_property
    def bidirectional_links_iterator(self):
        class BidirectionalLinksIterator:
            def __init__(self, page):
                self.page = page

            def __iter__(self):
                self.linker_iterator = iter(self.page.sub_pages)
                return self

            def __next__(self):
                link = next(self.linker_iterator)
                while self.page not in link.sub_pages or self.page is link:
                    # print(f"checking {link}")
                    link = next(self.linker_iterator)
                print(f"found {link}")
                return link


        # bidirectional_links = set()

        return BidirectionalLinksIterator(self)

    @cached_property
    def url(self) -> str:
        return Page.name_to_url(self.name)

    @cached_property
    def rank(self) -> str:
        return len(self.sub_pages)

    def __str__(self):
        return self.name

    # def __lt__(self, other) -> bool:
    #     return self.rank > other.rank


def normalize_text_for_nlp(text: str) -> str:
    return text.lower().replace("_", " ")

def get_nlp_similarity(text1, text2):
    doc1 = nlp(normalize_text_for_nlp(text1))
    doc2 = nlp(normalize_text_for_nlp(text2))
    if not doc1.has_vector:
        return 0
    else:
        return doc1.similarity(doc2)


def search_path_on_wikipedia(start_page_name, end_page_name):
    def rank_of_page(wiki_explorer, page_name):
        return -get_nlp_similarity(page_name, wiki_explorer.target_page)

    WikiExplorer(start_page_name,
                 end_page_name,
                 lambda page_name: [page.name for page in Page(page_name).sub_pages],
                 rank_of_page).search_path()


def main():
    parser = argparse.ArgumentParser(description="Search a path from one Wikipedia page to another")
    parser.add_argument("start_page", type=str, help="Start page")
    parser.add_argument("end_page", type=str, help="Target page")

    args = parser.parse_args()

    search_path_on_wikipedia(args.start_page, args.end_page)


if __name__ == "__main__":
    main()
