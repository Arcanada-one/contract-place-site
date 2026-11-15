// SPDX-License-Identifier: Apache-2.0
// Actual app/rendition renderers in a DOM stub. No browser, API or translation acceptance.
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const catalogue = JSON.parse(fs.readFileSync(path.join(root, 'src/content/catalog.json'), 'utf8'));
const app = fs.readFileSync(path.join(root, 'src/site/app.js'), 'utf8');
const renderer = fs.readFileSync(process.env.RENDITIONS_RENDERER || path.join(root, 'src/renditions/renditions.js'), 'utf8');
const names = ['independence_basis', 'method', 'limitations'];
const localized = {
  ru: {independence_basis: 'Синтетическое пояснение независимости.', method: 'Синтетическое описание метода.', limitations: 'Синтетические ограничения; внешней рецензии нет.'},
  'zh-Hans': {independence_basis: '用于测试的独立性说明。', method: '用于测试的方法说明。', limitations: '用于测试的局限说明；未经外部审校。'},
};
const notices = {
  ru: 'Эти переводы текста исторической рецензии не прошли смысловую проверку. Они не расширяют область исходной рецензии.',
  'zh-Hans': '以下历史审校记录的译文尚未经语义审校，也不扩大原审校的范围。',
};
const summaries = {ru: 'Исходный текст рецензии (английский)', 'zh-Hans': '原始审校记录（英文）'};
const escape = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const unescape = text => text.replace(/&(amp|lt|gt|quot|#39);/g, (_, name) => ({amp:'&',lt:'<',gt:'>',quot:'"','#39':"'"}[name]));
const originalFields = review => ({independence_basis: review.reviewer.independence_basis, method: review.method, limitations: review.limitations});
const history = catalogue.records.flatMap(record => ['ru', 'zh-Hans'].flatMap(locale => {
  const rd = record.renditions && record.renditions[locale];
  return rd && rd.review && ['reviewed', 'partially-reviewed'].includes(rd.state) ? [{work:record.id,locale}] : [];
}));
let cases = 0, originalChecks = 0, displayedFields = 0, syntheticOverlays = 0, actualOverlays = 0;
function check(name, fn) {
  try { fn(); cases++; }
  catch (error) { console.error('CASE FAILED: ' + name); throw error; }
}
function fixtureProjection(locale) {
  return {review_state:'unreviewed', language:locale, fields:{...localized[locale]},
    source:{path:'publication-review-localizations.json',sha256:'a'.repeat(64),revision:'b'.repeat(40),
      review_sha256:'c'.repeat(64),sidecar_path:'publication-renditions.json',sidecar_sha256:'d'.repeat(64),sidecar_revision:'e'.repeat(40)}};
}
function render(work, locale, configure = () => {}, source = renderer) {
  const data = structuredClone(catalogue);
  // build.mjs supplies this compatibility map; it is unrelated to this renderer.
  data.reader_aliases ||= {};
  const record = data.records.find(r => r.id === work);
  const rd = record.renditions[locale === 'en' ? 'ru' : locale];
  configure(rd);
  const frozenReview = JSON.stringify(rd.review);
  const frozenProjection = JSON.stringify(rd.review_localization);
  const elements = Object.fromEntries(['#header','#main','#footer','.skip','meta[name="description"]'].map(key => [key,
    {innerHTML:'',textContent:'',content:'',querySelector:()=>null,addEventListener(){},focus(){}}]));
  const context = {
    document:{documentElement:{lang:locale,dataset:{theme:'light'}},querySelector:selector=>elements[selector] || null,
      querySelectorAll:()=>[],addEventListener(){},title:'',getElementById(){return {scrollIntoView(){}};}},
    location:{pathname:record.route.replace('/en/', '/' + locale + '/'),search:'',hash:'',origin:'https://contract.place'},
    history:{replaceState(){},pushState(){}},localStorage:{getItem(){return null;},setItem(){}},
    window:{CP_CONTENT:data,addEventListener(){},scrollTo(){}},URL,URLSearchParams,Intl,Date,console,setTimeout,
  };
  vm.createContext(context);
  vm.runInContext(app, context);
  const before = elements['#main'].innerHTML, titleBefore = context.document.title;
  vm.runInContext(source, context);
  assert.equal(JSON.stringify(rd.review), frozenReview, 'historical review object is not mutated');
  assert.equal(JSON.stringify(rd.review_localization), frozenProjection, 'presentation object is not mutated');
  return {html:elements['#main'].innerHTML,before,titleBefore,titleAfter:context.document.title,record,rd,context,elements};
}
function extracted(html) {
  const details = html.match(/<details\b[^>]*data-review-original="true"[^>]*>[\s\S]*?<\/details>/);
  assert.ok(details, 'originals are kept in an explicitly labelled details');
  assert.doesNotMatch(details[0].slice(0,details[0].indexOf('>')+1), /\sopen(?:\s|=|>)/);
  assert.match(details[0], /^<details\b[^>]*lang="en"/);
  const values = Object.fromEntries([...details[0].matchAll(/<dd data-review-original-field="([^"]+)" lang="en">([\s\S]*?)<\/dd>/g)]
    .map(match => [match[1],unescape(match[2])]));
  assert.deepEqual(Object.keys(values).sort(), names.slice().sort());
  const visible = html.replace(details[0], '').replace(/<script\b[^>]*>[\s\S]*?<\/script>/g, '');
  return {details:details[0],values,visible};
}

check('exactly eight existing reviewed rendition records are exercised', () => assert.equal(history.length,8));
check('English reader remains unchanged by the rendition projection renderer', () => {
  const result = render(history[0].work,'en',rd=>{rd.review_localization=fixtureProjection('ru');});
  assert.equal(result.html,result.before);
  assert.equal(result.titleAfter,result.titleBefore);
  assert.doesNotMatch(result.html,/data-review-localization-field|data-review-original="true"/);
});
for (const {work,locale} of history) check('localized visible prose and exact historical original: ' + work + '/' + locale, () => {
  const result = render(work,locale,rd=>{
    if (rd.review_localization) actualOverlays++;
    else {rd.review_localization=fixtureProjection(locale);syntheticOverlays++;}
  });
  const {html,rd} = result, {details,values,visible} = extracted(html);
  const originals = originalFields(rd.review);
  assert.equal((html.match(/data-review-localization-field=/g) || []).length,3);
  for (const name of names) {
    assert.deepEqual(Buffer.from(values[name],'utf8'),Buffer.from(originals[name],'utf8'),name + ' original UTF-8 text');
    originalChecks++;
    const field = html.match(new RegExp('<(?:dd|span) data-review-localization-field="' + name + '" lang="' + locale + '">([\\s\\S]*?)</(?:dd|span)>'));
    assert.ok(field,name + ' visible current-locale field');
    assert.equal(unescape(field[1]),rd.review_localization.fields[name]);
    assert.ok(visible.includes(escape(rd.review_localization.fields[name])));
    assert.ok(!visible.includes(escape(originals[name])),name + ' English source prose is not shown by default');
    displayedFields++;
  }
  assert.ok(details.includes('<summary lang="' + locale + '">' + summaries[locale] + '</summary>'));
  assert.ok(visible.includes(notices[locale]));
  assert.match(visible,/data-review-localization-state="unreviewed"/);
  assert.ok(visible.includes('data-state="' + rd.state + '"'));
  const facts=JSON.parse(html.match(/<script type="application\/json" class="rendition-facts">([\s\S]*?)<\/script>/)[1]);
  assert.deepEqual(facts.review,rd.review);
  assert.equal(facts.state,rd.state);
  assert.deepEqual(facts.review_localization,{review_state:'unreviewed',language:locale,source:rd.review_localization.source});
  assert.equal(Object.hasOwn(facts.review_localization,'fields'),false);
  for (const id of rd.review.scope.sections) assert.ok(html.includes(escape(id)));
  const first = result.html;
  vm.runInContext(renderer,result.context);
  assert.equal(result.elements['#main'].innerHTML,first,'repeated apply does not duplicate the original or translated fields');
});
for (const locale of ['ru','zh-Hans']) check('missing descriptor retains legacy source-labelled review: ' + locale, () => {
  const result=render(history[0].work,locale,rd=>{delete rd.review_localization;});
  assert.doesNotMatch(result.html,/data-review-localization-field|data-review-original="true"/);
  for (const text of Object.values(originalFields(result.rd.review))) assert.ok(result.html.includes(escape(text)));
});
const invalid = [
  ['null object',()=>null],
  ['claimed reviewed state',p=>({...p,review_state:'reviewed'})],
  ['wrong language',p=>({...p,language:'zh-Hans'})],
  ['missing language',p=>{delete p.language;return p;}],
  ['missing fields',p=>{delete p.fields;return p;}],
  ['fields array',p=>({...p,fields:[]})],
  ['missing method',p=>{delete p.fields.method;return p;}],
  ['empty limitations',p=>{p.fields.limitations='  ';return p;}],
  ['nonstring field',p=>{p.fields.independence_basis=7;return p;}],
  ['extra field',p=>{p.fields.unbound='extra';return p;}],
];
for (const [name,mutate] of invalid) check('present malformed projection refuses silently different display: ' + name, () => {
  assert.throws(()=>render(history[0].work,'ru',rd=>{rd.review_localization=mutate(fixtureProjection('ru'));}),/REVIEW_LOCALIZATION_RENDER_INVALID/);
});
check('HTML-significant and multiline originals/translations are preserved as text', () => {
  const suffix='\nLiteral <tag> & "quoted" \'apostrophe\' text.\n';
  const result=render(history[0].work,'ru',rd=>{
    rd.review_localization=fixtureProjection('ru');
    rd.review.reviewer.independence_basis+=suffix;rd.review.method+=suffix;rd.review.limitations+=suffix;
    for(const name of names)rd.review_localization.fields[name]+='\nПеревод <img src=x onerror=alert(1)> & текст.\n';
  });
  const {values}=extracted(result.html);
  for(const name of names) assert.equal(values[name],originalFields(result.rd.review)[name]);
  assert.doesNotMatch(result.html,/<tag>|<img src=x onerror=/);
  assert.ok(result.html.includes('&lt;img src=x onerror=alert(1)&gt; &amp; текст.'));
});
console.log(JSON.stringify({schema:'kc-review-prose-renderer-tests/v1',result:'PASS',
  scope:'actual app/rendition renderers in a DOM stub; historical originals plus actual or explicitly synthetic presentation overlays; no browser, native execution or translation acceptance',
  cases,historical_records:history.length,original_utf8_field_checks:originalChecks,localized_field_checks:displayedFields,
  actual_compiled_overlays:actualOverlays,synthetic_overlays:syntheticOverlays}));
