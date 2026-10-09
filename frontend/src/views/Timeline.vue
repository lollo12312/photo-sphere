<template>
  <div class="timeline-page" :class="{ light: !store.darkTheme }">
    <div class="timeline-layout">
      <!-- 左：大图预览区 -->
      <aside class="preview-panel" :class="{ light: !store.darkTheme }">
        <template v-if="!current">
          <div class="preview-placeholder">
            <div class="ph-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
            </div>
            <p>点击右侧照片查看大图</p>
          </div>
        </template>

        <template v-else>
          <div class="preview-nav">
            <div class="preview-meta">
              <div class="meta-name">{{ current.name }}</div>
              <div class="meta-date">{{ current.date }}</div>
            </div>
          </div>

          <div
            class="preview-stage"
            ref="stage"
            :class="{ panning: isPanning }"
            @wheel.prevent="onWheelZoom"
            @mousedown="onPanStart"
          >
            <div v-if="imgLoading" class="img-loading">
              <div class="spinner-dots">
                <i v-for="n in 4" :key="n" :style="{ animationDelay: (n * 0.15) + 's' }"></i>
              </div>
              <span>加载中...</span>
            </div>
            <button class="nav-btn overlay prev" :disabled="currentIndex <= 0" @click.stop="goPrev" title="上一张">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
            <button class="nav-btn overlay next" :disabled="currentIndex >= flatList.length - 1" @click.stop="goNext" title="下一张">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
            </button>
            <div
              class="img-wrap"
              :class="{ loading: imgLoading }"
              :style="{
                width: naturalW + 'px',
                height: naturalH + 'px',
                transform: 'translate3d(' + panX + 'px, ' + panY + 'px, 0) scale(' + zoom + ')'
              }"
            >
              <img
                :src="getFullPhotoUrl(current.name)"
                :alt="current.name"
                draggable="false"
                @load="onImgLoaded"
              />
            </div>
          </div>

          <div class="preview-zoombar">
            <button class="zb-btn" @click="zoomOut" :disabled="zoom <= ZOOM_MIN">−</button>
            <span class="zb-val">{{ Math.round(zoom * 100) }}%</span>
            <button class="zb-btn" @click="zoomIn" :disabled="zoom >= ZOOM_MAX">+</button>
            <span class="zb-sep"></span>
            <button class="zb-btn fit" @click="zoomReset" title="适应屏幕">⤢</button>
          </div>
        </template>
      </aside>

      <!-- 拖拽分隔条：调整列表宽度 -->
      <div class="resize-handle" @mousedown="onResizeStart" title="拖动调整列表宽度"></div>

      <!-- 右：年份→月份 时间线列表 -->
      <main class="timeline-list" :class="{ light: !store.darkTheme }" :style="{ width: listWidth + 'px' }">
        <div class="tl-header">
          <div class="tl-head-top">
            <h1>⏳ 时间轴</h1>
            <span class="tl-count">{{ flatList.length }} 张</span>
          </div>
          <div class="tl-lib-tabs">
            <button :class="{ active: activeLib === 'pc' }" @click="switchLib('pc')">电脑库</button>
            <button :class="{ active: activeLib === 'phone' }" @click="switchLib('phone')">手机库</button>
          </div>
        </div>
        <div class="tl-scroll">
          <div v-for="year in years" :key="year.year" class="year-group">
            <div class="year-label" @click="toggleYear(year)">
              <span class="year-name">{{ year.year }} 年</span>
              <span class="year-count">{{ year.photoCount }} 张</span>
              <svg class="year-arrow" :class="{ collapsed: year.collapsed }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
            </div>
            <div v-show="!year.collapsed" class="months">
              <div v-for="month in year.months" :key="month.month" class="month-group">
                <div class="month-label" @click="toggleMonth(month)">
                  <span class="month-name">{{ month.month }} 月</span>
                  <span class="month-count">{{ month.photos.length }} 张</span>
                  <svg class="month-arrow" :class="{ collapsed: month.collapsed }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                </div>
                <div v-show="!month.collapsed" class="month-photos">
                  <div
                    v-for="photo in month.photos" :key="photo.name"
                    class="photo-item"
                    :class="{ active: current && current.name === photo.name }"
                    :ref="el => setItemRef(photo.name, el)"
                    @click="selectPhoto(photo)"
                  >
                    <img :src="getThumbnailUrl(photo.name)" :alt="photo.name" loading="lazy" />
                    <div class="photo-detail">
                      <div class="photo-name">{{ photo.name }}</div>
                      <div class="photo-date">{{ photo.date }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="years.length === 0" class="empty">{{ loaded ? '该目录暂无照片' : '加载中...' }}</div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import { getThumbnailUrl, getFullPhotoUrl } from '../api/photos'
import { store } from '../store'

// ---------- 数据 ----------
const years = ref([])
const flatList = ref([])
const current = ref(null)
const currentIndex = ref(-1)
const itemRefs = {}
// 双目录 Tab：电脑库（照片库根目录）/ 手机库（手机照片/）
const activeLib = ref('pc')
const pcList = ref([])
const phoneList = ref([])
const loaded = ref(false)
const isPhoneLib = p => p.name.startsWith('手机照片/')

function setItemRef(name, el) {
  if (el) itemRefs[name] = el
}

// 当前 Tab 对应的列表 → 重分年/月
function applyLib(lib) {
  flatList.value = lib === 'pc' ? pcList.value : phoneList.value
  groupBy(flatList.value)
}

function switchLib(lib) {
  if (activeLib.value === lib) return
  activeLib.value = lib
  current.value = null
  currentIndex.value = -1
  applyLib(lib)
}

onMounted(async () => {
  try {
    const res = await fetch('/api/photos/detail')
    const list = await res.json()
    store.photoList = list.map(p => p.name)
    // 电脑库 / 手机库 相互独立
    pcList.value = list.filter(p => !isPhoneLib(p))
    phoneList.value = list.filter(p => isPhoneLib(p))
    loaded.value = true
    applyLib('pc')
  } catch (e) {
    console.error(e)
  }
})

function groupBy(list) {
  const yearMap = {}
  for (const p of list) {
    if (!yearMap[p.year]) yearMap[p.year] = {}
    if (!yearMap[p.year][p.month]) yearMap[p.year][p.month] = []
    yearMap[p.year][p.month].push(p)
  }
  years.value = Object.entries(yearMap)
    .map(([year, monthMap]) => ({
      year,
      collapsed: false,
      photoCount: Object.values(monthMap).reduce((s, arr) => s + arr.length, 0),
      months: Object.entries(monthMap)
        .map(([month, photos]) => ({ month, collapsed: false, photos }))
        .sort((a, b) => Number(b.month) - Number(a.month)),
    }))
    .sort((a, b) => Number(b.year) - Number(a.year))
    // 默认只展开最新年份，更早的年份折叠
    .map((y, i) => ({ ...y, collapsed: i > 0 }))
}

function toggleYear(year) {
  year.collapsed = !year.collapsed
}
function toggleMonth(month) {
  month.collapsed = !month.collapsed
}

// ---------- 选中 / 上下张 ----------
function selectPhoto(photo) {
  current.value = photo
  currentIndex.value = flatList.value.findIndex(p => p.name === photo.name)
  ensureExpanded(photo)
  resetView()
  imgLoading.value = true
  scrollListTo(photo.name)
}

function ensureExpanded(photo) {
  const year = years.value.find(y => y.year === photo.year)
  if (year && year.collapsed) year.collapsed = false
  const month = year?.months.find(m => m.month === photo.month)
  if (month && month.collapsed) month.collapsed = false
}

function goPrev() {
  if (currentIndex.value <= 0) return
  selectPhoto(flatList.value[currentIndex.value - 1])
}
function goNext() {
  if (currentIndex.value >= flatList.value.length - 1) return
  selectPhoto(flatList.value[currentIndex.value + 1])
}

function scrollListTo(name) {
  nextTick(() => {
    const el = itemRefs[name]
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  })
}

// ---------- 缩放 / 拖拽（同增强页交互） ----------
const zoom = ref(1)
const ZOOM_STEP = 1.25
const ZOOM_MIN = 0.05
const ZOOM_MAX = 8
const naturalW = ref(0)
const naturalH = ref(0)
const panX = ref(0)
const panY = ref(0)
const stage = ref(null)
const imgLoading = ref(true)
let isPanning = false
let panStartX = 0, panStartY = 0, panStartPX = 0, panStartPY = 0

// ---------- 列表宽度拖拽 ----------
const listWidth = ref(340)
const RESIZE_MIN = 240
const RESIZE_MAX = 520
let resizing = false
let resizeStartX = 0, resizeStartW = 0

function onResizeStart(e) {
  resizing = true
  resizeStartX = e.clientX
  resizeStartW = listWidth.value
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
}
function onResizeMove(e) {
  if (!resizing) return
  listWidth.value = Math.max(RESIZE_MIN, Math.min(RESIZE_MAX, resizeStartW + (resizeStartX - e.clientX)))
}
function onResizeEnd() {
  resizing = false
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

function onImgLoaded(e) {
  const img = e.target
  naturalW.value = img.naturalWidth
  naturalH.value = img.naturalHeight
  imgLoading.value = false
  calcFitZoom()
}

function resetView() {
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

function calcFitZoom() {
  let attempts = 0
  function tryCalc() {
    attempts++
    requestAnimationFrame(() => {
      if (!stage.value || !naturalW.value || !naturalH.value) {
        if (attempts < 10) setTimeout(tryCalc, 100)
        return
      }
      const rect = stage.value.getBoundingClientRect()
      const sx = (rect.width - 24) / naturalW.value
      const sy = (rect.height - 24) / naturalH.value
      zoom.value = Math.max(Math.min(sx, sy, 1), ZOOM_MIN)
      syncZoomTarget()  // 直接设值后同步动画目标，避免下次滚轮从旧目标开始
    })
  }
  tryCalc()
}

// ===== 地图式平滑缩放：目标值 + 每帧插值（滚轮连续映射，缩放带平滑过渡） =====
const ZOOM_SENS = 0.004   // 滚轮灵敏度：缩放倍率 = 2^(-deltaY*sens)，随滚动量连续变化
let zoomTarget = 1        // 动画目标缩放
let panTX = 0, panTY = 0  // 动画目标平移
let zoomRaf = null

function startZoomAnim() {
  if (zoomRaf) return
  const step = () => {
    const k = 0.32  // 每帧插值系数：越大越跟手，越小越顺滑
    if (Math.abs(zoomTarget - zoom.value) < 0.0005 &&
        Math.abs(panTX - panX.value) < 0.4 &&
        Math.abs(panTY - panY.value) < 0.4) {
      zoom.value = zoomTarget
      panX.value = panTX
      panY.value = panTY
      zoomRaf = null
      return
    }
    zoom.value += (zoomTarget - zoom.value) * k
    panX.value += (panTX - panX.value) * k
    panY.value += (panTY - panY.value) * k
    clampPan()
    zoomRaf = requestAnimationFrame(step)
  }
  zoomRaf = requestAnimationFrame(step)
}

function stopZoomAnim() {
  if (zoomRaf) {
    cancelAnimationFrame(zoomRaf)
    zoomRaf = null
    zoom.value = zoomTarget
    panX.value = panTX
    panY.value = panTY
    clampPan()
  }
}

// 把目标值同步为当前值（直接改过 zoom 之后调用，避免动画从旧目标继续跑）
function syncZoomTarget() {
  zoomTarget = zoom.value
  panTX = panX.value
  panTY = panY.value
}

// 以 (clientX, clientY) 为锚点请求缩放：该点下的图像保持不动（地图手感）
function requestZoom(next, clientX, clientY) {
  const el = stage.value
  if (!el) return
  const old = zoom.value
  if (next === old) return
  const rect = el.getBoundingClientRect()
  const mx = (clientX - rect.left) - rect.width / 2
  const my = (clientY - rect.top) - rect.height / 2
  const ratio = next / old
  panTX = mx - (mx - panX.value) * ratio
  panTY = my - (my - panY.value) * ratio
  zoomTarget = next
  startZoomAnim()
}

// 按钮缩放：以图片当前中心为不动点
function zoomCenter(next) {
  const el = stage.value
  const rect = el ? el.getBoundingClientRect() : { left: 0, top: 0, width: 0, height: 0 }
  requestZoom(next, rect.left + rect.width / 2 + panX.value, rect.top + rect.height / 2 + panY.value)
}
function zoomIn() { zoomCenter(Math.min(zoom.value * ZOOM_STEP, ZOOM_MAX)) }
function zoomOut() { zoomCenter(Math.max(zoom.value / ZOOM_STEP, ZOOM_MIN)) }
function zoomReset() {
  stopZoomAnim()
  panX.value = 0
  panY.value = 0
  calcFitZoom()
  syncZoomTarget()
}

// 滚轮缩放：连续映射（地图手感，而非 1.25 倍跳变）
function onWheelZoom(e) {
  const f = Math.pow(2, -e.deltaY * ZOOM_SENS)
  const next = e.deltaY > 0
    ? Math.max(zoom.value * f, ZOOM_MIN)
    : Math.min(zoom.value * f, ZOOM_MAX)
  requestZoom(next, e.clientX, e.clientY)
}

function clampPan() {
  const el = stage.value
  if (!el) return
  const ww = naturalW.value * zoom.value
  const wh = naturalH.value * zoom.value
  const halfW = Math.max(0, ww - el.clientWidth) / 2
  const halfH = Math.max(0, wh - el.clientHeight) / 2
  panX.value = Math.max(-halfW, Math.min(halfW, panX.value))
  panY.value = Math.max(-halfH, Math.min(halfH, panY.value))
}

function onPanStart(e) {
  const el = stage.value
  if (!el || (naturalW.value * zoom.value <= el.clientWidth && naturalH.value * zoom.value <= el.clientHeight)) return
  if (e.target.closest('.nav-btn, .zb-btn')) return
  stopZoomAnim()  // 拖拽时立即落到目标位置，避免缩放动画与拖拽互相干扰
  isPanning = true
  panStartX = e.clientX; panStartY = e.clientY
  panStartPX = panX.value; panStartPY = panY.value
  document.addEventListener('mousemove', onPanMove)
  document.addEventListener('mouseup', onPanEnd)
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'grabbing'
}
function onPanMove(e) {
  if (!isPanning) return
  panX.value = panStartPX + (e.clientX - panStartX)
  panY.value = panStartPY + (e.clientY - panStartY)
}
function onPanEnd() {
  isPanning = false
  document.removeEventListener('mousemove', onPanMove)
  document.removeEventListener('mouseup', onPanEnd)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
  clampPan()
}

// 兜底：拖拽进行中卸载时清理监听，防止泄漏
onUnmounted(() => {
  document.removeEventListener('mousemove', onPanMove)
  document.removeEventListener('mouseup', onPanEnd)
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  if (zoomRaf) { cancelAnimationFrame(zoomRaf); zoomRaf = null }  // 停止缩放动画帧
})
</script>

<style scoped>
.timeline-page {
  width: 100%;
  height: 100%;
  background: #0c0c12;
  color: #eee;
  overflow: hidden;
}
.timeline-page.light {
  background: #f2f3f8;
  color: #1a1a2e;
}

.timeline-layout {
  display: flex;
  width: 100%;
  height: 100%;
}

/* ─── 左：预览区 ─── */
.preview-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #08080e;
  position: relative;
}
.preview-panel.light {
  background: #e6e7ee;
}

.preview-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: rgba(255,255,255,0.25);
}
.preview-panel.light .preview-placeholder {
  color: rgba(0,0,0,0.25);
}
.ph-icon svg { width: 60px; height: 60px; opacity: 0.4; }
.preview-placeholder p { font-size: 14px; }

.preview-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  flex-shrink: 0;
}
.nav-btn {
  width: 34px; height: 34px;
  border: none; border-radius: 8px;
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.light .nav-btn { background: rgba(0,0,0,0.05); color: rgba(0,0,0,0.6); }
.nav-btn:hover:not(:disabled) { background: rgba(108,99,255,0.2); color: #a8a0ff; }
.nav-btn:disabled { opacity: 0.25; cursor: not-allowed; }
.nav-btn svg { width: 18px; height: 18px; }

/* 悬浮在预览区左右两侧居中的切换按钮 */
.nav-btn.overlay {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(0,0,0,0.35);
  color: rgba(255,255,255,0.85);
  box-shadow: 0 2px 12px rgba(0,0,0,0.35);
  z-index: 10;
  backdrop-filter: blur(4px);
}
.nav-btn.overlay.prev { left: 14px; }
.nav-btn.overlay.next { right: 14px; }
.light .nav-btn.overlay {
  background: rgba(255,255,255,0.9);
  color: rgba(0,0,0,0.65);
  box-shadow: 0 2px 12px rgba(0,0,0,0.14);
}
.nav-btn.overlay:hover:not(:disabled) {
  background: #6c63ff;
  color: #fff;
  transform: translateY(-50%) scale(1.06);
}
.nav-btn.overlay:disabled { opacity: 0.3; }
.preview-meta {
  flex: 1;
  min-width: 0;
  text-align: center;
}
.meta-name {
  font-size: 13px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.meta-date { font-size: 11px; opacity: 0.45; margin-top: 2px; }

.preview-stage {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: grab;
}
.preview-stage.panning { cursor: grabbing; }

/* 图片加载占位动画 */
.img-loading {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: rgba(255,255,255,0.45);
  font-size: 13px;
  letter-spacing: 0.5px;
}
.light .img-loading { color: rgba(0,0,0,0.4); }
.spinner-dots { display: flex; gap: 7px; }
.spinner-dots i {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #6c63ff;
  animation: dot-pulse 0.9s ease-in-out infinite;
}
.light .spinner-dots i { background: #6c63ff; }
@keyframes dot-pulse {
  0%, 100% { transform: scale(0.35); opacity: 0.3; }
  50% { transform: scale(1); opacity: 1; }
}

.img-wrap {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.05), 0 20px 60px rgba(0,0,0,0.5);
  background: #0a0a0f;
  transform-origin: center center;
  will-change: transform;
  flex-shrink: 0;
  opacity: 1;
  transition: opacity 0.3s;
}
.img-wrap.loading { opacity: 0; }
.img-wrap img {
  display: block;
  width: 100%; height: 100%;
  object-fit: contain;
  pointer-events: none;
}

.preview-zoombar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
}
.zb-btn {
  width: 30px; height: 30px;
  border: none; border-radius: 6px;
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.7);
  font-size: 16px; line-height: 1;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.light .zb-btn { background: rgba(0,0,0,0.05); color: rgba(0,0,0,0.6); }
.zb-btn:hover:not(:disabled) { background: rgba(108,99,255,0.2); color: #a8a0ff; }
.zb-btn:disabled { opacity: 0.25; cursor: not-allowed; }
.zb-btn.fit { font-size: 13px; }
.zb-val {
  min-width: 48px; text-align: center;
  font-size: 12px; font-variant-numeric: tabular-nums; opacity: 0.7;
}
.zb-sep { width: 1px; height: 18px; background: rgba(255,255,255,0.1); }
.light .zb-sep { background: rgba(0,0,0,0.1); }

/* ─── 拖拽分隔条 ─── */
.resize-handle {
  width: 6px;
  flex-shrink: 0;
  cursor: col-resize;
  background: transparent;
  position: relative;
  z-index: 5;
  transition: background 0.2s;
}
.resize-handle:hover, .resize-handle:active {
  background: rgba(108, 99, 255, 0.25);
}
.resize-handle::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 28px;
  border-radius: 2px;
  background: rgba(255,255,255,0.08);
}
.light .resize-handle::after { background: rgba(0,0,0,0.08); }
.resize-handle:hover::after { background: #6c63ff; }

/* ─── 右：列表区 ─── */
.timeline-list {
  width: 340px;
  flex-shrink: 0;
  border-left: 1px solid rgba(255,255,255,0.05);
  background: #0f0f14;
  display: flex;
  flex-direction: column;
}
.timeline-list.light {
  border-left-color: rgba(0,0,0,0.07);
  background: #f7f7fb;
}
.tl-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  flex-shrink: 0;
}
.tl-head-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tl-header h1 { font-size: 17px; }
.tl-count { font-size: 12px; opacity: 0.5; }

/* 电脑库 / 手机库 Tab */
.tl-lib-tabs {
  display: flex;
  gap: 4px;
  background: rgba(128,128,160,0.1);
  border-radius: 10px;
  padding: 3px;
}
.tl-lib-tabs button {
  flex: 1;
  padding: 6px 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  opacity: 0.55;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.tl-lib-tabs button.active {
  background: #6c63ff;
  color: #fff;
  opacity: 1;
}
.timeline-page.light .tl-lib-tabs {
  background: rgba(0,0,0,0.06);
}
.timeline-page.light .tl-lib-tabs button.active {
  background: #6c63ff;
  color: #fff;
}

.tl-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px 16px;
}
.tl-scroll::-webkit-scrollbar { width: 4px; }
.tl-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

.year-group { margin-bottom: 6px; }
.year-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 8px;
  cursor: pointer;
  border-radius: 8px;
  user-select: none;
  transition: background 0.2s;
}
.year-label:hover { background: rgba(255,255,255,0.04); }
.light .year-label:hover { background: rgba(0,0,0,0.04); }
.year-name { font-size: 15px; font-weight: 600; }
.year-count { font-size: 12px; opacity: 0.45; margin-left: auto; }
.year-arrow, .month-arrow {
  width: 14px; height: 14px; opacity: 0.5;
  transition: transform 0.2s;
}
.year-arrow.collapsed, .month-arrow.collapsed { transform: rotate(-90deg); }

.month-group { margin-left: 10px; }
.month-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  cursor: pointer;
  border-radius: 8px;
  user-select: none;
  transition: background 0.2s;
}
.month-label:hover { background: rgba(255,255,255,0.04); }
.light .month-label:hover { background: rgba(0,0,0,0.04); }
.month-name { font-size: 13px; font-weight: 500; opacity: 0.85; }
.month-count { font-size: 11px; opacity: 0.4; margin-left: auto; }

.month-photos { margin-left: 12px; }
.photo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.photo-item:hover { background: rgba(255,255,255,0.04); }
.light .photo-item:hover { background: rgba(0,0,0,0.04); }
.photo-item.active {
  background: rgba(108,99,255,0.1);
  border-color: rgba(108,99,255,0.35);
}
.photo-item img {
  width: 44px; height: 44px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
}
.photo-detail { min-width: 0; }
.photo-name {
  font-size: 12px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.photo-date { font-size: 11px; opacity: 0.45; margin-top: 2px; }
.empty {
  text-align: center;
  padding: 60px;
  opacity: 0.5;
}
</style>