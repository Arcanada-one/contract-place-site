"""Public-surface and CSP hygiene of the source and the built site. Usage: check_hygiene.py <repo-root>

1. No private or preview hosts anywhere in public/ and src/ (Google Drive/Docs/accounts, Sites preview domains).
2. The production Content-Security-Policy is `script-src 'self' https://www.googletagmanager.com; style-src 'self'`:
   nothing inline may run or style; the Google tag host is the only remote script source.
   No inline <script> without src (JSON-LD and the compiler's rendition-facts data block are not executable),
   no style= attributes, no on*= handlers, in public/**/*.html and in the HTML templates inside app.js / search.js.
"""
import re
import sys
from pathlib import Path

# Attribute parser for <script ...> tags: name=value with double, single, or bare values.
_SCRIPT_ATTR = re.compile(r"""([^\s=]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)


def script_attr_map(attrs: str) -> dict:
    """Parse a <script> attribute string into a lower-cased name -> value map."""
    out = {}
    for match in _SCRIPT_ATTR.finditer(attrs or ""):
        key = match.group(1).lower()
        value = match.group(2) if match.group(2) is not None else (match.group(3) if match.group(3) is not None else match.group(4))
        out[key] = value
    return out


def is_allowed_data_script(attrs: str) -> bool:
    """Exempt only non-executable data blocks the compiler emits.

    - type must equal application/ld+json (JSON-LD), or
    - type must equal application/json AND class must equal rendition-facts
      (exact attribute values; substring matches such as data-x="application/json"
      or type="application/json+x" are not exempt).
    """
    amap = script_attr_map(attrs)
    typ = amap.get("type")
    if typ == "application/ld+json":
        return True
    if typ == "application/json" and amap.get("class") == "rendition-facts":
        return True
    return False


def is_inline_script_violation(attrs: str) -> bool:
    """True when a <script> opening tag is an inline executable script banned by CSP."""
    amap = script_attr_map(attrs)
    if "src" in amap:
        return False
    return not is_allowed_data_script(attrs)


if __name__ == "__main__":
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
            # JSON-LD and rendition-facts are data blocks, not executable script (CSP script-src 'self').
            if is_inline_script_violation(attrs):
                errs.append("%s: inline <script> (blocked by script-src 'self')" % f.relative_to(ROOT))
        if "<style" in text.lower():
            errs.append("%s: <style> element (blocked by style-src 'self')" % f.relative_to(ROOT))
        if STYLE_ATTR.search(text):
            errs.append("%s: style= attribute (blocked by style-src 'self')" % f.relative_to(ROOT))
        if HANDLER.search(text):
            errs.append("%s: inline event handler attribute" % f.relative_to(ROOT))

    for rel in ("src/site/app.js", "src/site/search.js", "src/site/analytics.js", "src/site/index.html", "src/site/theme.js"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for pat, what in ((STYLE_ATTR, "style= attribute in a template"), (HANDLER, "inline event handler in a template"),
                          (re.compile(r"setAttribute\(\s*['\"]style['\"]"), "setAttribute('style')"), (re.compile(r"\.cssText\b"), "style.cssText"),
                          (re.compile(r"<style\b", re.I), "<style> in a template"), (re.compile(r"javascript:", re.I), "javascript: URL")):
            if pat.search(text):
                errs.append("%s: %s" % (rel, what))
        if rel.endswith(".html"):
            for attrs in INLINE_SCRIPT.findall(text):
                if is_inline_script_violation(attrs):
                    errs.append("%s: inline <script>" % rel)

    if errs:
        print("\n".join(sorted(set(errs))[:60]))
        sys.exit(1)
    print("hygiene OK (no private hosts; no inline script/style/handlers under script-src 'self' https://www.googletagmanager.com; style-src 'self')")
