"""Licensing checks for the published page. Usage: check_page.py <index.html>"""
import json
import re
import sys

ORCID = "0009-0001-2567-4584"
CC_DEED = "https://creativecommons.org/licenses/by/4.0/"
APACHE = "https://www.apache.org/licenses/LICENSE-2.0"
ATTR = "https://github.com/Arcanada-one/knowledge-contract/blob/main/ATTRIBUTION.md"
FOOTER_TEXT = "Credit: Knowledge Contract Arcana,"


def check(page: str) -> None:
    head = re.search(r"<head>(.*?)</head>", page, re.S)
    assert head, "no <head>"
    assert re.search(r'<link\s+rel="license"\s+href="' + re.escape(CC_DEED) + r'"\s*>', head.group(1)), "head license link missing"

    footer = re.search(r"<footer>(.*?)</footer>", page, re.S)
    assert footer, "no <footer>"
    f = footer.group(1)
    text = re.sub(r"<[^>]+>", "", f)
    assert "Content CC BY 4.0, code Apache-2.0." in text, "footer licence text missing"
    assert FOOTER_TEXT in text and "https://contract.place" in text, "footer credit text missing"
    for url in (CC_DEED, APACHE, ATTR):
        assert 'href="' + url + '"' in f, "footer link missing: " + url

    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert blocks, "no JSON-LD block"
    data = json.loads(blocks[0])
    assert data.get("license") == CC_DEED, "JSON-LD license"
    assert data.get("author", {}).get("sameAs") == "https://orcid.org/" + ORCID, "JSON-LD author.sameAs"
    assert data.get("copyrightHolder", {}).get("name") == "Pavel Valentov", "JSON-LD copyrightHolder"


if __name__ == "__main__":
    check(open(sys.argv[1], encoding="utf-8").read())
    print("page licensing checks OK")
