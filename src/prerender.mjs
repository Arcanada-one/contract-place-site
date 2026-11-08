import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
const root=path.resolve(process.argv[2]||path.join(import.meta.dirname,'..','public'));
const ORIGIN='https://contract.place';
const original=fs.readFileSync(path.join(root,'index.html'),'utf8');
const template=original.replace(/<header id="header">[\s\S]*?<\/header>/,'<header id="header"></header>').replace(/<main id="main" tabindex="-1">[\s\S]*?<\/main>/,'<main id="main" tabindex="-1"></main>').replace(/<footer id="footer">[\s\S]*?<\/footer>/,'<footer id="footer"></footer>');
const routes=['','science','engineering','engineering/specifications','engineering/studies','reference','appendices','wiki','wiki/knowledge-contract','wiki/provenance','wiki/versioned-knowledge','research','research/anthropic','research/deepmind','research/hugging-face','research/mcp','research/stripe','research/supabase','books','repository','roadmap','journal','journal/building-a-place','docs','docs/model','docs/availability','search','lab/knowledge-journey'];
const content=fs.readFileSync(path.join(root,'content.js'),'utf8');
const source=fs.readFileSync(path.join(root,'app.js'),'utf8');
const LANGS=['en','ru','zh-Hans'];
// Present only when the build compiled language renditions (see build.mjs); absent otherwise.
const renditionSource=fs.existsSync(path.join(root,'renditions.js'))?fs.readFileSync(path.join(root,'renditions.js'),'utf8'):null;
// Indexing decision per route. Everything not listed here is canonical, in the sitemap and indexable.
// noindex: pages that duplicate a paper/article under another URL (aliases) or are design-brief references, not project content.
const LAB_ROUTES=new Set(['lab/knowledge-journey']);
const NOINDEX=new Set([...LAB_ROUTES,'wiki/knowledge-contract','wiki/provenance','wiki/versioned-knowledge','journal/building-a-place','docs/model','references','research/anthropic','research/deepmind','research/hugging-face','research/mcp','research/stripe','research/supabase']);
// Fallback-indexing rule for the localized pages of a work (K8, docs/versioned-renditions.md section 5). ONE switch. It applies to
// builds that compiled renditions (a sidecar exists). Whether it also applies to a build without renditions, where every
// /ru/ and /zh-Hans/ reading page has an English body, is an open decision of KC-Brain; set this to true to apply it there
// (every translation is then "missing", so those pages are noindex, carry no hreflang alternate and leave the sitemap).
// Caveat (recorded): with no sidecar and this switch false, /ru and /zh-Hans English bodies stay indexable with hreflang, exactly as main does today.
const APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS=false;
const fallbackIndexing=()=>APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS||!!renditionSource;
// A locale counts as translated, indexed content only with a bound internal agent review in its stated scope. English always counts.
const TRANSLATED=['reviewed','partially-reviewed'];
const workOf=rest=>data.records.find(r=>r.route==='/en/'+rest.replace(/\/+$/,'')+'/');
const counts=(record,l)=>l==='en'||TRANSLATED.includes(((record.renditions||{})[l]||{state:'missing'}).state);
function seo(route,lang){
 if(!/^\/(?:en|ru|zh-Hans)(?:\/|$)/.test(route)&&data.reader_aliases[route.replace(/^\/|\/$/g,'')])return '<meta name="robots" content="noindex,follow"><meta http-equiv="refresh" content="0;url='+data.reader_aliases[route.replace(/^\/|\/$/g,'')]+'">';
 const m=route.match(/^\/(?:en|ru|zh-Hans)(?:\/(.*))?$/);const rest=m&&m[1]?m[1]:'';
 // Earlier numeric addresses forward to the current document in the same interface language (the page body keeps the link).
 if(data.aliases[rest.replace(/\/+$/,'')])return '<meta name="robots" content="noindex,follow"><meta http-equiv="refresh" content="0;url=/'+lang+'/'+data.aliases[rest.replace(/\/+$/,'')]+'/">';
 const at=l=>ORIGIN+'/'+l+'/'+(rest?rest.replace(/\/+$/,'')+'/':'');
 const noindex=NOINDEX.has(rest.replace(/\/+$/,''));
 const lab=LAB_ROUTES.has(rest.replace(/\/+$/,''));
 if(noindex&&!lab)return '<meta name="robots" content="noindex,follow">';
 let alternates=LANGS;
 if(!lab&&fallbackIndexing()&&rest){const record=workOf(rest);
  if(record){
   if(!counts(record,lang))return '<meta name="robots" content="noindex,follow">';
   alternates=LANGS.filter(l=>counts(record,l));
  }}
 // Lab routes retain locale identity while excluded from search discovery.
 return (noindex?'<meta name="robots" content="noindex,follow">':'')+(lab?'<meta name="referrer" content="no-referrer">':'')+`<link rel="canonical" href="${at(lang)}">`+alternates.map(l=>`<link rel="alternate" hreflang="${l}" href="${at(l)}">`).join('')+`<link rel="alternate" hreflang="x-default" href="${at('en')}"><meta property="og:url" content="${at(lang)}"><meta property="og:site_name" content="Knowledge Contract Arcana">`;
}
function generate(route,lang){
 const element=()=>({innerHTML:'',textContent:'',content:'',querySelector:()=>null,addEventListener(){},focus(){}});
 const els=Object.fromEntries(['#header','#main','#footer','.skip','meta[name="description"]'].map(k=>[k,element()]));
 const document={documentElement:{lang,dataset:{theme:'light'}},querySelector:s=>els[s]||null,querySelectorAll:()=>[],addEventListener(){},title:''};
 const location={pathname:route,search:'',hash:''};
 const context={document,location,URLSearchParams,Intl,Date,console,setTimeout,history:{replaceState(){}},localStorage:{getItem(){return null}},window:{addEventListener(){}}};
 vm.createContext(context);vm.runInContext(content,context);vm.runInContext(source,context);
 if(renditionSource)vm.runInContext(renditionSource,context);
 const html=template.replace('<html lang="en">',`<html lang="${lang}">`).replace(/<meta name="description" content="[^"]*">/,()=>`<meta name="description" content="${String(els['meta[name="description"]'].content||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;')}">${seo(route,lang)}`).replace(/<title>.*?<\/title>/,`<title>${document.title}</title>`).replace('<header id="header"></header>',`<header id="header">${els['#header'].innerHTML}</header>`).replace('<main id="main" tabindex="-1"></main>',`<main id="main" tabindex="-1">${els['#main'].innerHTML}</main>`).replace('<footer id="footer"></footer>',`<footer id="footer">${els['#footer'].innerHTML}</footer>`);
 const bare=route.replace(/^\/(?:en|ru|zh-Hans)\/?/,'').replace(/\/$/,'');
 const record=data.records.find(r=>r.route==='/en/'+bare+'/');
 if(record){
   const author={'@type':'Person',name:'Pavel Valentov',sameAs:'https://orcid.org/0009-0001-2567-4584'};
   const rd=record.renditions&&record.renditions[lang];
   const shown=!!rd&&['reviewed','partially-reviewed','unreviewed'].includes(rd.state);
   // C9: the language-tagged object uses the localized URL; the English route lives only on translationOfWork.
   const pageUrl=ORIGIN+(shown?record.route.replace('/en/',`/${lang}/`):record.route);
   const ld={'@context':'https://schema.org','@type':record.kind==='paper'?'ScholarlyArticle':'CreativeWork',name:shown?rd.title:record.title,url:pageUrl,inLanguage:shown?lang:'en',version:data.publication.edition,license:'https://creativecommons.org/licenses/by/4.0/',author,copyrightHolder:author,isBasedOn:record.source,...(record.status?{creativeWorkStatus:record.status}:{}),...(shown?{translationOfWork:{'@type':'CreativeWork',name:record.title,url:ORIGIN+record.route,inLanguage:'en'}}:{})};
   const block='<script type="application/ld+json">'+JSON.stringify(ld).replaceAll('<','\\u003c')+'</script>';
   return html.replace('</head>',block+'</head>');
 }
 return html;
}
const data=JSON.parse(content.slice(content.indexOf('=')+1).trim().replace(/;$/,''));
for(const r of data.records)routes.push(r.route.replace(/^\/en\//,'').replace(/\/$/,''));
for(const alias of Object.keys(data.aliases)){routes.push(alias);NOINDEX.add(alias);}
for(const a of data.articles)routes.push('journal/'+a.id);
routes.push('about','references');
const uniqueRoutes=[...new Set(routes)];
const urls=[ORIGIN+'/'];
for(const lang of LANGS)for(const route of uniqueRoutes){const dir=path.join(root,lang,route);fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'index.html'),generate(`/${lang}/${route}`,lang));
 const record=fallbackIndexing()&&route?workOf(route):null;
 const indexable=!NOINDEX.has(route)&&!(record&&!counts(record,lang));
 if(indexable)urls.push(`${ORIGIN}/${lang}/${route?route+'/':''}`);}
for(const alias of Object.keys(data.reader_aliases)){const dir=path.join(root,alias);fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'index.html'),generate('/'+alias,'en'));}
fs.writeFileSync(path.join(root,'index.html'),generate('/en','en').replace('<link rel="canonical" href="'+ORIGIN+'/en/">','<link rel="canonical" href="'+ORIGIN+'/">').replace('<meta property="og:url" content="'+ORIGIN+'/en/">','<meta property="og:url" content="'+ORIGIN+'/">'));
fs.writeFileSync(path.join(root,'404.html'),generate('/en/not-found','en').replace(/<link rel="canonical"[^>]*>(<link rel="alternate"[^>]*>)*<meta property="og:url"[^>]*>/,'<meta name="robots" content="noindex">'));
fs.writeFileSync(path.join(root,'sitemap.xml'),'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+urls.map(u=>`  <url><loc>${u}</loc><lastmod>${data.retrieved&&String(data.retrieved).slice(0,10)||'2026-11-04'}</lastmod></url>`).join('\n')+'\n</urlset>\n');
console.log(`Prerendered ${uniqueRoutes.length*3} localized routes, root and 404; sitemap ${urls.length} URLs.`);
