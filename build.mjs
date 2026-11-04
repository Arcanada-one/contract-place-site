// Reproducible build: src/ -> public/ (the published directory). Run from the repository root: node build.mjs
// CI re-runs it and fails if public/ differs from what is committed.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const root = import.meta.dirname;
const src = path.join(root, 'src');
const out = path.join(root, 'public');
const data = JSON.parse(fs.readFileSync(path.join(src, 'content/catalog.json'), 'utf8'));
if (!Array.isArray(data.records) || !Array.isArray(data.articles)) throw new Error('catalog.json requires records and articles arrays.');
const seen = new Set();
for (const r of data.records) {
  if (!['paper', 'spec'].includes(r.kind) || typeof r.id !== 'string' || !r.id) throw new Error('Each record needs a paper/spec kind and an id.');
  const key = r.kind + '/' + r.id;
  if (seen.has(key)) throw new Error('Duplicate record: ' + key);
  seen.add(key);
}

fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(path.join(src, 'site'), out, { recursive: true });
fs.copyFileSync(path.join(out, 'assets/favicon.svg'), path.join(out, 'favicon.svg'));
fs.writeFileSync(path.join(out, 'content.js'), 'window.CP_CONTENT = ' + JSON.stringify(data) + ';\n');

// robots.txt: the public site is indexable (the design kit shipped a private-preview "Disallow: /").
fs.writeFileSync(path.join(out, 'robots.txt'), 'User-agent: *\nAllow: /\nSitemap: https://contract.place/sitemap.xml\n');

// llms.txt: structure of the site and the published corpus, generated from the catalog so it cannot drift.
const base = 'https://contract.place';
const line = (r) => `- ${r.id.toUpperCase()} ${r.title}: ${base}/en/${r.kind === 'paper' ? 'research' : 'docs'}/${r.id}/ (English entry page), ${r.russian} (Russian full text)`;
const papers = data.records.filter((r) => r.kind === 'paper');
const specs = data.records.filter((r) => r.kind === 'spec');
fs.writeFileSync(path.join(out, 'llms.txt'), `# Knowledge Contract Arcana

> Public research hub for scoped, evidenced knowledge reuse, at contract.place. Part of the Arcanada ecosystem (https://arcanada.ai). The specification and experiments are in progress; 3.0.0-draft.1 is a target, not a released protocol.

- Home: ${base}/ (languages: ${base}/en/, ${base}/ru/, ${base}/zh-Hans/; the Chinese interface has not received native editorial review)
- Research (papers): ${base}/en/research/
- Specifications: ${base}/en/docs/
- Journal: ${base}/en/journal/
- Full-document search: ${base}/en/search/#document-search
- Use and cite (licences): ${base}/en/about/
- Knowledge Contract repository: https://github.com/Arcanada-one/knowledge-contract
- Site source: https://github.com/Arcanada-one/contract-place-site
- Ecosystem: https://arcanada.ai/
- Architecture article: https://arcanada.ai/en/blog/meaning-management-knowledge-contract-architecture
- Version 2 article: https://arcanada.ai/en/blog/meaning-management-knowledge-contract-v2

## Access

Read-only HTTP API at https://api.contract.place (search, related, fetch over the published documents; schema ContractPlaceRead/v1) and an MCP endpoint at https://api.contract.place/mcp. The site search page calls /v1/search with anonymous GET requests and lists passages in the order the API returns them; it states no relevance threshold.

## Papers

Meaning Management, first release: ${papers.length} papers and ${specs.length} specifications, published as scientific drafts (concept level). Independent semantic review has not been performed. Russian full texts are the originals; English entry pages are summaries, not translations. Text is CC BY 4.0.

${papers.map(line).join('\n')}

## Specifications

${specs.map(line).join('\n')}

## License and attribution

Reuse allowed under CC BY 4.0; credit Knowledge Contract Arcana, https://contract.place; keep upstream source credits. Code is Apache-2.0. Attribution guidance: https://github.com/Arcanada-one/knowledge-contract/blob/main/ATTRIBUTION.md
`);

const r = spawnSync(process.execPath, [path.join(src, 'prerender.mjs'), out], { cwd: root, stdio: 'inherit' });
if (r.error) throw r.error;
process.exit(r.status ?? 1);
