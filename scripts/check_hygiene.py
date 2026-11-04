"""Public-surface and CSP hygiene of the source and the built site. Usage: check_hygiene.py <repo-root>

1. No private or preview hosts anywhere in public/ and src/ (Google Drive/Docs/accounts, Sites preview domains).
2. The production Content-Security-Policy is `script-src 'self'; style-src 'self'`: nothing inline may run or style.
   No inline <script> without src (JSON-LD data blocks are not executable), no style= attributes, no on*= handlers,
   in public/**/*.html and in the HTML templates inside app.js / search.js.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
FORBIDDEN = ("drive.google.com", "docs.google.com", "accounts.google.com", "chatgpt.site", "lavishwave")
TEXT = {".html", ".js", ".mjs", ".css", ".json", ".md", ".txt", ".xml", ".svg", ".toml", ".yml", ".py"}
errs = []

for top in ("public", "src"):
    for f in sorted((ROOT / top).rglob("*")):
        if not f.is_file() or f.suffix.lower() not in TEXT:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for bad in FORBIDDEN:
            if bad in text:
                errs.append("%s mentions %s" % (f.relative_to(ROOT), bad))

INLINE_SCRIPT = re.compile(r"<script\b([^>]*)>", re.I)
STYLE_ATTR = re.compile(r"""\sstyle\s*=""", re.I)
HANDLER = re.compile(r"""\son[a-z]+\s*=""", re.I)
for f in sorted((ROOT / "public").rglob("*.html")):
    text = f.read_text(encoding="utf-8")
    for attrs in INLINE_SCRIPT.findall(text):
        if "src=" not in attrs and "application/ld+json" not in attrs:
            errs.append("%s: inline <script> (blocked by script-src 'self')" % f.relative_to(ROOT))
    if "<style" in text.lower():
        errs.append("%s: <style> element (blocked by style-src 'self')" % f.relative_to(ROOT))
    if STYLE_ATTR.search(text):
        errs.append("%s: style= attribute (blocked by style-src 'self')" % f.relative_to(ROOT))
    if HANDLER.search(text):
        errs.append("%s: inline event handler attribute" % f.relative_to(ROOT))

for rel in ("src/site/app.js", "src/site/search.js", "src/site/index.html", "src/site/theme.js"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    for pat, what in ((STYLE_ATTR, "style= attribute in a template"), (HANDLER, "inline event handler in a template"),
                      (re.compile(r"setAttribute\(\s*['\"]style['\"]"), "setAttribute('style')"), (re.compile(r"\.cssText\b"), "style.cssText"),
                      (re.compile(r"<style\b", re.I), "<style> in a template"), (re.compile(r"javascript:", re.I), "javascript: URL")):
        if pat.search(text):
            errs.append("%s: %s" % (rel, what))
    if rel.endswith(".html"):
        for attrs in INLINE_SCRIPT.findall(text):
            if "src=" not in attrs and "application/ld+json" not in attrs:
                errs.append("%s: inline <script>" % rel)

if errs:
    print("\n".join(sorted(set(errs))[:60]))
    sys.exit(1)
print("hygiene OK (no private hosts; no inline script/style/handlers under script-src 'self'; style-src 'self')")
