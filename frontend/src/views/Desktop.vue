<template>
  <!-- 桌面软件 = 手机端 H5 页面（wx）嵌入调试：改 frontend/public/wx/index.html 后需 npm run build，刷新本页生效 -->
  <div class="desktop-page">
    <iframe class="desktop-frame" :src="H5_URL" title="手机端页面"></iframe>
  </div>
</template>

<script setup>
// dev 走 Vite(:3000) 时指向后端 :8000 的 wx；生产由后端同源托管则直接 /wx/
const H5_URL = location.port === '8000' ? '/wx/' : 'http://127.0.0.1:8000/wx/'
</script>

<style scoped>
.desktop-page {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 24px 16px 40px;
  overflow: auto;
  background: #0e0e16;
  scrollbar-width: none;                    /* 隐藏外层滚动条（内容仍可滚动） */
  -ms-overflow-style: none;
}
.desktop-page::-webkit-scrollbar { width: 0; height: 0; }
.desktop-frame {
  /* 按手机竖屏比例（9:16）居中显示，不占满整页宽度 */
  width: min(380px, 100%);
  aspect-ratio: 9 / 16;
  height: auto;
  border: 0;
  border-radius: 14px;
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.45);
  flex-shrink: 0;
}
</style>