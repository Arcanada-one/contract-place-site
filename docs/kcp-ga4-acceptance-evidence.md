# ACCEPTANCE CRITERIA v1 — KCP-GA4 (contract.place Google Analytics 4)

> Redaction note (2026-11-10): internal mesh IP addresses and local filesystem paths of the
> development environment were replaced with placeholders before publication. Host names are kept
> because they are already published in the reviewed origin documentation. The unredacted original of
> this document is held in the private task record; the substance of every measurement is unchanged.
> Redaction note (2026-11-10): internal mesh IP addresses and local filesystem paths of the
> development environment were replaced with placeholders before publication. Host names are kept
> because they are already published in the reviewed origin documentation. The unredacted original of
> this document is held in the private task record; the substance of every measurement is unchanged.
Work item: Muneral `093b8ab8-f5c0-4c29-83c6-5b3fe34fa479` — "KCP: Add Google Analytics 4 to contract.place"
Prepared: 2026-11-10 (Arcanada dev host `arcana-devs`, mesh `<dev-host mesh address>`)

This record carries the numbered acceptance criteria for the work item and the **author-side** evidence for each
criterion. The independent reviewer records its own verdict per criterion in
`docs/kcp-ga4-independent-review.md`; the two verdicts are kept apart on purpose and are never merged.

Sources under review:

| repository | exact head reviewed | pull request |
|---|---|---|
| `Arcanada-one/contract-place-site` | `e01585a` | https://github.com/Arcanada-one/contract-place-site/pull/31 |
| `Arcanada-one/arcanada-landing` | `7e2bece` | https://github.com/Arcanada-one/arcanada-landing/pull/178 |

Product state under review: the deployed public site `https://contract.place` (static publication) served by the
`contract.place` origin vhost on `arcana-www`; GA4 property `532478786` ("Arcanada Ecosystem"), web data stream
`contract.place`, measurement ID `G-C5J1NVE11Z`, `defaultUri` `https://contract.place`.

The task description carried no numbered criteria at creation. The seven criteria below restate the description's
three clauses — GA4 with a consent gate, the origin CSP extension, and browser verification of the gate — into
observable results, without widening the scope. Where a criterion was measured only in the author session, the
evidence names the measurement; where it was not measured at all, the verdict is `NOT_MEASURED`.

## AC1 — GA4 data stream and measurement ID

Criterion: a GA4 web data stream for `https://contract.place` exists in property `532478786` with measurement ID
`G-C5J1NVE11Z`, and the site code uses that exact measurement ID.

Author verdict: **PASS**

Evidence:

- GA4 Admin API — property `532478786`, web data stream named `contract.place`, measurement ID `G-C5J1NVE11Z`,
  `defaultUri` `https://contract.place`.
- `src/site/analytics.js` at head `e01585a` carries `G-C5J1NVE11Z` as the only measurement ID in the code.
- GA4 Data API, realtime report on the property: dimension `streamName` resolves to `contract.place`.

## AC2 — Consent gate before any GA request

Criterion: on a cold visit with no stored choice the site issues zero requests to any Google analytics host and
shows the consent banner; "Necessary only" keeps the request count at zero; "Accept analytics" loads the tag and GA
collects a hit.

Author verdict: **PASS**

Evidence (browser, production site, Chromium via Playwright):

- No choice made → GA request count **0**, banner **shown**.
- "Necessary only" → GA request count **0**, banner hidden afterwards.
- "Accept analytics" → GA request count **2**, host set exactly `www.googletagmanager.com` and
  `region1.google-analytics.com`; `POST /g/collect` answered **204**.
- The tag is not referenced from HTML: the request for `googletagmanager.com` happens only after the consent
  decision, issued from `src/site/analytics.js`.

## AC3 — Consent state, dismissal, re-opening, localisation

Criterion: the consent choice persists across page loads as `cookie-consent` (`accepted` | `functional`); the banner
can be dismissed and re-opened from the footer's "Cookie settings" control; the banner renders correctly in `en`,
`ru` and `zh-Hans`.

Author verdict: **PASS**

Evidence (browser, production site):

- After "Accept analytics": the stored choice is `accepted`, banner closed; after "Necessary only": the stored choice is
  `functional`. The storage medium is `localStorage` under the key `cookie-consent` (not an HTTP cookie); the
  measurement is `localStorage['cookie-consent']`. Google's own `_ga` / `_ga_C5J1NVE11Z` cookies appear only after
  consent is granted.
- The footer's "Cookie settings" control re-opens the dismissed banner; the choice can be changed afterwards.
- The banner was rendered and dismissed in `en`, `ru` and `zh-Hans`; no console errors in any of the three.

## AC4 — Origin CSP allows GA and stays strict

Criterion: the deployed origin CSP for `contract.place` allows the GA tag and the GA collection endpoints while
keeping the policy strict — `script-src` / `connect-src` extended only by domain-scoped Google wildcards, no bare
`*`, no `unsafe-inline`, no scheme sources, and the public response actually carries that policy.

Author verdict: **PASS**

Evidence:

- `ops/nginx/contract.place.conf` at head `7e2bece`, sha256 `5706d854f392c71220b20d0f30ee4cf82edba4cbf50cae3658108fb97b8e246a`;
  the change is exactly one rewritten line:
  `script-src 'self' https://*.googletagmanager.com; connect-src https://api.contract.place https://*.google-analytics.com`.
- The live digest of the installed origin configuration equals the digest above.
- The public response `https://contract.place/en/` carries the policy above; it contains no bare `*`, no
  `unsafe-inline`, no scheme source, and no nonce/hash handling was removed.
- Origin gate `ops/nginx/tests/test_contract_place_install.py`: **30 tests OK** at the reviewed head.

## AC5 — Repository gates stay green, static-publication constraints hold

Criterion: the site gates pass at the exact head; the generated HTML carries no external resource reference; the
only script-src addition is the first-party `/analytics.js`.

Author verdict: **PASS**

Evidence at head `e01585a`:

- `check_publication.py` (30 documents / 90 localised pages / 300 pages), `check_hygiene.py`, `check_page.py`,
  `check_papers.py`, `check_links.py` (16 888 links), `check_roadmap.py`, `test_build.py` (14),
  `test_renditions.py` (126), `test_roadmap.py` (32), `test_roadmap_names.py` (45),
  `test_roadmap_display_names.py` (22), `test_programme.py` (9), `test_rendition_preamble.py` (22),
  `test_search.js` (21), `test_lab.js`, `node scripts/test_analytics.js` (10) — all pass.
- REUSE lint: **403/403 files compliant**.
- CI run `42768514094` on `contract-place-site` at the reviewed head `e01585a`: **4 jobs, all success**
  (`reuse-lint`, `static-site-smoke / publication`, `network-exposure`, `security-audit`). The deploy run for the same
  head is `42768542087` (success).
- `scripts/check_page.py` — the expected script source list is
  `["/theme.js","/content.js","/search.js","/analytics.js","/app.js"]`; `/analytics.js` is first-party, no external
  script source was added.
- `scripts/check_hygiene.py` — no inline script or handler, no external resource reference in the generated HTML.

## AC6 — GA4 receives the data

Criterion: the GA4 Data API realtime report for the property shows a stream named `contract.place` with events, and
the `/g/collect` request carries `tid=G-C5J1NVE11Z` and `en=page_view`.

Author verdict: **PASS**

Evidence:

- GA4 Data API `runRealtimeReport`, dimension `streamName` → `contract.place`, event count **3**, events
  `page_view`, `first_visit`, `session_start`, country Germany.
- The captured `/g/collect` request carried `tid=G-C5J1NVE11Z`, `en=page_view`, `dl=https://contract.place/en/`,
  and was answered **204**.
- SPA navigation inside the site queued `event:page_view` in `dataLayer` and produced a further `/g/collect`.

Known limitation, carried as `NOT_MEASURED` for the standard report only **at the time of the author's measurement**:
the standard (non-realtime) GA4 report for the same day showed no rows for any host in the property at the time of
checking. GA4 fills that report with a delay of hours to days; the realtime report carries the hits. This is Google-side
latency, not a site defect, and it is **not** claimed as a pass anywhere else in this record.

Correction (2026-11-10, after the independent review): the condition has since resolved. The standard report for
`2026-11-10` filtered to `streamName = contract.place` now returns three rows — `first_visit 1`, `page_view 1`,
`session_start 1`, all on host `contract.place` — and the property-wide report lists `contract.place` next to the other
streams. The limitation above is kept as a record of what was true at the author's moment; it is no longer observable.

## AC7 — Secret hygiene

Criterion: no credentials, tokens, private keys or secret-adjacent values are committed in the diff of either
repository; only the public measurement ID appears.

Author verdict: **PASS**

Evidence:

- The diffs of PR #31 (`contract-place-site`) and PR #178 (`arcanada-landing`) contain no credential value; the
  only Google identifier added is the public measurement ID `G-C5J1NVE11Z`.
- The GA4 OAuth token stayed on the operator's machine at `<local GA4 OAuth token path>` (mode 0600) and
  was never committed, echoed into a log or written into the workspace.
- Secrets live only under `config/credentials/` (gitignored) on the operator's machine.

## Author-side summary

| criterion | author verdict | independent reviewer verdict (exact head) |
|---|---|---|
| AC1 — data stream and measurement ID | PASS | PASS |
| AC2 — consent gate before any GA request | PASS | PASS |
| AC3 — consent state, dismissal, re-opening, localisation | PASS | PASS |
| AC4 — origin CSP allows GA and stays strict | PASS | PASS |
| AC5 — gates green, static-publication constraints hold | PASS | PASS |
| AC6 — GA4 receives the data | PASS | PASS |
| AC7 — secret hygiene | PASS | PASS |

The independent reviewer examined the exact heads `e01585a` (contract-place-site) and `7e2bece` (arcanada-landing) and
recorded its own verdict per criterion, with the commands behind each one, in `docs/kcp-ga4-independent-review.md`. Its
overall verdict is PASS (7/7).

## Corrections recorded after the independent review (2026-11-10)

Provenance: an independent verifier (read-only) reviewed this work item on 2026-11-10 and reported three deviations
from this record. None of them is a defect in the delivered change; the first two were corrected in this file before it
was published, the third is retained as an appended note rather than rewritten away.

1. **CI run citation corrected.** This record originally cited CI run `42767664452` for AC5. That run's head is
   `fe24d012`, not the reviewed head. The run that covers `e01585a` is **42768514094** (CI, success, 4 jobs) and the
   deploy run is **42768542087** (success). The corrected ids are in the AC5 block above.
2. **Consent storage medium stated precisely.** The original AC3 wording read like an HTTP cookie. The choice is
   stored in `localStorage['cookie-consent']` with the values `accepted` and `functional`; Google's own cookies are
   set only after consent. The key and value names are exactly as required. Corrected in the AC3 block above.
3. **AC6 limitation appended as resolved.** The standard GA4 report was empty at the author's moment and now returns
   the three events for `contract.place`. The original limitation is kept and the resolution appended in the AC6
   block above.

The reviewer additionally noted (informational, not a discrepancy in the criteria) that the site hygiene gate
`scripts/check_hygiene.py` now models the production CSP as `script-src 'self' https://www.googletagmanager.com`
instead of `script-src 'self'`. The gate still forbids inline script, style and handlers, and the reviewer verified
independently that no built page carries any external subresource.

The author-side machine-readable record of the same change — impact set, per-entity verdicts, deployment runs and
runtime acceptance measurements — is `docs/kcp-ga4-change-admission-receipt.json`
(`ChangeAdmissionReceipt/v1`).
