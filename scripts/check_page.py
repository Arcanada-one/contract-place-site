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
LAB_ROUTES = ("lab/knowledge-journey",)


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
    css = (Path(__file__).resolve().parent.parent / "public" / "style.css").read_text(encoding="utf-8")
    assert "[hidden]{display:none!important}" in css, "style.css must keep [hidden] hidden (.button sets display and would show a hidden More button)"
    assert re.search(r"var inflight = null;[^\n]*\n\s*var serial = 0;\n\n\s*function mount", script), "inflight/serial must be shared by all mounts"


def expected_script_sources(page: str) -> list[str]:
    """Base reader scripts; renditions.js is present only when the build compiled a sidecar."""
    sources = ["/theme.js", "/content.js", "/search.js", "/app.js"]
    if re.search(r'<script\b[^>]*\bsrc="/renditions\.js', page):
        sources.append("/renditions.js")
    return sources


def check_head_and_scripts(page: str, where: str) -> None:
    head = re.search(r"<head>(.*?)</head>", page, re.S)
    assert head, where + ": no <head>"
    assert re.search(r'<link rel="license" href="' + re.escape(CC_DEED) + r'">', head.group(1)), where + ": head license link missing"
    assert re.search(r'<link rel="canonical" href="https://contract\.place/', head.group(1)), where + ": canonical link on https://contract.place missing"
    srcs = re.findall(r"<script\b[^>]*\bsrc=\"([^\"]*)\"", page)
    assert [s.split("?")[0] for s in srcs] == expected_script_sources(page), where + ": unexpected script sources: %r" % srcs
    # theme.js is synchronous (no defer/async) and comes before the stylesheet so the saved theme is applied before first paint
    assert re.search(r'<script src="/theme\.js[^"]*"></script><link rel="stylesheet"', head.group(1)), where + ": theme.js must be a synchronous script before the stylesheet"
    inline = [m for m in re.findall(r"<script\b([^>]*)>", page) if "src=" not in m and "application/ld+json" not in m and "application/json" not in m]
    assert not inline, where + ": inline scripts are blocked by the production CSP (script-src 'self')"
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


NOINDEX_ROUTES = ("wiki/knowledge-contract", "wiki/provenance", "wiki/versioned-knowledge", "journal/building-a-place", "docs/model", "references",
                  "research/anthropic", "research/deepmind", "research/hugging-face", "research/mcp", "research/stripe", "research/supabase")


def url_target(root: Path, url: str) -> Path:
    path = url[len("https://contract.place/"):]
    assert path == "" or path.endswith("/") or "." in path.rsplit("/", 1)[-1], "URL must end with / or a file name: " + url
    return root / path / "index.html" if (path == "" or path.endswith("/")) else root / path


RENDITION_INDEXED = ("reviewed", "partially-reviewed")


def locale_counts_for_indexing(catalog: dict, locale: str, bare: str) -> bool:
    """English always counts; a translation counts only with a bound reviewed/partially-reviewed state (C5)."""
    if locale == "en" or not bare:
        return True
    if not catalog.get("renditions_source") and not any(r.get("renditions") for r in catalog.get("records", [])):
        return True
    record = next((r for r in catalog.get("records", []) if r.get("route") == "/en/" + bare + "/"), None)
    if not record or not record.get("renditions"):
        return True
    state = (record["renditions"].get(locale) or {}).get("state", "missing")
    return state in RENDITION_INDEXED


def check_urls(root: Path) -> None:
    """Every sitemap URL, canonical and hreflang URL ends with / (or a file name) and maps to a built file; indexing decisions hold."""
    locs = re.findall(r"<loc>([^<]+)</loc>", read(root, "sitemap.xml"))
    for u in locs:
        assert url_target(root, u).is_file(), "sitemap URL does not map to a built file: " + u
    listed = set(locs)
    catalog = json.loads((root / "content.js").read_text().split("=", 1)[1].strip().rstrip(";"))
    aliases = catalog["aliases"]
    for page in sorted(root.rglob("index.html")) + [root / "404.html"]:
        rel = page.relative_to(root).as_posix()
        text = page.read_text(encoding="utf-8")
        head = re.search(r"<head>(.*?)</head>", text, re.S).group(1)
        urls = re.findall(r'<link rel="(?:canonical|alternate)"[^>]*\bhref="(https://contract\.place/[^"]*)"', head)
        route = rel[:-len("index.html")].strip("/")
        parts = route.split("/", 1)
        locale = parts[0] if parts and parts[0] in LOCALES else ""
        bare = parts[1] if len(parts) == 2 and parts[0] in LOCALES else ""
        fallback_noindex = bool(locale and bare and not locale_counts_for_indexing(catalog, locale, bare))
        if rel == "404.html" or bare in NOINDEX_ROUTES or bare in aliases or route in catalog.get("reader_aliases", {}) or fallback_noindex:
            assert 'name="robots" content="noindex' in head, rel + ": must be noindex"
            assert not urls, rel + ": noindex page must not carry canonical/hreflang"
            assert ("https://contract.place/" + route + "/") not in listed, rel + ": noindex page is in the sitemap"
            continue
        assert urls, rel + ": no canonical/hreflang"
        for u in urls:
            assert url_target(root, u).is_file(), rel + ": canonical/hreflang does not map to a built file: " + u
        if bare in LAB_ROUTES:
            assert 'name="robots" content="noindex,follow"' in head, rel + ": lab must be noindex"
            assert ("https://contract.place/" + route + "/") not in listed, rel + ": lab must be absent from sitemap"
        elif rel != "index.html":
            assert ("https://contract.place/" + route + "/") in listed, rel + ": indexable page missing from sitemap.xml"


def check_zh_notice(root: Path) -> None:
    for rel in ("zh-Hans/index.html", "zh-Hans/research/index.html", "zh-Hans/about/index.html"):
        text = re.sub(r"<[^>]+>", "", read(root, rel))
        assert "中文界面尚未经过母语编辑审校" in text, rel + ": zh-Hans pages must say the Chinese interface has no native editorial review"
    for rel in ("en/index.html", "ru/index.html"):
        assert "中文界面尚未经过母语编辑审校" not in read(root, rel)


def check_laboratory(root: Path) -> None:
    """Public shells must not look like an executing or authorized run."""
    for locale in LOCALES:
        where = locale + "/lab/knowledge-journey/index.html"
        page = read(root, where)
        check_head_and_scripts(page, where)
        main = re.search(r'<main\b[^>]*>(.*?)</main>', page, re.S).group(1)
        assert 'data-live-lab-state="unconnected"' in main, where + ": unconnected state missing"
        assert re.search(r'<fieldset\b[^>]*\bdisabled\b', main), where + ": controls must be disabled"
        assert re.search(r'<button\b[^>]*type="button"[^>]*\bdisabled\b', main), where + ": start must be disabled"
        assert re.search(r'<input\b[^>]*type="file"[^>]*\bdisabled\b', main), where + ": upload must be disabled"
        assert '<form' not in main, where + ": unconnected shell must not submit"
        for region in ("graph", "timeline", "inspector"):
            assert 'data-live-lab-region="' + region + '"' in main, where + ": missing region " + region
        assert 'role="status"' in main and 'aria-live="polite"' in main, where + ": accessible state missing"
        footer = re.search(r'<footer\b[^>]*>(.*?)</footer>', page, re.S).group(1)
        assert 'href="/' + locale + '/lab/knowledge-journey/"' in footer, where + ": footer link missing"
        header = re.search(r'<header\b[^>]*>(.*?)</header>', page, re.S).group(1)
        assert '/lab/knowledge-journey' not in header, where + ": lab must not enter primary navigation"
        assert '<meta name="robots" content="noindex,follow">' in page, where + ": lab must be noindex"
        assert '<meta name="referrer" content="no-referrer">' in page, where + ": lab selection must not be a referrer"
        for other in LOCALES:
            assert 'hreflang="' + other + '" href="https://contract.place/' + other + '/lab/knowledge-journey/"' in page, where + ": reciprocal locale metadata missing"


def check_site(root: Path) -> None:
    check_laboratory(root)
    pages = ["index.html"] + ["%s/index.html" % l for l in LOCALES] + ["en/research/index.html", "en/science/controlled-knowledge-reuse/index.html", "en/search/index.html", "en/about/index.html"]
    for rel in pages:
        page = read(root, rel)
        check_head_and_scripts(page, rel)
        check_footer(page, rel)
    check_jsonld(read(root, "index.html"))
    check_search(read(root, "en/search/index.html"), read(root, "search.js"))
    check_urls(root)
    check_zh_notice(root)

    robots = read(root, "robots.txt")
    assert re.search(r"(?mi)^User-agent:\s*\*\s*$", robots) and "Allow: /" in robots, "robots.txt must allow indexing"
    assert not re.search(r"(?mi)^Disallow:\s*/\s*$", robots), "robots.txt must not disallow the whole site"
    assert "Sitemap: https://contract.place/sitemap.xml" in robots, "robots.txt must point at the sitemap"

    sitemap = read(root, "sitemap.xml")
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    for needed in ("https://contract.place/", "https://contract.place/en/", "https://contract.place/ru/", "https://contract.place/zh-Hans/",
                   "https://contract.place/en/research/", "https://contract.place/en/science/controlled-knowledge-reuse/",
                   "https://contract.place/ru/engineering/studies/dependency-closure-and-package-delivery/",
                   "https://contract.place/zh-Hans/engineering/studies/dependency-closure-and-package-delivery/",
                   "https://contract.place/en/docs/", "https://contract.place/en/search/", "https://contract.place/en/journal/"):
        assert needed in locs, "sitemap.xml missing " + needed
    # C5: English-fallback locales of works without a counting review stay out of the sitemap.
    assert "https://contract.place/ru/science/controlled-knowledge-reuse/" not in locs, "unreviewed/missing locale must not be sitemap-listed"
    assert all(u.startswith("https://contract.place/") for u in locs), "sitemap.xml has a foreign host"

    llms = read(root, "llms.txt")
    for needed in ("https://contract.place/en/research/", "https://api.contract.place", "https://arcanada.ai", "CC BY 4.0"):
        assert needed in llms, "llms.txt missing " + needed
    assert (root / "favicon.svg").is_file(), "favicon.svg missing"
    notfound = read(root, "404.html")
    assert 'name="robots" content="noindex"' in notfound, "404.html must be noindex"


if __name__ == "__main__":
    check_site(Path(sys.argv[1]))
    print("site checks OK (licensing, SEO, search, robots, sitemap, llms.txt)")
