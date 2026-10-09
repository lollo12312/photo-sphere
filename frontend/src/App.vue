<template>
  <!-- ===== index.html 原样结构：root-el ===== -->
  <!-- light：昼夜替换→亮色主题（暗色为默认深色主题） -->
  <div class="app-shell" :class="{ 'app-shell--fit': isFitRoute, light: !store.darkTheme }">
    <!-- 相册页移除内嵌顶栏，全局统一使用本顶部导航 -->
    <!-- 流星雨：全站生效（含长列表页），开关切换立即可见；canvas 已 pointer-events: none 不挡操作 -->
    <MeteorShower v-if="store.meteorEnabled" />

    <!-- ===== 原样：main-top 顶部导航（全路由常驻） ===== -->
    <div class="main-top">
      <!-- Logo -->
      <a href="#" class="logo" @click.prevent>
        <span class="logo-img">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>
        </span>
        <span class="logo-text">照片球体</span>
      </a>

      <!-- 中间导航区（5 tab 结构） -->
      <div class="header-top-view">
        <div class="TopBody is-nt-front">
          <div class="wrapper" ref="menuWrapperEl">
            <div class="transition-box">
              <!-- 6 个真实路由 tab -->
              <template v-for="(item, i) in menuItems" :key="item.label">
                <router-link
                  v-if="item.toUrl" :to="item.to"
                  class="twoTopLable"
                  :class="{ 'tab-active': isActive(item.to) }"
                  @click="moveTab(i)"
                >
                  <div class="tabCss">
                    <a class="tab-nuxt-link" :title="item.label">
                      <i class="el-icon" v-html="item.icon"></i>
                      <span class="top-nav-text">{{ item.label }}<span v-if="item.badge" class="new-tab">N</span></span>
                    </a>
                  </div>
                </router-link>
                <div v-else class="twoTopLable" @click="moveTab(i)">
                  <div class="tabCss">
                    <a class="tab-nuxt-link" :title="item.label">
                      <i class="el-icon" v-html="item.icon"></i>
                      <span class="top-nav-text">{{ item.label }}<span v-if="item.badge" class="new-tab">N</span></span>
                    </a>
                  </div>
                </div>
              </template>
              <!-- lableEnd（功能空着） -->
              <div class="lableEnd">
                <!-- 低功耗模式：按钮 + 下拉菜单（昼夜替换 / 流星效果） -->
                <div ref="powerBtnEl" class="small-icon power-menu" :class="{ open: powerMenuOpen }" title="低功耗模式" @click.stop="openPowerMenu">
                  <svg class="icon" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
                </div>
                <div class="small-icon" :class="{ active: route.path === '/trash' }" title="回收站" @click="router.push('/trash')">
                  <svg class="icon" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                </div>
                <div class="small-icon" title="积分奖励">
                  <svg class="icon" viewBox="0 0 1024 1024" fill="currentColor"><path d="M512 64l166.4 337.3L1040 432 780 688.4l61.3 336.1L512 848.5l-329.3 176 61.3-336.1L-16 432l361.6-30.7z"/></svg>
                  <span class="reward" style="color:#ffc743;">+1</span>
                </div>
              </div>
              <!-- 低功耗下拉菜单：teleport 到 body + fixed 定位，绕开 .header-top-view 的 overflow 裁剪 -->
              <teleport to="body">
                <div v-if="powerMenuOpen" ref="dropEl" class="power-drop" :style="{ top: dropPos.top + 'px', left: dropPos.left + 'px' }" @click.stop>
                  <div class="power-item" @click="toggleDark">
                    <span class="power-item-icon" v-html="darkIcon"></span>
                    <span class="power-item-text">昼夜替换</span>
                    <span class="power-item-state">{{ store.darkTheme ? '暗色' : '亮色' }}</span>
                  </div>
                  <div class="power-item" @click="store.meteorEnabled = !store.meteorEnabled">
                    <span class="power-item-icon" v-html="STAR_ICON"></span>
                    <span class="power-item-text">流星效果</span>
                    <span class="mini-switch" :class="{ on: store.meteorEnabled }"></span>
                  </div>
                </div>
              </teleport>
            </div>
            <!-- tab 滑块（原样；不在任何 tab 的路由如回收站时隐藏，避免错位高亮） -->
            <div class="tab" ref="slideTabEl" v-show="isNavRoute"></div>
          </div>
        </div>
      </div>

      <!-- 右侧登录区（原样结构，功能空着） -->
      <div class="navbar header-tab-tight-top">
        <div class="topDiv dlBefore" :class="{ show: loginOpen }" @click="loginOpen = !loginOpen">
          <a href="#" class="nuxt-link" @click.prevent>
            <svg viewBox="0 0 24 24" fill="currentColor" width="90%" height="90%"><path fill="#ffffff80" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
          </a>
          <div class="processing-indicator"><div class="spinner"></div></div>
        </div>
        <!-- center-div 原样（内容空着） -->
        <div class="center-div" :class="{ show: loginOpen }">
          <div class="partition"></div>
          <div class="top-name">未登录</div>
          <div class="center-div-1">
            <div>我的</div>
            <div>收藏</div>
            <div>上传</div>
          </div>
          <div class="center-div-2">
            <div class="t-1" title="微信登录">
              <div class="weix"></div>
            </div>
          </div>
          <div class="center-div-3">
            <div class="cd2-1">登录 / 注册</div>
          </div>
        </div>
      </div>
    </div>

    <router-view />

    <!-- ===== 原样：页脚推广位（占位空着） ===== -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { store } from './store'
import MeteorShower from './components/MeteorShower.vue'

const route = useRoute()
const router = useRouter()
const loginOpen = ref(false)

// 低功耗模式 = 顶栏按钮 + 下拉菜单（昼夜替换 darkTheme / 流星效果 meteorEnabled，状态全局共享）
const powerMenuOpen = ref(false)
const powerBtnEl = ref(null)
const dropEl = ref(null)
const dropPos = ref({ top: -9999, left: -9999 })
const toggleDark = () => { store.darkTheme = !store.darkTheme }
function openPowerMenu() {
  if (!powerMenuOpen.value) {
    const b = powerBtnEl.value?.getBoundingClientRect()
    if (b) {
      // 先按按钮右缘定位，弹出后测量自身宽度再右对齐（避免 fixed 位置闪动）
      dropPos.value = { top: b.bottom + 6, left: b.right }
      powerMenuOpen.value = true
      nextTick(() => {
        const d = dropEl.value
        if (d) {
          const r = d.getBoundingClientRect()
          dropPos.value = { top: b.bottom + 6, left: b.right - r.width }
        }
      })
    }
  } else {
    powerMenuOpen.value = false
  }
}

// 路由分两类，决定页面是否锁定成一屏：
// - 长列表页（电脑库 / 手机库）：两页共用同一套相册布局，需要**文档正常滚动**
//   （滚动才能实现「左侧分页点击定位」「火箭回顶」「搜索栏 sticky 吸附」）
// - 整屏一页（全景球 / 时间轴 / 智能增强 / 桌面软件 / 回收站）：锁 100dvh，只有内部区域滚动
const LONG_LIST_ROUTES = ['/', '/mobile']
const FIT_ROUTES = ['/sphere', '/timeline', '/enhance', '/desktop', '/trash']
const isLongListRoute = computed(() => LONG_LIST_ROUTES.includes(route.path))
const isFitRoute = computed(() => FIT_ROUTES.includes(route.path))

// ===== rem 基准：全站统一锁为 lib-flexible 的桌面值（rem=54px 恒定） =====
// libflex.js 规则：桌面 width>540*dpr 时 width 被钳制到 540*dpr，rem = width/10；dpr=1 → 54px
// 这样顶部导航（rem 布局）在所有页面等大、跨页一致，不随各页窗口/缩放变化
const GLOBAL_REM = 54
function applyRem() {
  document.documentElement.style.fontSize = GLOBAL_REM + 'px'
}
applyRem()

// ===== 6 个 tab → 6 个页面（结构原样；图标改为与当前页面语义匹配的线性图标） =====
// 说明：svg 的 fill 被全局规则设为 var(--color-text)，这里用 inline style 覆盖为 none，
// 改为 stroke=currentColor 描边，尺寸仍由 .tabCss .tab-nuxt-link .el-icon svg (0.22rem) 控制，不影响布局
const NAV_SVG = 'viewBox="0 0 24 24" style="fill:none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'

// 低功耗下拉菜单图标：昼夜（暗色=月亮 / 亮色=太阳）+ 流星
const MOON_ICON = `<svg ${NAV_SVG}><path d="M20.5 13.6A8 8 0 1 1 10.4 3.5a6.2 6.2 0 0 0 10.1 10.1z"/></svg>`
const SUN_ICON = `<svg ${NAV_SVG}><circle cx="12" cy="12" r="4.2"/><path d="M12 2.8v2.2M12 19v2.2M2.8 12H5M19 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6"/></svg>`
const STAR_ICON = `<svg ${NAV_SVG}><path d="M12 3.4l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z"/></svg>`
const darkIcon = computed(() => (store.darkTheme ? MOON_ICON : SUN_ICON))

const menuItems = [
  { to: '/', label: '电脑库', badge: false, toUrl: true,
    icon: `<svg ${NAV_SVG}><rect x="3" y="4.2" width="18" height="15.6" rx="2.4"/><circle cx="8.6" cy="9.6" r="1.6"/><path d="M3.4 17.6l4.8-4.8 3.6 3.6 3.2-3.2 5.6 5.6"/></svg>` },
  { to: '/mobile', label: '手机库', badge: true, toUrl: true,
    icon: `<svg ${NAV_SVG}><rect x="6.6" y="2.4" width="10.8" height="19.2" rx="2.6"/><path d="M10.6 18.6h2.8"/></svg>` },
  { to: '/sphere', label: '全景球', badge: false, toUrl: true,
    icon: `<svg ${NAV_SVG}><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><ellipse cx="12" cy="12" rx="4.2" ry="9"/></svg>` },
  { to: '/timeline', label: '时间轴', badge: false, toUrl: true,
    icon: `<svg ${NAV_SVG}><circle cx="12" cy="12" r="9"/><path d="M12 6.8v5.4l3.6 2.1"/></svg>` },
  { to: '/enhance', label: '智能增强', badge: true, toUrl: true,
    icon: `<svg ${NAV_SVG}><path d="M9.6 3.2l1.6 4.6 4.6 1.6-4.6 1.6-1.6 4.6-1.6-4.6L3.4 9.4l4.6-1.6z"/><path d="M17.4 14.4l.9 2.5 2.5.9-2.5.9-.9 2.5-.9-2.5-2.5-.9 2.5-.9z"/></svg>` },
  { to: '/desktop', label: '桌面软件', badge: true, toUrl: true,
    icon: `<svg ${NAV_SVG}><rect x="2.6" y="4" width="18.8" height="12.8" rx="2"/><path d="M12 16.8v3.4"/><path d="M8.6 20.2h6.8"/></svg>` }
]

const menuWrapperEl = ref(null)
const slideTabEl = ref(null)

function isActive(to) { return route.path === to }

// 回收站等非菜单路由：不属于任何 tab，隐藏滑块、不高亮任何导航项
const isNavRoute = computed(() => menuItems.some(m => m.to === route.path))

// ===== index.html 原版脚本：moveTab 滑块定位 =====
function moveTab(index) {
  const wrapper = menuWrapperEl.value
  const tabEl = slideTabEl.value
  if (!wrapper || !tabEl) return
  const items = wrapper.querySelectorAll('.twoTopLable')
  const tab = items[index]
  if (!tab) return
  const rect = tab.getBoundingClientRect()
  const wrapperRect = wrapper.getBoundingClientRect()
  tabEl.style.left = (rect.left - wrapperRect.left) + 'px'
  tabEl.style.width = rect.width + 'px'
}

function onResize() {
  applyRem()
  const idx = menuItems.findIndex(m => m.to === route.path)
  if (idx >= 0) moveTab(idx)
}

function onDocClick(e) {
  if (loginOpen.value && !e.target.closest('.navbar')) loginOpen.value = false
  if (powerMenuOpen.value && !e.target.closest('.power-menu')) powerMenuOpen.value = false
}

// 滑块对齐兜底：路由切换 / 容器尺寸变化（滚动条出现消失 → grid 列宽重排 1-2px）后，
// 用下一帧重新测量按钮实际宽度同步滑块，保证高亮块始终与按钮完全重合
let slideRaf = null
let slideObserver = null
function syncSlide() {
  cancelAnimationFrame(slideRaf)
  slideRaf = requestAnimationFrame(() => {
    const idx = menuItems.findIndex(m => m.to === route.path)
    if (idx >= 0) moveTab(idx)
  })
}

onMounted(() => {
  nextTick(() => {
    const idx = menuItems.findIndex(m => m.to === route.path)
    if (idx >= 0) moveTab(idx)
  })
  window.addEventListener('resize', onResize)
  document.addEventListener('click', onDocClick)
  window.addEventListener('scroll', onPageScroll, true) // capture：内部滚动容器（如时间轴列表）滚动也会触发
  if (menuWrapperEl.value && typeof ResizeObserver !== 'undefined') {
    slideObserver = new ResizeObserver(syncSlide)
    slideObserver.observe(menuWrapperEl.value)
  }
})

function onPageScroll() {
  // 低功耗下拉 fixed 定位不随滚动，滚动时直接收起避免悬空错位
  if (powerMenuOpen.value) powerMenuOpen.value = false
}

onUnmounted(() => {
  slideObserver?.disconnect()
  cancelAnimationFrame(slideRaf)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('scroll', onPageScroll, true)
})

watch(() => route.path, () => {
  loginOpen.value = false
  powerMenuOpen.value = false
  // 全站统一 rem=54px（对齐桌面基准值），路由切换时重设一次
  applyRem()
  syncSlide()
})

// 昼夜替换：<html> 挂 .light 类，配合全局变量覆盖实现全站亮色（含 body 底色）
watch(() => store.darkTheme, (v) => {
  document.documentElement.classList.toggle('light', !v)
}, { immediate: true })
</script>

<style>
/* ===== 还原页面 CSS 变量 (darkBody 主题) ===== */
:root {
  --vt-c-black1: #282828;
  --vt-c-black2: #000000;
  --vt-c-black-soft: #222222;
  --vt-c-black-mute: #282828;
  --vt-c-divider-dark-2: #5454547a;
  --vt-c-text-dark-1: #ffffff;
  --vt-card-bag-dark: #4e474799;
  --lable-card-bag-dark: #96969642;
  --vt-tm-dark: #000000bf;
  --ty-tm-dark: #0009;
  --fd-a-dark: #3535351a;
  --color-text-dark-cale: #b7b7b7;
  --color-text-darkgray-cale: #dedede;
  --ccc-color-dark-3: #565151;
  --font-color-dark: #ffffff;
  --webkit-color-dark: #5d5d5d;
  --fc-color-dark: #fff1f1;
  --shen-color-dark: #6f6f6f80;
  --card-bottom-bg-dark: #00000042;
  --ps-bg-color-light: #0009;
  --cropper-accent: #fee450;
  --color-tm-text: #ffffffa6;
  --page-margin: 5px;
  --col-bg-start: #191919;
  --col-bg-end: #5c5b5c80;
  --cursor-touch: auto;
  --top-color-dark: #6f8bbea3;

  --main-bg-tw: var(--vt-tm-dark);
  --frosted-bg: var(--fd-a-dark);
  --color-background-vk: var(--vt-c-divider-dark-2);
  --color-background-soft: var(--vt-c-black-soft);
  --color-background-mute: var(--vt-c-black-mute);
  --color-text: var(--vt-c-text-dark-1);
  --color-cale-text: var(--color-text-dark-cale);
  --font-background-webkit: var(--font-color-dark);
  --card-background-webkit: var(--vt-card-bag-dark);
  --card-bottom-bg: var(--card-bottom-bg-dark);
  --fc-background-webkit: var(--fc-color-dark);
  --ps-bg-bag: var(--ps-bg-color-light);
  --color-background-webkit: var(--webkit-color-dark);
  --top-color: var(--top-color-dark);
  --svg-color: #666565;
  --switch-bt-color: #41414ff2;

  --ps-go-surface: #2d313582;
  --ps-go-surface-deep: #232629d1;
  --ps-go-text: #f7f9faf0;
  --ps-go-muted: #e1e7ec94;
  --ps-go-faint: #e1e7ec5c;
  --ps-go-line: #ffffff1a;
  --ps-go-line-strong: #ffffff2b;
  --ps-go-overlay: #07090b85;
  --ps-go-accent: #dbe4ea;
  --ps-go-accent-text: #20262b;
  --ps-go-shadow: 0 18px 46px #00000057;
  --ps-go-inner: inset 3px 3px 8px #0000003d, inset -2px -2px 6px #ffffff09;
}

/* ===== 亮色主题（昼夜替换 → darkTheme=false）：重定义全局变量，var() 使用处全站变亮 =====
   挂载方式：App.vue watch store.darkTheme 给 <html> 加/去 .light；页面级深色硬编码由各页 .light 规则补兜底 */
html.light, html.light body, html.light #app {
  background: #f3f2f7;
  color: #1f2126;
}
.app-shell.light {
  /* 文字与主色 */
  --vt-c-text-dark-1: #1f2126;
  --font-color-dark: #1f2126;
  --fc-color-dark: #20222a;
  --color-text-dark-cale: #70707a;
  --color-text-darkgray-cale: #4c4c55;
  --ccc-color-dark-3: #ebebf0;
  --svg-color: #3a3a44;
  --switch-bt-color: #4b4b58;
  /* ── 衍生变量必须在同一选择器下重定义：:root 里的 `--x: var(--y)` 在 :root 求值，
       只改源头变量不会传导到这些衍生值（如 --color-text）── */
  --color-text: #1f2126;
  --color-cale-text: #70707a;
  --font-background-webkit: #1f2126;
  --card-background-webkit: rgba(255, 255, 255, 0.6);
  --card-bottom-bg: rgba(255, 255, 255, 0.62);
  --fc-background-webkit: #20222a;
  --ps-bg-bag: rgba(255, 255, 255, 0.75);
  --color-background-webkit: #e8e8ee;
  --top-color: #d6dbe8;
  /* 面板 / 底 / 背景 */
  --vt-c-black1: #f6f6f8;
  --vt-c-black2: #ffffff;
  --vt-c-black-soft: #f0f0f4;
  --vt-c-black-mute: #f5f5f8;
  --vt-c-divider-dark-2: rgba(0, 0, 0, 0.08);
  --fd-a-dark: rgba(255, 255, 255, 0.5);          /* 导航毛玻璃底 */
  --vt-card-bag-dark: rgba(255, 255, 255, 0.6);
  --lable-card-bag-dark: rgba(0, 0, 0, 0.04);
  --vt-tm-dark: rgba(255, 255, 255, 0.72);
  --ty-tm-dark: rgba(255, 255, 255, 0.6);
  --ps-bg-color-light: rgba(255, 255, 255, 0.75);
  --card-bottom-bg-dark: rgba(255, 255, 255, 0.62);
  --shen-color-dark: rgba(0, 0, 0, 0.06);
  --webkit-color-dark: #e8e8ee;
  --top-color-dark: #d6dbe8;
  --col-bg-start: #e7e6ee;
  --col-bg-end: rgba(220, 220, 235, 0.7);
  /* Go 弹窗体系 */
  --ps-go-surface: rgba(250, 250, 253, 0.9);
  --ps-go-surface-deep: rgba(238, 238, 245, 0.95);
  --ps-go-text: #1f2126;
  --ps-go-muted: rgba(31, 33, 38, 0.55);
  --ps-go-faint: rgba(31, 33, 38, 0.28);
  --ps-go-line: rgba(0, 0, 0, 0.1);
  --ps-go-line-strong: rgba(0, 0, 0, 0.16);
  --ps-go-overlay: rgba(240, 240, 246, 0.86);
  --ps-go-accent: #e6ecf5;
  --ps-go-accent-text: #20262b;
  --ps-go-shadow: 0 18px 46px rgba(60, 60, 90, 0.28);
  --ps-go-inner: inset 3px 3px 8px rgba(0, 0, 0, 0.06), inset -2px -2px 6px rgba(255, 255, 255, 0.8);
  background: #f3f2f7;
  color: #1f2126;
}

/* 低功耗下拉菜单亮色（teleport 挂在 body 下，用 html.light 命中；深度深于对等 scoped 规则） */
html.light .power-drop { background: rgba(248, 248, 252, 0.94); border-color: rgba(0, 0, 0, 0.08); box-shadow: 0 10px 28px rgba(60, 60, 90, 0.22); }
html.light .power-drop .power-item:hover { background: rgba(0, 0, 0, 0.06); }
html.light .power-drop .power-item-state { color: rgba(0, 0, 0, 0.5); }
html.light .power-drop .mini-switch { background: rgba(0, 0, 0, 0.14); }

/* ===== index.html 原样：全局基础（不加 scoped，与原文件一致） ===== */
* { margin: 0; padding: 0; box-sizing: border-box; }
::-webkit-scrollbar { width: 0; height: 0; }
::-webkit-scrollbar-thumb { background: #000; border-radius: 30px; }
::-webkit-scrollbar-track { background-color: #7d717a; border-radius: 30px; }

html, body, #app {
  /* 全局统一滚动条槽位：长列表页有滚动条（占 15px）、整屏页无滚动条（占 0），
     会让顶部导航整体宽度随页面切换跳 1-2px（按钮 107↔109）。
     stable 让所有页面恒定保留滚动条空间，导航宽度处处一致 */
  scrollbar-gutter: stable;
  background: #262626;
  color: #ffffff;
  font-family: -apple-system, Arial, Helvetica, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  /* 注意：不能用 overflow-x:hidden —— 它会强制 overflow-y 计算为 auto，使 body/#app 变成滚动容器，
     导致相册页搜索栏的 position:sticky 绑定到错误的滚动容器而失效（无法悬浮贴底）。
     overflow-x:clip 同样裁掉横向溢出，但不创建滚动容器，sticky 才能正常吸附。 */
  overflow-x: hidden; /* 旧浏览器回退 */
  overflow-x: clip;
  /* 滚动条外观：浅灰滑块 + 黑色轨道（firefox 等现代浏览器生效） */
  scrollbar-color: #acb8bb #000;
  width: 100%;
}
a { color: inherit; text-decoration: none; }
button { font-family: inherit; cursor: pointer; }

.app-shell {
  z-index: 10;
  background: #262626;
  flex-direction: column;
  min-height: 100vh;
  font-size: 15px;
  position: relative;
  top: 0;
  width: 100%;
  display: flex;
  align-items: center;
}

/* ===== 全景球 / 时间轴 / 智能增强：整屏一页，不出现整页滚动（页面内部区域自行滚动） =====
   说明：相册页不加 .app-shell--fit，保持文档流正常滚动 + 搜索栏 sticky 行为不变 */
.app-shell--fit {
  height: 100vh;  /* 旧浏览器回退 */
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
}
/* 顶栏按自身高度，不参与伸缩 */
.app-shell--fit > .main-top { flex: 0 0 auto; }
/* 其余兄弟节点（页面根节点）：占满顶栏之下的剩余高度，允许收缩到内容以下 */
.app-shell--fit > *:not(.main-top) {
  flex: 1 1 auto;
  min-height: 0;
}
</style>

<style scoped>
/* ===== index.html 原样：main-top 顶部导航 ===== */
.main-top {
  align-items: center;
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-evenly;
  min-height: 1.4rem;
  margin-top: 0.3rem;
  padding: 0.1rem;
  position: relative;
  z-index: 100;
}

.main-top .logo {
  white-space: nowrap;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  width: 3.5rem;
  box-shadow: 2px 2px 5px var(--col-bg-start);
  border-radius: 40px;
  justify-content: center;
  align-items: center;
  padding: 0.2rem;
  display: flex;
  position: relative;
  cursor: default;
}
.main-top .logo .logo-img {
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 50%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.08);
  color: #837f84;
}
.main-top .logo .logo-img svg { width: 70%; height: 70%; }
.main-top .logo span.logo-text {
  color: #837f84;
  text-shadow: 0 0 30px #515050;
  font-size: 0.5rem;
  font-weight: 500;
  margin-left: 0.16rem;
}

.main-top .header-top-view {
  justify-content: center;
  width: 65%;
  height: 100%;
  padding: 0.2rem;
  display: flex;
  flex-grow: 1;
  overflow: auto;
}

.TopBody {
  z-index: 110;
  min-width: 80%;
  color: var(--color-text);
  -webkit-user-select: none;
  user-select: none;
  background-color: var(--frosted-bg);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 50px;
  justify-content: center;
  align-items: center;
  display: flex;
}
.TopBody.is-nt-front {
  box-shadow: 2px 2px 6px var(--col-bg-start), -2px -2px 6px var(--col-bg-end);
}
.transition-box {
  width: 100%;
  height: 100%;
  /* grid 严格等分：6 个 tab 每列 1fr 完全同宽（flex 均分会因小数舍入出现 107/109 的偏差），
     最后一列 auto 给右侧功能控件（开关/回收站/积分）按内容取宽，不再参与均分 */
  display: grid;
  grid-template-columns: repeat(6, 1fr) auto;
  position: relative;
  overflow: visible;
}
.transition-box .noneInput { display: none; }
.TopBody .wrapper {
  border-radius: 50px;
  justify-content: center;
  align-items: center;
  width: 100%;
  display: flex;
  position: relative;
  bottom: 0;
  height: 0.9rem !important;
}
.wrapper .tab {
  will-change: transform, background-color;
  width: 15%;
  height: 100%;
  /* 温和一致的滑动：去掉原来的 0.9s 回弹曲线（负值 overshoot 会让高亮块先膨胀再回落，
     且各 tab 宽度/位移不同导致每次变化幅度不一致） */
  transition: left 0.35s cubic-bezier(0.4, 0, 0.2, 1), width 0.35s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.5s;
  position: absolute;
  background-color: var(--main-bg-tw);
  box-shadow: 0 0 10px var(--color-background-soft);
  border-radius: 1rem;
  left: 0;
}
.twoTopLable {
  z-index: 1;
  border-radius: 100px;
  /* 统一等宽：flex-basis 0 让 6 个 tab 完全均分容器宽度，
     避免文字长度不同导致按钮宽度不一（101px vs 120px），切换时高亮块无需缩放 */
  flex: 1 1 0;
  min-width: 0;
  justify-content: center;
  align-items: center;
  height: 100%;
  position: relative;
  display: flex;
  text-decoration: none;
}
.twoTopLable.tab-active {
  background-color: var(--main-bg-tw);
  box-shadow: 0 0 10px var(--color-background-soft);
  border-radius: 1rem;
  transition: background-color 0.35s;
}
.tabCss {
  z-index: -1;
  text-align: center;
  text-decoration: none;
  position: relative;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  display: flex;
}
.tabCss .tab-nuxt-link {
  color: var(--color-text);
  gap: 4px;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  display: flex;
  text-decoration: none;
  cursor: pointer;
}
.tabCss .tab-nuxt-link .el-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tabCss .tab-nuxt-link .el-icon svg {
  width: 0.44rem;  /* 图标放大一倍，观感与 0.3rem 文字匹配 */
  height: 0.44rem;
  fill: var(--color-text);
}
.tabCss .top-nav-text {
  white-space: nowrap;
  font-size: 0.3rem;
  font-weight: 500;
  position: relative;
  line-height: 1;  /* 与放大后的图标垂直居中对齐 */
}
.tabCss h1, .tabCss span:not(.top-nav-text):not(.new-tab) {
  white-space: nowrap;
  font-size: 0.3rem;
  font-weight: 500;
}

/* NEW badge 原样 */
.new-tab {
  color: #fff;
  background-color: #4a0f3b7d;
  border-radius: 50%;
  justify-content: center;
  align-items: center;
  width: 0.37rem;
  height: 0.37rem;
  font-weight: 500;
  display: flex;
  position: absolute;
  top: -0.26rem;
  right: -0.23rem;
  box-shadow: 0 0 20px #ff43be;
  font-size: 70% !important;
}

/* 右侧登录区宽度 原样 */
.main-top .header-tab-tight-top {
  width: 3.5rem;
}

/* lableEnd 原样 */
.lableEnd {
  justify-content: flex-end;
  gap: 0.3rem;
  padding-right: 0.35rem;
  align-items: center;
  height: 100%;
  display: flex;
}
.lableEnd .cut-subject,
.lableEnd .small-icon {
  align-items: center;
  height: 100%;
  display: flex;
}
.lableEnd .small-icon {
  justify-content: center;
  position: relative;
  cursor: pointer;
  transition: color 0.2s;
}
/* 回收站入口激活态：当前在回收站页面时高亮 */
.lableEnd .small-icon.active .icon {
  fill: #6c63ff;
  opacity: 1;
}
.lableEnd .small-icon .icon {
  width: 30px;
  fill: var(--color-text);
}
.lableEnd .small-icon .reward {
  font-size: 0.2rem;
  position: absolute;
  bottom: -0.1rem;
}
.lableEnd .cut-select {
  aspect-ratio: 1;
  white-space: nowrap;
  height: 100%;
  text-shadow: 0 0 15px var(--fc-background-webkit);
  border-radius: 50%;
  justify-content: center;
  align-items: center;
  transition: background-color 0.3s;
  display: flex;
}
.lableEnd .cut-select span {
  font-size: 0.3rem;
  font-weight: 500;
}
.lableEnd .cut-select:hover {
  background-color: var(--webkit-color-dark);
}
.lableEnd .cut-select-1 { box-shadow: -15px 0 26px #f08a8d; }
.lableEnd .cut-select-2 { box-shadow: -15px 0 26px #8587ea; }

/* switch 原样 */
.switch {
  --switch-width: 1.1rem;
  --switch-height: 0.5rem;
  --switch-thumb-gap: 0.07rem;
  --switch-thumb-size: calc(var(--switch-height) - var(--switch-thumb-gap) * 2);
  box-sizing: border-box;
  width: var(--switch-width);
  height: var(--switch-height);
  z-index: 100;
  background-color: #b7b6b6;
  border: 0;
  border-radius: 2rem;
  justify-content: center;
  align-items: center;
  font-size: 0.2rem;
  font-weight: 500;
  transition: all 0.3s;
  display: flex;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 5px #8f8f8fa1;
  cursor: pointer;
}
.switch.switch-checked {
  background-color: #2f2f2f;
}
.switch.switch-checked:after {
  left: calc(100% - var(--switch-thumb-size) - var(--switch-thumb-gap));
}
.switch:after {
  content: "";
  left: var(--switch-thumb-gap);
  width: var(--switch-thumb-size);
  height: var(--switch-thumb-size);
  background-color: #c9c9c9;
  background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAAXNSR0IArs4c6QAAAv1JREFUaEPVml1y4yAMx437uvHkRk1Ptu3Jmt6o4+xrzY5IoSBLQsjQmfglTcaG/09fyFA3PfjlHlz/1A3gz/l8mbft4r1/TkZx7hL+9v4KH865D/jc5vn67/Mz/Hb0OgQAot3X198gIoptUOSm6Q1uX9f1teGx4lYTQBJuEE0JPQLSBCAK/w4T//QUrApXDBN4Dr5DiIWImqa719AFIK3eUAME8dv2vpvV+yuIbo3plDMETAuICmBZlted1YzCKctT42shqgC7wTsKz2EoD2sgRABK/O12e7FWDM1zp9PpPa9oNQgWAIuvDRQT3JIPGAzP7ef5hcsxFuC0LD4N7P2VszyuTLd1rYalxRMcBDkZtgAnqtVLGuH5PUU4MUbcAWjdd6RyaEFwYlNeEAG4uCfLKixQQqxqReP7al4oADShw4kPK+wAgJoXWADO+kVyI3ONAIApJC8UALk4Soxk/VEegHELL6BkTgDYVVTlkaw/EgB7ITduAsitS4VPzfq/CZDr6wpQW62tlUgKowSQJ4ol/oM4YcU+Ir4LAG6yOEG9Wgk8PpfIPx7Ieh9LAscJR5XSkMiExu4AI8NIBsj6cMqK2hAaVY3qIdQRYIQXfhcAtokMOwxSpeLWKXIdoCzI7koIs/ZM6CqA1G9EjbVWgmLpBcH1aWUzV8kDTTtBQRwNJ6lPYwG4RGypRjnMEQipTysAai8PuyXd0B9YQPLwwc/vXilrr3Cg2RpKFo/UuuQdgMYLvSASELPbh7VQ3iO3VTRe6ArBdLFS6ER4EmBX84U2+XA4ceLRFiPX5bK7aBr35THdDCJsErdsmHXf3IXJ7+82/rk4dkIHINxeZ7fN3WhdyrK9Vtfcg9Tpj6bkqjZiR24jcsdWGvFgABWAVHFgIsuxqXTe1uJhNYAUUllJCwd8AASf+JAvWEw6ljWc/jQDRG+ERGVOG5s7DINwcR3QCkgVxwKSVaXWE07UkmjlyvfFY9NUQkO8lP9qcP/JfVhyhpvdFEJ9kPuM8vAA/wF0MBZeGK3yxgAAAABJRU5ErkJggg==);
  background-size: cover;
  border-radius: 2rem;
  transition: left 0.25s;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  box-shadow: 1px 1px 3px #00000040;
}

/* ===== 低功耗模式：按钮 + 下拉菜单 ===== */
.power-menu { cursor: pointer; }
.power-menu.open .icon { fill: #6c63ff; opacity: 1; }
.power-drop {
  position: fixed;
  z-index: 999;
  min-width: 3.7rem;
  padding: 0.18rem;
  background: rgba(22, 22, 32, 0.92);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.18rem;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4);
}
.power-item {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.28rem 0.26rem;
  border-radius: 0.12rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s;
}
.power-item:hover { background: rgba(255, 255, 255, 0.07); }
.power-item:active { background: rgba(108, 99, 255, 0.28); }
.power-item-icon {
  width: 0.36rem;
  height: 0.36rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--fc-background-webkit, #fff);
}
.power-item-icon :deep(svg) { width: 0.3rem; height: 0.3rem; }
.power-item-text { font-size: 0.21rem; color: var(--color-text, #fff); flex: 1; }
.power-item-state { font-size: 0.18rem; color: rgba(255, 255, 255, 0.55); }
.mini-switch {
  width: 0.58rem;
  height: 0.32rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.18);
  position: relative;
  flex-shrink: 0;
  transition: background-color 0.25s;
}
.mini-switch::after {
  content: "";
  position: absolute;
  top: 50%;
  left: 0.05rem;
  width: 0.24rem;
  height: 0.24rem;
  border-radius: 50%;
  background: #fff;
  transform: translateY(-50%);
  transition: left 0.25s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}
.mini-switch.on { background: #6c63ff; }
.mini-switch.on::after { left: calc(100% - 0.29rem); }

/* navbar 原样 */
.navbar {
  z-index: 200;
  -webkit-user-select: none;
  user-select: none;
  flex-direction: column;
  height: 1.5rem;
  display: flex;
  position: relative;
  align-items: center;
}
.navbar .topDiv {
  z-index: 6;
  aspect-ratio: 1;
  height: 100%;
  will-change: transform;
  backface-visibility: hidden;
  border: 1px solid var(--fc-background-webkit);
  border-radius: 20px;
  justify-content: center;
  transition: transform 0.3s, box-shadow 0.3s;
  transform: translateZ(0);
  display: flex;
  position: relative;
  align-items: center;
  overflow: hidden;
  cursor: pointer;
}
.navbar .topDiv .nuxt-link {
  border-radius: 20px;
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.navbar .topDiv .nuxt-link:hover {
  box-shadow: 0 0 15px #f4a460;
}
.navbar .topDiv svg {
  background-size: cover;
  border-radius: 20px;
  width: 90%;
  height: 90%;
}
.navbar .dlBefore::before {
  content: "登入";
  color: #ffffffd6;
  text-align: center;
  border-radius: inherit;
  z-index: 1000;
  background: #0003;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  font-size: 0.3rem;
  line-height: 100%;
  display: flex;
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
.navbar .processing-indicator {
  z-index: 10;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: none;
}
.navbar .topDiv.processing {
  opacity: 0.7;
  pointer-events: none;
}
.navbar .topDiv.processing .processing-indicator {
  display: flex;
}
.navbar .spinner {
  border: 2px solid #f3f3f3;
  border-top: 2px solid var(--color-text-darkgray-cale);
  border-radius: 50%;
  width: 20px;
  height: 20px;
  animation: 1s linear infinite spin;
}
@keyframes spin { to { transform: rotate(1turn); } }

/* center-div 原样 */
.navbar .center-div {
  visibility: hidden;
  opacity: 0;
  background: var(--main-bg-tw);
  will-change: opacity, transform;
  backface-visibility: hidden;
  border-radius: 20px;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  width: 4.4rem;
  height: 6rem;
  transition: opacity 0.3s, transform 0.3s, visibility 0.3s;
  display: flex;
  position: fixed;
  transform: translateZ(0);
  box-shadow: 0 0 15px #121212;
  z-index: 500;
}
.navbar .center-div .partition {
  width: 100%; height: 15%;
}
.navbar .center-div .top-name {
  z-index: 9900;
  text-align: center;
  width: 100%;
  color: #fff;
  font-size: 0.3rem;
  font-weight: 500;
}
.navbar .center-div .center-div-1 {
  z-index: 999;
  justify-content: space-evenly;
  width: 100%;
  display: flex;
  position: relative;
}
.navbar .center-div .center-div-1 div {
  color: #fff;
  text-shadow: 4px 4px 10px #222;
  font-size: 0.3rem;
  font-weight: 500;
  cursor: pointer;
}
.navbar .center-div .center-div-2 {
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 25%;
  display: flex;
}
.navbar .center-div .center-div-2 .t-1 {
  width: 0.7rem;
  height: 0.7rem;
  color: #fff;
  box-shadow: 0 0 10px #ffffffa6;
  border-radius: 50%;
  justify-content: center;
  align-items: center;
  transition: all 0.3s;
  display: flex;
  cursor: pointer;
}
.navbar .center-div .center-div-2 .t-1:hover {
  width: 1.2rem;
  height: 1.2rem;
  box-shadow: 0 0 15px #ffffffa6;
  background-color: #94949440;
}
.navbar .center-div .center-div-3 {
  width: 100%;
  color: #fff;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  padding-bottom: 3px;
  display: flex;
}
.navbar .center-div .center-div-3 .cd2-1 {
  border-radius: 0 20px;
  justify-content: space-evenly;
  align-items: center;
  width: 80%;
  margin-top: 10px;
  margin-left: 10%;
  padding-bottom: 3px;
  font-size: 0.27rem;
  font-weight: 500;
  display: flex;
  box-shadow: 0 0 10px #878787;
  cursor: pointer;
}
.navbar .center-div.show {
  visibility: visible !important;
  opacity: 1 !important;
  transform: translate(-20px, 40px) !important;
}
.navbar .topDiv.show {
  transform: translate(-20px) !important;
}

/* ===== 原样：响应式 ===== */
@media screen and (max-width: 1100px) {
  .main-top .header-top-view {
    flex-grow: 1;
    order: 3;
    overflow: auto;
    width: 100% !important;
  }
  .main-top .header-top-view .TopBody {
    width: 100% !important;
  }
  .main-top .header-tab-tight-top,
  .main-top .logo {
    margin-bottom: 0.25rem;
  }
  /* 仅作用于 App 自身的顶部导航（.app-shell 直接子级），不影响相册页内嵌导航 */
  .app-shell > .main-top .TopBody .tab,
  .app-shell > .main-top .TopBody .top-nav-text { display: none !important; }
}
@media (max-width: 800px) {
  /* 同上，仅限 App 顶栏 */
  .app-shell > .main-top .lableEnd,
  .app-shell > .main-top .switch { display: none; }
}
</style>
