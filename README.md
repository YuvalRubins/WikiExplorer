# WikiExplorer
Find a path between two Wikipedia pages

## Requirements

Run:
1) `pip install -r requirements.txt`
1) `python -m spacy download en_core_web_lg`

## Usage:

```bash
python WikiExplorer.py -h
usage: WikiExplorer.py [-h] [--start-page START_PAGE] [--end-page END_PAGE] [--no-nav-boxes]

Search a path from one Wikipedia page to another

options:
  -h, --help            show this help message and exit
  --start-page START_PAGE, -s START_PAGE
                        Start page (takes a random page is not set)
  --end-page END_PAGE, -e END_PAGE
                        Target page (takes a random page is not set)
  --no-nav-boxes, -nn   Don't use links in navigation boxes
```

## Website
To run backend: `python app.py` \
(listens on 0.0.0.0:5000)
