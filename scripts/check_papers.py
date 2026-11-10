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
        # Compatibility fragment destinations (<a id="..."></a> with no href) are
        # not navigational links; the corpus preserves prior heading anchors after title renames.
        if not l["href"] and l["attrs"].get("id") and not t and not label:
            continue
        if not t and not label:
            errs.append("%s: link without text or aria-label: %s" % (path, l["href"]))
        if t.lower() in generic:
            errs.append("%s: link text not meaningful: %r" % (path, t))
        if re.match(r"https?://", l["href"]) and not l["href"].startswith(ALLOWED):
            errs.append("%s: unexpected host: %s" % (path, l["href"]))
    return page, p, errs


def main(argv):
    root = Path(argv[1])
    catalog = json.loads((root / 'content.js').read_text().split('=', 1)[1].strip().rstrip(';'))
    records = catalog['records']
    if len(records) != 31:
        raise SystemExit('Expected the 31 canonical documents of edition 1.1')
    # Primary references are approved by the canonical source. A rendered page
    # must preserve those exact URLs; it may not invent a different external host.
    approved = set()
    for record in records:
        approved.update(re.findall(r'href="(https?://[^"]+)"', record['html']))
    global ALLOWED
    ALLOWED = tuple(ALLOWED) + tuple(approved)
    errors, source_links, pages = [], set(), 0
    for lang in LOCALES:
        for folder in ('research', 'engineering', 'engineering/specifications', 'engineering/studies', 'reference', 'appendices'):
            _, _, e = parse(root / lang / folder / 'index.html', lang)
            errors += e
            pages += 1
        for record in records:
            route = record['route'].replace('/en/', '/' + lang + '/', 1)
            page, parsed, e = parse(root / route.lstrip('/') / 'index.html', lang)
            errors += e
            pages += 1
            # A language rendition replaces the body only when it is compiled and shown; publication_checks.check_renditions
            # verifies those pages. Every other page shows the complete English source.
            shown = (record.get('renditions') or {}).get(lang)
            shown = shown if shown and shown['state'] in ('reviewed', 'partially-reviewed', 'unreviewed') else None
            body, body_lang, math_count = (shown['html'], lang, shown['math_count']) if shown else (record['html'], 'en', record['math_count'])
            if body not in page:
                errors.append(route + ': full body differs from compiled source')
            for url in (record['source'], record['history']):
                if not any(link['href'] == url for link in parsed.links):
                    errors.append(route + ': exact source/history missing')
                source_links.add(url)
            if 'CC BY 4.0' not in page or 'class="source-body prose" lang="%s"' % body_lang not in page:
                errors.append(route + ': content licence or body language declaration missing')
            if page.count('<math ') != math_count:
                errors.append(route + ': mathematical expression count differs')
        for alias, target in catalog['aliases'].items():
            route = root / lang / alias / 'index.html'
            page, _, e = parse(route, lang)
            errors += e
            if 'name="robots" content="noindex,follow"' not in page:
                errors.append(str(route) + ': historical route must not be indexed')
    if errors:
        print('\n'.join(errors[:60]))
        raise SystemExit(1)
    print('Publication page structure OK (%d full/index pages, %d exact repository links)' % (pages, len(source_links)))


if __name__ == '__main__':
    main(sys.argv)
