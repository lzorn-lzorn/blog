// 右侧栏文章目录：自动提取文章标题，生成可点击跳转的右侧 TOC
'use strict';

const cheerio = require('cheerio');

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildToc(headings) {
  let html = '<nav class="kira-right-toc">';
  html += '<div class="kira-right-toc-title">目录</div>';
  html += '<ul class="kira-right-toc-list">';
  for (const h of headings) {
    html +=
      '<li class="toc-level-' +
      h.level +
      '"><a href="#' +
      h.id +
      '">' +
      escapeHtml(h.text) +
      '</a></li>';
  }
  html += '</ul></nav>';
  return html;
}

hexo.extend.filter.register('after_render:html', function (html, data) {
  const page = data.page;
  if (!page || page.layout !== 'post') return html;

  const $ = cheerio.load(html);

  // 只提取正文里带 <span id> 的标题（hexo-kira-toc 已为正文标题生成 id）
  const headings = [];
  $('h1 > span[id], h2 > span[id], h3 > span[id]').each(function () {
    const level = parseInt(this.parent.name.substring(1), 10);
    const id = $(this).attr('id');
    const text = $(this).text().trim();
    if (text && id) headings.push({ level, id, text });
  });

  if (headings.length === 0) return html;

  const toc = buildToc(headings);
  const $right = $('.kira-right-column');
  if (!$right.length) return html;

  $right.find('.kira-backtotop').before(toc);
  $right.addClass('has-toc');

  return $.html();
});
