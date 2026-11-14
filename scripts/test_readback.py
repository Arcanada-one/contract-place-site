#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline tests for readback_served.py against a local http.server fixture."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import os
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
    """Serves behaviours[path] or behaviours[(path, query)] for each request variant."""

    def __init__(self):
        self.behaviours = {}
        self.counts = {}
        self.queries = []
        self.variant_counts = {}
        self.agents = []
        self.accepts = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                path, _, query = self.path.partition("?")
                outer.queries.append(query)
                outer.agents.append(self.headers.get("User-Agent"))
                outer.accepts.append(self.headers.get("Accept"))
                outer.counts[path] = outer.counts.get(path, 0) + 1
                variant = (path, query)
                outer.variant_counts[variant] = outer.variant_counts.get(variant, 0) + 1
                behaviour = outer.behaviours.get(variant, outer.behaviours.get(path))
                result = behaviour(outer.variant_counts[variant])
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
        self.assertEqual(self.fx.queries, ["", "readback=t1", "", "readback=t1"])
        for route in rb.default_routes(self.pub):
            for variant in ("bare", "readback_query"):
                self.assertTrue(any(l.startswith(f"IDENTICAL {route} status=200 ") and
                                    f"variant={variant}" in l for l in self.lines), self.lines)
        self.assertTrue(all(a and "Python-urllib" not in a for a in self.fx.agents))

    def test_query_match_does_not_hide_bare_404(self):
        self.serve(lambda n: (200, PAGE))
        self.fx.behaviours[("/", "")] = lambda n: (404, b"nope")
        self.assertEqual(self.go(attempts=1), 1)
        self.assertTrue(any(l.startswith("ERROR / status=404 ") and "variant=bare" in l
                            for l in self.lines), self.lines)
        self.assertTrue(any(l.startswith("IDENTICAL / status=200 ") and "variant=readback_query" in l
                            for l in self.lines), self.lines)
        self.assertIn("readback: 1/2 IDENTICAL, 1 not identical", self.lines)

    def test_query_match_does_not_hide_old_bare_body(self):
        self.serve(lambda n: (200, PAGE))
        self.fx.behaviours[("/", "")] = lambda n: (200, PAGE.replace(b"Hello", b"Old page"))
        self.assertEqual(self.go(attempts=1), 1)
        self.assertTrue(any(l.startswith("DIFF / status=200 ") and "variant=bare" in l
                            for l in self.lines), self.lines)
        self.assertTrue(any(l.startswith("IDENTICAL / status=200 ") and "variant=readback_query" in l
                            for l in self.lines), self.lines)

    def test_bare_match_does_not_hide_query_failure(self):
        self.serve(lambda n: (200, PAGE))
        self.fx.behaviours[("/", "readback=t1")] = lambda n: (404, b"nope")
        self.assertEqual(self.go(attempts=1), 1)
        self.assertTrue(any(l.startswith("IDENTICAL / status=200 ") and "variant=bare" in l
                            for l in self.lines), self.lines)
        self.assertTrue(any(l.startswith("ERROR / status=404 ") and "variant=readback_query" in l
                            for l in self.lines), self.lines)

    def test_one_changed_byte_fails(self):
        self.serve(lambda n: (200, PAGE.replace(b"Hello", b"Hellp")))
        self.assertEqual(self.go(), 1)
        diff = [l for l in self.lines if l.startswith("DIFF /")][0]
        self.assertIn("first-differing-offset=", diff)
        self.assertEqual(diff.count("served-sha256="), 1)
        self.assertEqual(diff.count("build-sha256="), 1)

    def test_analytics_only_difference_passes(self):
        self.serve(lambda n: (200, PAGE.replace(b"</body>", TAG + b"\n</body>")))
        self.assertEqual(self.go(), 0)

    def test_beacon_without_newline_not_stripped(self):
        self.served_with(TAG)

    def test_beacon_with_newline_in_head_not_stripped(self):
        self.serve(lambda n: (200, PAGE.replace(b"<body>", TAG + b"\n<body>")))
        self.assertEqual(self.go(attempts=1), 1)
        self.assertTrue(any(l.startswith("DIFF /") for l in self.lines), self.lines)

    def test_beacon_with_newline_not_before_body_end_not_stripped(self):
        self.served_with(TAG + b"\n<p>x</p>")

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
        self.served_with(TAG + b"\n" + TAG)

    def test_redirect_to_identical_route_fails(self):
        self.serve(lambda n: (200, PAGE))
        self.fx.behaviours["/en/x/"] = lambda n: (302, b"", "/")
        self.assertEqual(self.go(attempts=1), 1)
        self.assertTrue(any(l.startswith("ERROR /en/x/ status=302 ") and l.endswith("HTTP 302 Location=/")
                            for l in self.lines), self.lines)

    def test_404_fails(self):
        self.serve(lambda n: (404, b"nope"))
        self.assertEqual(self.go(), 1)
        self.assertTrue(any(l.startswith("ERROR / status=404 ") and l.endswith("HTTP 404") for l in self.lines),
                        self.lines)

    def test_timeout_fails(self):
        self.serve(lambda n: "hang")
        self.assertEqual(self.go(attempts=1, timeout=0.3), 1)
        self.assertTrue(any(l.startswith("ERROR /") for l in self.lines))

    def test_mismatch_converging_on_retry_passes(self):
        self.serve(lambda n: (200, b"old" if n < 3 else PAGE))
        self.assertEqual(self.go(attempts=5), 0)
        self.assertEqual(self.sleeps, [7.0, 7.0])
        self.assertEqual(self.fx.counts["/en/x/"], 2)  # identical route pairs are not refetched
        self.assertEqual(self.fx.variant_counts[("/", "")], 3)
        self.assertEqual(self.fx.variant_counts[("/", "readback=t1")], 3)

    def test_variants_must_match_in_the_same_attempt(self):
        self.serve(lambda n: (200, PAGE))
        self.fx.behaviours[("/", "")] = lambda n: (200, PAGE if n == 1 else b"old")
        self.fx.behaviours[("/", "readback=t1")] = lambda n: (200, b"old" if n == 1 else PAGE)
        self.assertEqual(self.go(attempts=2), 1)
        self.assertEqual(self.fx.variant_counts[("/", "")], 2)
        self.assertEqual(self.fx.variant_counts[("/", "readback=t1")], 2)
        self.assertEqual(self.fx.counts["/en/x/"], 2)
        self.assertIn("readback: 1/2 IDENTICAL, 1 not identical", self.lines)

    def test_never_converging_fails_after_bounded_window(self):
        self.serve(lambda n: (200, b"old"))
        self.assertEqual(self.go(attempts=4), 1)
        self.assertEqual(self.fx.counts["/"], 8)
        self.assertEqual(len(self.sleeps), 3)

    # --- witness ---
    KEYS = ("build_revision", "origin", "request_method", "request_accept", "request_user_agent", "request_variants", "redirects",
            "cache_token", "probe", "probe_region", "started_utc", "finished_utc", "normaliser")

    def witness(self):
        return {l[len("witness: "):].split(": ", 1)[0]: l.split(": ", 2)[2]
                for l in self.lines if l.startswith("witness: ") and ": " in l[9:]}

    def go_env(self, env, **kw):
        keep = {k: os.environ.pop(k) for k in ("GITHUB_SHA", "RUNNER_NAME", "RUNNER_OS", "RUNNER_ENVIRONMENT")
                if k in os.environ}
        os.environ.update(env)
        try:
            self.serve(lambda n: (200, PAGE))
            rb.run(self.pub, self.fx.url, rb.default_routes(self.pub), "t1", 1, 1.0, 5.0,
                   sleep=lambda s: None, out=self.lines.append, **kw)
        finally:
            for k in ("GITHUB_SHA", "RUNNER_NAME", "RUNNER_OS", "RUNNER_ENVIRONMENT"):
                os.environ.pop(k, None)
            os.environ.update(keep)

    def assert_received(self, received, expected, printed):
        self.assertTrue(received, "server received no requests")
        self.assertEqual(set(received), {expected}, f"received {received!r}")
        self.assertEqual(printed, expected)

    def test_received_header_assertion_is_not_vacuous(self):
        # Accept changed to */* in the script: server receives it, helper must reject it.
        real = rb.ACCEPT
        rb.ACCEPT = "*/*"
        try:
            self.go_env({})
        finally:
            rb.ACCEPT = real
        self.assertEqual(set(self.fx.accepts), {"*/*"})
        with self.assertRaises(AssertionError):
            self.assert_received(self.fx.accepts, "text/html", self.witness()["request_accept"])
        # Accept absent / User-Agent altered as recorded by the server: helper must reject too.
        for bad in ([None, None], ["text/html", None]):
            with self.assertRaises(AssertionError):
                self.assert_received(bad, "text/html", "text/html")
        with self.assertRaises(AssertionError):
            self.assert_received(["other/1.0"], rb.USER_AGENT, rb.USER_AGENT)

    def test_header_has_every_key_before_routes(self):
        self.go_env({}, build_revision="abc123")
        w = self.witness()
        for key in self.KEYS:
            self.assertIn(key, w)
        self.assertEqual(w["build_revision"], "abc123")
        self.assertEqual((w["request_method"], w["request_accept"], w["redirects"], w["cache_token"]),
                         ("GET", "text/html", "refused", "t1"))
        self.assertEqual(w["request_user_agent"], rb.USER_AGENT)
        self.assertEqual(w["request_variants"], "bare,readback_query")
        # printed value = value the server actually received, on every request
        self.assert_received(self.fx.accepts, "text/html", w["request_accept"])
        self.assert_received(self.fx.agents, rb.USER_AGENT, w["request_user_agent"])
        self.assertEqual(w["origin"], self.fx.url)
        self.assertEqual(w["probe_region"], "UNKNOWN")
        self.assertTrue(w["started_utc"].endswith("Z") and w["finished_utc"].endswith("Z"))
        first_route = next(i for i, l in enumerate(self.lines) if l.startswith("IDENTICAL"))
        self.assertTrue(all(any(l.startswith(f"witness: {k}:") for l in self.lines[:first_route]) for k in self.KEYS))

    def test_probe_region_and_runner_env(self):
        self.go_env({"RUNNER_NAME": "GitHub Actions 7", "RUNNER_OS": "Linux", "RUNNER_ENVIRONMENT": "github-hosted"},
                    probe_region="eu-test")
        w = self.witness()
        self.assertEqual(w["probe_region"], "eu-test")
        self.assertEqual(w["probe"], "RUNNER_NAME=GitHub Actions 7 RUNNER_OS=Linux RUNNER_ENVIRONMENT=github-hosted")

    def test_build_revision_from_github_sha(self):
        self.go_env({"GITHUB_SHA": "deadbeef"})
        self.assertEqual(self.witness()["build_revision"], "deadbeef")

    def test_build_revision_falls_back_to_unknown(self):
        real = rb.subprocess.run
        rb.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("git"))
        try:
            self.go_env({})
        finally:
            rb.subprocess.run = real
        self.assertEqual(self.witness()["build_revision"], "UNKNOWN")

    def test_no_hostname_when_runner_unset(self):
        import socket
        self.go_env({})
        self.assertEqual(self.witness()["probe"], "local")
        host = socket.gethostname()
        if len(host) > 3 and host not in ("localhost", "local"):
            self.assertFalse(any(host in l for l in self.lines))

    def test_normaliser_identity_changes_with_pattern(self):
        before = rb.normaliser_identity()
        real = rb.ANALYTICS
        rb.ANALYTICS = rb.re.compile(real.pattern + b"x")
        try:
            after = rb.normaliser_identity()
        finally:
            rb.ANALYTICS = real
        self.assertNotEqual(before, after)
        self.assertIn("sha256=" + rb.sha256(real.pattern).hexdigest(), before)

    def test_stripped_and_injected_pages_counted(self):
        injected = lambda n: (200, PAGE.replace(b"</body>", TAG + b"\n</body>"))
        self.serve(injected, injected)
        self.assertEqual(self.go(), 0)
        root = [l for l in self.lines if l.startswith("IDENTICAL / ")][0]
        other = [l for l in self.lines if l.startswith("IDENTICAL /en/x/ ")][0]
        self.assertIn("status=200", root)
        self.assertIn("stripped=1", root)
        self.assertIn("stripped=1", other)
        self.assertIn("norm_sha256=" + rb.sha256(PAGE).hexdigest(), root)
        self.assertNotIn("raw_sha256=" + rb.sha256(PAGE).hexdigest(), root)
        self.assertIn("witness: injected_pages=2", self.lines)
        self.assertEqual(self.lines[-2][:9], "readback:")

    def test_plain_pages_not_counted_as_injected(self):
        self.serve(lambda n: (200, PAGE))
        self.assertEqual(self.go(), 0)
        self.assertTrue(all("stripped=0" in l for l in self.lines if l.startswith("IDENTICAL")))
        self.assertIn("witness: injected_pages=0", self.lines)
        self.assertIn("readback: 2/2 IDENTICAL, 0 not identical", self.lines)

    def test_error_line_carries_status(self):
        self.serve(lambda n: (404, b"nope"))
        self.go(attempts=1)
        self.assertTrue(any(l.startswith("ERROR / status=404 raw_sha256=none") for l in self.lines))
        self.serve(lambda n: "hang")
        self.lines.clear()
        self.go(attempts=1, timeout=0.3)
        self.assertTrue(any(l.startswith("ERROR / status=none ") for l in self.lines), self.lines)


if __name__ == "__main__":
    unittest.main()
