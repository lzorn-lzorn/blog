// 本地预览(show.py)时注入心跳，供 show.py 检测页面是否已关闭。
// 仅当环境变量 HEXO_PREVIEW=1 时生效，正式生成/部署不会注入。
'use strict';

if (process.env.HEXO_PREVIEW === '1') {
  hexo.extend.injector.register(
    'body_end',
    '<script>(function(){if(window.__hexoPreviewHeartbeat)return;window.__hexoPreviewHeartbeat=true;setInterval(function(){try{fetch("/__hb__",{cache:"no-store"})}catch(e){}},4000)})();</script>',
    'default'
  );
}
