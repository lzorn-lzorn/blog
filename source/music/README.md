# 音乐文件说明

请将你的音乐文件放在这个目录下：

## 需要的文件：

1. **music-night.mp3** - 音乐文件（支持 mp3/flac/m4a 等格式）
2. **cover.jpg** - 封面图片（可选，建议 300x300 以上）
3. **magic-night.lrc** - 歌词文件（可选，LRC 格式）

## 示例：

```
source/music/
  ├── magic-night.mp3   # 你的音乐文件
  ├── cover.jpg         # 专辑封面
  └── magic-night.lrc   # 歌词（可选）
```

## 添加更多歌曲：

编辑 `/scripts/global-music.js`，在 `audio` 数组中添加：

```javascript
{
  name: '歌曲名',
  artist: '艺术家',
  url: '/music/song.mp3',
  cover: '/music/cover.jpg',
  lrc: '/music/song.lrc'  // 可选
}
```

**注意：**
- 文件名建议使用英文，避免中文路径问题
- 如果没有封面，可以删除 `cover` 这一行
- 如果没有歌词，可以删除 `lrc` 这一行
