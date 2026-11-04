"""Static checks for the paper and specification pages of the built site.

Usage: check_papers.py <public-dir> [--tree <file>]
  --tree: a list of repository paths (output of `git ls-tree -r --name-only main` in
          Arcanada-one/knowledge-contract); every link of the pages into that
          repository must point at a path in the list.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

KC = "https://github.com/Arcanada-one/knowledge-contract"
VOID = {"meta", "link", "br", "input", "img", "hr", "path", "circle"}
SVG = {"svg", "path", "circle", "g", "rect", "use"}
LOCALES = ("en", "ru", "zh-Hans")
ALLOWED = ("https://github.com/Arcanada-one/", "https://arcanada.ai", "https://creativecommons.org/", "https://www.apache.org/", "https://orcid.org/", "https://api.contract.place/", "https://contract.place")


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.links, self.ids, self.headings = [], [], [], [], []
        self.cur_a, self.in_h = None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag not in VOID:
            self.stack.append(tag)
        if tag == "a":
            self.cur_a = {"href": a.get("href", ""), "text": "", "attrs": a}
        if re.fullmatch(r"h[1-6]", tag):
            self.in_h = [int(tag[1]), ""]
        if tag in ("script", "img", "iframe") and re.match(r"https?://", a.get("src", "")):
            self.errors.append("external resource: %s %s" % (tag, a["src"]))
        if tag == "link" and a.get("rel") == "stylesheet" and re.match(r"https?://", a.get("href", "")):
            self.errors.append("external stylesheet")

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("bad nesting at </%s>, open: %s" % (tag, self.stack[-3:]))
            if tag in self.stack:
                while self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()
        if tag == "a" and self.cur_a is not None:
            self.links.append(self.cur_a)
            self.cur_a = None
        if self.in_h and tag == "h%d" % self.in_h[0]:
            self.headings.append(tuple(self.in_h))
            self.in_h = None

    def handle_data(self, d):
        if self.cur_a is not None:
            self.cur_a["text"] += d
        if self.in_h:
            self.in_h[1] += d


def parse(path: Path, lang: str):
    page = path.read_text(encoding="utf-8")
    p = P()
    p.feed(page)
    p.close()
    errs = ["%s: %s" % (path, e) for e in p.errors]
    if p.stack:
        errs.append("%s: unclosed tags: %r" % (path, p.stack))
    if len(p.ids) != len(set(p.ids)):
        errs.append("%s: duplicate ids" % path)
    if '<html lang="%s">' % lang not in page:
        errs.append("%s: html lang is not %s" % (path, lang))
    lv = [h[0] for h in p.headings]
    if lv.count(1) != 1:
        errs.append("%s: need exactly one h1, found %d" % (path, lv.count(1)))
    for a, b in zip(lv, lv[1:]):
        if b > a + 1:
            errs.append("%s: heading level skipped h%d -> h%d" % (path, a, b))
    if re.search(r"\son[a-z]+\s*=", page, re.I):
        errs.append("%s: inline event handler" % path)
    generic = {"click here", "here", "link", "read more", "more"}
    for l in p.links:
        t = l["text"].strip()
        label = l["attrs"].get("aria-label", "").strip()
        if not t and not label:
            errs.append("%s: link without text or aria-label: %s" % (path, l["href"]))
        if t.lower() in generic:
            errs.append("%s: link text not meaningful: %r" % (path, t))
        if re.match(r"https?://", l["href"]) and not l["href"].startswith(ALLOWED):
            errs.append("%s: unexpected host: %s" % (path, l["href"]))
    return page, p, errs


def main(argv):
    root = Path(argv[1])
    tree = None
    if "--tree" in argv:
        tree = set(Path(argv[argv.index("--tree") + 1]).read_text(encoding="utf-8").split("\n"))
    catalog = json.loads((root / "content.js").read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
    papers = [r for r in catalog["records"] if r["kind"] == "paper"]
    specs = [r for r in catalog["records"] if r["kind"] == "spec"]
    errs = []
    if len(papers) != 14 or len(specs) != 10:
        errs.append("catalog: expected 14 papers and 10 specifications, got %d and %d" % (len(papers), len(specs)))
    kc_links = set()
    pages = 0
    for lang in LOCALES:
        for kind, folder, recs in (("paper", "research", papers), ("spec", "docs", specs)):
            index = root / lang / folder / "index.html"
            page, p, e = parse(index, lang)
            errs += e
            pages += 1
            if kind == "paper":
                cards = {m for m in re.findall(r'href="/%s/research/(p\d\d)"' % lang, page)}
                if cards != {r["id"] for r in papers}:
                    errs.append("%s: research index does not list all 14 papers (found %d)" % (index, len(cards)))
                text = re.sub(r"<[^>]+>", " ", page)
                if lang == "en" and "Independent semantic review has not been performed" not in text and "scientific draft" not in text.lower():
                    errs.append("%s: scientific-draft status text missing" % index)
            for r in recs:
                path = root / lang / folder / r["id"] / "index.html"
                page, p, e = parse(path, lang)
                errs += e
                pages += 1
                srcs = [l for l in p.links if l["href"] == r["source"]]
                rus = [l for l in p.links if l["href"] == r["russian"]]
                if not srcs or not rus:
                    errs.append("%s: English entry page or Russian original link missing" % path)
                if not any(l["attrs"].get("hreflang") == "ru" for l in rus):
                    errs.append("%s: no Russian original link with hreflang=ru" % path)
                if "CC BY 4.0" not in page:
                    errs.append("%s: CC BY 4.0 credit missing" % path)
                kc_links.add(r["source"])
                kc_links.add(r["russian"])
    zh = (root / "zh-Hans" / "about" / "index.html").read_text(encoding="utf-8")
    if re.search(r"(?i)native (editorial )?review(ed)?|母语审校已完成", zh):
        errs.append("zh-Hans must not claim native editorial review")
    if tree is not None:
        dead = 0
        for href in sorted(kc_links):
            path = href[len(KC + "/blob/main/"):]
            if path not in tree:
                dead += 1
                errs.append("dead link: " + path)
        print("knowledge-contract links checked: %d, dead: %d" % (len(kc_links), dead))
    if errs:
        print("\n".join(errs[:60]))
        sys.exit(1)
    print("paper/spec page checks OK (%d pages, %d repository links)" % (pages, len(kc_links)))


main(sys.argv)
