# Analytics and consent

The site measures how the published documents are read with Google Analytics 4. The
measurement stream is `G-C5J1NVE11Z` in the Arcanada Ecosystem property, and the reader
is identified by a first-party Google identifier stored in the reader's own browser.

## The gate

`src/site/analytics.js` is the only code that talks to Google. It is loaded as a plain
script from the site's own origin (`/analytics.js`) and it never asks Google for anything
until the reader makes an explicit choice:

| Stored choice | Google tag | Data leaves the browser |
|---|---|---|
| none (first visit) | not requested; the banner is shown | no |
| `accepted` | requested from `www.googletagmanager.com` | yes, analytics only |
| `functional` | not requested | no |

The choice is stored in `localStorage` under `cookie-consent` and can be changed at any
time from the **Cookie settings** button in the footer. The banner text follows the
interface language (English, Russian, Chinese).

The Google tag is requested from JavaScript, never from an inline `<script>` element and
never from a `src` attribute in the HTML. The site's content security policy keeps
`script-src 'self'` for everything else, so the tag is the only remote script the origin
serves.

## What is sent

- Consent Mode v2 defaults: `analytics_storage` granted, `ad_storage`, `ad_user_data` and
  `ad_personalization` denied.
- `ads_data_redaction` is on and Google signals are off, so no advertising identifiers or
  signal data are collected.
- A `page_view` event carries the current location and title; client-side navigation
  reports the new page.

## What is not sent

- No request reaches Google before the reader accepts analytics.
- No advertising data, no cross-site identifiers, no Google signals.
- The consent choice itself is never transmitted.

## Origin policy

The origin vhost (`Arcanada-one/arcanada-landing`, `ops/nginx/contract.place.conf`) allows
exactly two Google hosts: `https://*.googletagmanager.com` for the tag script and
`https://*.google-analytics.com` for the regional collection endpoint. The wildcard is
scoped to Google-owned hosts; there is no bare `*`, no `unsafe-inline` and no scheme
source in the policy.

## Checks

- `node scripts/test_analytics.js` — the consent gate: no tag without consent, one tag with
  consent, the stored choices, consent defaults, no page view before the tag exists, and
  the banner text following the interface language.
- `python3 -B scripts/check_hygiene.py .` — no inline script or style under the production
  policy, and the analytics loader is checked as a template.
- The ecosystem gate `dev-tools/check-ga4-consent-gate.mjs` checks a live page in a real
  browser: no Google request without consent, the tag request with consent.
