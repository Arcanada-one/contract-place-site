# Contract Place

Contract Place is the planned public home for Knowledge Contract rules, research papers, and implementation resources. Knowledge Contract is a research effort toward a verifiable way to decide what an agent may know, reuse, and act on. Its current target is `3.0.0-draft.1`; the specification and experiments remain in progress.

This repository contains the static placeholder for [contract.place](https://contract.place). It publishes only the files in `public/`. Research materials and an API will be added through their own repositories when ready.

## Preview

Run `python3 -m http.server 8000 --directory public`, then open `http://localhost:8000/`.

## Deployment

The `deploy` workflow calls the pinned shared static-site workflow. It publishes `public/` into the `contract.place` webroot on the site runner. Deployment is manual while the domain and origin are being configured.

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
