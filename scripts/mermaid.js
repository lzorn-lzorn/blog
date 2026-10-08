// Mermaid 图表渲染支持
// 1. before_post_render: 把 ```mermaid 代码块直接转成 <div class="mermaid">(HTML 转义)
// 2. after_render:html: 在含 mermaid 的页面注入本地 mermaid.js 并初始化
'use strict';

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

hexo.extend.filter.register('before_post_render', function (data) {
  data.content = data.content.replace(
    /```mermaid\s*\n([\s\S]*?)```/g,
    function (match, code) {
      return '<div class="mermaid">' + escapeHtml(code.trim()) + '</div>';
    }
  );
  return data;
}, 9);

hexo.extend.filter.register('after_render:html', function (html) {
  if (typeof html !== 'string' || html.indexOf('class="mermaid"') === -1) return html;

  const script =
    '<script src="/lib/mermaid.min.js"></script>' +
    '<script>if (window.mermaid) { mermaid.initialize({ startOnLoad: true }); }</script>';

  return html.replace('</body>', script + '</body>');
});
