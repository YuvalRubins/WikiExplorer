import os
import pytest
from WikiExplorer import search_path_on_wikipedia, validate_path, Page

CLI_COMMAND = "python WikiExplorer.py"


def run_search(start_page, end_page, **kwargs):
    print(f"Searching path from {start_page} to {end_page}")
    path = search_path_on_wikipedia(start_page, end_page, **kwargs)
    if Page(end_page).incoming_pages and Page(start_page).outgoing_pages:
        validate_path(path, start_page, end_page)
    else:
        assert path is None


def run_cli(args):
    print(f"Running {CLI_COMMAND} {args}")
    assert 0 == os.system(f"{CLI_COMMAND} {args}")


@pytest.mark.parametrize("start_page, end_page", [("חתול", "כובע"), ("ביצה", "שמש")])
def test_hebrew_search(start_page, end_page):
    start_page = start_page[::-1]
    end_page = end_page[::-1]
    Page.IS_HEBREW = True
    run_search(start_page, end_page, is_hebrew=True)


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
