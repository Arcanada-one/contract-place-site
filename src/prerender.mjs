import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
const root=path.resolve(process.argv[2]||path.join(import.meta.dirname,'..','public'));
const ORIGIN='https://contract.place';
const original=fs.readFileSync(path.join(root,'index.html'),'utf8');
const template=original.replace(/<header id="header">[\s\S]*?<\/header>/,'<header id="header"></header>').replace(/<main id="main" tabindex="-1">[\s\S]*?<\/main>/,'<main id="main" tabindex="-1"></main>').replace(/<footer id="footer">[\s\S]*?<\/footer>/,'<footer id="footer"></footer>');
const routes=['','wiki','wiki/knowledge-contract','wiki/provenance','wiki/versioned-knowledge','research','research/anthropic','research/deepmind','research/hugging-face','research/mcp','research/stripe','research/supabase','books','repository','repository/design-kit/history','journal','journal/building-a-place','docs','docs/model','docs/availability','search'];
const content=fs.readFileSync(path.join(root,'content.js'),'utf8');
const source=fs.readFileSync(path.join(root,'app.js'),'utf8');
const LANGS=['en','ru','zh-Hans'];
function seo(route,lang){
 const m=route.match(/^\/(?:en|ru|zh-Hans)(?:\/(.*))?$/);const rest=m&&m[1]?m[1]:'';
 const at=l=>ORIGIN+'/'+l+'/'+rest;
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
 return html;
}
const data=JSON.parse(content.slice(content.indexOf('=')+1).trim().replace(/;$/,''));
for(const r of data.records)routes.push((r.kind==='paper'?'research/':'docs/')+r.id);
for(const a of data.articles)routes.push('journal/'+a.id);
routes.push('about','references');
const listed=new Set(['','wiki','research','docs','docs/availability','journal','books','repository','search','about','references']);
const urls=[ORIGIN+'/'];
for(const lang of LANGS)for(const route of routes){const dir=path.join(root,lang,route);fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'index.html'),generate(`/${lang}/${route}`,lang));
 const indexable=listed.has(route)||route.startsWith('research/p')||route.startsWith('docs/')&&route!=='docs/model'||route.startsWith('journal/')&&route!=='journal/building-a-place';
 if(indexable)urls.push(`${ORIGIN}/${lang}/${route}`);}
fs.writeFileSync(path.join(root,'index.html'),generate('/en','en').replace('<link rel="canonical" href="'+ORIGIN+'/en/">','<link rel="canonical" href="'+ORIGIN+'/">').replace('<meta property="og:url" content="'+ORIGIN+'/en/">','<meta property="og:url" content="'+ORIGIN+'/">'));
fs.writeFileSync(path.join(root,'404.html'),generate('/en/not-found','en').replace(/<link rel="canonical"[^>]*>(<link rel="alternate"[^>]*>)*<meta property="og:url"[^>]*>/,'<meta name="robots" content="noindex">'));
fs.writeFileSync(path.join(root,'sitemap.xml'),'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+urls.map(u=>`  <url><loc>${u}</loc><lastmod>${data.retrieved&&String(data.retrieved).slice(0,10)||'2026-11-04'}</lastmod></url>`).join('\n')+'\n</urlset>\n');
console.log(`Prerendered ${routes.length*3} localized routes, root and 404; sitemap ${urls.length} URLs.`);
