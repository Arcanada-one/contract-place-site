"""Licensing, SEO and search checks for the built site. Usage: check_page.py <public-dir>"""
import json
import re
import sys
from pathlib import Path

ORCID = "0009-0001-2567-4584"
CC_DEED = "https://creativecommons.org/licenses/by/4.0/"
APACHE = "https://www.apache.org/licenses/LICENSE-2.0"
ATTR = "https://github.com/Arcanada-one/knowledge-contract/blob/main/ATTRIBUTION.md"
LOCALES = ("en", "ru", "zh-Hans")


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def check_search(page: str, script: str) -> None:
    """The document-search section and its script: markup present, no third-party script, no unsafe sinks, no credentials or storage."""
    assert re.search(r'<section[^>]*\bid="document-search"', page), "document search section (#document-search) missing"
    form = re.search(r'<form\b[^>]*\bid="search-form"[^>]*>', page)
    assert form and re.search(r"\bhidden\b", form.group(0)), "search form missing or not hidden until JavaScript runs"
    for needle in ('id="search-q"', 'id="search-status"', 'role="status"', 'aria-live="polite"', 'id="search-results"', 'id="search-more"', "<noscript>"):
        assert needle in page, "search markup missing: " + needle
    for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "localStorage", "sessionStorage", "document.cookie", "indexedDB", "sendBeacon", "XMLHttpRequest", "WebSocket"):
        assert bad not in script, "search.js must not use " + bad
    assert "credentials: 'omit'" in script, "search.js must send no credentials"
    assert "referrerPolicy: 'no-referrer'" in script, "search.js must send no referrer"
    hosts = set(re.findall(r"https?://[A-Za-z0-9.-]+", script))
    assert "https://api.contract.place" in hosts, "API origin missing"
    assert not hosts - {"https://api.contract.place", "https://github.com"}, "unexpected hosts in search.js: %r" % sorted(hosts)
    assert "mount" in script and "KcpSearch" in script, "search.js must expose KcpSearch.mount for the single-page app"


def check_head_and_scripts(page: str, where: str) -> None:
    head = re.search(r"<head>(.*?)</head>", page, re.S)
    assert head, where + ": no <head>"
    assert re.search(r'<link rel="license" href="' + re.escape(CC_DEED) + r'">', head.group(1)), where + ": head license link missing"
    assert re.search(r'<link rel="canonical" href="https://contract\.place/', head.group(1)), where + ": canonical link on https://contract.place missing"
    srcs = re.findall(r"<script\b[^>]*\bsrc=\"([^\"]*)\"", page)
    assert [s.split("?")[0] for s in srcs] == ["/content.js", "/search.js", "/app.js"], where + ": unexpected script sources: %r" % srcs
    inline = [m for m in re.findall(r"<script\b([^>]*)>", page) if "src=" not in m and "application/ld+json" not in m]
    assert len(inline) == 1, where + ": exactly one inline script (the theme bootstrap) is allowed, found %d" % len(inline)
    assert not re.search(r"\son[a-z]+\s*=", page, re.I), where + ": inline event handler attributes are not allowed"


def check_footer(page: str, where: str) -> None:
    footer = re.search(r"<footer[^>]*>(.*?)</footer>", page, re.S)
    assert footer, where + ": no <footer>"
    f = footer.group(1)
    text = re.sub(r"<[^>]+>", "", f)
    assert "Credit: Knowledge Contract Arcana," in text and "https://contract.place" in text, where + ": footer credit text missing"
    for url in (CC_DEED, APACHE, ATTR, "https://arcanada.ai"):
        assert 'href="' + url + '"' in f, where + ": footer link missing: " + url


def check_jsonld(page: str) -> None:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert blocks, "no JSON-LD block"
    data = json.loads(blocks[0])
    assert data.get("license") == CC_DEED, "JSON-LD license"
    assert data.get("author", {}).get("sameAs") == "https://orcid.org/" + ORCID, "JSON-LD author.sameAs"
    assert data.get("copyrightHolder", {}).get("name") == "Pavel Valentov", "JSON-LD copyrightHolder"
    assert data.get("name") == "Knowledge Contract Arcana", "JSON-LD name"
    assert data.get("isPartOf", {}).get("url") == "https://arcanada.ai", "JSON-LD isPartOf (Arcanada)"


def check_site(root: Path) -> None:
    pages = ["index.html"] + ["%s/index.html" % l for l in LOCALES] + ["en/research/index.html", "en/research/p09/index.html", "en/search/index.html", "en/about/index.html"]
    for rel in pages:
        page = read(root, rel)
        check_head_and_scripts(page, rel)
        check_footer(page, rel)
    check_jsonld(read(root, "index.html"))
    check_search(read(root, "en/search/index.html"), read(root, "search.js"))

    robots = read(root, "robots.txt")
    assert re.search(r"(?mi)^User-agent:\s*\*\s*$", robots) and "Allow: /" in robots, "robots.txt must allow indexing"
    assert not re.search(r"(?mi)^Disallow:\s*/\s*$", robots), "robots.txt must not disallow the whole site"
    assert "Sitemap: https://contract.place/sitemap.xml" in robots, "robots.txt must point at the sitemap"

    sitemap = read(root, "sitemap.xml")
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    for needed in ("https://contract.place/", "https://contract.place/en/", "https://contract.place/ru/", "https://contract.place/zh-Hans/",
                   "https://contract.place/en/research", "https://contract.place/en/research/p09", "https://contract.place/ru/research/p09",
                   "https://contract.place/en/docs", "https://contract.place/en/search", "https://contract.place/en/journal"):
        assert needed in locs, "sitemap.xml missing " + needed
    assert all(u.startswith("https://contract.place/") for u in locs), "sitemap.xml has a foreign host"
    for u in locs:  # every sitemap URL is a built page
        rel = u[len("https://contract.place/"):].strip("/")
        assert (root / rel / "index.html").is_file(), "sitemap URL without a built page: " + u

    llms = read(root, "llms.txt")
    for needed in ("https://contract.place/en/research", "https://api.contract.place", "https://arcanada.ai", "CC BY 4.0"):
        assert needed in llms, "llms.txt missing " + needed
    assert (root / "favicon.svg").is_file(), "favicon.svg missing"
    notfound = read(root, "404.html")
    assert 'name="robots" content="noindex"' in notfound, "404.html must be noindex"


if __name__ == "__main__":
    check_site(Path(sys.argv[1]))
    print("site checks OK (licensing, SEO, search, robots, sitemap, llms.txt)")
