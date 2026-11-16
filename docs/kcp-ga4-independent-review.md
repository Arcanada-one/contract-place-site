# KCP-GA4 — Independent Review (verifier)

> Redaction note (2026-11-10): internal mesh IP addresses and local filesystem paths of the
> development environment were replaced with placeholders before publication. Host names are kept
> because they are already published in the reviewed origin documentation. The unredacted original of
> this document is held in the private task record; the substance of every measurement is unchanged.
> Redaction note (2026-11-10): internal mesh IP addresses and local filesystem paths of the
> development environment were replaced with placeholders before publication. Host names are kept
> because they are already published in the reviewed origin documentation. The unredacted original of
> this document is held in the private task record; the substance of every measurement is unchanged.
Work item: "KCP: Add Google Analytics 4 to contract.place" (Muneral 093b8ab8-f5c0-4c29-83c6-5b3fe34fa479)

Reviewer role: independent verifier. Read-only. No repository file was modified, nothing committed, pushed, or
cleaned; Muneral was not touched.

**Overall verdict: PASS (7/7 acceptance criteria PASS)** — with three discrepancies against the author's own
evidence record recorded in §3 (one of them a wrong CI-run citation, one a precision issue about the consent
storage medium, one a now-obsolete limitation claim).

---

## 1. Heads reviewed, and the CI verdict

### 1.1 Exact heads

```
$ cd <dev-host scratch dir>/contract-place-site && git rev-parse HEAD
e01585a63dc12cc81f2feeb95bc2be138fc3a370
$ git rev-parse --abbrev-ref HEAD
docs/kcp-ga4-acceptance-records          # author's branch, with expected uncommitted docs
$ git rev-parse e01585a^
8648e00d7f7855d45d5ce27d320d35b68290e99b

$ cd <dev-host scratch dir>/arcanada-landing && git rev-parse HEAD
7e2beceb08daa3e2a8640b5432947ed0cd5c4346
$ git rev-parse --abbrev-ref HEAD
main
$ git rev-parse 7e2bece^
ea8c17adcc61ad27549e1e6a73647ea41222d1f1
```

Reviewed content was read with `git show <head>:<path>` / `git diff <parent> <head> -- <path>`; the author's dirty
working tree was never used as the source of truth. Verified: `git diff --stat e01585a -- scripts/ build.mjs public/ src/`
is empty, i.e. the scripts and built site on disk are byte-identical to the reviewed commit, so the gates below
measure the reviewed head.

### 1.2 CI verdict for the reviewed head

```
$ gh run view 42768514094 --json conclusion,headSha,name,jobs
run: CI | conclusion: success | headSha: e01585a63dc12cc81f2feeb95bc2be138fc3a370
  job: reuse-lint                          | completed | success
  job: static-site-smoke / publication      | completed | success
  job: network-exposure / network-exposure-lint | completed | success
  job: security-audit / security-audit (framework) | completed | success
```

The deploy run at the same head also succeeded: `gh run list --commit e01585a…` →
`{"databaseId":42768542087,"conclusion":"success","headSha":"e01585a…","name":"Deploy"}`.

**The CI verdict is what carries the parts of AC5 that were not re-run locally** (check_publication.py,
check_papers.py, check_links.py, check_roadmap.py, test_build.py, test_renditions.py, test_search.js, test_lab.js,
REUSE lint 403/403). Those were deliberately not re-run here, per the review brief.

---

## 2. Per-criterion verdicts

### AC1 — PASS

GA4 Admin API v1beta, property 532478786:

```
GET https://analyticsadmin.googleapis.com/v1beta/properties/532478786/dataStreams
status 200 — 21 WEB_DATA_STREAM entries, including
  "name": "properties/532478786/dataStreams/16306296753", "type": "WEB_DATA_STREAM", "displayName": "contract.place"

GET https://analyticsadmin.googleapis.com/v1beta/properties/532478786/dataStreams/16306296753
status 200
{
  "name": "properties/532478786/dataStreams/16306296753",
  "type": "WEB_DATA_STREAM",
  "displayName": "contract.place",
  "createTime": "2026-11-09T19:11:44.235Z",
  "webStreamData": { "measurementId": "G-C5J1NVE11Z", "defaultUri": "https://contract.place" }
}
```

Site code uses that exact ID:
- `git show e01585a:src/site/analytics.js` → line 9: `const MEASUREMENT_ID='G-C5J1NVE11Z';`
- `git show e01585a:public/analytics.js` → line 9: `const MEASUREMENT_ID='G-C5J1NVE11Z';`
- Live `curl -sS https://contract.place/analytics.js` → line 9 identical.

`G-C5J1NVE11Z` is the only measurement ID anywhere in either diff (`grep -oE "G-[A-Z0-9]{8,12}"` over both diffs
→ 6 occurrences, all `G-C5J1NVE11Z`).

### AC2 — PASS

Playwright + Chromium (dev host, `executablePath=<dev-host>/.cache/ms-playwright/chromium-1254/chrome-linux64/chrome`,
headless) against the **live production site** `https://contract.place`. A fresh browser context per scenario.
Requests counted with `page.on('request')` against
`/(googletagmanager\.com|google-analytics\.com|analytics\.google\.com|doubleclick\.net|googlesyndication\.com)/i`.

| scenario | GA requests | result |
|---|---|---|
| A. cold visit, no prior choice | **0** | banner present & visible, title "Analytics and cookies", buttons ["Accept analytics", "Necessary only"], `localStorage['cookie-consent']` = null, `document.cookie` = "" |
| B. "Necessary only" | **0** | banner removed (present:false), `localStorage['cookie-consent']` = "functional" |
| C. "Accept analytics" | **2** | `GET https://www.googletagmanager.com/gtag/js?id=G-C5J1NVE11Z` → 200; `POST https://region1.google-analytics.com/g/collect?...` → **204**; banner removed; `localStorage['cookie-consent']` = "accepted" |

Console/page errors captured in every scenario: **none** (empty `consoleErrors` in A, B, C, F_en, F_ru, F_zh-Hans).
No CSP violation was raised on the consented load — the deployed policy permits the tag and the collection endpoint.

The GA host is not referenced from HTML at all: `grep -rEl "googletagmanager|google-analytics" public --include=*.html`
→ no match; the live page contains **0** matches for `googletagmanager|google-analytics`. The tag is requested only
from JS after the consent decision (`src/site/analytics.js:97-110` `startTag()`, gated by `shouldLoadTag()` at
line 30, called from `applyChoice`/`install` at lines 115-123).

### AC3 — PASS

- **Persistence across page loads** (same context, `page.reload()`): `localStorage['cookie-consent']` stayed
  `"accepted"`; GA requests went 2 → 4 (the tag reloads for an already-accepted reader); the banner was not shown
  again on reload.
- **Dismissal and re-open**: after the banner was dismissed, the footer's control was found —
  `[data-consent-settings]`, button text "Cookie settings" — and clicking it re-opened the banner
  (`present:true, visible:true`, title "Analytics and cookies"). Choosing "Necessary only" from the re-opened
  banner changed the stored value to `"functional"` and removed the banner again.
- **Localisation** — banner rendered and visible in all three locales, with the correct strings:

| locale | `document.documentElement.lang` | title | buttons | GA requests |
|---|---|---|---|---|
| `/en/` | en | Analytics and cookies | Accept analytics / Necessary only | 0 |
| `/ru/` | ru | Аналитика и cookie | Принять аналитику / Только необходимые | 0 |
| `/zh-Hans/` | zh-Hans | 分析与 Cookie | 接受分析 / 仅必要项 | 0 |

Console errors in all three locales: none.

Note (precision, not a defect): the consent choice is stored in **localStorage** under the key `cookie-consent` with
values `accepted` / `functional` (`src/site/analytics.js:10-12, 19-29`), not in a cookie. The criterion's key and
value names match exactly. GA's own `_ga` / `_ga_C5J1NVE11Z` cookies appear only after consent is granted, which is
the correct behaviour.

### AC4 — PASS

**Committed config** (`git diff ea8c17a 7e2bece -- ops/nginx/contract.place.conf`) — exactly one rewritten line:

```
-    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; connect-src https://api.contract.place; style-src 'self'; img-src 'self' data:; base-uri 'none'; object-src 'none'; frame-ancestors 'none'" always;
+    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://*.googletagmanager.com; connect-src https://api.contract.place https://*.google-analytics.com; style-src 'self'; img-src 'self' data:; base-uri 'none'; object-src 'none'; frame-ancestors 'none'" always;
```

Strictness, checked against the committed string: no bare `*` source, no `unsafe-inline`, no scheme-only source
(`https:`/`http:`), and no nonce/hash was present before or removed after (the predecessor carried none either).
The two additions are domain-scoped host wildcards on `script-src` and `connect-src` only; `default-src`, `style-src`,
`img-src`, `base-uri`, `object-src`, `frame-ancestors` are unchanged.

**Deployed origin config** — read on the origin host `arcana-www` (mesh <origin-host mesh address>, `<origin-host>`):

```
$ sha256sum /etc/nginx/sites-enabled/contract.place
5706d854f392c71220b20d0f30ee4cf82edba4cbf50cae3658108fb97b8e246a
$ git show 7e2bece:ops/nginx/contract.place.conf | shasum -a 256
5706d854f392c71220b20d0f30ee4cf82edba4cbf50cae3658108fb97b8e246a
```

Installed file == reviewed commit, byte for byte.

**Public response carries the policy**:

```
$ curl -sSI https://contract.place/en/
HTTP/2 200
content-security-policy: default-src 'self'; script-src 'self' https://*.googletagmanager.com; connect-src https://api.contract.place https://*.google-analytics.com; style-src 'self'; img-src 'self' data:; base-uri 'none'; object-src 'none'; frame-ancestors 'none'
```

Live response header == committed config. Browser run confirmed the policy is functionally sufficient: the tag
loaded (200) and the collect request was sent and answered 204, with **no CSP violation logged**.

Origin gate, run locally on the dev host: `python3 -B ops/nginx/tests/test_contract_place_install.py` →
`Ran 30 tests … OK` (exit 0).

### AC5 — PASS

**Gates run by me at the reviewed head** (scripts verified identical to `e01585a`):

```
$ python3 -B scripts/check_hygiene.py .
hygiene OK (no private hosts; no inline script/style/handlers under script-src 'self' https://www.googletagmanager.com; style-src 'self')      exit 0
$ node scripts/test_analytics.js
ok a fresh reader stores no choice and no tag is requested
ok the tag URL is the reviewed measurement id on the Google host
ok a necessary-only choice never requests the tag
ok only the two known choices are stored
ok consent mode grants analytics only and denies advertising
ok the banner follows the interface language
ok an accepted reader starts the tag on install, a declined one does not
ok no page view is sent before the tag exists
ok a page view is sent after consent and carries the current location
ok the open banner follows a later language change
analytics consent tests OK (10 cases)                                                                                      exit 0
$ python3 -B scripts/check_page.py public
site checks OK (licensing, SEO, search, robots, sitemap, llms.txt)                                                          exit 0
```

**Static-publication constraints, checked independently of the gate scripts:**

- *Only script-src addition is the first-party /analytics.js* — script tags in the built page:

```
$ grep -o "<script[^>]*>" public/en/index.html
<script src="/theme.js?v=fbf6f88c…">
<script type="application/ld+json">
<script src="/content.js?v=1208dfbc…" defer>
<script src="/search.js?v=538768df…" defer>
<script src="/analytics.js?v=02e3d1270e7612fd65bc2f922dc6db3029c1f63fa956d5eedac1777e64ad5a96" defer>
<script src="/app.js?v=5508458825f5…" defer>
<script src="/renditions.js?v=9bb9504974e3…" defer>
```

  Every script source is a first-party path; the only added one is `/analytics.js` (`git diff 8648e00d e01585a --
  scripts/check_page.py` shows the expected list changed from `["/theme.js","/content.js","/search.js","/app.js"]`
  to `["/theme.js","/content.js","/search.js","/analytics.js","/app.js"]`). The live page serves the identical set.
- *No external resource reference in the generated HTML* — scanning every resource tag (`script|link|img|iframe|
  source|video|audio|embed|object`) across all **300** built HTML files for `https?://` yields only self-referential
  links (`href="https://contract.place/en/…"` canonical/hreflang) and one hyperlink
  (`href="https://creativecommons.org/licenses/by/4.0/"`, a licence link, not a subresource). **No external
  script/style/image subresource exists anywhere in the built site.**
- Served asset integrity: `curl https://contract.place/analytics.js` → sha256
  `02e3d1270e7612fd65bc2f922dc6db3029c1f63fa956d5eedac1777e64ad5a96`, identical to
  `git show e01585a:public/analytics.js`; the served URL carries that same content hash as `?v=`.

**Remaining gates** — carried by the CI verdict at the reviewed head (run 42768514094, `static-site-smoke /
publication` = success, `reuse-lint` = success). Not re-run by me; see §1.2.

### AC6 — PASS

**Realtime report**, GA4 Data API `runRealtimeReport` on property 532478786, dimension `streamName`:

```
POST https://analyticsdata.googleapis.com/v1beta/properties/532478786:runRealtimeReport
status 200
rows=1 → stream=contract.place  eventCount=3
```

and by event dimension: `first_visit 1`, `page_view 1`, `session_start 1`.

**/g/collect parameters**, captured from the live browser run (scenario C):

```
POST https://region1.google-analytics.com/g/collect?v=2&tid=G-C5J1NVE11Z&…&dl=https%3A%2F%2Fcontract.place%2Fen%2F&…&en=page_view&…
  tid = G-C5J1NVE11Z
  en  = page_view
  dl  = https://contract.place/en/
response: 204
```

Standard (non-realtime) report, `runReport` with `dimensionFilter.filter` on `streamName = contract.place`,
date range today → 3 rows, all on host `contract.place`, date 20261110:
`first_visit 1`, `page_view 1`, `session_start 1`.

Caveat recorded honestly: the realtime report is **not stably populated**. On my first poll (6 consecutive attempts
over ~90 s, immediately after an earlier consented visit) `runRealtimeReport` returned `rows=0` for the entire
property, including streams with known traffic. It only showed `contract.place`/3 events when polled right after a
fresh consented visit. The underlying collection is not in doubt (the /g/collect POST is answered 204 and the
standard report shows the events), but the realtime assertion depends on GA-side ingestion timing/filtering.

### AC7 — PASS

Secret-pattern scan over the full diffs of both repositories
(`git diff 8648e00d e01585a` and `git diff ea8c17a 7e2bece`) for
`BEGIN … PRIVATE KEY | AKIA… | ghp_ | github_pat_ | AIza… | ya29. | sk-… | xox[baprs]- | mun_sk_ | client_secret |
password | api_key= | bearer <token>`:

- contract-place-site: **no matches**.
- arcanada-landing: **no matches**.
- The only Google identifier added in either diff is the public measurement ID `G-C5J1NVE11Z` (6 occurrences,
  contract-place-site; 0 in arcanada-landing).
- The GA4 OAuth token was read only from `<local GA4 OAuth token path>` (mode 0600) on the reviewer's
  machine and was never written into the workspace, a repository, or a log.

---

## 3. Discrepancies between the author's claims and my measurements

**D1 — The cited CI run is not the reviewed head (citation error in the author's evidence record).**
The author's `docs/kcp-ga4-acceptance-evidence.md` (AC5) cites "CI run `42767664452` on `contract-place-site`: 4 jobs,
all success". That run's head is a different commit:

```
$ gh run view 42767664452 --json conclusion,headSha
run: CI | conclusion: success | headSha: fe24d0125dc14b3f923309e83b0e660c7630f87a
```

The run that actually covers the reviewed head `e01585a` is **42768514094** (CI, success, 4/4 jobs) plus the Deploy
run 42768542087 (success). The gates are green at the reviewed head, so this is a wrong citation in the evidence
record, not a product defect — but a reader following the citation would be checking the wrong commit.

**D2 — The consent value is stored in localStorage, not in a cookie.**
The author's AC3 evidence is written as "`cookie-consent=accepted`" / "`cookie-consent=functional`", which reads as
a cookie. Measured: `document.cookie` is empty on a cold visit and after "Necessary only"; the values live in
`localStorage['cookie-consent']`. The criterion's key and value names (`cookie-consent`, `accepted` | `functional`)
are met exactly and persistence works, so AC3 stands — but the storage medium differs from how the author's record
phrases it. (GA's own `_ga`/`_ga_C5J1NVE11Z` cookies are set by Google only after consent.)

**D3 — The author's "known limitation" about the standard report has since resolved.**
The author's AC6 record carries a limitation that the standard (non-realtime) report "showed no rows for any host in
the property at the time of checking". Measured now: `runReport` for today returns `contract.place → 3` events, and
the property-wide 30-day report lists `contract.place 3` alongside arcanada.one 273, cubrim.com 255, etc. The
limitation was Google-side latency at the author's moment, not a site defect; it is no longer observable.

**D4 (informational, not a discrepancy in the acceptance criteria) — the site-level hygiene gate was relaxed to
admit a remote script host.** `scripts/check_hygiene.py` was changed at this commit so that its model of the
production CSP is `script-src 'self' https://www.googletagmanager.com` (previously `script-src 'self'`). The gate
still enforces "no inline script/style/handlers". This is consistent with AC4's origin CSP, and I verified
independently that no built HTML page carries any external subresource, so the relaxation did not let an external
reference into the site. It is noted only because the gate is now weaker than before the change, in the direction
AC4 permits.

No other discrepancy was found. Specifically checked and confirmed consistent with the author's record: the GA request
counts (0 / 0 / 2), the GA host set (`www.googletagmanager.com`, `region1.google-analytics.com`), the /g/collect
parameters, the banner strings in en/ru/zh-Hans, the footer "Cookie settings" control, the origin config digest
`5706d854…`, the 30-test origin gate, the 10-case analytics gate, and the presence of exactly one new first-party
script (`/analytics.js`).

---

## 4. Working-tree hygiene

**Neither checkout was dirtied by this review.** Verified after all checks:

```
$ cd <dev-host scratch dir>/contract-place-site && git status --porcelain
 M REUSE.toml
?? docs/kcp-ga4-acceptance-evidence.md
?? docs/kcp-ga4-change-admission-receipt.json
?? docs/kcp-ga4-compliance-checklist.md

$ cd <dev-host scratch dir>/arcanada-landing && git status --porcelain
(empty)
```

This is byte-identical to the pre-review state (the contract-place-site entries are the author's own uncommitted
documentation additions, which were present before the review and are not the reviewer's). I ran no `git checkout`,
`git reset`, `git commit`, `git clean` or `rm -rf`. Everything this reviewer created lives outside every git
repository: this report at `<dev-host scratch dir>/kcp-ga4-independent-review.md` (scratch dir, outside any repo) and
throwaway scripts in `/tmp` on the dev host (`/tmp/kcp-ga4-browser.js`, `/tmp/kcp-ga4-accept.js`). The only writes
to the origin host `arcana-www` were read-only (`ls`, `sha256sum`).

---

## 5. Summary

| criterion | reviewer verdict |
|---|---|
| AC1 — data stream + measurement ID | **PASS** |
| AC2 — consent gate, zero requests before consent | **PASS** |
| AC3 — persistence, re-open, en/ru/zh-Hans | **PASS** |
| AC4 — origin CSP allows GA and stays strict | **PASS** |
| AC5 — gates green, static-publication constraints | **PASS** |
| AC6 — GA4 receives the data | **PASS** |
| AC7 — secret hygiene | **PASS** |

**VERDICT: PASS** — every acceptance criterion is established by evidence measured in this session (browser,
GA4 Admin/Data APIs, live HTTP headers, deployed origin config on the origin host, and the local gates), with the
CI verdict at the exact reviewed head carrying the gate subset that was intentionally not re-run. Three
discrepancies against the author's evidence record are listed in §3 (D1 wrong CI-run citation, D2 localStorage vs
cookie wording, D3 a now-resolved limitation claim); none of them is a defect in the delivered change.
