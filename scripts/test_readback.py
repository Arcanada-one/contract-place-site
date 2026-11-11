#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for readback_served.py against a local http.server fixture."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import tempfile
import threading
import time
import unittest

SPEC = importlib.util.spec_from_file_location("readback_served", Path(__file__).with_name("readback_served.py"))
rb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rb)

PAGE = b"<!doctype html><html><body><p>Hello</p></body></html>\n"
def beacon(src=b"https://static.cloudflareinsights.com/beacon.min.js/vce701823e78c4301a35b7e07294d87301792088814092",
           extra=b"", body=b""):
    return (b'<script type="module" src="' + src + b'" integrity="sha512-UKNk8GbxkABxKcXYuLkO16EleLGUkcvJWtpSNmExE0Too3ZaFAxTscNWEc1OdAv5/'
            b'BikHawapSCaiD2XCmp+Bw==" data-cf-beacon=\'{"version":"2024.11.0","token":"0123456789abcdef0123456789abcdef",'
            b'"r":1,"spa":2}\'' + extra + b' crossorigin="anonymous">' + body + b'</script>')


TAG = beacon()
OTHER = b'<script defer src="https://example.test/other.js"></script>'


class Fixture:
    """Serves behaviours[path] = callable(request_count) -> (status, body) or 'hang'."""

    def __init__(self):
        self.behaviours = {}
        self.counts = {}
        self.queries = []
        self.agents = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                path, _, query = self.path.partition("?")
                outer.queries.append(query)
                outer.agents.append(self.headers.get("User-Agent"))
                outer.counts[path] = outer.counts.get(path, 0) + 1
                result = outer.behaviours[path](outer.counts[path])
                if result == "hang":
                    time.sleep(1.5)
                    return
                status, body = result[0], result[1]
                self.send_response(status)
                if len(result) > 2:
                    self.send_header("Location", result[2])
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pub = Path(self.tmp.name)
        (self.pub / "en" / "x").mkdir(parents=True)
        (self.pub / "index.html").write_bytes(PAGE)
        (self.pub / "en" / "x" / "index.html").write_bytes(PAGE)
        self.fx = Fixture()
        self.lines = []

    def tearDown(self):
        self.fx.close()
        self.tmp.cleanup()

    def go(self, attempts=3, timeout=5.0):
        sleeps = []
        code = rb.run(self.pub, self.fx.url, rb.default_routes(self.pub), "t1", attempts, 7.0, timeout,
                      sleep=sleeps.append, out=self.lines.append)
        self.sleeps = sleeps
        return code

    def serve(self, fn_root, fn_x=None):
        self.fx.behaviours["/"] = fn_root
        self.fx.behaviours["/en/x/"] = fn_x or (lambda n: (200, PAGE))

    def test_routes_mapped(self):
        self.assertEqual(rb.default_routes(self.pub), ["/", "/en/x/"])

    def test_identical_passes_with_probe_headers(self):
        self.serve(lambda n: (200, PAGE))
        self.assertEqual(self.go(), 0)
        self.assertEqual(self.sleeps, [])
        self.assertTrue(all(q == "readback=t1" for q in self.fx.queries))
        self.assertTrue(all(a and "Python-urllib" not in a for a in self.fx.agents))

    def test_one_changed_byte_fails(self):
        self.serve(lambda n: (200, PAGE.replace(b"Hello", b"Hellp")))
        self.assertEqual(self.go(), 1)
        diff = [l for l in self.lines if l.startswith("DIFF /")][0]
        self.assertIn("first-differing-offset=", diff)
        self.assertEqual(diff.count("sha256="), 2)

    def test_analytics_only_difference_passes(self):
        self.serve(lambda n: (200, PAGE.replace(b"</body>", TAG + b"</body>")))
        self.assertEqual(self.go(), 0)

    def test_other_script_tag_not_stripped(self):
        self.serve(lambda n: (200, PAGE.replace(b"</body>", OTHER + b"</body>")))
        self.assertEqual(self.go(), 1)

    def served_with(self, extra):
        self.serve(lambda n: (200, PAGE.replace(b"</body>", extra + b"</body>")))
        self.assertEqual(self.go(attempts=1), 1)
        self.assertTrue(any(l.startswith("DIFF /") for l in self.lines), self.lines)

    def test_foreign_script_mentioning_cloudflareinsights_not_stripped(self):
        self.served_with(b'<script src="https://example.test/evil.js" data-note="cloudflareinsights"></script>')

    def test_beacon_shape_on_other_host_not_stripped(self):
        self.served_with(beacon(src=b"https://example.test/beacon.min.js/vce701823e78c4301a35b7e07294d87301792088814092"))

    def test_beacon_with_extra_attribute_not_stripped(self):
        self.served_with(beacon(extra=b' data-extra="1"'))

    def test_beacon_with_body_not_stripped(self):
        self.served_with(beacon(body=b"alert(1)"))

    def test_two_beacons_when_build_has_none_fail(self):
        self.served_with(TAG + TAG)

    def test_redirect_to_identical_route_fails(self):
        self.serve(lambda n: (200, PAGE))
        self.fx.behaviours["/en/x/"] = lambda n: (302, b"", "/")
        self.assertEqual(self.go(attempts=1), 1)
        self.assertIn("ERROR /en/x/ HTTP 302 Location=/", self.lines)

    def test_404_fails(self):
        self.serve(lambda n: (404, b"nope"))
        self.assertEqual(self.go(), 1)
        self.assertIn("ERROR / HTTP 404", self.lines)

    def test_timeout_fails(self):
        self.serve(lambda n: "hang")
        self.assertEqual(self.go(attempts=1, timeout=0.3), 1)
        self.assertTrue(any(l.startswith("ERROR /") for l in self.lines))

    def test_mismatch_converging_on_retry_passes(self):
        self.serve(lambda n: (200, b"old" if n < 3 else PAGE))
        self.assertEqual(self.go(attempts=5), 0)
        self.assertEqual(self.sleeps, [7.0, 7.0])
        self.assertEqual(self.fx.counts["/en/x/"], 1)  # identical routes are not refetched

    def test_never_converging_fails_after_bounded_window(self):
        self.serve(lambda n: (200, b"old"))
        self.assertEqual(self.go(attempts=4), 1)
        self.assertEqual(self.fx.counts["/"], 4)
        self.assertEqual(len(self.sleeps), 3)


if __name__ == "__main__":
    unittest.main()
