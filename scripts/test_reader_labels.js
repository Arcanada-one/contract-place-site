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
for(const bad of [null,17,'CTX-R000','CTX-R13','CTX-R013<script>','ctx-r013','CTX-R013.'])
 t('refuse bad '+String(bad),api.kcReadableRequirementLabel(bad,'ru')===null);
t('generic unknown requirement',api.kcReadableRequirementLabel('ABC-R021','ru')==='Требование 21');
const sample = text => ({
 textContent:text, dataset:{},attrs:{},classes:new Set(),
 setAttribute(k,v){this.attrs[k]=v;if(k==='data-requirement-id')this.dataset.requirementId=v},
 classList:{add(k){sampleClasses.add(k)}}
});
const sampleClasses = new Set();
const node = sample('CTX-R013.');
const invalid = sample('CTX-R013<script>.');
const root={querySelectorAll(selector){assert.equal(selector,'.source-body strong');return [node,invalid]}};
t('first pass modifies only valid marker',api.kcDecorateRequirementMarkers(root,'ru')===1);
t('readable science-specific label',node.textContent.includes('Сохранение защищённых единиц'));
t('original ID kept',node.attrs['data-requirement-id']==='CTX-R013' && node.attrs.title==='CTX-R013');
t('language attribute',node.attrs.lang==='ru');
t('original invalid untouched',invalid.textContent==='CTX-R013<script>.');
t('second pass idempotent',api.kcDecorateRequirementMarkers(root,'ru')===0);
t('no DOM available returns zero',api.kcDecorateRequirementMarkers(null,'en')===0);
t('source HTML not rewritten by renderer',source.includes('${r.html}')&&source.includes("typeof requestAnimationFrame==='function'"));
t('render invokes after initial DOM update',source.indexOf("if(typeof requestAnimationFrame==='function')")>source.indexOf("document.querySelector('#main').innerHTML=html"));
console.log('PASS '+checks+' requirement-reader checks; these do not constitute browser translation review');
