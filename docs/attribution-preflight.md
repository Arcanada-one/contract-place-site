# Attribution preflight for single-study journal issues

Status: a bounded automated check in CI. It does not replace the human byline review.

## What it checks

`scripts/check_attribution.py` reads `attribution-scope.json`. For each entry it:

1. hashes the checker, the pinned STUDY file and each locale file (`en.md`, `ru.md`, `zh-Hans.md`) the way `git hash-object` does, and fails with exit 2, naming the file, when a blob differs from its pin;
2. runs `python3 -I scripts/attribution/test_attribution_cardinality.py --check STUDY EN RU ZH` and fails the job on any exit code other than 0.

The checker is a byte-identical copy of blob `759e3229217c1e26d0fdb33903a64e1dfcb3477f` from `Arcanada-one/arcanada-workspace` (commit `23743e9d`, workspace PR #1928, merged). Its licence is Apache-2.0, declared in the file's own SPDX header by its author KC-Brain (mail 20261115T121519Z-49f473fd); DEUS-Arcana passed the exact blob (mail 20261115T122031Z-b03295bf). Do not edit it; a new checker version is a new reviewed copy with a new pin.

## Codes

| Code | Meaning | CI |
| --- | --- | --- |
| 0 | No bounded single-author pattern matched | pass |
| 1 | DEFECT: an explicit contradiction to the study's sole author | fail |
| 2 | UNKNOWN (missing or unsupported author metadata, unreadable input) or a pin mismatch | fail |
| 3 | REVIEW_REQUIRED: ambiguous or externally attributed plural wording | fail |

## Limit

Exit 0 means only that the bounded patterns did not match. It is not scientific acceptance, not language acceptance and not a byline review. A human still reviews the byline of every issue.

## Scope: single study only

The scope is `"single-study"`: one issue built from one study with one author. Do not add an issue that draws on several studies unless a reviewed byline mapping (which statement belongs to which study and author) exists first. The checker has no such mapping.

## Add an issue

1. Review the issue and its single source study by hand, including the byline.
2. Add one entry to `attribution-scope.json` with the issue directory, the study repository, commit, path and blob, the three locale files with their blobs (`git hash-object <file>`) and the checker path and blob.
3. If the study commit differs from the existing entry, add a source checkout for it in `.github/workflows/check-publication.yml` (the workflow currently asserts exactly one entry).
4. Run locally against a checkout of the study commit:

```sh
python3 -B scripts/check_attribution.py --source-dir /absolute/path/to/knowledge-contract
ATTRIBUTION_SOURCE_DIR=/absolute/path/to/knowledge-contract python3 -B scripts/test_check_attribution.py
```

## Re-pin on change

A changed locale file, STUDY or checker fails with a pin mismatch (exit 2) until the entry is re-pinned. Re-pin only after the changed text has been reviewed again; the re-pin commit is the record of that review. A re-pinned file is then judged by the checker as usual.

## Tests

`scripts/test_check_attribution.py` (stdlib, temp dirs only) covers: the real pinned entry gives 0; the historical Russian text (blob `be2047af7955…`, PR 50, kept as `scripts/fixtures/attribution/ru-be2047af7955-pr50.md`) gives checker exit 3; one-byte changes to a locale file or the checker without re-pinning give exit 2; a STUDY with `author: "Lee and Kim"` and a refreshed pin gives a non-zero exit.
