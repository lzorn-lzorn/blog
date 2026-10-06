// 禁止搜索引擎收录：给每个页面 head 注入 noindex 标签
// 配合 source/robots.txt 使用，两者结合可最大程度避免被搜索引擎抓取/收录
'use strict';

hexo.extend.injector.register('head_begin', '<meta name="robots" content="noindex, nofollow">', 'default');
