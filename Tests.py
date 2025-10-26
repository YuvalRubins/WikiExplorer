import os
import pytest
from WikiExplorer import search_path_on_wikipedia
from Pages import PageManager

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


def get_all_incoming_pages(page, page_manager, max_size=float("inf")):
    def get_incoming_pages(page):
        incoming_pages = page.incoming_pages
        not_incoming_pages = set()
        for page in incoming_pages:
            if page not in page.outgoing_pages:
                not_incoming_pages.add(page)
        incoming_pages.difference_update(not_incoming_pages)
        return incoming_pages

    return bfs(page_manager.get_page(page), get_incoming_pages, max_size)


def get_all_outgoing_pages(page, page_manager, max_size=float("inf")):
    return bfs(page_manager.get_page(page), lambda page: page.outgoing_pages, max_size)


def run_search(start_page, end_page, should_be_no_path=False, **kwargs):
    print(f"Searching path from {start_page} to {end_page}")
    path, wiki_exp = search_path_on_wikipedia(start_page, end_page, **kwargs)
    if should_be_no_path:
        assert path is None
        return

    if path:
        if kwargs.get('is_hebrew'):
            start_page = start_page[::-1]
            end_page = end_page[::-1]
        wiki_exp.page_manager.validate_path(path, start_page, end_page)
        return path
    else:
        MAX_SIZE = 100
        page_manager = PageManager(is_hebrew=kwargs.get("is_hebrew", False),
                                   forbidden_pages=kwargs.get("forbidden_pages", None),
                                   no_nav_boxes=kwargs.get("no_nav_boxes", False))
        incoming_pages = get_all_incoming_pages(end_page, page_manager, max_size=MAX_SIZE)
        assert page_manager.get_page(start_page) not in incoming_pages
        if len(incoming_pages) >= MAX_SIZE:
            outgoing_pages = get_all_outgoing_pages(start_page, page_manager, max_size=MAX_SIZE)
            assert page_manager.get_page(end_page) not in outgoing_pages
            assert len(outgoing_pages) < MAX_SIZE


def run_cli(args):
    print(f"Running {CLI_COMMAND} {args}")
    assert 0 == os.system(f"{CLI_COMMAND} {args}")

@pytest.mark.sanity
@pytest.mark.parametrize("start_page, end_page", [("House", "Cow"), ("Hat", "Bat")])
def test_search(start_page, end_page):
    run_search(start_page, end_page)


@pytest.mark.sanity
def test_search_no_path():
    run_search("4_AM_club", "Xpertdoc", should_be_no_path=True)


@pytest.mark.sanity
@pytest.mark.parametrize("start_page, end_page", [("חתול", "כובע"), ("ביצה", "שמש")])
def test_hebrew_search(start_page, end_page):
    run_search(start_page, end_page, is_hebrew=True)


@pytest.mark.sanity
@pytest.mark.parametrize("i", range(10))
def test_random_search_sanity(i):
    start_page = PageManager().get_random_page_name()
    end_page = PageManager().get_random_page_name()
    run_search(start_page, end_page)


@pytest.mark.sanity
@pytest.mark.parametrize("i", range(10))
def test_random_search_without_nav_sanity(i):
    start_page = PageManager().get_random_page_name()
    end_page = PageManager().get_random_page_name()
    run_search(start_page, end_page, no_nav_boxes=True)


@pytest.mark.sanity
@pytest.mark.parametrize("i", range(10))
def test_hebrew_random_search_sanity(i):
    start_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    end_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    run_search(start_page, end_page, is_hebrew=True)


@pytest.mark.sanity
@pytest.mark.parametrize("i", range(10))
def test_hebrew_random_search_without_nav_sanity(i):
    start_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    end_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    run_search(start_page, end_page, is_hebrew=True, no_nav_boxes=True)


@pytest.mark.parametrize("i", range(2_000))
def test_random_search(i):
    start_page = PageManager().get_random_page_name()
    end_page = PageManager().get_random_page_name()
    run_search(start_page, end_page)


@pytest.mark.parametrize("i", range(1_000))
def test_random_search_without_nav(i):
    start_page = PageManager().get_random_page_name()
    end_page = PageManager().get_random_page_name()
    run_search(start_page, end_page, no_nav_boxes=True)


@pytest.mark.parametrize("i", range(2_000))
def test_hebrew_random_search(i):
    start_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    end_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    run_search(start_page, end_page, is_hebrew=True)


@pytest.mark.parametrize("i", range(1_000))
def test_hebrew_random_search_without_nav(i):
    start_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    end_page = PageManager(is_hebrew=True).get_random_page_name()[::-1]
    run_search(start_page, end_page, is_hebrew=True, no_nav_boxes=True)


@pytest.mark.sanity
def test_max_length():
    path = run_search("Neutral_Milk_Hotel", "Pankaj_Dheer", no_nav_boxes=True)
    assert path is not None
    assert len(path) > 6
    path = run_search("Neutral_Milk_Hotel", "Pankaj_Dheer", no_nav_boxes=True, max_path_length=6)
    assert path is not None
    assert len(path) <= 6


@pytest.mark.sanity
def test_too_short_length():
    run_search("Hazari_Lane_violence", "Pretty_Hate_Machine_(Gotham)", should_be_no_path=True, max_path_length=4)


@pytest.mark.sanity
def test_forbidden_page():
    path = run_search("Jerusalem", "Kangaroo")
    assert "Whale" in path
    path = run_search("Jerusalem", "Kangaroo", forbidden_pages=["Whale"])
    assert path is not None
    assert "Whale" not in path


@pytest.mark.sanity
def test_two_forbidden_pages():
    path = run_search("Jerusalem", "Kangaroo", forbidden_pages=["Whale", "Ark_of_the_Covenant"])
    assert path is not None
    assert "Whale" not in path
    assert "Ark_of_the_Covenant" not in path


@pytest.mark.parametrize("args", ["", "-s Cat", "-e Cat", "-s Cat -e Dog", "-s Cat -e '*'",
                                  "-s '*' -e Cat", "-s '*' -e '*'", "-nn", "-s Cat -e Dog -nn",
                                  "-he",
                                  "-s Cat -nn",
                                  "-s Cat -nn -ml 4",
                                  "-s Cat -nn -ml 4 -fp United_Kingdom -e Dog",
                                  "-s Cat -fp United_Kingdom -e Dog",
                                  "-s Jerusalem -fp Whale -e Kangaroo",
                                  "-s Jerusalem -fp Mammal -fp Whale -e Kangaroo",
                                  "-s Jerusalem -fp Mammal -fp Whale -e Kangaroo -fp Ark_of_the_Covenant",
                                  "-he -s חתול -e כלב", "-he -s חתול -e כלב -nn"])
def test_cli(args):
    run_cli(args)
