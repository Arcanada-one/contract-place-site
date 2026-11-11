#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Read the served site back and compare it byte for byte with the build.

Deploy reports success when files are uploaded, not when the served site equals
the build. For every route this fetches the page anonymously with a cache-busting
query, removes only the Cloudflare Web Analytics injection and compares the bytes
with the local file. Mismatching routes are retried as a set for a bounded window
to absorb edge propagation. Exit 0 only if every route is IDENTICAL.

Usage: readback_served.py --publish-dir public --base-url https://contract.place
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "contract-place-readback/1.0 (+https://contract.place)"
# The only normalisation: the one Web Analytics tag Cloudflare injects at the edge
# (only for requests that send Accept: text/html). Anchored full-tag permitlist: same
# attributes in the same order, fixed origin and path prefix, empty body. Version and
# token vary, so only their character classes are fixed.
ANALYTICS = re.compile(
    rb'<script type="module" '
    rb'src="https://static\.cloudflareinsights\.com/beacon\.min\.js/v[0-9a-f]+" '
    rb'integrity="sha512-[A-Za-z0-9+/]+={0,2}" '
    rb"data-cf-beacon='\{\"version\":\"[0-9A-Za-z.\-]+\",\"token\":\"[0-9a-f]{32}\","
    rb"\"r\":[0-9]+,\"spa\":[0-9]+\}' "
    rb'crossorigin="anonymous"></script>')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: the requested route itself must serve the bytes."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def route_for(publish_dir: Path, file: Path) -> str:
    rel = file.relative_to(publish_dir).as_posix()
    if rel == "index.html":
        return "/"
    return "/" + rel[: -len("index.html")]


def default_routes(publish_dir: Path) -> list[str]:
    return sorted(route_for(publish_dir, f) for f in publish_dir.rglob("index.html"))


def local_file(publish_dir: Path, route: str) -> Path:
    rel = route.lstrip("/")
    if route.endswith("/"):
        rel += "index.html"
    return publish_dir / rel


def normalise(body: bytes) -> bytes:
    return ANALYTICS.sub(b"", body, count=1)  # at most one tag per page


def fetch(base_url: str, route: str, run_id: str, timeout: float) -> bytes:
    url = base_url.rstrip("/") + urllib.parse.quote(route, safe="/%") + "?readback=" + run_id
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with OPENER.open(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return response.read()


def check_route(publish_dir: Path, base_url: str, route: str, run_id: str, timeout: float) -> str:
    """Return a status line for one route; it starts with IDENTICAL, DIFF or ERROR."""
    expected = local_file(publish_dir, route).read_bytes()
    try:
        served = normalise(fetch(base_url, route, run_id, timeout))
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            return f"ERROR {route} HTTP {error.code} Location={error.headers.get('Location')}"
        return f"ERROR {route} HTTP {error.code}"
    except Exception as error:  # timeouts, DNS, TLS, connection resets: never skipped
        return f"ERROR {route} {type(error).__name__}: {error}"
    if served == expected:
        return f"IDENTICAL {route}"
    offset = next((i for i, (a, b) in enumerate(zip(served, expected)) if a != b), min(len(served), len(expected)))
    return (f"DIFF {route} first-differing-offset={offset} "
            f"served-sha256={sha256(served).hexdigest()} build-sha256={sha256(expected).hexdigest()}")


def run(publish_dir: Path, base_url: str, routes: list[str], run_id: str, attempts: int = 10,
        interval: float = 30.0, timeout: float = 20.0, sleep=time.sleep, out=print) -> int:
    pending = list(routes)
    results: dict[str, str] = {}
    for attempt in range(1, max(attempts, 1) + 1):
        for route in pending:
            results[route] = check_route(publish_dir, base_url, route, run_id, timeout)
        pending = [r for r in pending if not results[r].startswith("IDENTICAL")]
        if not pending:
            break
        if attempt < attempts:
            out(f"attempt {attempt}/{attempts}: {len(pending)} of {len(routes)} routes not yet identical; "
                f"retrying in {interval:g}s")
            sleep(interval)
    for route in routes:
        out(results[route])
    identical = len(routes) - len(pending)
    out(f"readback: {identical}/{len(routes)} IDENTICAL, {len(pending)} not identical")
    return 0 if routes and not pending else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--publish-dir", default="public")
    parser.add_argument("--base-url", default="https://contract.place")
    parser.add_argument("--paths-file", help="file with one route per line (default: every index.html)")
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--run-id", default=str(int(time.time())))
    args = parser.parse_args(argv)
    publish_dir = Path(args.publish_dir)
    if args.paths_file:
        routes = [l.strip() for l in Path(args.paths_file).read_text().splitlines()
                  if l.strip() and not l.startswith("#")]
    else:
        routes = default_routes(publish_dir)
    if not routes:
        print("readback: no routes to check", file=sys.stderr)
        return 1
    return run(publish_dir, args.base_url, routes, args.run_id, args.attempts, args.interval, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
