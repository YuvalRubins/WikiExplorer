# WikiExplorer
Find a path between two Wikipedia pages

## Requirements

Run:
1) `pip install -r requirements.txt`
1) `python -m spacy download en_core_web_lg`

For full requirements (for testing, backend, etc.) run instead of first step: `pip install -r requirements.txt`

## Usage:

```bash
python .\WikiExplorer.py -h
usage: WikiExplorer.py [-h] [--start-page START_PAGE] [--end-page END_PAGE] [--no-nav-boxes] [--hebrew] [--max-length MAX_LENGTH]
                       [--forbidden-page FORBIDDEN_PAGE]

Search a path from one Wikipedia page to another

options:
  -h, --help            show this help message and exit
  --start-page START_PAGE, -s START_PAGE
                        Start page (takes a random page is not set)
  --end-page END_PAGE, -e END_PAGE
                        Target page (takes a random page is not set)
  --no-nav-boxes, -nn   Don't use links in navigation boxes
  --hebrew, -he         In hebrew Wikipedia
  --max-length MAX_LENGTH, -ml MAX_LENGTH
                        Maximum allowed length of path (including start and end page)
  --forbidden-page FORBIDDEN_PAGE, -fp FORBIDDEN_PAGE
                        Forbidden pages to pass through
```

## Website
To run backend: `python app.py` \
(listens on 0.0.0.0:5000)
