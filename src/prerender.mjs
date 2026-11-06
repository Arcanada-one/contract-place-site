import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
const root=path.resolve(process.argv[2]||path.join(import.meta.dirname,'..','public'));
const ORIGIN='https://contract.place';
const original=fs.readFileSync(path.join(root,'index.html'),'utf8');
const template=original.replace(/<header id="header">[\s\S]*?<\/header>/,'<header id="header"></header>').replace(/<main id="main" tabindex="-1">[\s\S]*?<\/main>/,'<main id="main" tabindex="-1"></main>').replace(/<footer id="footer">[\s\S]*?<\/footer>/,'<footer id="footer"></footer>');
const routes=['','science','engineering','engineering/specifications','engineering/studies','reference','appendices','wiki','wiki/knowledge-contract','wiki/provenance','wiki/versioned-knowledge','research','research/anthropic','research/deepmind','research/hugging-face','research/mcp','research/stripe','research/supabase','books','repository','roadmap','journal','journal/building-a-place','docs','docs/model','docs/availability','search'];
const content=fs.readFileSync(path.join(root,'content.js'),'utf8');
const source=fs.readFileSync(path.join(root,'app.js'),'utf8');
const LANGS=['en','ru','zh-Hans'];
// Indexing decision per route. Everything not listed here is canonical, in the sitemap and indexable.
// noindex: pages that duplicate a paper/article under another URL (aliases) or are design-brief references, not project content.
const NOINDEX=new Set(['wiki/knowledge-contract','wiki/provenance','wiki/versioned-knowledge','journal/building-a-place','docs/model','references','research/anthropic','research/deepmind','research/hugging-face','research/mcp','research/stripe','research/supabase']);
function seo(route,lang){
 if(!/^\/(?:en|ru|zh-Hans)(?:\/|$)/.test(route)&&data.reader_aliases[route.replace(/^\/|\/$/g,'')])return '<meta name="robots" content="noindex,follow"><meta http-equiv="refresh" content="0;url='+data.reader_aliases[route.replace(/^\/|\/$/g,'')]+'">';
 const m=route.match(/^\/(?:en|ru|zh-Hans)(?:\/(.*))?$/);const rest=m&&m[1]?m[1]:'';
 // Earlier numeric addresses forward to the current document in the same interface language (the page body keeps the link).
 if(data.aliases[rest.replace(/\/+$/,'')])return '<meta name="robots" content="noindex,follow"><meta http-equiv="refresh" content="0;url=/'+lang+'/'+data.aliases[rest.replace(/\/+$/,'')]+'/">';
 const at=l=>ORIGIN+'/'+l+'/'+(rest?rest.replace(/\/+$/,'')+'/':'');
 if(NOINDEX.has(rest.replace(/\/+$/,'')))return '<meta name="robots" content="noindex,follow">';
 return `<link rel="canonical" href="${at(lang)}">`+LANGS.map(l=>`<link rel="alternate" hreflang="${l}" href="${at(l)}">`).join('')+`<link rel="alternate" hreflang="x-default" href="${at('en')}"><meta property="og:url" content="${at(lang)}"><meta property="og:site_name" content="Knowledge Contract Arcana">`;
}
function generate(route,lang){
 const element=()=>({innerHTML:'',textContent:'',content:'',querySelector:()=>null,addEventListener(){},focus(){}});
 const els=Object.fromEntries(['#header','#main','#footer','.skip','meta[name="description"]'].map(k=>[k,element()]));
 const document={documentElement:{lang,dataset:{theme:'light'}},querySelector:s=>els[s]||null,querySelectorAll:()=>[],addEventListener(){},title:''};
 const location={pathname:route,search:'',hash:''};
 const context={document,location,URLSearchParams,Intl,Date,console,setTimeout,history:{replaceState(){}},localStorage:{getItem(){return null}},window:{addEventListener(){}}};
 vm.createContext(context);vm.runInContext(content,context);vm.runInContext(source,context);
 const html=template.replace('<html lang="en">',`<html lang="${lang}">`).replace(/<meta name="description" content="[^"]*">/,()=>`<meta name="description" content="${String(els['meta[name="description"]'].content||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;')}">${seo(route,lang)}`).replace(/<title>.*?<\/title>/,`<title>${document.title}</title>`).replace('<header id="header"></header>',`<header id="header">${els['#header'].innerHTML}</header>`).replace('<main id="main" tabindex="-1"></main>',`<main id="main" tabindex="-1">${els['#main'].innerHTML}</main>`).replace('<footer id="footer"></footer>',`<footer id="footer">${els['#footer'].innerHTML}</footer>`);
 const bare=route.replace(/^\/(?:en|ru|zh-Hans)\/?/,'').replace(/\/$/,'');
 const record=data.records.find(r=>r.route==='/en/'+bare+'/');
 if(record){
   const author={'@type':'Person',name:'Pavel Valentov',sameAs:'https://orcid.org/0009-0001-2567-4584'};
   const ld={'@context':'https://schema.org','@type':record.kind==='paper'?'ScholarlyArticle':'CreativeWork',name:record.title,url:ORIGIN+record.route,inLanguage:'en',version:data.publication.edition,license:'https://creativecommons.org/licenses/by/4.0/',author,copyrightHolder:author,isBasedOn:record.source,...(record.status?{creativeWorkStatus:record.status}:{})};
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
 const indexable=!NOINDEX.has(route);
 if(indexable)urls.push(`${ORIGIN}/${lang}/${route?route+'/':''}`);}
for(const alias of Object.keys(data.reader_aliases)){const dir=path.join(root,alias);fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'index.html'),generate('/'+alias,'en'));}
fs.writeFileSync(path.join(root,'index.html'),generate('/en','en').replace('<link rel="canonical" href="'+ORIGIN+'/en/">','<link rel="canonical" href="'+ORIGIN+'/">').replace('<meta property="og:url" content="'+ORIGIN+'/en/">','<meta property="og:url" content="'+ORIGIN+'/">'));
fs.writeFileSync(path.join(root,'404.html'),generate('/en/not-found','en').replace(/<link rel="canonical"[^>]*>(<link rel="alternate"[^>]*>)*<meta property="og:url"[^>]*>/,'<meta name="robots" content="noindex">'));
fs.writeFileSync(path.join(root,'sitemap.xml'),'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+urls.map(u=>`  <url><loc>${u}</loc><lastmod>${data.retrieved&&String(data.retrieved).slice(0,10)||'2026-11-04'}</lastmod></url>`).join('\n')+'\n</urlset>\n');
console.log(`Prerendered ${uniqueRoutes.length*3} localized routes, root and 404; sitemap ${urls.length} URLs.`);
