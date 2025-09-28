import networkx as nx
import heapq
from functools import cached_property
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse
import spacy
nlp = spacy.load("en_core_web_lg")


def print_path_of_pages(pages):
    print(" -> ".join(pages))


def search_path(start, end, get_neighbors: callable, get_node_rank: callable):
    graph = nx.DiGraph()
    current_nodes = [(get_node_rank(start), start)]
    heapq.heapify(current_nodes)
    graph.add_node(start)
    seen_nodes = set([start])

    while current_nodes:
        _, node = heapq.heappop(current_nodes)
        print_path_of_pages(nx.shortest_path(graph, start, node))
        # print(f"Page rank: {get_node_rank(node)}")
        neighbors = set(get_neighbors(node))
        new_neighbors = neighbors.difference(seen_nodes)
        seen_nodes.update(new_neighbors)
        new_neighbors_with_ranks = [(get_node_rank(neighbor), neighbor) for neighbor in new_neighbors]
        heapq.heapify(new_neighbors_with_ranks)
        current_nodes = list(heapq.merge(current_nodes, new_neighbors_with_ranks))
        graph.add_nodes_from(new_neighbors)
        graph.add_edges_from([(node, neighbor) for neighbor in neighbors])

        if end in seen_nodes:
            return nx.shortest_path(graph, start, end)


class NotWikiPage(Exception):
    pass


# @dataclass
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
    def url(self) -> str:
        return Page.name_to_url(self.name)

    @cached_property
    def rank(self) -> str:
        return len(self.sub_pages)

    # def __lt__(self, other) -> bool:
    #     return self.rank > other.rank


def search_path_on_wikipedia(start_page_name, end_page_name):
    end_page_doc = nlp(end_page_name.replace("_", " "))

    def rank_of_page(page_name):
        current_page_doc = nlp(page_name.replace("_", " "))
        if not current_page_doc.has_vector:
            return 0
        else:
            return -end_page_doc.similarity(current_page_doc)

    path = search_path(start_page_name,
                       end_page_name,
                       lambda page_name: [page.name for page in Page(page_name).sub_pages],
                       rank_of_page)
    print_path_of_pages(path)


def main():
    parser = argparse.ArgumentParser(description="Search a path from one Wikipedia page to another")
    parser.add_argument("start_page", type=str, help="Start page")
    parser.add_argument("end_page", type=str, help="Target page")

    args = parser.parse_args()

    search_path_on_wikipedia(args.start_page, args.end_page)


if __name__ == "__main__":
    main()
