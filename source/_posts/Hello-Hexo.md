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
Hexo 是基于 node.js 的个人博客框架:
```bash
brew install node@18 # 可以使用任何包管理器, @之后是版本号
# npm 会和 nodejs一起安装
```
安装 Hexo:
```bash
npm install -g hexo-cli # 全局安装 Hexo
hexo init blog-name
cd blog-name
npm install
```
这里的 `npm install` 是安装 hexo 内的依赖模块, hexo init 时在 node_modules 中写入了依赖项, `npm install` 是读取了内部的 package.json 然后下载依赖.

```bash
hexo s -p 4000 # hexo 会在本地的 4000 端口启动这个静态界面
```
打开浏览器, 输入 localhost:4000 就可以查看到这个静态网页

可以在 [Hexo Themes](https://hexo.io/themes/) 中选择你喜欢的主题, 注意看主题的主页有没有安装教学, 因为有的主题可以通过更少的命令跳过以上 hexo init 这些步骤. 例如 [kira](kira.host/hexo/)

```bash
# 无须 hexo init, 直接
npm create kira-hexo@latest blog-name 
npm i hexo-theme-kira
```
在 `_config.yml` 中, 将 theme 选项设置为kira, 即 `theme: kira`

修改完之后, 使用 
```bash
hexo g # 重新生成静态网页
hexo s -p 4000 # 在本地查看效果
```

# 部署至 github.io
在 blog-name 文件夹中, 使用
```bash
git init 
git config --global user.name "your-name"
git config --global user.email "your-email@xxx.com"
```
来初始化一个 git 仓库, 并生成一个 ssh 密钥
```bash
ssh-keygen -t rsa -C "your-email@xxx.com"
```
然后根据提示, 三次Enter(回车), 表示yes, 生成 SSH-Key, 通过
```Bash
cat ~/.ssh/id_rsa.pub

# Windows Powershell:
Test-Path "$env:USERPROFILE.ssh\id_rsa.pub" # 检查文件是否存在
Get-Content "$env:USERPROFILE.ssh\id_rsa.pub" # 显示文件内容 or
cat "$env:USERPROFILE.ssh\id_rsa.pub"

# Windows cmd:
type "%USERPROFILE%.ssh\id_rsa.pub" 
```
在 个人的 GitHub 主页: settings > SSH and GPG keys > New SSH key, 将在 ssh-keygen 中生成的密钥复制过来
然后, 在本地
```bash
ssh -T git@github.com # 首次要授权
```
在 `_config.yml` 中, 填写 deploy, 让hexo知道部署的后端在哪, 如果使用github作为后端, 必须创建一个名为 "{your-github-name}.github.io" 其中 {your-github-name} 必须和你的仓库同名
```yml
deploy:
    type: git
    repo: https://github.com/your-github-name/your-github-name.github.io.git
    branch: main # 也有可能是 master, 在仓库的 settings > general > default branch
```
最后安装一个 hexo 插件用于部署
```bash
npm install hexo-deployer-git --save
```
最后重新生成, 然后部署既可
```bash
hexo g
hexo d
```

# 多端同步
为了可以在不同的电脑上编写和上传博客, 需要将本地的这个 hexo 部分的上传至另一个仓库, 每次换到新的电脑上, 安装好 hexo 环境, 从github拉下该仓库写博客上传, 然后本地部署.
注意, 之前虽然 git init 创建了仓库, 也通过 `hexo d` 部署了博客, 但该仓库依然没有链接至远程仓库, 此时使用
```bash
git remote add origin https://github.com/your-github-name/your-blog-repo-name.git
```
去将该仓库上传至远端, 其中要配置 .gitignore文件, 因为有的东西是 hexo 生成的或者 npm 创建的, 不需要上传
```gitignore
.DS_Store
Thumbs.db
db.json
*.log
node_modules/
public/
.deploy*/
_multiconfig.yml
```
同时在新的电脑上依然需要重复一遍上述的 ssh-keygen 的操作, 并在 github 上创建新的 SSH-Key, 因为这个一个电脑一个的