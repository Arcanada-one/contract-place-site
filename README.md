# Knowledge Contract Arcana

Knowledge Contract Arcana is an Arcanada research project on preserving the source, scope, evidence, and conditions of use when people and agents reuse knowledge. Its current Knowledge Contract target is `3.0.0-draft.1`; the specification and experiments remain in progress.

The project is about managing knowledge and its reuse by people and agents: contracts for managing the heritage of human knowledge, designed to replace hand-written skills, rules and prompt files kept in each agent harness with one unified, self-evolving knowledge contract that the community and contributors improve. The unified contract, the self-evolution loop, community intake, the sourced corpus and search/MCP access are planned, not built. The backend engine stays closed and proprietary; whatever knowledge is published is open.

This repository contains the static placeholder for [contract.place](https://contract.place). It publishes only the files in `public/`. Research materials and an API will be added through their own repositories when ready.

Read the [research repository](https://github.com/Arcanada-one/knowledge-contract), the [Arcanada project page](https://arcanada.ai/en/ecosystem/contract-place), and the existing [architecture](https://arcanada.ai/en/blog/meaning-management-knowledge-contract-architecture) and [version 2](https://arcanada.ai/en/blog/meaning-management-knowledge-contract-v2) articles. The site and repository link to each other.

## Preview

Run `python3 -m http.server 8000 --directory public`, then open `http://localhost:8000/`.

## Deployment

The `deploy` workflow calls the pinned shared static-site workflow. It publishes `public/` into the `contract.place` webroot on the site runner. Deployment is manual while the domain and origin are being configured.

## Licensing

Site content is licensed under [CC BY 4.0](LICENSE) and site code under [Apache-2.0](LICENSE-CODE). Reuse, including commercial and derivative projects, is free on the condition that you credit the author and link to the source (https://contract.place); keep the [NOTICE](NOTICE) and any upstream source credits. Credit lines are in [ATTRIBUTION.md](https://github.com/Arcanada-one/knowledge-contract/blob/main/ATTRIBUTION.md) and in the "Use and cite" section of the site. The names "Knowledge Contract Arcana" and "Arcanada" and any logos are not licensed. Contributions are accepted under the Developer Certificate of Origin (sign off commits with `git commit -s`).

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
