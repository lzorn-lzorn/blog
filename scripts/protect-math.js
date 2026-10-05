// 保护数学公式，避免被 Markdown 渲染器(marked)破坏。
// 背景：marked 会把 LaTeX 里的下划线 _、双反斜杠 \\ 等当作 Markdown 语法处理，
// 导致 $...$ / $$...$$ / \begin{...}...\end{...} 中的公式在渲染前就被打乱。
// 做法：渲染前把公式替换成占位符，渲染后再还原，随后交给 hexo-filter-mathjax 生成 SVG。
'use strict';

const TOKEN_PREFIX = 'HEXOMATHTOKEN';

function protect(content, blocks) {
  let count = 0;
  const push = (math) => {
    const token = TOKEN_PREFIX + count;
    blocks.push(math);
    count += 1;
    return token;
  };

  // 1. 行间公式 $$...$$（可跨行）
  content = content.replace(/\$\$([\s\S]+?)\$\$/g, (_, body) => push('$$' + body + '$$'));

  // 2. 环境 \begin{name}...\end{name}（按同名环境配对，支持 align 内嵌 bmatrix 等不同名环境）
  content = content.replace(/\\begin\{([^}]+)\}([\s\S]*?)\\end\{\1\}/g, (match) => push(match));

  // 3. 行内公式 $...$（单行，$ 之间不含换行）
  content = content.replace(/\$([^$\n]+)\$/g, (_, body) => push('$' + body + '$'));

  return content;
}

function restore(content, blocks) {
  return content.replace(new RegExp(TOKEN_PREFIX + '(\\d+)', 'g'), (match, idx) => {
    const i = parseInt(idx, 10);
    return blocks[i] !== undefined ? blocks[i] : match;
  });
}

hexo.extend.filter.register('before_post_render', function (data) {
  const blocks = [];
  data.content = protect(data.content, blocks);
  data.__mathBlocks = blocks;
  return data;
}, 11);

hexo.extend.filter.register('after_post_render', function (data) {
  const blocks = data.__mathBlocks;
  if (blocks && blocks.length) {
    data.content = restore(data.content, blocks);
  }
  delete data.__mathBlocks;
  return data;
}, 1);
