# 如何更新图标库并添加邮箱图标

## 操作步骤

### 1. 访问 iconfont 项目
访问：https://www.iconfont.cn/manage/index?manage_type=myprojects&projectId=3299330

### 2. 添加邮箱图标
- 点击"从图标库添加"
- 搜索关键词："邮箱" 或 "mail" 或 "email" 或 "envelope"
- 推荐图标：
  * icon-mail
  * icon-email
  * icon-youxiang
- 选择喜欢的图标，点击"加入购物车"
- 点击购物车 → "添加至项目" → 选择 "my-blog"

### 3. 下载图标文件
- 在项目页面点击"下载至本地"
- 解压下载的 zip 文件

### 4. 复制文件到本目录
将解压后的以下文件复制到当前目录（/Users/lzorn/blog/source/lib/iconfont/）：
- iconfont.css
- iconfont.js
- iconfont.json
- iconfont.ttf
- iconfont.woff
- iconfont.woff2

**注意：** 这些文件会覆盖 node_modules 中主题自带的图标文件。

### 5. 查看新图标的名称
打开 `iconfont.json` 文件，找到邮箱图标的 `font_class` 字段，例如：
```json
{
  "icon_id": "xxxxxx",
  "name": "mail",
  "font_class": "mail",  // 这就是图标的名称
  ...
}
```

### 6. 更新配置文件
编辑 `_config.kira.yml`，将邮箱配置中的图标名称改为新图标：
```yaml
social:
    邮箱:
        - mailto:your-email@example.com
        - icon-mail  # 改成实际的图标名称（加 icon- 前缀）
        - rgb(255, 87, 34)
        - rgba(255, 87, 34, .15)
```

### 7. 重新生成网站
```bash
hexo clean && hexo generate
```

### 8. 启动服务器查看效果
```bash
hexo server
```

## 快速命令

在项目根目录执行：

```bash
# 假设你已经下载并解压了图标文件到 ~/Downloads/font_3299330/

# 复制图标文件
cp ~/Downloads/font_3299330/iconfont.* /Users/lzorn/blog/source/lib/iconfont/

# 重新生成
hexo clean && hexo g

# 启动服务器
hexo s
```

## 常见图标名称参考

添加图标后，常见的邮箱图标名称可能是：
- `icon-mail`
- `icon-email`
- `icon-youxiang` (邮箱的拼音)
- `icon-envelope`

记得在配置文件中使用 `icon-` 前缀！
