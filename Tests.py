import os
import pytest
from WikiExplorer import search_path_on_wikipedia, validate_path, Page

CLI_COMMAND = "python WikiExplorer.py"


def get_all_incoming_pages(page, max_size=float("inf")):
    pages_to_explore = {Page(page)}
    explored_pages = set()
    while pages_to_explore and len(explored_pages) < max_size:
        current_page = pages_to_explore.pop()
        print(current_page)
        explored_pages.add(current_page)
        incoming_pages = current_page.incoming_pages
        not_incoming_pages = set()
        for page in incoming_pages:
            if current_page not in page.outgoing_pages:
                not_incoming_pages.add(page)
        incoming_pages.difference(not_incoming_pages)
        incoming_pages.difference_update(explored_pages)
        pages_to_explore.update(incoming_pages)

    return explored_pages


def run_search(start_page, end_page, **kwargs):
    print(f"Searching path from {start_page} to {end_page}")
    path = search_path_on_wikipedia(start_page, end_page, **kwargs)
    if path:
        validate_path(path, start_page, end_page)
    else:
        MAX_SIZE = 100
        incoming_pages = get_all_incoming_pages(end_page, max_size=MAX_SIZE)
        assert Page(start_page) not in incoming_pages
        assert len(incoming_pages) < MAX_SIZE


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


@pytest.mark.parametrize("i", range(1000))
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
