"""Build index.html (a full HTML document for local use) from page.html.

page.html holds the page body only, because that is the format the published
Claude artifact uses. Edit page.html, then run:  python build_index.py
"""
from pathlib import Path
here = Path(__file__).parent
body = (here / 'page.html').read_text(encoding='utf-8')
(here / 'index.html').write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '</head>\n<body>\n' + body + '\n</body>\n</html>\n', encoding='utf-8')
print('index.html written')
