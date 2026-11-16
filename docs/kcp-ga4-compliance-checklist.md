# Task-level compliance checklist — KCP-GA4 (contract.place Google Analytics 4)

> Redaction note (2026-11-10): internal mesh IP addresses and local filesystem paths of the
> development environment were replaced with placeholders before publication. Host names are kept
> because they are already published in the reviewed origin documentation. The unredacted original of
> this document is held in the private task record; the substance of every measurement is unchanged.
> Redaction note (2026-11-10): internal mesh IP addresses and local filesystem paths of the
> development environment were replaced with placeholders before publication. Host names are kept
> because they are already published in the reviewed origin documentation. The unredacted original of
> this document is held in the private task record; the substance of every measurement is unchanged.
Work item: Muneral `093b8ab8-f5c0-4c29-83c6-5b3fe34fa479`
Prepared: 2026-11-10, on the Arcanada dev host `arcana-devs` (`<dev-host mesh address>`)
Heads reviewed: `Arcanada-one/contract-place-site` @ `e01585a`, `Arcanada-one/arcanada-landing` @ `7e2bece`

Verdicts are tri-valued: `PASS`, `FAIL`, `NOT_MEASURED`. `NOT_MEASURED` is neither a pass nor a failure and is not
promoted anywhere in this record.

## 1. Secret scanning and handling — PASS

- The GA4 OAuth token stayed on the operator's machine at `<local GA4 OAuth token path>` (mode 0600). It was
  never written into a repository, a comment, a log or the shared workspace.
- The diffs of PR #31 and PR #178 contain no credential, token, private key or password. The only Google identifier
  added is the public measurement ID `G-C5J1NVE11Z`, which is designed to be published.
- The root broker installed on `arcana-www` is the reviewed public artefact of `ops/nginx/contract-place-install.sh`
  (sha256 `2308c577ff3719da62bb48a9d6fe20877a9cfb5be21619f9f6fea46cc3490cc1`); it carries no secret and reads the
  sudoers boundary from the host.
- Credentials remain under `config/credentials/` on the operator's machine, which is gitignored.

## 2. Public-surface hygiene (public repositories and releases) — PASS

- Both repositories are public. The shipped public surface of `contract-place-site` — `AGENTS.md`, `README.md`, the
  site copy in `src/site/`, the generated pages — is English-only, as required by the public-surface hygiene mandate.
- The new site strings (`Cookie settings`, `Analytics and cookies`, the consent banner in `en` / `ru` / `zh-Hans`) are
  product copy inside the site bundle, not shipped framework instructions; the consent banner in `ru` and `zh-Hans` is
  user-facing localisation of the product surface and is allowed to be non-English.
- The documentation added for this change (`docs/analytics-consent.md`, and the records in `docs/kcp-ga4-*.md`) is
  English, consistent with the artifact language of this workspace.
- No release, tag or marketplace publication was made for this change, so the release half of the mandate has no
  scope here.
- REUSE lint on `contract-place-site`: **403/403 files compliant** before this record was added; the new files are
  covered by the `REUSE.toml` annotations added in the same commit.

## 3. Security policy — PASS

- The origin CSP stays strict. The only change is one rewritten directive pair: `script-src` gained
  `https://*.googletagmanager.com` and `connect-src` gained `https://*.google-analytics.com`. There is no bare `*`, no
  `unsafe-inline`, no scheme source, no `data:` in `script-src`, and no nonce/hash mechanism was removed.
- The GA tag is never referenced from HTML; the browser loads it only from `src/site/analytics.js` after the consent
  decision, so the script source list of the static site gained only the first-party `/analytics.js`.
- Google signals and ad storage are off: `allow_google_signals:false`, `ads_data_redaction:true`, and the ad-storage
  consent is `denied`. In the measured session the only Google hosts requested were `www.googletagmanager.com` and
  `region1.google-analytics.com`.
- The measured browser session produced **0 console errors** and no third-party request before consent.
- `SECURITY.md` in `contract-place-site` is unchanged by this work and remains the reporting surface for it.

## 4. Graph-verified change evidence for program-code changes — PASS

- A `ChangeAdmissionReceipt/v1` was produced for the change: `docs/kcp-ga4-change-admission-receipt.json`. It names
  the impact set (both repositories), every affected entity with its edge type, and a per-entity verdict.
- The impact set was computed before the merge and covers: the site script, loader, styles, template, build script,
  the four gates that changed, the new test file, the licence file, the CI workflow, the regenerated `public/`, and —
  in `arcanada-landing` — the origin config, the root broker, the origin deploy workflow, the origin gate and the
  origin documentation.
- Every entity carries a verdict together with the command or run that produced it. No entity was left unmeasured.

## 5. Publisher-only external publishing — NOT APPLICABLE (scope reason)

The change publishes no content to any social network or external site. Its only outward effect is the deployment of
`contract.place` and of the `contract.place` origin vhost, both performed through the repositories' own
`workflow_dispatch` deploy workflows after merge into `main`. The Publisher mandate governs social and external-site
publications and has no scope here; the "own sites publish by push to `main`" rule was followed.

## 6. Workspace and source-control discipline — PASS

- Every repository change went through a branch and a pull request: `contract-place-site` PR #31, `arcanada-landing`
  PR #178; both merged into `main`. No commit was made directly on `main` and no commit was pushed without review.
- No production server file was edited directly. The origin change was installed through the fixed-digest root broker
  (`ops/nginx/contract-place-install.sh`, sha256-pinned in the workflow) after the documented one-time broker
  bootstrap; the site was published by the repository deploy workflow. The nginx configuration itself is installed by
  the broker from the reviewed `main` commit, not hand-edited on the host.
- Merge to `main` did not deploy: both deploys were explicit `workflow_dispatch` runs (`42767992096` for the origin,
  `42768542087` for the site), in that order — origin CSP first, then the site.
- The shared workspace `~/arcanada` was left clean: no scratch files remain in `dev-tools/`, and the temporary
  worktrees used for the task were removed. Both task checkouts on the dev host are clean at the reviewed heads.
- The GA4 measurement ID and the CSP change introduce no secret into any commit (see item 1).

## 7. Human Outcome Reporting — PASS

- A human-facing outcome report accompanies the close of the work item, in the operator's resolved reply language, and
  states the observed outcome, the meaning of each checked condition, the verification performed, the evidence and the
  material limitations — including the two items that are not a pass: the standard GA4 report latency and the missing
  native editorial review of the `ru` / `zh-Hans` banner copy.
- The reusable records in `docs/` are written in English, the resolved artifact language of this workspace.

## 8. Development-host mandate (Arcanada DEVS only) — PASS

- All implementation, building, gate execution and measurement happened on `arcana-devs`
  (`<dev-host mesh address>`, workspace `<dev-host workspace>`); the operator's Mac was used as a control host for reading,
  review and merge only.
- The one host write outside the dev host — installing the pinned root broker on `arcana-www` — is the documented
  one-time broker bootstrap of `ops/nginx/contract-place-origin.md`, performed with the pinned artefact whose digest
  was verified on the host afterwards, and it changed no site content.

## 9. Legal-0052 consent gate (task-specific mandate) — PASS

- The Google tag is requested only after an explicit reader decision. A cold visit produces **zero** requests to any
  Google analytics host; "Necessary only" keeps it at zero; "Accept analytics" loads the tag and GA collects.
- The consent state is stored as `cookie-consent` with the values `accepted` and `functional`, is readable from the
  footer's "Cookie settings" control, and is presented in `en`, `ru` and `zh-Hans`.

## 10. Independent review against the exact head (DEC-AUP-0168, before review) — PASS

- An independent verifier reviewed the work item on 2026-11-10, read-only, against the exact heads
  `e01585a` (contract-place-site) and `7e2bece` (arcanada-landing), and recorded a separate verdict per criterion:
  AC1 PASS, AC2 PASS, AC3 PASS, AC4 PASS, AC5 PASS, AC6 PASS, AC7 PASS — overall PASS (7/7).
- The review is kept apart from the author's own evidence and is published as `docs/kcp-ga4-independent-review.md` with
  the commands behind every verdict. The verifier did not modify any repository file, commit, push or reset anything;
  the two checkouts were byte-identical before and after the review.
- The reviewer reported three deviations from the author's evidence record (a wrong CI-run citation, an imprecise
  wording of the consent storage medium, and a limitation that had since resolved). The first two were corrected in
  `docs/kcp-ga4-acceptance-evidence.md` before publication; the third is appended there as a dated correction rather
  than rewritten away. None of the three is a defect in the delivered change.

## 11. Task-record carrier — NOT_MEASURED (tooling gap, disclosed)

The acceptance mandate (`documentation/mandates/task-lifecycle-and-acceptance.md`, DEC-AUP-0168) asks for the
criterion-mapped evidence and this compliance checklist to be recorded **as Muneral CONTENT**. The Muneral instance
that serves this task exposes no CONTENT route: the served route table (154 routes) has no content/record/document
route, and `GET`/`POST /tasks/:taskId/checklist` answers `403` for an agent key (`MUN-0043` — the route is JWT-only).
The two carriers that an agent key does hold were used instead:

- `POST /api/v1/tasks/:taskId/evidence` — `WorkItemEvidenceAttachment/v1` records: URI + sha256 + media type, one row
  per artefact, attributed to the agent, written together with an activity entry.
- `POST /api/v1/tasks/:taskId/comments` — the criterion-mapped evidence text, the reviewer verdict and this checklist.

This item is recorded as `NOT_MEASURED` against the literal "Muneral CONTENT" carrier because that carrier was not
reachable for this key; it is **not** a claim that a CONTENT record exists. The substance the mandate asks for —
criterion-mapped evidence with tri-valued verdicts, an independent per-criterion verdict against the exact head, and a
task-level mandate checklist — is recorded through the carriers above and in the durable artefacts linked from them.
Closing the gap requires either a scoped checklist route for agent keys or a CONTENT route on the Muneral API; that is
a Muneral product change, outside this work item.

## Summary

| item | verdict |
|---|---|
| 1. Secret scanning and handling | PASS |
| 2. Public-surface hygiene | PASS |
| 3. Security policy | PASS |
| 4. Graph-verified change evidence | PASS |
| 5. Publisher-only external publishing | NOT APPLICABLE (scope reason) |
| 6. Workspace and source-control discipline | PASS |
| 7. Human Outcome Reporting | PASS |
| 8. Development-host mandate | PASS |
| 9. Legal-0052 consent gate | PASS |
| 10. Independent review against the exact head | PASS (7/7 criteria) |
| 11. Task-record carrier (Muneral CONTENT) | NOT_MEASURED — tooling gap, disclosed |

No item is `FAIL`. One item is `NOT_MEASURED` for a tooling reason, and one is not applicable with a scope reason.
