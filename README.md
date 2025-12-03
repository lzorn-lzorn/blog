# Hexo 博客使用指南

这是我的 Hexo 博客源代码仓库。本文档说明如何在不同电脑上编辑和发布博客文章。

## 📁 仓库说明

- **本仓库 (`blog`)**：存储 Hexo 源代码、Markdown 文章、配置文件
- **GitHub Pages 仓库 (`lzorn-lzorn.github.io`)**：存储生成的静态网站文件
- **网站地址**：https://lzorn-lzorn.github.io

---

## 🚀 新电脑首次设置

### 1. 安装必要软件

#### Node.js
- 访问：https://nodejs.org/
- 下载并安装 LTS 版本

#### Git
- 访问：https://git-scm.com/
- 下载并安装

### 2. 配置 Git

```bash
git config --global user.name "你的名字"
git config --global user.email "your-email@example.com"
```

### 3. 配置 SSH（推荐）

#### 生成 SSH 密钥

```bash
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
# 一路回车使用默认设置
```

#### 查看并复制公钥

```bash
cat ~/.ssh/id_rsa.pub
# 复制输出的全部内容
```

#### 添加到 GitHub

1. 访问：https://github.com/settings/keys
2. 点击 "New SSH key"
3. Title：填写 "我的 MacBook"（或其他便于识别的名称）
4. Key：粘贴公钥内容
5. 点击 "Add SSH key"

#### 测试连接

```bash
ssh -T git@github.com
# 第一次会提示输入 yes
# 成功输出：Hi lzorn-lzorn! You've successfully authenticated...
```

### 4. 克隆博客仓库

```bash
git clone git@github.com:lzorn-lzorn/blog.git
cd blog
```

### 5. 安装依赖

```bash
npm install
```

### 6. 测试运行

```bash
# 本地预览
hexo server
# 或简写
hexo s

# 访问 http://localhost:4000 查看效果
```

---

## ✍️ 日常写作流程

### 创建新文章

```bash
# 1. 确保是最新代码
git pull

# 2. 创建文章
hexo new "文章标题"
# 会在 source/_posts/ 目录下创建 Markdown 文件

# 3. 编辑文章
# 使用任何文本编辑器打开 source/_posts/文章标题.md
```

### 文章格式示例

```markdown
---
title: 我的第一篇博客
date: 2025-12-03 23:00:00
tags: 
  - 技术
  - 学习
categories: 编程
---

这里是文章摘要，显示在首页...

<!-- more -->

这里是文章正文...

## 标题

内容...
```

### 本地预览

```bash
# 清理缓存
hexo clean

# 启动本地服务器
hexo server

# 访问 http://localhost:4000 预览
# 按 Ctrl+C 停止服务器
```

### 发布文章

```bash
# 1. 提交源代码到 blog 仓库
git add .
git commit -m "新增文章：文章标题"
git push

# 2. 生成并部署网站
hexo clean          # 清理缓存
hexo generate       # 生成静态文件（简写 hexo g）
hexo deploy         # 部署到 GitHub Pages（简写 hexo d）

# 或者一条命令完成
hexo clean && hexo g && hexo d
```

### 等待生效

- 部署后等待 1-2 分钟
- 访问 https://lzorn-lzorn.github.io 查看效果

---

## 🛠️ 常用命令

| 命令 | 说明 |
|------|------|
| `hexo new "标题"` | 创建新文章 |
| `hexo new page "页面名"` | 创建新页面 |
| `hexo clean` | 清理缓存和生成的文件 |
| `hexo generate` 或 `hexo g` | 生成静态网站 |
| `hexo server` 或 `hexo s` | 启动本地预览服务器 |
| `hexo deploy` 或 `hexo d` | 部署到 GitHub Pages |
| `hexo g -d` | 生成并部署 |

---

## 📝 配置文件说明

- **`_config.yml`**：Hexo 主配置文件
  - 网站标题、描述、作者等基本信息
  - URL 和部署设置

- **`_config.kira.yml`**：Kira 主题配置文件
  - 头像、背景图
  - 菜单、社交链接
  - 颜色主题

- **`source/_posts/`**：存放所有博客文章的 Markdown 文件

- **`source/about.md`**：关于页面

- **`source/friends.md`**：友链页面

---

## 🎨 修改主题配置

编辑 [`_config.kira.yml`](_config.kira.yml ) 文件，常用修改项：

```yaml
# 修改头像
avatar: /1.png

# 修改背景图
background:
    path: bg.jpg

# 添加社交链接
social:
    邮箱:
        - mailto:your-email@example.com
        - icon-link
        - rgb(255, 87, 34)
        - rgba(255, 87, 34, .15)
```

---

## 🔧 故障排查

### 问题：本地预览没有新文章

```bash
hexo clean  # 清理缓存
hexo s      # 重新启动
```

### 问题：部署失败

```bash
# 检查部署配置
cat _config.yml | grep -A 3 "deploy:"

# 确认配置：
# deploy:
#   type: git
#   repo: git@github.com:lzorn-lzorn/lzorn-lzorn.github.io.git
#   branch: main

# 重新部署
hexo clean && hexo g && hexo d
```

### 问题：Git push 失败

```bash
# 先拉取远程更新
git pull --rebase

# 再推送
git push
```

### 问题：网站显示旧内容

- 等待 1-2 分钟让 GitHub Pages 更新
- 清除浏览器缓存（Ctrl+Shift+R 或 Cmd+Shift+R）

---

## ⚠️ 注意事项

1. **不要提交敏感信息**
   - API Keys
   - 密码
   - Token
   - 已在 [`.gitignore`](.gitignore ) 中忽略 `.obsidian/` 目录

2. **图片存放**
   - 小图片：放在 `source/` 目录
   - 大图片：建议使用图床（如 GitHub、阿里云 OSS 等）

3. **多台电脑同步**
   - 开始前：`git pull`
   - 完成后：`git push`

4. **备份重要文章**
   - 所有 Markdown 文件都在 `source/_posts/`
   - 定期推送到 GitHub = 自动备份

---

## 📚 参考资料

- Hexo 官方文档：https://hexo.io/zh-cn/docs/
- Kira 主题文档：https://kira.host/
- Git 教程：https://git-scm.com/book/zh/v2
- Markdown 语法：https://markdown.com.cn/

---

## 🎯 快速命令备忘

```bash
# === 写文章 ===
git pull
hexo new "文章标题"
# 编辑 source/_posts/文章标题.md
hexo s  # 本地预览

# === 发布 ===
git add . && git commit -m "新增文章" && git push
hexo clean && hexo g && hexo d

# === 完成！ ===
# 访问 https://lzorn-lzorn.github.io
```

---

**最后更新：2025年12月3日**
