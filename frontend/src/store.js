import { reactive } from 'vue'

export const store = reactive({
  // 当前选中的照片
  currentPhoto: null,
  // 照片列表
  photoList: [],
  // 是否从其他页面跳转到球体
  navigateToSphere: false,
  // 主题
  darkTheme: true,
  // 流星雨
  meteorEnabled: true,
  // 球体控制面板（由全局顶栏按钮控制）
  panelOpen: false,
  // 球体照片数量（电脑照片超过该值时随机抽取子集，默认 60）
  spherePhotoCount: 60,
  // 球体抽样结果会话缓存：照片总数未变时复用上次子集（跨页往返更快、子集稳定）
  sphereSampleCache: null
})