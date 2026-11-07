// Reproduce the compiled publication and localized interface without network access.
// Compile the canonical Markdown first with scripts/build_publication.py.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=import.meta.dirname,src=path.join(root,'src'),out=path.join(root,'public');
const data=JSON.parse(fs.readFileSync(path.join(src,'content/catalog.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'publication-manifest.json'),'utf8'));
for(const key of ['schema_version','repository','commit','edition','catalog'])
  if(data.publication?.[key]!==manifest[key])throw new Error('Compiled publication pin mismatch: '+key);
if(!/^[0-9a-f]{40}$/.test(manifest.commit)||manifest.repository!=='Arcanada-one/knowledge-contract')throw new Error('Invalid source pin');
// The roadmap has its own pin; it must match the compiled data and is never confused with the manuscript pin.
const roadmapManifest=JSON.parse(fs.readFileSync(path.join(root,'roadmap-manifest.json'),'utf8'));
const road=data.roadmap;
if(roadmapManifest.schema_version!==1||roadmapManifest.repository!==manifest.repository||!/^[0-9a-f]{40}$/.test(roadmapManifest.commit))throw new Error('Invalid roadmap pin');
if(!road||road.pin.commit!==roadmapManifest.commit||road.pin.repository!==roadmapManifest.repository)throw new Error('Compiled roadmap pin mismatch');
if(JSON.stringify(road.pin.files.map(f=>[f.path,f.role,f.sha256]))!==JSON.stringify(roadmapManifest.files.map(f=>[f.path,f.role,f.sha256])))throw new Error('Compiled roadmap files differ from the roadmap pin');
if(road.tasks.length!==25||road.tasks.some((k,i)=>k.id!=='RM-'+String(i+1).padStart(2,'0')||k.status!=='planned'))throw new Error('Roadmap must contain RM-01..RM-25, all planned');
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
let template=fs.readFileSync(path.join(out,'index.html'),'utf8');
template=template.replace(/src="\/content\.js(?:\?[^"]*)?"/g,'src="/content.js?v='+manifest.commit+'"');
// Changed runtime code or styles must not reuse an earlier edition's browser cache entry.
const assetHashes=Object.fromEntries(['theme.js','style.css','search.js','app.js'].map(name=>
  [name,createHash('sha256').update(fs.readFileSync(path.join(out,name))).digest('hex')]));
template=template.replace(/(src|href)="\/(theme\.js|style\.css|search\.js|app\.js)(?:\?[^"]*)?"/g,
  (_,attribute,name)=>attribute+'="/'+name+'?v='+assetHashes[name]+'"');
// Language renditions: their script and stylesheet are shipped only when the compiled catalogue contains renditions,
// so a build without renditions is byte-identical to one made before this support existed.
const hasRenditions=data.records.some(r=>r.renditions);
if(hasRenditions){
  const rendHashes={};
  for(const name of ['renditions.js','renditions.css']){
    const bytes=fs.readFileSync(path.join(src,'renditions',name));fs.writeFileSync(path.join(out,name),bytes);
    rendHashes[name]=createHash('sha256').update(bytes).digest('hex');
  }
  if(!template.includes('</head>')||!/<script src="\/app\.js\?v=[0-9a-f]+" defer><\/script>/.test(template))throw new Error('Cannot place the renditions assets in the page template');
  template=template.replace('</head>','<link rel="stylesheet" href="/renditions.css?v='+rendHashes['renditions.css']+'"></head>');
  template=template.replace(/(<script src="\/app\.js\?v=[0-9a-f]+" defer><\/script>)/,'$1<script src="/renditions.js?v='+rendHashes['renditions.js']+'" defer></script>');
  for(const r of data.records)for(const [lang,rd] of Object.entries(r.renditions||{})){
    if(!['ru','zh-Hans'].includes(lang)||!/^[0-9a-f]{40}$/.test(rd.source.revision)||!/^[0-9a-f]{64}$/.test(rd.source.sha256)||rd.source.path!==r.path)throw new Error('Unbound rendition source pin: '+r.id+' '+lang);
    if(rd.current_source_sha256!==undefined&&rd.current_source_sha256!==r.source_sha256)throw new Error('Rendition compared against another source edition: '+r.id+' '+lang);
    if(rd.state==='missing'?!!rd.rendition:!(rd.rendition&&/^[0-9a-f]{40}$/.test(rd.rendition.revision)&&/^[0-9a-f]{64}$/.test(rd.rendition.sha256)))throw new Error('Unbound rendition pin: '+r.id+' '+lang);
    if(rd.counts_as_independent_source!==undefined&&rd.counts_as_independent_source!==false)throw new Error('A rendition is not an independent source: '+r.id+' '+lang);
  }
}
fs.writeFileSync(path.join(out,'index.html'),template);
fs.copyFileSync(path.join(out,'assets/favicon.svg'),path.join(out,'favicon.svg'));
fs.writeFileSync(path.join(out,'content.js'),'window.CP_CONTENT = '+JSON.stringify(data)+';\n');
fs.writeFileSync(path.join(out,'robots.txt'),'User-agent: *\nAllow: /\nSitemap: https://contract.place/sitemap.xml\n');
const renditionSummary=r=>Object.fromEntries(Object.entries(r.renditions).map(([lang,rd])=>[lang,{state:rd.state,source_sha256:rd.source.sha256,current_source_sha256:rd.current_source_sha256??rd.source.sha256,source_revision:rd.source.revision,...(rd.rendition?{rendition_path:rd.rendition.path,rendition_sha256:rd.rendition.sha256,rendition_revision:rd.rendition.revision,review_status:rd.review.status,review_scope:rd.review.scope}:{}),counts_as_independent_source:false}]));
const documents=data.records.map(r=>({type:r.type,slug:r.id,path:r.path,title:r.title,summary:r.summary,language:'en',route:r.route,sha256:r.source_sha256,math_count:r.math_count,...(r.status?{status:r.status}:{}),...(r.renditions?{renditions:renditionSummary(r)}:{})}));
fs.writeFileSync(path.join(out,'publication.json'),JSON.stringify({...manifest,renderer:{name:'pandoc',version:'3.1.3',math:'MathML'},interface_languages:['en','ru','zh-Hans'],document_language:'en',...(hasRenditions?{renditions:{schema_version:1,source:data.renditions_source}}:{}),documents},null,2)+'\n');
fs.writeFileSync(path.join(out,'roadmap.json'),JSON.stringify({kind:'roadmap-provenance',status:'planned work; no execution state is published',roadmap_pin:{repository:road.pin.repository,commit:road.pin.commit,files:road.pin.files.map(({path:p,role,sha256})=>({path:p,role,sha256}))},manuscript_pin:{repository:manifest.repository,commit:manifest.commit,edition:manifest.edition},same_commit:road.pin.commit===manifest.commit,definition_revision:road.revision,tasks:road.tasks.map(k=>({id:k.id,priority:k.priority,owner:k.owner,status:k.status,requires:k.requires,informs:k.informs})),advisory_links:road.advisory},null,2)+'\n');
const base='https://contract.place';
const lines=['# Knowledge Contract Arcana','',
'Publication edition '+manifest.edition+'. Source commit '+manifest.commit+'.',
'Complete English documents with an English, Russian and Chinese interface. The Chinese interface has not received native editorial review.','',
'- Home: '+base+'/',
'- Science: '+base+'/en/research/',
'- Research roadmap (planned work, not results): '+base+'/en/roadmap/ ; provenance '+base+'/roadmap.json',
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
...documents.map(d=>'- ['+d.title+']('+base+d.route+'): '+d.type+(d.status?' ('+d.status.replace('-',' ')+', not an accepted paper)':'')+'.'),'',
'## Scope and access','',
'Scientific papers state assumptions, conditional results and counterexamples. Engineering specifications define requirements. Studies retain finite observations and their limitations. Publication is not runtime admission.',
'The public read API at https://api.contract.place exposes search, related and fetch. An MCP endpoint is documented at https://api.contract.place/mcp. API results may belong to a different source snapshot. Task-specific contract delivery has separate requirements in the API appendix.','',
'## Reuse','',
'Text: CC BY 4.0. Code and schemas: Apache-2.0. Credit Pavel Valentov, Knowledge Contract Arcana, https://contract.place, and retain upstream sources.',
'Historical source versions and Russian manuscripts: '+base+'/en/appendices/source-map/.',''];
fs.writeFileSync(path.join(out,'llms.txt'),lines.join('\n'));
const child=spawnSync(process.execPath,[path.join(src,'prerender.mjs'),out],{cwd:root,stdio:'inherit'});
if(child.error)throw child.error;process.exit(child.status??1);
