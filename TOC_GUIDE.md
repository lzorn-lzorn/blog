# Kira 主题 - 文章目录 (TOC) 使用指南

## 🎯 什么是目录（TOC）

TOC (Table of Contents) 是文章的目录导航，可以帮助读者快速了解文章结构并跳转到对应章节。

## 📝 如何添加目录

### 方法：在文章中添加 `<!-- toc -->` 注释

在文章的 **Front Matter 之后**、**正文开始之前** 添加 `<!-- toc -->` 注释即可：

```markdown
---
title: 文章标题
date: 2025-12-04
tags: [标签1, 标签2]
categories: [分类]
---

<!-- toc -->

# 第一章节

这是第一章节的内容...

## 1.1 小节

这是小节内容...

# 第二章节

这是第二章节的内容...
```

## ✨ 目录生成规则

1. **自动识别标题**：目录会自动识别文章中的所有标题（H1-H6）
2. **生成层级结构**：根据标题级别生成嵌套的目录结构
3. **可点击跳转**：目录中的每一项都可以点击跳转到对应章节
4. **自动更新**：当你修改标题时，目录会自动更新

## 📋 示例

### 示例 1: 基础使用

```markdown
---
title: Python 教程
date: 2025-12-04
---

<!-- toc -->

# 简介

Python 是一门...

# 安装

## Windows 安装

## Mac 安装

## Linux 安装

# 基础语法

## 变量

## 数据类型

## 函数
```

生成的目录效果：
```
- 简介
- 安装
  - Windows 安装
  - Mac 安装
  - Linux 安装
- 基础语法
  - 变量
  - 数据类型
  - 函数
```

### 示例 2: 你的文章

你的 `Hello-Hexo.md` 已经添加了目录：

```markdown
---
title: 使用 Hexo 配置个人博客
date: 2025-12-03 22:38:51
tags:
categories:
  - Hexo
cover: /lib/background/bg2.jpg
---

<!-- toc -->

# Hello Hexo
Hexo 是基于 node.js 的个人博客框架...

# 其他章节
...
```

## ⚙️ 高级配置（可选）

如果需要自定义目录样式，可以在根目录的 `_config.yml` 中添加配置：

```yaml
toc:
  maxDepth: 3        # 目录最大深度（1-6），默认 6
  class: 'toc'       # 目录容器的 CSS 类名
  slugify: 'transliteration'  # URL 化方式
  decodeEntities: false       # 是否解码 HTML 实体
  anchor:
    position: 'after'  # 锚点位置：before 或 after
    symbol: '#'        # 锚点符号
    style: 'header-anchor'  # 锚点样式类名
```

## 🎨 自定义目录样式

如果想自定义目录样式，可以在 `source/custom.css` 中添加：

```css
/* 目录容器样式 */
.toc {
    background: #f5f7fa;
    border-left: 4px solid #42b983;
    padding: 15px 20px;
    margin: 20px 0;
    border-radius: 4px;
}

/* 目录标题 */
.toc::before {
    content: "📑 目录";
    display: block;
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
    color: #42b983;
}

/* 目录列表 */
.toc ul {
    list-style: none;
    padding-left: 0;
}

.toc ul ul {
    padding-left: 20px;
}

.toc li {
    margin: 8px 0;
}

.toc a {
    color: #2c3e50;
    text-decoration: none;
    transition: color 0.3s;
}

.toc a:hover {
    color: #42b983;
}
```

## 📌 注意事项

1. **位置很重要**：`<!-- toc -->` 必须放在 Front Matter 之后
2. **标题规范**：确保文章中使用正确的 Markdown 标题语法（`#`、`##` 等）
3. **标题唯一性**：尽量避免相同的标题，否则跳转可能不准确
4. **不要嵌套**：每篇文章只添加一次 `<!-- toc -->`

## 🚀 部署查看效果

添加目录后，记得重新生成和部署：

```bash
# 方法 1: 使用 Python 脚本
python3 deploy.py

# 方法 2: 手动执行
hexo clean && hexo generate && hexo deploy
```

## 💡 提示

- 目录会自动根据标题层级生成缩进
- H1 标题会作为主目录项
- H2-H6 会根据层级嵌套显示
- 点击目录项可以平滑滚动到对应位置

## 🔗 参考资源

- [Kira 主题官方文档](https://kira.host/hexo/)
- [Kira 主题示例](https://kira.host/)
- [Hexo 官方文档](https://hexo.io/zh-cn/docs/)

## 📝 常见问题

**Q: 目录没有显示？**
A: 检查 `<!-- toc -->` 的位置是否正确，确保在 Front Matter 之后。

**Q: 目录显示不完整？**
A: 检查文章中的标题是否使用了正确的 Markdown 语法。

**Q: 如何隐藏某个标题不在目录中显示？**
A: Kira 主题默认会显示所有标题，如需隐藏可以通过 CSS 控制。

**Q: 目录可以放在侧边栏吗？**
A: 默认是在文章内容中，如需放在侧边栏需要修改主题模板。
