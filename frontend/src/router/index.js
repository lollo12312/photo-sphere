import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'AlbumList',
    component: () => import('../views/AlbumList.vue')
  },
  {
    path: '/sphere',
    name: 'PhotoSphere',
    component: () => import('../views/PhotoSpherePage.vue')
  },
  {
    path: '/timeline',
    name: 'Timeline',
    component: () => import('../views/Timeline.vue')
  },
  {
    path: '/enhance',
    name: 'Enhance',
    component: () => import('../views/Enhance.vue')
  },
  {
    // 手机照片：复用相册页布局（AlbumList 内按 /mobile 走「手机模式」：只显示竖版 + 竖屏比例卡片）
    path: '/mobile',
    name: 'MobilePhotos',
    component: () => import('../views/AlbumList.vue')
  },
  {
    // 「桌面软件」页嵌入手机端 H5 调试窗，保证各 tab 行为一致
    path: '/desktop',
    name: 'Desktop',
    component: () => import('../views/Desktop.vue')
  },
  {
    // 回收站：删除的照片（入口在全局导航栏右侧垃圾桶图标）
    path: '/trash',
    name: 'Trash',
    component: () => import('../views/Trash.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
