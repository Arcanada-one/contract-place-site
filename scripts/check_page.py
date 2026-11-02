"""Licensing checks for the published page. Usage: check_page.py <index.html>"""
import json
import re
import sys

ORCID = "0009-0001-2567-4584"
CC_DEED = "https://creativecommons.org/licenses/by/4.0/"
APACHE = "https://www.apache.org/licenses/LICENSE-2.0"
ATTR = "https://github.com/Arcanada-one/knowledge-contract/blob/main/ATTRIBUTION.md"
FOOTER_TEXT = "Credit: Knowledge Contract Arcana,"


def check_search(page: str, script: str) -> None:
    """The search control and its script: markup present, no inline code, no third-party script, no unsafe sinks, no credentials or storage."""
    assert re.search(r'<section[^>]*\bid="search"', page), "search section (#search) missing"
    form = re.search(r'<form\b[^>]*\bid="search-form"[^>]*>', page)
    assert form and re.search(r"\bhidden\b", form.group(0)), "search form missing or not hidden until JavaScript runs"
    for needle in ('id="search-q"', 'id="search-status"', 'role="status"', 'aria-live="polite"', 'id="search-results"', 'id="search-more"', "<noscript>"):
        assert needle in page, "search markup missing: " + needle
    head = re.search(r"<head>(.*?)</head>", page, re.S).group(1)
    assert '<script src="/search.js" defer></script>' in head, "search.js must be one deferred same-origin script in <head>"
    srcs = re.findall(r"<script\b[^>]*\bsrc=\"([^\"]*)\"", page)
    assert srcs == ["/search.js"], "unexpected script sources: %r" % srcs
    inline = [m for m in re.findall(r"<script\b([^>]*)>", page) if "src=" not in m and "application/ld+json" not in m]
    assert not inline, "inline scripts are not allowed"
    assert not re.search(r"\son[a-z]+\s*=", page, re.I), "inline event handler attributes are not allowed"
    for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "localStorage", "sessionStorage", "document.cookie", "indexedDB", "sendBeacon", "XMLHttpRequest", "WebSocket"):
        assert bad not in script, "search.js must not use " + bad
    assert "credentials: 'omit'" in script, "search.js must send no credentials"
    assert "referrerPolicy: 'no-referrer'" in script, "search.js must send no referrer"
    assert re.findall(r"https?://[A-Za-z0-9.-]+", script).count("https://api.contract.place") >= 1, "API origin missing"
    others = {h for h in re.findall(r"https?://[A-Za-z0-9.-]+", script)} - {"https://api.contract.place", "https://github.com"}
    assert not others, "unexpected hosts in search.js: %r" % sorted(others)


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

    purpose = re.search(r'<section[^>]*\bid="purpose"[^>]*>(.*?)</section>', page, re.S)
    assert purpose, "purpose section (#purpose) missing"
    ptext = re.sub(r"<[^>]+>", " ", purpose.group(1))
    assert "Working today" in ptext, "purpose: 'Working today' marker missing"
    assert "Planned" in ptext, "purpose: 'Planned' marker missing"

    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert blocks, "no JSON-LD block"
    data = json.loads(blocks[0])
    assert data.get("license") == CC_DEED, "JSON-LD license"
    assert data.get("author", {}).get("sameAs") == "https://orcid.org/" + ORCID, "JSON-LD author.sameAs"
    assert data.get("copyrightHolder", {}).get("name") == "Pavel Valentov", "JSON-LD copyrightHolder"


if __name__ == "__main__":
    page_text = open(sys.argv[1], encoding="utf-8").read()
    check(page_text)
    print("page licensing checks OK")
    if len(sys.argv) > 2:
        check_search(page_text, open(sys.argv[2], encoding="utf-8").read())
        print("search page checks OK")
