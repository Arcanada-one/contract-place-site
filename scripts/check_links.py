"""Every internal link and asset reference in the built site resolves to a file. Usage: check_links.py <public-dir> [--external]

--external additionally prints the distinct external URLs (for a separate reachability run); it does no network access itself.
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

root = Path(sys.argv[1]).resolve()
attr = re.compile(r'\b(?:href|src)="([^"]*)"')
bad, checked, external = [], 0, set()


def resolves(path: str) -> bool:
    p = root / unquote(path.lstrip("/"))
    return p.is_file() or (p.is_dir() and (p / "index.html").is_file())


for page in sorted(root.rglob("*.html")):
    text = page.read_text(encoding="utf-8")
    ids = set(re.findall(r'\bid="([^"]+)"', text))
    for raw in attr.findall(text):
        if not raw or raw.startswith(("mailto:", "javascript:", "data:")):
            continue
        u = urlparse(raw)
        if u.scheme in ("http", "https"):
            if u.netloc == "contract.place":
                checked += 1
                if not resolves(u.path or "/"):
                    bad.append("%s -> %s" % (page.relative_to(root), raw))
                elif (root / unquote((u.path or "/").lstrip("/"))).is_dir() and not (u.path or "/").endswith("/"):
                    bad.append("%s -> %s (directory route without trailing slash)" % (page.relative_to(root), raw))
            else:
                external.add(raw.split("#")[0])
            continue
        checked += 1
        if u.path and not resolves(u.path):
            bad.append("%s -> %s" % (page.relative_to(root), raw))
        elif u.path and (root / unquote(u.path.lstrip("/"))).is_dir() and not u.path.endswith("/"):
            bad.append("%s -> %s (directory route without trailing slash: the host answers 301)" % (page.relative_to(root), raw))
        # hash targets inside the same page are checked only for links without a path
        elif not u.path and u.fragment and u.fragment not in ids:
            bad.append("%s -> #%s (no such id)" % (page.relative_to(root), u.fragment))

if "--external" in sys.argv:
    print("\n".join(sorted(external)))
    sys.exit(0)
if bad:
    print("\n".join(sorted(set(bad))[:80]))
    print("broken internal references: %d of %d checked" % (len(set(bad)), checked))
    sys.exit(1)
print("internal links OK (%d checked, %d external URLs not fetched)" % (checked, len(external)))
