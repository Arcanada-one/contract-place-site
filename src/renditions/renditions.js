// Language renditions of the English manuscripts. Loaded only when the compiled catalogue contains renditions.
// It never invents text: it shows the compiled rendition, or the pinned English source with an explicit state label.
(function () {
  'use strict';
  const LOCALES = ['en', 'ru', 'zh-Hans'];
  const L = (en, ru, zh) => ({ en, ru, 'zh-Hans': zh });
  const LABELS = {
    reviewed: L('Reviewed translation', 'Рецензированный перевод', '已审校译文'),
    'partially-reviewed': L('Partially reviewed translation', 'Частично рецензированный перевод', '部分审校译文'),
    unreviewed: L('Unreviewed translation', 'Перевод без рецензирования', '未审校译文'),
    stale: L('Translation out of date: the English source has changed.', 'Перевод устарел: английский источник изменился.', '译文已过期：英文源文已更改。'),
    missing: L('No translation of this document is available.', 'Перевода этого документа нет.', '本文档暂无译文。'),
    fallback: L('The pinned English source text is shown instead.', 'Вместо него показан закреплённый английский исходный текст.', '此处改为显示固定版本的英文源文。'),
    rendition: L('This translation is a rendition of the pinned English source, not an independent source.', 'Этот перевод — версия закреплённого английского источника, а не независимый источник.', '本译文是固定版本英文源文的译本，不是独立来源。'),
    sourceText: L('English source text', 'Английский исходный текст', '英文源文'),
    source: L('Source', 'Источник', '源文'),
    translation: L('Translation', 'Перевод', '译文'),
    review: L('Review', 'Рецензия', '审校'),
    scope: L('Scope', 'Охват', '范围'),
    method: L('Method', 'Метод', '方法'),
    reviewers: L('Reviewers', 'Рецензенты', '审校者'),
    evidence: L('Evidence', 'Свидетельства', '依据'),
    limits: L('Limits', 'Ограничения', '局限'),
    notRecorded: L('none recorded', 'не записаны', '无记录'),
    full: L('full document', 'весь документ', '全文'),
    sections: L('listed sections only', 'только перечисленные разделы', '仅限所列章节'),
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
    lines.push('<p class="rendition-state-label"><strong>' + esc(t(rendered ? rd.state : rd.state)) + '</strong>' + (rendered ? '' : ' ' + esc(t('fallback'))) + '</p>');
    if (rendered) lines.push('<p>' + esc(t('rendition')) + '</p>');
    const pins = [];
    pins.push('<dt>' + esc(t('source')) + '</dt><dd><a href="' + esc(rd.source.url) + '" lang="en">' + esc(rd.source.path) + '</a> <code>' + esc(short(rd.source.sha256)) + '</code> <code>' + esc(short(rd.source.revision)) + '</code></dd>');
    if (rd.rendition) {
      pins.push('<dt>' + esc(t('translation')) + '</dt><dd><a href="' + esc(rd.rendition.url) + '" lang="en">' + esc(rd.rendition.path) + '</a> <code>' + esc(short(rd.rendition.sha256)) + '</code> <code>' + esc(short(rd.rendition.revision)) + '</code></dd>');
      const v = rd.review;
      const who = v.reviewers.length ? v.reviewers.map(x => x.kind + ': ' + x.ref).join('; ') : t('notRecorded');
      const ev = v.evidence.length ? v.evidence.join('; ') : t('notRecorded');
      pins.push('<dt>' + esc(t('review')) + '</dt><dd>' + esc(v.status) + '</dd>');
      pins.push('<dt>' + esc(t('scope')) + '</dt><dd>' + esc(t(v.scope === 'full' ? 'full' : 'sections')) + (v.reviewed_sections ? ': ' + v.reviewed_sections.map(esc).join(', ') : '') + '</dd>');
      pins.push('<dt>' + esc(t('method')) + '</dt><dd lang="en">' + esc(v.method || t('notRecorded')) + '</dd>');
      pins.push('<dt>' + esc(t('reviewers')) + '</dt><dd lang="en">' + esc(who) + '</dd>');
      pins.push('<dt>' + esc(t('evidence')) + '</dt><dd lang="en">' + esc(ev) + '</dd>');
      pins.push('<dt>' + esc(t('limits')) + '</dt><dd lang="en">' + esc(v.limits || t('notRecorded')) + '</dd>');
    }
    lines.push('<dl class="rendition-pins">' + pins.join('') + '</dl>');
    lines.push('<p><a href="' + esc(record.route) + '" hreflang="en" lang="en">' + esc(LABELS.sourceText[locale]) + '</a></p>');
    return '<aside class="rendition-state" data-state="' + esc(rd.state) + '" data-language="' + esc(rd.language) + '" data-body-language="' + (rendered ? esc(rd.language) : 'en') + '" data-independent-source="false" lang="' + locale + '" aria-label="' + esc(t('stateLabel')) + '">' + lines.join('') + '</aside>';
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
