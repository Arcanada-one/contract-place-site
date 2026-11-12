#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Apply the operator-requested presentation delta, only to its exact source base.
All inputs are checked before any write. No network, main push or deployment.
A completed exact application is idempotent; an unknown source is refused.
"""
from pathlib import Path
import hashlib,re
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PINS={
'src/site/app.js':('de594c13cdb003a889c8f3ff5adfa1ebd7e74e4c','db64df711e7053c10d487820c2f4b340033b7003'),
'src/site/style.css':('54b6d123dd2965d24cd25790f245dc5e7fdc3ac9','9d35787d403045ff32248c906961e227ae4df43d'),
'scripts/build_publication.py':('070732d5bc219f9985e5c41dfe600bd11c3b8141','19a2cad9dfe508ddb3ff9380ad0437e70330fc20'),
'scripts/renditions.py':('f387ded563e9ab03d37436b3ad9dafb53792a70c','0baf25628f7d5f031c15f90ceaacc7473ecf36fa'),
'src/renditions/renditions.js':('c420a45ad051977178b3141e771656cf4e0af952','5698c701c8032a3db773a809cf99c122707cec8b')}
def blob(s):
 b=s.encode();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
before={p:(ROOT/p).read_text() for p in PINS}
if all(blob(s)==PINS[p][1] for p,s in before.items()):
 print('Already applied: exact output blobs verified');raise SystemExit(0)
for p,s in before.items():
 if (ROOT/p).is_symlink() or blob(s)!=PINS[p][0]:raise SystemExit('REFUSED source drift: '+p)
a=before['src/site/app.js']
locale="""const localeSelect=()=>`<nav class="cp-language-switch" aria-label="${t('language')}">${langs.map((l,i)=>{const suffix=location.pathname.replace(/^\\/(?:en|ru|zh-Hans)(?=\\/|$)/,'');const href='/'+l+(suffix||'/')+location.search+location.hash;return `<a class="cp-language" data-cp-language="${l}" href="${esc(href)}" hreflang="${l}" lang="${l}" aria-label="${languageNames[i]}" ${l===locale?'aria-current="true"':''}>${flag(l).replace('viewBox=','preserveAspectRatio="xMidYMid slice" viewBox=')}<span class="cp-language-code" aria-hidden="true">${['EN','РУ','中'][i]}</span><span class="cp-language-tooltip" aria-hidden="true">${languageNames[i]}</span></a>`}).join('')}</nav>`;"""
a,n=re.subn(r'^const localeSelect=.*;$',lambda _:locale,a,flags=re.M)
if n!=1:raise SystemExit('REFUSED locale definition count')
marker="if(typeof module!=='undefined'&&module.exports){"
if a.count(marker)!=1:raise SystemExit('REFUSED entrypoint count')
a=a.replace(marker,(HERE/'reader.js').read_text()+'\n'+marker)
c=before['src/site/style.css']+'\n'+(HERE/'reader.css').read_text()
b=before['scripts/build_publication.py']
helper='''\ndef readable_requirement_markers(content: str) -> str:
    """Decorate only a leading requirement label; retain its exact source text.

    Reading CSS hides the bookkeeping label by default. The stable fragment and
    source bytes stay available to citations, tools and the explicit detail toggle.
    No arbitrary code span or scientific abbreviation is rewritten.
    """
    pattern = r'<p><strong>([A-Z][A-Z0-9]{1,15}-R[0-9]{3})(\\.?)</strong> '
    return re.sub(pattern, lambda m: '<p data-requirement="'+m[1]+'"><strong class="requirement-id" id="'+m[1]+'">'+m[1]+m[2]+'</strong> ', content)

'''
b=b.replace('\nclass Renderer:',helper+'\nclass Renderer:')
b=b.replace('content = csp_table_classes(content)','content = readable_requirement_markers(csp_table_classes(content))')
r=before['scripts/renditions.py'].replace('"title": title, "title_id": fragment["title_id"],','"title": title, "summary": meta_value(rendition_ast, "description") or "", "title_id": fragment["title_id"],')
j=before['src/renditions/renditions.js'].replace("lines.push('<dl class=\"rendition-pins\">' + pins.join('') + '</dl>');","lines.push('<details class=\"rendition-details\"><summary>' + esc(L('Source, version and review details', 'Источник, версия и подробности проверки', '来源、版本与审校详情')[locale]) + '</summary><dl class=\"rendition-pins\">' + pins.join('') + '</dl></details>');")
after={'src/site/app.js':a,'src/site/style.css':c,'scripts/build_publication.py':b,'scripts/renditions.py':r,'src/renditions/renditions.js':j}
for p,s in after.items():
 if blob(s)!=PINS[p][1]:raise SystemExit('REFUSED unexpected output: '+p+' '+blob(s))
for p in PINS:
 if (ROOT/p).read_text()!=before[p]:raise SystemExit('REFUSED concurrent source change')
for p,s in after.items():(ROOT/p).write_text(s)
print('Applied five exact source edits; scientific source files unchanged')
