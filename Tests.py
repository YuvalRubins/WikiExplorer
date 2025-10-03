import pytest
from WikiExplorer import search_path_on_wikipedia, Page

@pytest.mark.parametrize("i", range(1_000))
def test_random_search(i):
    start_page = Page.get_random_page_name()
    end_page = Page.get_random_page_name()
    print(f"Searching path from {start_page} to {end_page}")
    search_path_on_wikipedia(start_page, end_page)
