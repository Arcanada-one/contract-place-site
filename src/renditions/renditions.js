// Language renditions of the English manuscripts. Loaded only when the compiled catalogue contains renditions.
// It never invents text: it shows the compiled rendition, or the pinned English source with an explicit state label.
(function () {
  'use strict';
  const LOCALES = ['en', 'ru', 'zh-Hans'];
  const L = (en, ru, zh) => ({ en, ru, 'zh-Hans': zh });
  const LABELS = {
    // All five state labels: KC-Brain-proposed (unreviewed/reviewed from letter 7b4d2cc6 (5); the rest brought to the same register).
    reviewed: L('Translation reviewed within the stated scope (internal agent review)', 'Перевод проверен в указанном объёме (внутренняя агентная рецензия)', '译文已按所述范围完成内部代理审查'),
    'partially-reviewed': L('Translation partly reviewed within the stated scope (internal agent review)', 'Перевод проверен частично, в указанном объёме (внутренняя агентная рецензия)', '译文已按所述范围完成部分内部代理审查'),
    unreviewed: L('Translation without semantic review', 'Перевод без смысловой рецензии', '尚未经语义审校的译文'),
    stale: L('Translation out of date: the English source has changed.', 'Перевод устарел: английский источник изменился.', '译文已过期：英文源文已更改。'),
    missing: L('No translation of this document is available.', 'Перевода этого документа нет.', '本文档暂无译文。'),
    fallback: L('The pinned English source text is shown instead.', 'Вместо него показан закреплённый английский исходный текст.', '此处改为显示固定版本的英文源文。'),
    rendition: L('This translation is a rendition of the pinned English source, not an independent source.', 'Этот перевод — версия закреплённого английского источника, а не независимый источник.', '本译文是固定版本英文源文的译本，不是独立来源。'),
    sourceText: L('English source text', 'Английский исходный текст', '英文源文'),
    source: L('Source', 'Источник', '源文'),
    translation: L('Translation', 'Перевод', '译文'),
    review: L('Review', 'Рецензия', '审校'),
    internal: L('Internal agent review by a reviewer independent of the author. It is not an external peer review.', 'Внутренняя агентная рецензия рецензентом, независимым от автора. Это не внешняя экспертная рецензия.', '由独立于作者的代理完成的内部审查，并非外部同行评审。'),
    reviewer: L('Reviewer', 'Рецензент', '审校者'),
    author: L('Author', 'Автор', '译者'),
    independence: L('Independence', 'Независимость', '独立性'),
    independentYes: L('independent of the author', 'независим от автора', '独立于译者'),
    method: L('Method', 'Метод', '方法'),
    reviewedBlobs: L('Reviewed blobs', 'Проверенные блобы', '已审校的文件版本'),
    scope: L('Scope', 'Охват', '范围'),
    coverageFull: L('full document', 'весь документ', '全文'),
    coveragePartial: L('listed parts only', 'только перечисленное', '仅限所列部分'),
    sectionsLabel: L('sections', 'разделы', '章节'),
    claimsLabel: L('claims', 'утверждения', '论断'),
    proofsLabel: L('proofs', 'доказательства', '证明'),
    corrections: L('Corrections', 'Исправления', '更正'),
    noneMade: L('none made', 'не вносились', '无'),
    time: L('Time (UTC)', 'Время (UTC)', '时间 (UTC)'),
    limits: L('Limitations', 'Ограничения', '局限'),
    evidence: L('Evidence', 'Свидетельства', '依据'),
    issueUnbound: L('A review is claimed but it is not bound to the pinned source, translation or evidence file. It is not counted.', 'Заявлена рецензия, но она не привязана к закреплённым источнику, переводу или файлу свидетельств. Она не учитывается.', '已声明审校，但未绑定到固定版本的源文、译文或依据文件，不予计入。'),
    issueIndependent: L('A review is claimed but the reviewer is not independent of the author. It is not counted.', 'Заявлена рецензия, но рецензент не независим от автора. Она не учитывается.', '已声明审校，但审校者并非独立于译者，不予计入。'),
    stateLabel: L('Translation status', 'Статус перевода', '译文状态'),
    bodyLanguage: { ru: L('Full text in Russian', 'Полный текст на русском', '俄文全文'), 'zh-Hans': L('Full text in Chinese', 'Полный текст на китайском', '中文全文') },
  };
  const RENDERED = ['reviewed', 'partially-reviewed', 'unreviewed'];
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const short = h => (h || '').slice(0, 12);
  function stateBox(record, rd, locale) {
    const t = k => LABELS[k][locale];
    const rendered = RENDERED.includes(rd.state);
    const lines = [];
    lines.push('<p class="rendition-state-label"><strong>' + esc(t(rd.state)) + '</strong>' + (rendered ? '' : ' ' + esc(t('fallback'))) + '</p>');
    if (rendered) lines.push('<p>' + esc(t('rendition')) + '</p>');
    if (rendered && rd.review) lines.push('<p>' + esc(t('internal')) + '</p>');
    if (rd.review_issue) lines.push('<p class="rendition-review-issue" data-review-issue="' + esc(rd.review_issue.code) + '">' + esc(t(rd.review_issue.code === 'RENDITION_REVIEW_NOT_INDEPENDENT' ? 'issueIndependent' : 'issueUnbound')) + ' <code>' + esc(rd.review_issue.code) + '</code></p>');
    const pins = [];
    pins.push('<dt>' + esc(t('source')) + '</dt><dd><a href="' + esc(rd.source.url) + '" lang="en">' + esc(rd.source.path) + '</a> <code>' + esc(short(rd.source.sha256)) + '</code> <code>' + esc(short(rd.source.revision)) + '</code></dd>');
    if (rd.rendition) {
      pins.push('<dt>' + esc(t('translation')) + '</dt><dd><a href="' + esc(rd.rendition.url) + '" lang="en">' + esc(rd.rendition.path) + '</a> <code>' + esc(short(rd.rendition.sha256)) + '</code> <code>' + esc(short(rd.rendition.revision)) + '</code></dd>');
    }
    const v = rd.review;
    if (rendered && v) {
      const code = x => '<code>' + esc(short(x)) + '</code>';
      const list = (label, items) => items.length ? esc(t(label)) + ': ' + items.map(esc).join('; ') : '';
      const scope = [list('sectionsLabel', v.scope.sections), list('claimsLabel', v.scope.claims), list('proofsLabel', v.scope.proofs)].filter(Boolean).join(' · ');
      pins.push('<dt>' + esc(t('reviewer')) + '</dt><dd lang="en">' + esc(v.reviewer.identity) + ' (' + esc(v.reviewer.kind) + ')</dd>');
      pins.push('<dt>' + esc(t('author')) + '</dt><dd lang="en">' + esc(v.author) + '</dd>');
      pins.push('<dt>' + esc(t('independence')) + '</dt><dd><span>' + esc(t('independentYes')) + '</span> <span lang="en">' + esc(v.reviewer.independence_basis) + '</span></dd>');
      pins.push('<dt>' + esc(t('method')) + '</dt><dd lang="en">' + esc(v.method) + '</dd>');
      pins.push('<dt>' + esc(t('reviewedBlobs')) + '</dt><dd>' + code(v.reviewed.source_blob) + ' ' + code(v.reviewed.rendition_blob) + '</dd>');
      pins.push('<dt>' + esc(t('scope')) + '</dt><dd>' + esc(t(v.scope.coverage === 'full' ? 'coverageFull' : 'coveragePartial')) + ' <span lang="en">' + scope + '</span></dd>');
      pins.push('<dt>' + esc(t('corrections')) + '</dt><dd lang="en">' + (v.corrections.length ? v.corrections.map(c => esc(c.section + ': ' + c.description)).join('; ') : '<span lang="' + locale + '">' + esc(t('noneMade')) + '</span>') + '</dd>');
      pins.push('<dt>' + esc(t('time')) + '</dt><dd><time datetime="' + esc(v.reviewed_at) + '">' + esc(v.reviewed_at) + '</time></dd>');
      pins.push('<dt>' + esc(t('limits')) + '</dt><dd lang="en">' + esc(v.limitations) + '</dd>');
      pins.push('<dt>' + esc(t('evidence')) + '</dt><dd><a href="' + esc(v.evidence.url) + '" lang="en">' + esc(v.evidence.path) + '</a> ' + code(v.evidence.blob) + '</dd>');
    }
    lines.push('<dl class="rendition-pins">' + pins.join('') + '</dl>');
    lines.push('<p><a href="' + esc(record.route) + '" hreflang="en" lang="en">' + esc(LABELS.sourceText[locale]) + '</a></p>');
    // C4: machine-readable pins and review with full digests (served-page bytes alone).
    const facts = {
      relation: 'rendition_of',
      work: record.id,
      state: rd.state,
      independent_source: false,
      source_language: 'en',
      rendition_language: rd.language,
      body_language: rendered ? rd.language : 'en',
      source: {path: rd.source.path, sha256: rd.source.sha256, revision: rd.source.revision, language: rd.source.language || 'en', url: rd.source.url},
      digest_label: 'sha256',
    };
    if (rd.rendition) {
      facts.rendition = {path: rd.rendition.path, sha256: rd.rendition.sha256, revision: rd.rendition.revision, url: rd.rendition.url};
    }
    if (rd.current_source_sha256) facts.current_source_sha256 = rd.current_source_sha256;
    if (rd.review_issue) facts.review_issue = rd.review_issue;
    if (rendered && rd.review) facts.review = rd.review;
    lines.push('<script type="application/json" class="rendition-facts">' + JSON.stringify(facts).replaceAll('<', '\\u003c') + '</script>');
    // Keep the four data-* attributes before lang= in the order publication_checks expects; C4 pins follow.
    return '<aside class="rendition-state" data-state="' + esc(rd.state) + '" data-language="' + esc(rd.language) + '" data-body-language="' + (rendered ? esc(rd.language) : 'en') + '" data-independent-source="false" lang="' + locale + '" aria-label="' + esc(t('stateLabel')) + '" data-relation="rendition_of" data-work="' + esc(record.id) + '" data-source-sha256="' + esc(rd.source.sha256) + '"' + (rd.rendition ? ' data-rendition-sha256="' + esc(rd.rendition.sha256) + '"' : '') + '>' + lines.join('') + '</aside>';
  }
  function once(html, pattern, replacement, what) {
    if (!pattern.test(html)) throw new Error('RENDITION_SILENT_FALLBACK: reading page structure changed; cannot place ' + what);
    return html.replace(pattern, replacement);
  }
  function apply() {
    const corpus = window.CP_CONTENT;
    const main = document.querySelector('#main');
    if (!corpus || !main) return;
    const parts = location.pathname.split('/').filter(Boolean);
    if (!LOCALES.includes(parts[0]) || parts[0] === 'en') return;
    const locale = parts.shift();
    const record = corpus.records.find(r => r.route === '/en/' + parts.join('/') + '/');
    const rd = record && record.renditions && record.renditions[locale];
    if (!rd) return;
    let html = main.innerHTML;
    if (html.indexOf('class="rendition-state"') >= 0) return;
    const box = stateBox(record, rd, locale);
    const note = /<p class="reading-language-note">[\s\S]*?<\/p>/;
    if (!RENDERED.includes(rd.state)) {
      main.innerHTML = once(html, note, m => box + m, 'the state label');
      return;
    }
    html = once(html, note, () => box, 'the state label');
    html = once(html, /<h1 id="[^"]*" lang="en">[\s\S]*?<\/h1>/, () => '<h1 id="' + esc(rd.title_id) + '" lang="' + rd.language + '">' + esc(rd.title) + '</h1>', 'the title');
    html = once(html, /(<div class="source-body prose" lang=")en(">)[\s\S]*?(<\/div>)(<section class="document-citation")/, (m, a, b, c, d) => a + rd.language + b + rd.html + c + d, 'the body');
    html = once(html, /(<details class="reader-contents"[^>]*>\s*<summary>[\s\S]*?<\/summary>\s*<nav[^>]*>)[\s\S]*?(<\/nav>)/, (m, a, b) => a + rd.toc.map(h => '<a class="toc-level-' + h.level + '" href="#' + esc(h.id) + '" lang="' + rd.language + '">' + esc(h.title) + '</a>').join('') + b, 'the contents');
    html = once(html, /(<div class="provenance metadata">(?:<span>[^<]*<\/span>){2})<span>[^<]*<\/span>/, (m, a) => a + '<span>' + esc(LABELS.bodyLanguage[rd.language][locale]) + '</span>', 'the language label');
    main.innerHTML = html;
    document.title = rd.title + ' — contract.place';
  }
  apply();
  if (typeof MutationObserver !== 'undefined') {
    const main = document.querySelector('#main');
    if (main) new MutationObserver(() => apply()).observe(main, { childList: true });
  }
})();
