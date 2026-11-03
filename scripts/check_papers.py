"""Static checks for the Papers section of the published page.

Usage: check_papers.py <index.html> [--tree <file>]
  --tree: a list of repository paths (output of `git ls-tree -r --name-only main` in
          Arcanada-one/knowledge-contract); every link of the page into that
          repository must point at a path in the list.
"""
import re
import sys
from html.parser import HTMLParser

KC = "https://github.com/Arcanada-one/knowledge-contract"
VOID = {"meta", "link", "br", "input", "img", "hr"}


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.links, self.ids = [], [], [], []
        self.headings, self.cur_a = [], None
        self.in_h = None

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
        for k in ("src", "href"):
            v = a.get(k)
            if v and tag in ("script", "img", "iframe") and re.match(r"https?://", v):
                self.errors.append("external resource: %s %s" % (tag, v))
        if tag == "link" and a.get("rel") == "stylesheet" and re.match(r"https?://", a.get("href", "")):
            self.errors.append("external stylesheet")

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


def main(argv):
    page = open(argv[1], encoding="utf-8").read()
    tree = None
    if "--tree" in argv:
        tree = set(open(argv[argv.index("--tree") + 1], encoding="utf-8").read().split("\n"))
    p = P()
    p.feed(page)
    p.close()
    errs = list(p.errors)
    if p.stack:
        errs.append("unclosed tags: %r" % p.stack)
    if len(p.ids) != len(set(p.ids)):
        errs.append("duplicate ids")
    if not re.search(r'<html lang="en">', page):
        errs.append("html lang missing")
    lv = [h[0] for h in p.headings]
    if lv.count(1) != 1:
        errs.append("need exactly one h1")
    for a, b in zip(lv, lv[1:]):
        if b > a + 1:
            errs.append("heading level skipped: h%d -> h%d" % (a, b))
    if re.search(r"<style\b|\sstyle\s*=", page, re.I):
        errs.append("inline style")
    if re.search(r"\son[a-z]+\s*=", page, re.I):
        errs.append("inline event handler")
    sec = re.search(r'<section[^>]*\bid="papers"[^>]*aria-labelledby="papers-title"[^>]*>(.*?)</section>', page, re.S)
    sec_html = sec.group(1) if sec else ""
    if not sec:
        errs.append("papers section missing")
    text = re.sub(r"<[^>]+>", " ", sec_html)
    for need in ("scientific drafts", "late research synthesis is still open", "Independent semantic review has not been performed", "Updated: 2026-11-03", "CC BY 4.0", "not translations"):
        if need not in text:
            errs.append("status text missing: " + need)
    if 'href="#papers"' not in page:
        errs.append("nav link to #papers missing")
    seclinks = [l for l in p.links if l["href"].startswith(KC + "/blob/main/")]
    papers = [l for l in seclinks if re.search(r"/blob/main/papers/(ru/)?P\d\d_", l["href"])]
    en = [l for l in papers if "/papers/ru/" not in l["href"]]
    ru = [l for l in papers if "/papers/ru/" in l["href"]]
    if len(en) != 14 or len(ru) != 14:
        errs.append("expected 14 + 14 paper links, got %d + %d" % (len(en), len(ru)))
    for l in ru:
        if l["attrs"].get("hreflang") != "ru":
            errs.append("Russian link without hreflang: " + l["href"])
    generic = {"click here", "here", "link", "read more", "more"}
    allowed = ("https://github.com/Arcanada-one/", "https://arcanada.ai/", "https://creativecommons.org/", "https://www.apache.org/", "https://orcid.org/", "https://api.contract.place/", "https://contract.place")
    for l in p.links:
        t = l["text"].strip()
        if not t or t.lower() in generic:
            errs.append("link text not meaningful: %r %s" % (t, l["href"]))
        if re.match(r"https?://", l["href"]) and not l["href"].startswith(allowed):
            errs.append("unexpected host: " + l["href"])
    if re.search(r"[Ѐ-ӿ]", page):
        errs.append("Cyrillic text present: needs lang=ru markup")
    for h in re.findall(r'href="(https?://[^"]+)"', sec_html):
        if not h.startswith("https://github.com/"):
            errs.append("non-github link in papers section: " + h)
    if tree is not None:
        dead = checked = 0
        for l in seclinks:
            path = l["href"][len(KC + "/blob/main/"):]
            checked += 1
            if path not in tree:
                dead += 1
                errs.append("dead link: " + path)
        linked = {l["href"] for l in seclinks}
        for f in sorted(x for x in tree if re.fullmatch(r"papers/(ru/)?P\d\d_[a-z_]+\.md", x)):
            if KC + "/blob/main/" + f not in linked:
                errs.append("paper in tree not linked: " + f)
        print("knowledge-contract links checked: %d, dead: %d" % (checked, dead))
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    print("papers section checks OK (%d links in page)" % len(p.links))


main(sys.argv)
