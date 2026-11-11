#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Read the served site back and compare it byte for byte with the build.

Deploy reports success when files are uploaded, not when the served site equals
the build. For every route this fetches the page anonymously with a cache-busting
query, removes only the Cloudflare Web Analytics injection and compares the bytes
with the local file. Mismatching routes are retried as a set for a bounded window
to absorb edge propagation. Exit 0 only if every route is IDENTICAL.

The output opens with a `witness:` header (request shape, probe, revision, normaliser
identity, UTC times); a verdict holds only for that request shape and probe.

Usage: readback_served.py --publish-dir public --base-url https://contract.place
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "contract-place-readback/1.0 (+https://contract.place)"
ACCEPT = "text/html"
NORMALISER_NAME = "cloudflare-web-analytics-tag-v1"
# The only normalisation: the one Web Analytics tag Cloudflare injects at the edge
# (only for requests that send Accept: text/html). Anchored full-tag permitlist: same
# attributes in the same order, fixed origin and path prefix, empty body. Version and
# token vary, so only their character classes are fixed. The edge adds the tag and one
# newline immediately before </body>; both are removed, nothing else is.
ANALYTICS = re.compile(
    rb'<script type="module" '
    rb'src="https://static\.cloudflareinsights\.com/beacon\.min\.js/v[0-9a-f]+" '
    rb'integrity="sha512-[A-Za-z0-9+/]+={0,2}" '
    rb"data-cf-beacon='\{\"version\":\"[0-9A-Za-z.\-]+\",\"token\":\"[0-9a-f]{32}\","
    rb"\"r\":[0-9]+,\"spa\":[0-9]+\}' "
    rb'crossorigin="anonymous"></script>'
    rb"\n(?=</body>)")  # the edge inserts the tag plus one newline directly before </body>


class ServedStatus(Exception):
    """A non-200 response that was not an HTTPError; carries the status for the witness."""

    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


def normaliser_identity() -> str:
    return f"{NORMALISER_NAME} sha256={sha256(ANALYTICS.pattern).hexdigest()}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_build_revision(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


def probe_description() -> str:
    # Never the hostname, IP or user name: this output goes to public logs.
    keys = ("RUNNER_NAME", "RUNNER_OS", "RUNNER_ENVIRONMENT")
    found = [f"{k}={os.environ[k]}" for k in keys if os.environ.get(k)]
    return " ".join(found) if found else "local"


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


def fetch(base_url: str, route: str, run_id: str, timeout: float) -> tuple[int, bytes]:
    url = base_url.rstrip("/") + urllib.parse.quote(route, safe="/%") + "?readback=" + run_id
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})
    with OPENER.open(request, timeout=timeout) as response:
        if response.status != 200:
            raise ServedStatus(response.status)
        return response.status, response.read()


def check_route(publish_dir: Path, base_url: str, route: str, run_id: str, timeout: float) -> str:
    """Return a status line for one route; it starts with IDENTICAL, DIFF or ERROR."""
    expected = local_file(publish_dir, route).read_bytes()
    try:
        status, raw = fetch(base_url, route, run_id, timeout)
    except urllib.error.HTTPError as error:
        witness = f"status={error.code} raw_sha256=none norm_sha256=none stripped=0"
        if 300 <= error.code < 400:
            return f"ERROR {route} {witness} HTTP {error.code} Location={error.headers.get('Location')}"
        return f"ERROR {route} {witness} HTTP {error.code}"
    except ServedStatus as error:
        return f"ERROR {route} status={error.status} raw_sha256=none norm_sha256=none stripped=0 {error}"
    except Exception as error:  # timeouts, DNS, TLS, connection resets: never skipped
        return (f"ERROR {route} status=none raw_sha256=none norm_sha256=none stripped=0 "
                f"{type(error).__name__}: {error}")
    served = normalise(raw)
    witness = (f"status={status} raw_sha256={sha256(raw).hexdigest()} "
               f"norm_sha256={sha256(served).hexdigest()} stripped={int(served != raw)}")
    if served == expected:
        return f"IDENTICAL {route} {witness}"
    offset = next((i for i, (a, b) in enumerate(zip(served, expected)) if a != b), min(len(served), len(expected)))
    return (f"DIFF {route} {witness} first-differing-offset={offset} "
            f"served-sha256={sha256(served).hexdigest()} build-sha256={sha256(expected).hexdigest()}")


def run(publish_dir: Path, base_url: str, routes: list[str], run_id: str, attempts: int = 10,
        interval: float = 30.0, timeout: float = 20.0, sleep=time.sleep, out=print, build_revision: str | None = None,
        probe_region: str | None = None) -> int:
    started = utc_now()
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
    finished = utc_now()
    for line in (
        f"build_revision: {resolve_build_revision(build_revision)}",
        f"origin: {base_url.rstrip('/')}",
        "request_method: GET",
        f"request_accept: {ACCEPT}",
        f"request_user_agent: {USER_AGENT}",
        "redirects: refused",
        f"cache_token: {run_id}",
        f"probe: {probe_description()}",
        f"probe_region: {probe_region or 'UNKNOWN'}",
        f"started_utc: {started}",
        f"finished_utc: {finished}",
        f"normaliser: {normaliser_identity()}",
    ):
        out(f"witness: {line}")
    for route in routes:
        out(results[route])
    identical = len(routes) - len(pending)
    out(f"readback: {identical}/{len(routes)} IDENTICAL, {len(pending)} not identical")
    out(f"witness: injected_pages={sum(' stripped=1' in results[r] for r in routes)}")
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
    parser.add_argument("--build-revision", help="source/build revision (default: $GITHUB_SHA, git HEAD, UNKNOWN)")
    parser.add_argument("--probe-region", help="probe location, if known (default: UNKNOWN)")
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
    return run(publish_dir, args.base_url, routes, args.run_id, args.attempts, args.interval, args.timeout,
               build_revision=args.build_revision, probe_region=args.probe_region)


if __name__ == "__main__":
    raise SystemExit(main())
