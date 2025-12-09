// 全局音乐播放器注入
hexo.extend.filter.register('after_render:html',function (htmlContent) {
	// 使用 APlayer 直接加载本地音乐，不依赖第三方API
	const musicPlayer = `
    <div id="global-aplayer"></div>
    <script>
      if (typeof APlayer !== 'undefined') {
        const ap = new APlayer({
          container: document.getElementById('global-aplayer'),
          fixed: true,
          mini: true,
          autoplay: false,
          theme: '#FF6347',
          loop: 'all',
          order: 'list',
          preload: 'auto',
          volume: 0.4,
          mutex: true,
          listFolded: false,
          listMaxHeight: 200,
          audio: [
            {
              name: '魔法使いの夜～メインテーマ',
              artist: '深澤秀行',
              url: '/music/magic-night.mp3',
              cover: '/music/cover.jpg',
              lrc: '/music/magic-night.lrc'
            }
          ]
        });
      }
    </script>
  `;

	// 在 </body> 标签前插入播放器代码
	return htmlContent.replace(/<\/body>/i,musicPlayer + '</body>');
});
