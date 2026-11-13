// SPDX-License-Identifier: Apache-2.0
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname,'../src/site/app.js'),'utf8');
const begin = source.indexOf('/* KC-READER-LABELS-BEGIN');
const end = source.indexOf('/* KC-READER-LABELS-END */',begin);
assert.ok(begin>=0 && end>begin, 'bounded helper exists');
const cut = source.slice(begin,end + '/* KC-READER-LABELS-END */'.length);
const api = vm.runInNewContext(cut+'\n({kcRequirementTitles,kcReadableRequirementLabel,kcDecorateRequirementMarkers})');
let checks=0;
function t(n,p){assert.ok(p,n);checks++}
for(let i=1;i<=20;i++) {
  const id = 'CTX-R'+String(i).padStart(3,'0');
  for(const language of ['en','ru','zh-Hans']) t('localized '+id+' '+language,!!api.kcReadableRequirementLabel(id,language).includes(' — '));
}
// Clause-scoped editorial acceptance: these are labels, not substitute clauses.
// Source: knowledge-contract@161a01af, engineering/specifications/context-package/SPECIFICATION.md,
// exact EN blob 30ca8d2e. Assert what was actually missing in review 6857239243.
const clauseCaptions = {
  'CTX-R009': {en:'Reports bound to stage and subject revision',ru:'Привязка отчёта к этапу и редакции объекта оценки'},
  'CTX-R010': {en:'Empty top-k does not prove global absence',ru:'Пустая выдача top-k не доказывает глобальное отсутствие'},
  'CTX-R017': {ru:'Формат доставки и возможности читателя','zh-Hans':'交付格式与读者能力'},
  'CTX-R018': {en:'Assessment names delivered package and requirements revision',ru:'Оценка указывает доставленный пакет и редакцию требований'},
};
for(const [id,localized] of Object.entries(clauseCaptions)) {
  for(const [language,expected] of Object.entries(localized)) {
    t('source-scoped '+id+' '+language,api.kcReadableRequirementLabel(id,language).endsWith(' — '+expected));
  }
}
// A semantic mutant restores the prior, overbroad R010 English caption. It must
// demonstrably violate the exact-source fixture, while structural tests stay green.
const oldR010 = '"Empty search is not absence"';
const exactR010 = '"Empty top-k does not prove global absence"';
t('semantic mutant has unique target',cut.split(exactR010).length===2);
const semanticMutant = vm.runInNewContext(cut.replace(exactR010,oldR010)+'\\n({kcReadableRequirementLabel})');
t('semantic mutant is detected',!semanticMutant.kcReadableRequirementLabel('CTX-R010','en').endsWith(' — '+clauseCaptions['CTX-R010'].en));
for(const bad of [null,17,'CTX-R000','CTX-R13','CTX-R013<script>','ctx-r013','CTX-R013.'])
 t('refuse bad '+String(bad),api.kcReadableRequirementLabel(bad,'ru')===null);
t('unmapped BPK title remains canonical',api.kcReadableRequirementLabel('BPK-R001','ru')===null);
t('unmapped API title remains canonical',api.kcReadableRequirementLabel('API-R001','zh-Hans')===null);
// A guard-removal mutant must expose a generic fallback, which is unacceptable.
const guard = '  if (!title) return null;';
t('unique unmapped-code guard',cut.split(guard).length===2);
const mutant = vm.runInNewContext(cut.replace(guard,'  // intentionally removed scoped-map guard')+'\n({kcReadableRequirementLabel})');
t('negative mutant falsely decorates BPK',mutant.kcReadableRequirementLabel('BPK-R001','en')!==null);
const sample = text => ({
 ownText:text, children:[],dataset:{},attrs:{},classes:new Set(),
 get textContent(){return this.ownText+this.children.map(c=>c.textContent).join('')},
 set textContent(value){this.ownText=value;this.children=[]},
 setAttribute(k,v){this.attrs[k]=v;if(k==='data-requirement-id')this.dataset.requirementId=v},
 appendChild(child){this.children.push(child);return child},
 ownerDocument:{createElement(tag){return {tagName:tag.toUpperCase(),textContent:'',className:''}}},
 classList:{add(){}}
});
const node = sample('CTX-R013.');
const invalid = sample('CTX-R013<script>.');
const unmappedBpk = sample('BPK-R001.');
const unmappedApi = sample('API-R001.');
const root={querySelectorAll(selector){assert.equal(selector,'.source-body strong');return [node,invalid,unmappedBpk,unmappedApi]}};
t('first pass modifies only valid marker',api.kcDecorateRequirementMarkers(root,'ru')===1);
t('readable science-specific label',node.textContent.includes('Сохранение защищённых единиц'));
t('original ID kept',node.attrs['data-requirement-id']==='CTX-R013' && node.attrs.title==='CTX-R013');
t('source ID retained as accessible text',node.children.length===1 && node.children[0].tagName==='SPAN' && node.children[0].className==='sr-only' && node.children[0].textContent===' (CTX-R013)' && node.textContent.includes('(CTX-R013)'));
t('strong is not given prohibited ARIA names',!Object.hasOwn(node.attrs,'aria-label') && !Object.hasOwn(node.attrs,'aria-labelledby'));
t('language attribute',node.attrs.lang==='ru');
t('original invalid untouched',invalid.textContent==='CTX-R013<script>.');
t('visible BPK source ID untouched',unmappedBpk.textContent==='BPK-R001.' && unmappedBpk.children.length===0 && !Object.hasOwn(unmappedBpk.attrs,'data-requirement-id'));
t('visible API source ID untouched',unmappedApi.textContent==='API-R001.' && unmappedApi.children.length===0 && !Object.hasOwn(unmappedApi.attrs,'data-requirement-id'));
t('second pass idempotent',api.kcDecorateRequirementMarkers(root,'ru')===0);
t('repeated decoration does not duplicate accessible source ID',node.children.length===1 && node.textContent.split('CTX-R013').length===2);
const rerendered=sample('CTX-R013.');
t('new SPA body receives localized label and accessible original ID',api.kcDecorateRequirementMarkers({querySelectorAll(){return [rerendered]}},'zh-Hans')===1 && rerendered.attrs.lang==='zh-Hans' && rerendered.textContent.includes('(CTX-R013)') && rerendered.children.length===1);
t('no DOM available returns zero',api.kcDecorateRequirementMarkers(null,'en')===0);
t('source HTML not rewritten by renderer',source.includes('${r.html}')&&source.includes("typeof requestAnimationFrame==='function'"));
t('render invokes after initial DOM update',source.indexOf("if(typeof requestAnimationFrame==='function')")>source.indexOf("document.querySelector('#main').innerHTML=html"));
console.log('PASS '+checks+' requirement-reader checks; these do not constitute browser translation review');
