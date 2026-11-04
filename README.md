# Knowledge Contract Arcana

Knowledge Contract Arcana is an Arcanada research project on preserving the source, scope, evidence, and conditions of use when people and agents reuse knowledge. Its current Knowledge Contract target is `3.0.0-draft.1`; the specification and experiments remain in progress.

The project is about managing knowledge and its reuse by people and agents: contracts for managing the heritage of human knowledge, designed to replace hand-written skills, rules and prompt files kept in each agent harness with one unified, self-evolving knowledge contract that the community and contributors improve. The unified contract, the self-evolution loop, community intake and the sourced corpus are planned, not built. The first Meaning Management release (14 papers and 10 specifications, scientific drafts, Russian full texts with English entry pages) is published in the research repository and listed on the site under Research and Specifications. A read-only HTTP API (search, related, fetch) is live at https://api.contract.place over the published documents (measured 2026-10-31), and an MCP endpoint at https://api.contract.place/mcp answered an initialize request on 2026-11-03. The search page (`/en/search#document-search`, script `search.js`) calls the search route with anonymous GET requests and lists passages in the order the API returns them; it states no relevance threshold. The API accepts browser requests from the `https://contract.place` origin only. The backend engine stays closed and proprietary; whatever knowledge is published is open.

This repository contains the static site for [contract.place](https://contract.place) in three interface languages (English, Russian, Chinese; the Chinese interface has not received native editorial review). The editable source is in `src/`; `node build.mjs` generates `public/`, which is the only directory published. Research materials stay in their own repositories.

Read the [research repository](https://github.com/Arcanada-one/knowledge-contract), the [Arcanada project page](https://arcanada.ai/en/ecosystem/contract-place), and the existing [architecture](https://arcanada.ai/en/blog/meaning-management-knowledge-contract-architecture) and [version 2](https://arcanada.ai/en/blog/meaning-management-knowledge-contract-v2) articles. The site and repository link to each other.

## Build and preview

- Edit `src/content/catalog.json` (papers, specifications, articles), `src/site/app.js` (interface text and templates), `src/site/style.css`, `src/site/assets/`. Change the `?v=` query in `src/site/index.html` when `app.js` or `style.css` change.
- Run `node build.mjs` (Node.js 20.11 or newer, no dependencies). It rewrites `public/` completely: static files, `content.js`, `robots.txt`, `llms.txt`, `sitemap.xml` and all prerendered routes. Commit `public/` together with `src/`; CI rebuilds and fails if `public/` differs.
- Preview with `python3 -m http.server 8000 --directory public`, then open `http://localhost:8000/en/`.
- Checks: `python3 scripts/check_page.py public`, `python3 scripts/check_papers.py public`, `python3 scripts/check_links.py public`, `node scripts/test_search.js`.

## Deployment

The `deploy` workflow calls the pinned shared static-site workflow. It publishes `public/` into the `contract.place` webroot on the site runner. Deployment is manual while the domain and origin are being configured.

## Licensing

Site content is licensed under [CC BY 4.0](LICENSE) and site code under [Apache-2.0](LICENSE-CODE). Reuse, including commercial and derivative projects, is free on the condition that you credit the author and link to the source (https://contract.place); keep the [NOTICE](NOTICE) and any upstream source credits. Credit lines are in [ATTRIBUTION.md](https://github.com/Arcanada-one/knowledge-contract/blob/main/ATTRIBUTION.md) and in the "Use and cite" section of the site. The names "Knowledge Contract Arcana" and "Arcanada" and any logos are not licensed. Contributions are accepted under the Developer Certificate of Origin (sign off commits with `git commit -s`).

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
