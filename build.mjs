// Reproduce the compiled publication and localized interface without network access.
// Compile the canonical Markdown first with scripts/build_publication.py.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const root=import.meta.dirname,src=path.join(root,'src'),out=path.join(root,'public');
const data=JSON.parse(fs.readFileSync(path.join(src,'content/catalog.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'publication-manifest.json'),'utf8'));
for(const key of ['schema_version','repository','commit','edition','catalog'])
  if(data.publication?.[key]!==manifest[key])throw new Error('Compiled publication pin mismatch: '+key);
if(!/^[0-9a-f]{40}$/.test(manifest.commit)||manifest.repository!=='Arcanada-one/knowledge-contract')throw new Error('Invalid source pin');
const seen=new Set();
for(const r of data.records){
  if(!r.canonical||!['paper','spec','study','glossary','bibliography','appendix'].includes(r.kind))throw new Error('Unknown canonical document kind');
  if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(r.id)||!r.route.startsWith('/en/')||!r.route.endsWith('/'))throw new Error('Invalid readable route');
  if(seen.has(r.route))throw new Error('Duplicate publication route');seen.add(r.route);
  if(r.revision!==manifest.commit||!/^[0-9a-f]{64}$/.test(r.source_sha256))throw new Error('Unbound source revision');
  if(r.source!=='https://github.com/'+manifest.repository+'/blob/'+manifest.commit+'/'+r.path)throw new Error('Unpinned source URL');
}
for(const [alias,target] of Object.entries(data.aliases))
  if(!/^[a-z0-9/-]+$/.test(alias)||!seen.has('/en/'+target+'/'))throw new Error('Invalid compatibility route');
// Earlier reader URLs remain navigable without competing with the locale routes.
data.reader_aliases={
  science:'/en/science/',engineering:'/en/engineering/',
  'engineering/specifications':'/en/engineering/specifications/',
  'engineering/studies':'/en/engineering/studies/',
  reference:'/en/reference/',appendices:'/en/appendices/',search:'/en/search/'
};
for(const record of data.records)data.reader_aliases[record.route.replace(/^\/en\//,'').replace(/\/$/,'')]=record.route;
fs.rmSync(out,{recursive:true,force:true});
fs.cpSync(path.join(src,'site'),out,{recursive:true});
// A previously cached catalog must never replace a new prerendered edition.
// The source pin is an immutable cache identity shared by every localized page.
const template=fs.readFileSync(path.join(out,'index.html'),'utf8');
fs.writeFileSync(path.join(out,'index.html'),template.replace(/src="\/content\.js(?:\?[^"]*)?"/g,'src="/content.js?v='+manifest.commit+'"'));
fs.copyFileSync(path.join(out,'assets/favicon.svg'),path.join(out,'favicon.svg'));
fs.writeFileSync(path.join(out,'content.js'),'window.CP_CONTENT = '+JSON.stringify(data)+';\n');
fs.writeFileSync(path.join(out,'robots.txt'),'User-agent: *\nAllow: /\nSitemap: https://contract.place/sitemap.xml\n');
const documents=data.records.map(r=>({type:r.type,slug:r.id,path:r.path,title:r.title,summary:r.summary,language:'en',route:r.route,sha256:r.source_sha256,math_count:r.math_count}));
fs.writeFileSync(path.join(out,'publication.json'),JSON.stringify({...manifest,renderer:{name:'pandoc',version:'3.1.3',math:'MathML'},interface_languages:['en','ru','zh-Hans'],document_language:'en',documents},null,2)+'\n');
const base='https://contract.place';
const lines=['# Knowledge Contract Arcana','',
'Publication edition '+manifest.edition+'. Source commit '+manifest.commit+'.',
'Complete English documents with an English, Russian and Chinese interface. The Chinese interface has not received native editorial review.','',
'- Home: '+base+'/',
'- Science: '+base+'/en/research/',
'- Engineering specifications: '+base+'/en/engineering/specifications/',
'- Engineering studies: '+base+'/en/engineering/studies/',
'- Glossary and bibliography: '+base+'/en/reference/',
'- Appendices: '+base+'/en/appendices/',
'- Journal: '+base+'/en/journal/',
'- Full-document search: '+base+'/en/search/#document-search',
'- Manifest: '+base+'/publication.json',
'- Repository: https://github.com/Arcanada-one/knowledge-contract',
'- Arcanada ecosystem: https://arcanada.ai','',
'## Publication documents','',
...documents.map(d=>'- ['+d.title+']('+base+d.route+'): '+d.type+'.'),'',
'## Scope and access','',
'Scientific papers state assumptions, conditional results and counterexamples. Engineering specifications define requirements. Studies retain finite observations and their limitations. Publication is not runtime admission.',
'The public read API at https://api.contract.place exposes search, related and fetch. An MCP endpoint is documented at https://api.contract.place/mcp. API results may belong to a different source snapshot. Task-specific contract delivery has separate requirements in the API appendix.','',
'## Reuse','',
'Text: CC BY 4.0. Code and schemas: Apache-2.0. Credit Pavel Valentov, Knowledge Contract Arcana, https://contract.place, and retain upstream sources.',
'Historical source versions and Russian manuscripts: '+base+'/en/appendices/source-map/.',''];
fs.writeFileSync(path.join(out,'llms.txt'),lines.join('\n'));
const child=spawnSync(process.execPath,[path.join(src,'prerender.mjs'),out],{cwd:root,stdio:'inherit'});
if(child.error)throw child.error;process.exit(child.status??1);
