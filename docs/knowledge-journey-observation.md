# Knowledge Journey observation consumer

This consumer makes an existing, decoded Knowledge Collective observation state
inspectable on `/{en,ru,zh-Hans}/lab/knowledge-journey/`. It renders graph records,
selectable nodes, edges and crosslinks, the retained event timeline and artifact
metadata. The public page remains empty and unconnected until a protected reader
explicitly supplies a state. This change installs no reader or execution service.

## One implementation of observations

`src/site/lab/observation-inspector.b35b9e7e.js` is the unchanged browser inspector
from `Arcanada-one/arcanada-shared` commit
`3ae9a8649a63b545dc2385264d8ce8c4264c1f3c`, source path
`packages/access-contracts/browser/observation-inspector.js`.
Its SHA-256 is
`b35b9e7e30ee08c870434bfada3f77a596aac3d9d687e2017775f6cb31084b97`.
The same bytes are used by Arcanada Agent Runs. A source pin is an identity; it is
not independent acceptance of a new consumer or evidence of a deployment.

The decoder and both projectors are the existing packaged shared module from
`46ab74e636993c6fca3ff31b9f030534f5e64876`, already vendored by Arcanada Landing.
`OBSERVATION-PROVENANCE.json` records the exact retrieval commit, paths, hashes,
licence and test-fixture origins. Both vendors remain MIT. Site glue remains
Apache-2.0. There is no second wire parser, reducer, join algorithm or status model.

## Protected reader interface

An integration includes the pinned stylesheet and imports the module from an external script. The current public page has neither an automatic mount nor a reader bootstrap. These hashes identify the exact prepared bytes:

```html
<link rel="stylesheet" href="/lab/knowledge-journey-observation.css?v=34ce415ffbc8185eb6c59334a5c102cc9a6baecb49abe514031be8f35b350bf8">
```

```js
import { mountKnowledgeJourneyObservation } from '/lab/knowledge-journey-observation.js?v=a6b33aeec81c2c5b5287795c7ffa8d563519951fd659842c21cbe1c42e538f33';

const root = document.querySelector('[data-live-lab="knowledge-journey"]');
const surface = mountKnowledgeJourneyObservation({ document, root });

// Called only by the protected reader after its normal decoder and scope binding.
surface.update(observationReducerState);

// Navigation and authorization lifecycle are owned by that same reader.
surface.clear();   // Drop displayed private records immediately.
surface.destroy(); // Dispose controls before leaving the page or changing reader.
```

The optional `state` mount argument performs the initial `update`. `select(kind,
key)` selects a retained node, edge, crosslink, event, evidence reference or artifact;
it returns false when that exact identity is not retained. `update` returns the two
shared projections, or an explicit `unconnected`, `unavailable` or `disposed` result.
The mount is synchronous and replaces the entire displayed projection from one
state. It does not independently accept graph and detail objects from different
runs. Replacing a mount on the same root disposes the previous controller.

Only the protected reader may supply state. A JS object with the reducer schema
tag is not proof of authorization. The tag check refuses accidental raw-record
input; it is not a security boundary. The reader must verify access and identity,
run the existing shared decoder/reducer, handle its refusals and snapshots, and
call `clear` or `destroy` on read failure, logout, scope change or route disposal.
An events-only export cannot be promoted into a complete graph by this consumer.

No state is obtained from page JSON, URL parameters, custom DOM events, browser
storage or a global data object. There is no automatic bootstrap, network request,
new endpoint or service-key handling. No fixture is installed as a public source.

## Visible boundaries

The projected mode, freshness, stale flag, cursor and plan revision are displayed
without upgrading fixture or replay data to live evidence. The existing
`data-live-lab-state="unconnected"` and disabled upload/start controls remain
unchanged. Observation display is separate from permission to execute a job.

All record text uses text nodes and isolated `bdi` elements. Selection shows the
exact qualified identity and evidence references. Only an exact retained artifact
record ID resolves a reference; no relationship is inferred from a similar name.
Artifact locators are never rendered. File-open controls remain disabled pending
a protected file reader and current authorization plus byte checks.

The shared inspector retains source and independent verdicts separately. Its
timeline preserves the reducer's retained applied-event order and three clocks;
it does not invent progress, reorder by timestamps or claim complete history.
Each state update removes the previous graph, detail text and listeners before
projection. A failure displays a localized `NOT_MEASURED` notice without raw error
content. A subsequent valid update removes that notice. Revocation to an empty
shared state restores the original placeholders.

## Verification and publication

`node --test scripts/test_lab_observation.mjs` is part of the existing
`check-publication.yml` renderer step. The tests use the real vendored shared
decoder/reducer/projectors, a small DOM double and existing synthetic records
kept only under `scripts/fixtures/`. They cover idle state, localized graph and
evidence selection, retained event ordering, artifact access boundaries,
revocation, failed projection and recovery, old-controller disposal, text safety
and refusal of raw records. A DOM double does not establish browser layout,
keyboard behavior in a real browser, native ingestion or independent acceptance.

The existing build copies `src/site/` byte for byte before prerendering. This
candidate therefore includes the seven exact `src/site/lab/` asset copies under
`public/lab/`. No renderer or manuscript was executed to prepare those copies.
The consumer temporarily marks the existing empty paragraphs during display and
restores their exact original attribute values (including `hidden="until-found"`)
on clear/disposal; `app.js`, `style.css`, all
prerendered HTML, the catalogue, content provenance and publication pins remain
unchanged. The standalone CSS is included by the eventual protected reader.

The normal pinned publication CI must rebuild and prove the output equal through
its existing clean-tree reproducibility check. The test also compares all seven
source/public asset pairs. No generated HTML is hand-edited, no source hash is
substituted by a guessed value, and no reproducibility gate is weakened.

This candidate has not run a build, tests or a browser in its preparation
environment. The ordinary build/CI and the real protected-reader integration must
be measured separately. Current user-delegation and execution gaps are not solved
by adding the inspector.
