# Books page: retained registry snapshot

This repairs the existing [PR #17](https://github.com/Arcanada-one/contract-place-site/pull/17)
on site main `d3d17929f209612669f38db6a735d46bc9ec309c`, preserving the earlier
candidate `8718188398b9286b5f255cabce7fcf9ebb216c43`. The old candidate conflicted
with the current interface and generated pages. Its book-list source change was
not already included in main, and PR #18 did not contain that source change
despite extensive overlap in generated filenames.

## Exact historical evidence

The existing candidate already names books-library revision
`75f9d778c5159f1e42366b2c36167c0f33790909`. On 16 November 2026, an authorised
read of that exact revision established:

| Field | Observed value |
| --- | --- |
| Repository | `Arcanada-one/books-library` |
| Register path | `registry/registry.json` |
| Git blob | `03a51a17b4cb593b41a4b14ea77cff1b772d28de` |
| SHA-256 of exact UTF-8 bytes | `701c0f7194b38bf16e95f1a4d30e6b34acb3a33861e868f17b0d56b0188a2901` |
| Source schema | `BooksLibraryRegistry/v1` |
| Entries | `[]` |

The registry is empty at this historical revision. This does not establish an
empty current library, the absence of books elsewhere, rights for a later title,
or approval to publish or redistribute a book. The source repository is private
at this observation. The page retains the repository and full revision identity
already identified by PR #17, as plain text; it does not promise a publicly
accessible source link or copy any private title, package, rights record or
book-source bytes.

`LIBRARY_INDEX` remains the site's bounded display projection of this retained
empty register, not a live importer or the authoritative library registry.
English, Russian and Simplified Chinese separately label the historical scope,
the scoped entry count and the absence of a publication grant. The previous
unqualified sentence about no books or redistribution licences is replaced.

## Repair and verification

Port the authored Books renderer into the current interface, use its existing
HTML escaping and table scrolling, and rebuild generated pages. Retain the
publication pin `39e4054830d9cb05bc0432d25f7320cb8a97f054`, independent roadmap
pin `55e279c43dc9bcf8732467a32661c2ac4b7cf920`, 31-work catalogue, all current
routes and rendition review states. Do not import the old PR's generated HTML.

`node scripts/test_books_snapshot.js` checks the actual app renderer and all
three generated Books pages against the retained registry identity, full visible
revision, count and historical/authority qualifications. Four concrete mutants
change the source pin, count, historical notice and visible revision; every
locale must detect each. An unrelated presentation change remains valid. A
single synthetic damaged row checks escaping and damage labelling but never
enters the committed display data. The stock publication workflow executes this
test; its hosted run and checkout still need to be observed for a candidate.

These checks establish bounded representation fidelity, not authenticated
library intake, new rights acceptance, independent linguistic review or native
Knowledge Contract admission. Later library data needs fresh exact-source and
rights review; no current state is inferred from this historical snapshot.

### Local preparation result, 16 November 2026

With Node 24.22.1 and Pandoc 3.1.3, the full pinned compiler completed: 31 works,
62 rendition pairs and 322 HTML files. The seven publication, hygiene, page,
paper, link, roadmap and complete-localization commands passed. The link check
examined 19,106 internal links; its 332 external addresses were not fetched.
Existing UI/navigation tests passed all 491 controls. The Books test passed 13
positive controls and detected all four applied mutants in each of three
languages (12 adverse locale checks). Its one damaged row remained synthetic.

An exact inventory comparison retained every one of the 322 HTML paths. After
normalising only the `app.js` and `style.css` content-hash query values, the
only changed page bodies were the three Books pages. Publication and roadmap
manifests, compiled catalogue, content provenance, `publication.json` and
`content.js` remained byte-identical to the current main baseline.

Preparation also retained environment failures: a narrowed PATH first omitted
Node, and a separate rebuild using the default Pandoc 3.1.11.1 was refused by
the existing version check. The corrected commands prepend Pandoc 3.1.3 while
retaining the inherited Node path. A generated-page check attempted before
the first successful rebuild correctly rejected the still-old Books HTML.
These attempts are separate from the final successful build and regression
results; no version or output check was relaxed.

Non-author review, exact-head hosted checks, release and served/browser checks
remain distinct from local preparation. Rollback keeps site `d3d17929` and its
source pin and generated files together. No second PR, task, worker, private
library mutation or manuscript/roadmap pin update is part of this repair.
