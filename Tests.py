import os
import pytest
from WikiExplorer import search_path_on_wikipedia, validate_path, Page

CLI_COMMAND = "python WikiExplorer.py"


def bfs(start_node, get_neighbors, max_size):
    nodes_to_explore = {start_node}
    explored_nodes = set()
    while nodes_to_explore and len(explored_nodes) < max_size:
        current_node = nodes_to_explore.pop()
        print(current_node)
        explored_nodes.add(current_node)
        neighbors = get_neighbors(current_node)
        neighbors.difference_update(explored_nodes)
        nodes_to_explore.update(neighbors)

    return explored_nodes


def get_all_incoming_pages(page, max_size=float("inf")):
    def get_incoming_pages(page):
        incoming_pages = page.incoming_pages
        not_incoming_pages = set()
        for page in incoming_pages:
            if page not in page.outgoing_pages:
                not_incoming_pages.add(page)
        incoming_pages.difference_update(not_incoming_pages)
        return incoming_pages

    return bfs(Page(page), get_incoming_pages, max_size)


def get_all_outgoing_pages(page, max_size=float("inf")):
    return bfs(Page(page), lambda page: page.outgoing_pages, max_size)


def run_search(start_page, end_page, **kwargs):
    print(f"Searching path from {start_page} to {end_page}")
    path = search_path_on_wikipedia(start_page, end_page, **kwargs)
    if path:
        validate_path(path, start_page, end_page)
    else:
        MAX_SIZE = 100
        incoming_pages = get_all_incoming_pages(end_page, max_size=MAX_SIZE)
        assert Page(start_page) not in incoming_pages
        if len(incoming_pages) >= MAX_SIZE:
            outgoing_pages = get_all_outgoing_pages(start_page, max_size=MAX_SIZE)
            assert Page(end_page) not in outgoing_pages
            assert len(outgoing_pages) < MAX_SIZE


def run_cli(args):
    print(f"Running {CLI_COMMAND} {args}")
    assert 0 == os.system(f"{CLI_COMMAND} {args}")


@pytest.mark.parametrize("start_page, end_page", [("חתול", "כובע"), ("ביצה", "שמש")])
def test_hebrew_search(start_page, end_page):
    start_page = start_page[::-1]
    end_page = end_page[::-1]
    Page.IS_HEBREW = True
    run_search(start_page, end_page, is_hebrew=True)
    Page.IS_HEBREW = False


@pytest.mark.parametrize("i", range(1_000))
def test_random_search(i):
    start_page = Page.get_random_page_name()
    end_page = Page.get_random_page_name()
    run_search(start_page, end_page)


@pytest.mark.parametrize("i", range(1_000))
def test_random_search_without_nav(i):
    Page.NO_NAV_BOXES = True
    start_page = Page.get_random_page_name()
    end_page = Page.get_random_page_name()
    run_search(start_page, end_page)
    Page.NO_NAV_BOXES = False


@pytest.mark.parametrize("args", ["", "-s Cat", "-e Cat", "-s Cat -e Dog", "-s Cat -e '*'",
                                  "-s '*' -e Cat", "-s '*' -e '*'", "-nn", "-s Cat -e Dog -nn",
                                  "-s Cat -nn",
                                  "-he -s חתול -e כלב", "-he -s חתול -e כלב -nn"])
def test_cli(args):
    run_cli(args)
