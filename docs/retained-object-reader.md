# Protected retained-object browser reader

Status: source candidate, not mounted or deployed. This patch prepares a private
file-inspection component for Knowledge Journey. It does not make the public lab
connected, change upload/start controls, add a demo dataset, or claim admission.

## Existing providers and exact source identities

- Arcanada-one/contract-place-api@b56d1db20616e2d734dda052a582c3dfdf87d661,
  src/lab/lab.controller.ts, retained-registry.ts, user-grant.ts and
  docs/lab-app/reference.md: the candidate upstream routes are
  GET /v1/lab/user/objects and GET /v1/lab/user/objects/:objectId.
  Production has no UserGrantAuthority; the user subtree stays unavailable.
  The candidate Lab is a separate process, absent from the public image.
- Arcanada-one/arcanada-shared@3ae9a8649a63b545dc2385264d8ce8c4264c1f3c,
  packages/oidc-bff/src/index.ts, store.ts, live-lab-sites.ts and README:
  the existing browser identity route is GET /api/auth/session.
  It returns identity only: {authenticated:true,subject}. It does not grant
  access to files, and its cookies/tokens remain server-controlled.
- The existing site access-contracts.46ab74e.js supplies parseBoundedJson.
  This patch adds domain checks for the retained list, not another JSON parser.
- Site base: Arcanada-one/contract-place-site
  4b9f27720ff06fe7a1ec6b2c38a6005f87c9041a (merged PR46).

The private object list is a closed RetainedObjectList/v1 with objects:
id, run_id, media_type, size, sha256. It has no locators, graph,
snapshot, trusted observation binding or accepted semantic objects. The UI
therefore displays exactly those entries and separately verifies requested
bytes. It does not synthesize an observation graph from names or counts.

## Missing production port

There is no approved same-origin browser mapping for the upstream user routes.
The host must supply objectListPath after its BFF mapping is admitted. This
option has no default. Passing no mapping returns null and sends no request,
including no identity probe. The module has no import-time bootstrap.

The supplied path must be an exact origin-relative path ending in /objects,
with ordinary fixed path segments and no query, fragment, traversal or service
credential endpoint. It is host configuration in reviewed code, never a URL
parameter, page JSON, user input or browser storage. The origin is the host's
actual HTTPS origin; the browser also enforces Fetch mode: same-origin.

createSameOriginRetainedTransport sends only GET requests with
credentials: same-origin, cache: no-store, redirect: error,
referrerPolicy: no-referrer and Accept. It never creates or forwards a
bearer, subject header, tenant ID, storage path, project identity or grant.
An injected transport must implement the same three methods:

| Method | Input | Response |
| --- | --- | --- |
| session | {signal} | Same-origin identity response from /api/auth/session |
| list | {signal} | Current user-authorized RetainedObjectList/v1 |
| read | {id,signal} | Current user-authorized exact representation bytes |

Each method returns a Fetch Response, honors cancellation and uses the
admitted same-origin mapping. Only the server decides authorization. Its BFF
must reuse the existing BrowserIdentity and mandatory durable SessionStore,
authenticate the current HttpOnly session, obtain issuer-verifiable delegated
READ, and pass that credential to the separate Lab process server-side.
Implementing this browser port does not implement the server store, delegation,
revocation authority, process deployment or network route.

The native byte response must preserve its exact Content-Type,
X-Object-Sha256, X-Object-Size, quoted digest ETag and
Content-Disposition: attachment. Responses must be non-redirected HTTP 200
with Cache-Control: no-store; the bytes must match both the listed size and
SHA-256. No browser action treats an observed digest as authorization.

## Explicit host integration

After the missing port is approved, the host imports the module from an external
script, supplies its admitted configuration, then calls
mountRetainedObjectReader({document, root, transport}) with the existing
[data-live-lab="knowledge-journey"] root. The mount performs no request.
The user explicitly presses “Read permitted files” and then “Inspect bytes.”

Do not install a guessed sample production path. Do not repurpose the fixture
/v1/lab/service/** routes or expose their credentials. Do not silently fall
back to public fixture data.

The mount appends a separate retained-files section. It does not overwrite
mountKnowledgeJourneyObservation, the existing graph, the observed event
timeline, the page's connection state or its disabled execution controls.
When a trusted observation producer and user-bound snapshot exist, their
existing consumer remains a separate mount.

## Lifecycle and data boundaries

The controller keeps a finite list and current text only in memory. It uses no
local storage, service worker, object URL, iframe, download link or HTML/Markdown
renderer. Only text/plain, text/markdown and application/json receive a
strict UTF-8 inert text view. Other media types get size/hash verification and
an explicit unavailable-inline-preview message.

Refresh discards the old list and content before requesting a new one. Opening
another item discards the former text immediately. Identity is checked before
and after each list/read sequence. A changed principal, denied request,
unavailable authority, malformed response, digest mismatch or timeout clears
the private model. Generation fencing prevents late success after clearing,
replacement or disposal from restoring data.

Before enabling this mount, the host must connect its existing invalidation
mechanism to clear() or destroy(). It must clear **synchronously before**
logout, account change, session-generation change or project/view change, and
on cross-tab session invalidation. Do not wait for the logout request to finish.
Even logout followed by login as the same person is a new session boundary;
the identical subject string cannot detect or authorize it. No new browser
session protocol is defined by this component.

The mount also clears on visibilitychange away from visible and on pagehide.
There is no polling or claim of instantaneous server-revocation detection:
a retained readable response cannot itself supply a new authorization lease.
A session ID/generation is not exposed by the existing identity API; the host
owns synchronous invalidation and the backend owns exact session/grant
enforcement. Merely implementing the three transport methods is insufficient
for production mounting without these lifecycle hooks.

The local 10-second default request timeout bounds UI work; it is not an Auth
deadline or a measured service budget. Tests inject a shorter timeout.
The object byte cap is 8 MiB. This is a browser cap equal to the native registry
schema maximum and LAB_MAX_RESPONSE_BYTES configuration maximum, not a claim
about the active server setting (its response default is 1 MiB).
The whole-list cap is 65,532 bytes, inherited from the existing shared parser;
a larger permitted native list is refused whole and never silently truncated.
The native entry ceiling remains 2,048, and one list must refer to one run.
These browser limits do not establish support for every valid larger registry.

## Origin integration requirement

At Landing 376011fb46c3783a6946749e29ae57fd6326b2f5,
ops/nginx/contract.place.conf has a static try_files route only and
connect-src https://api.contract.place https://*.google-analytics.com,
without 'self'. The admitted BFF mapping needs an origin route and a scoped
CSP update by the existing owner through the separate origin deployment
workflow. Shipping this component alone changes no origin policy.

## Verification and release scope

node --test scripts/test_retained_object_reader.mjs is added to the ordinary
check-publication.yml renderer lane. Cases exercise the real shared strict
parser and WebCrypto, synthetic native-shaped lists/bytes, Fetch streams and a
small DOM double. They cover absent configuration, path/redirect refusal,
schema and size bounds, missing grants, exact byte checks, changed identity,
late responses, timeout and private DOM clearing.

The existing build copies src/site/ into public/. The candidate includes the
exact public asset copy and leaves HTML, manuscript/catalogue pins, app.js and
the public bootstrap unchanged. Normal publication CI must reproduce it.

No project code, tests, build or browser was executed during source preparation.
Static source review and byte-copy comparison are not test success.
Required next evidence is ordinary CI, bounded non-author source review,
approved native BFF/delegation/process wiring, browser qualification using the
actual retained files, and deployed route/asset/header readback.
