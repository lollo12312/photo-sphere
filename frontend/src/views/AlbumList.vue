<template>
  <!-- ===== 相册页主体布局 ===== -->
  <!-- /mobile 复用同一布局（is-phone：只显示竖版照片 + 卡片用竖屏比例 + 多一个批量上传按钮） -->
  <div class="ps-album-page" :class="{ 'is-phone': isPhoneMode, light: !store.darkTheme }">
  <!-- 背景闪现层 -->
  <div class="page-bg-image" ref="bgImageEl"></div>
  <!-- 细腻背景纹理层：径向微光 + 渐变，避免纯黑平板感 -->
  <div class="bg-texture" aria-hidden="true"></div>

  <!-- ===== 主内容区：卡片网格（顶部导航由全局 App 顶栏提供） ===== -->
  <div class="main-content">
    <div class="middleViewCom">
      <div class="pc-wallpaper-main">
        <div class="pc-container-dad">
          <!-- 页码 / 筛选 / 搜索变化时换 key，触发整块网格的过渡（卡片自带的 slideTop 进场动画也会重播） -->
          <Transition name="page-swap">
          <div class="home-container" :key="gridKey" ref="gridEl">
            <div
              v-for="(photo, i) in visibleWallpapers" :key="i"
              class="card"
              :style="{ animationDuration: ((i % 7) + 1) * 0.143 + 's' }"
              @click="openViewer(i)"
            >
              <div class="resource-container img-or-video">
                <img v-if="photo.img" :src="photo.img" :alt="photo.alt" :title="photo.name" loading="lazy" draggable="false" />
                <div v-else class="ph-media"><span>暂无照片</span></div>
                <button class="card-del" title="删除" @click.stop="openDelPopup(photo)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>
                </button>
              </div>
              <div class="card-content hert-col">
                <div class="labelDiv">
                  <span v-for="tag in photo.tags" :key="tag">{{ tag }}</span>
                </div>
                <div class="card--button">
                  <a href="#" class="ps-bottom-nav-end col-card" @click.prevent.stop>
                    <div class="ps-bottom-nav-end__face"><span>前往</span><span></span></div>
                  </a>
                </div>
                <div class="card-bottom">
                  <div v-for="cell in photo.meta" :key="cell.key" v-html="cell.html"></div>
                </div>
              </div>
            </div>
          </div>
          </Transition>
          <!-- 空态：无结果时提示（手机模式引导去右侧上传） -->
          <div v-if="!wallpapers.length" class="grid-empty">
            <p>{{ isPhoneMode ? '还没有手机比例的照片' : '没有符合条件的照片' }}</p>
            <p class="hint">{{ isPhoneMode ? '点右侧的「上传」按钮，把手机里的照片批量传进来' : '换个筛选条件或清空搜索试试' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== 底部搜索栏 ===== -->
  <div class="search-bar-container is-sticky">
    <div class="search-bar-wrapper">
      <div class="search-main-row">
        <!-- 搜索输入 -->
        <div class="search-input-container">
          <div class="search-input-wrapper" :class="{ 'is-focused': searchFocused }">
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="插画、简单、动漫..."
              @focus="searchFocused = true; searchLoading = true"
              @blur="onSearchBlur"
              @input="onSearchInput"
            />
            <div class="search-loading" :style="{ display: searchLoading ? 'flex' : 'none' }"><div class="loading-spinner"></div></div>
          </div>
          <div class="search-results" :class="{ show: showResults }">
            <div
              v-for="(r, i) in searchSuggestions" :key="i"
              class="search-result-item" @click="applySuggestion(r)"
            >{{ r.label }}</div>
            <div v-if="!searchSuggestions.length" class="search-result-item is-empty">无匹配结果</div>
          </div>
        </div>
        <!-- 筛选选项 -->
        <div class="filter-options" :class="[filterExpanded ? 'is-expanded' : 'is-collapsed']">
          <div
            v-for="(f, i) in filters" :key="f.key"
            class="search-dropdown-container"
          >
            <div class="search-dropdown-trigger" :class="{ 'is-open': openFilter === i }" @click="toggleFilter(i)">
              <div class="trigger-content">
                <i v-if="f.icon" class="trigger-icon" v-html="f.icon"></i>
                <span class="trigger-text">{{ f.activeLabel || f.label }}</span>
              </div>
            </div>
            <!-- 下拉面板 -->
            <div class="search-dropdown-content" :class="{ show: openFilter === i }">
              <div class="dropdown-options">
                <div
                  v-for="opt in f.options" :key="opt.value || 'all'"
                  class="dropdown-option" :class="{ 'is-selected': opt.selected }"
                  @click.stop="pickOption(f.key, opt.value)"
                >
                  <span class="option-text">{{ opt.label }}</span>
                  <!-- 色系：文字后跟颜色圆点；无映射色（如「不限」）显示空心占位圆点，保持各行结构对齐 -->
                  <span v-if="f.key === 'color'" class="color-dot" :class="{ 'is-mute': !COLOR_DOTS[opt.value] }" :style="COLOR_DOTS[opt.value] ? { background: COLOR_DOTS[opt.value] } : {}"></span>
                  <span v-if="opt.count !== null" class="option-count">{{ opt.count }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <!-- 上传按钮 -->
        <div class="upload-button-wrapper">
          <div class="upload-button" @click="onUpload">
            <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="#ffffffe6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span class="upload-text">上传</span>
          </div>
        </div>
      </div>
    </div>
    <div class="collapse-button desktop-collapse-button" :class="{ 'is-collapsed': !filterExpanded }" @click="filterExpanded = !filterExpanded" title="收起搜索栏">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>
    </div>
  </div>

  <!-- ===== 分页（左侧竖排）：点击页码 → 平滑滚动到对应位置；列表不切分，可一直往下滚 ===== -->
  <div class="page-main">
    <div class="ps-pagination">
      <div class="page-content">
        <a href="#" class="nav-btn" :class="{ disabled: page <= 1 }" title="上一页" @click.prevent="goPage(page - 1)"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="15 18 9 12 15 6"/></svg></a>
        <template v-for="(p, i) in pageWindow" :key="i">
          <span v-if="p === '...'" class="ellipsis">...</span>
          <div v-else-if="p === page" class="current">{{ p }}</div>
          <a v-else href="#" class="isDefault" @click.prevent="goPage(p)">{{ p }}</a>
        </template>
        <div class="nav-btn go-btn" title="跳转到指定页 (Go)" @click="openGo">Go</div>
        <a href="#" class="nav-btn" :class="{ disabled: page >= totalPages }" title="下一页" @click.prevent="goPage(page + 1)"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block;vertical-align:middle;"><polyline points="9 18 15 12 9 6"/></svg></a>
      </div>
    </div>
  </div>

  <!-- ===== Go 跳页对话框 ===== -->
  <div class="ps-pagination-go-overlay" :class="{ show: goOverlayOpen }" @click.self="goOverlayOpen = false">
    <div class="ps-pagination-go-dialog ps-pagination-go-card">
      <div class="ps-pagination-go-form">
        <button class="ps-pagination-go-close" title="关闭" @click="goOverlayOpen = false">&times;</button>
        <div class="ps-pagination-go-header">
          <div>
            <h3>跳转到页码</h3>
            <p>输入页码后按 Enter 或点击确认</p>
          </div>
          <div class="ps-pagination-go-current">当前第 {{ page }} 页</div>
        </div>
        <div class="ps-pagination-go-command">
          <button class="ps-pagination-go-step" title="减少" @click="goInput = Math.max(1, parseInt(goInput || 1, 10) - 1)">&minus;</button>
          <div class="ps-pagination-go-input-wrap">
            <input v-model="goInput" type="text" class="ps-pagination-go-input" inputmode="numeric" placeholder="1" @keydown.enter="goConfirm" @keydown.esc="goOverlayOpen = false" />
          </div>
          <button class="ps-pagination-go-step" title="增加" @click="goInput = parseInt(goInput || 0, 10) + 1">+</button>
          <button class="ps-pagination-go-confirm" @click="goConfirm">Go<span>→</span></button>
        </div>
        <div class="ps-pagination-go-foot">
          <span>共 {{ totalPages }} 页</span>
          <span><kbd>Enter</kbd> 确认 &nbsp; <kbd>Esc</kbd> 关闭</span>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== 右侧悬浮按钮（屏幕右侧垂直居中）：手机照片页额外一个「批量上传」；两页都有「回到顶部（火箭）」
      火箭用 class 控制显隐而非 v-if —— 始终占位，出现/消失时整组按钮不会上下跳动 ===== -->
  <div class="side-actions">
    <button
      v-if="isPhoneMode" class="side-btn upload-side-btn"
      :disabled="uploading" title="批量上传到手机库" @click="onUpload"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
    </button>
    <button class="side-btn top-side-btn" :class="{ 'is-hidden': !showTop }" title="回到顶部" @click="scrollTop">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2.8c2.7 2 4.2 5 4.2 8.4 0 2.1-.5 3.9-1.4 5.5H9.2a11.8 11.8 0 0 1-1.4-5.5c0-3.4 1.5-6.4 4.2-8.4Z"/>
        <circle cx="12" cy="9.9" r="1.9"/>
        <path d="M9.2 16.7 7 19.7l2.6-.6M14.8 16.7l2.2 3-2.6-.6"/>
        <path d="M10.7 19.3c.2 1.4.8 2.4 1.3 2.7.5-.3 1.1-1.3 1.3-2.7"/>
      </svg>
    </button>
  </div>

  <!-- 上传进度 / 结果提示 -->
  <Transition name="toast-fade">
    <div v-if="toast" class="side-toast">{{ toast }}</div>
  </Transition>

  <!-- 常驻隐藏文件选择框（两页都支持多选：手机页批量进照片库；首页多张进增强素材区） -->
  <input ref="fileInput" type="file" accept="image/*,.heic,.heif" multiple style="display:none" @change="onFileChange" />

  <!-- 拖拽上传遮罩：文件拖入窗口时显示，松手即上传（绕开选择框单选限制） -->
  <Teleport to="body">
    <div v-show="dragging" class="drop-overlay">
      <div class="drop-overlay-inner">
        <div class="drop-icon">⇪</div>
        <div class="drop-title">{{ isPhoneMode ? '松开批量上传到手机库' : '松开上传照片' }}</div>
        <div class="drop-sub">支持多张 · JPG/PNG/WebP/HEIC</div>
      </div>
    </div>
  </Teleport>

  <!-- ===== 大图查看层（teleport 到 body，fixed 覆盖层，不参与页面布局） ===== -->
  <teleport to="body">
    <transition name="viewer-fade">
      <div v-if="viewerOpen" class="viewer" @click.self="closeViewer">
        <div class="viewer-bg">
          <img v-if="viewerPhoto" :key="viewerPhoto.name" :src="getThumbnailUrl(viewerPhoto.name)" alt="" aria-hidden="true" />
        </div>
        <div class="viewer-top">
          <div class="viewer-meta">
            <div class="viewer-name">{{ viewerPhoto ? viewerPhoto.name : '' }}</div>
            <div class="viewer-date" v-if="viewerPhoto">{{ (viewerPhoto.tags || []).join(' · ') }}</div>
          </div>
          <button class="viewer-close" @click="closeViewer" title="关闭 (Esc)">✕</button>
        </div>
        <div ref="vCardEl" class="v-card" @wheel.prevent="vWheelZoom" @mousedown="vPanStart">
          <img
            v-if="viewerPhoto"
            ref="vImgEl"
            :src="getFullPhotoUrl(viewerPhoto.name)"
            :alt="viewerPhoto.name"
            :class="{ loading: viewerLoading, 'v-rot': vRotate === 90 || vRotate === 270 }"
            :style="vImgStyle"
            draggable="false"
            @load="vLoaded"
          />
          <div v-if="viewerLoading" class="v-loading">
            <div class="v-spin-circle"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/></svg></div>
            <span>加载中...</span>
          </div>
          <div class="v-hint">滚轮缩放 · 放大后拖动 · ← → 切换</div>
        </div>
        <button class="v-nav prev" :disabled="viewerIndex <= 0" @click="viewerPrev">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="v-nav next" :disabled="viewerIndex >= viewerList.length - 1" @click="viewerNext">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
        <div class="viewer-bottom">
          <div class="v-zoom">
            <button @click="vZoomOut" :disabled="vZoom <= ZOOM_MIN">−</button>
            <span class="v-val">{{ Math.round(vZoom * 100) }}%</span>
            <button @click="vZoomIn" :disabled="vZoom >= ZOOM_MAX">+</button>
            <span class="v-sep"></span>
            <button class="v-fit" @click="vZoomReset" title="适应屏幕">⤢</button>
            <button class="v-fit" @click="vRotateLeft" title="向左旋转 90°">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 1 2.64-6.36"/><polyline points="3 3 3 9 9 9"/></svg>
            </button>
            <button class="v-fit" @click="vRotateRight" title="向右旋转 90°">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><polyline points="21 3 21 9 15 9"/></svg>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>

  <!-- ===== 删除确认弹窗：居中毛玻璃 ===== -->
  <Teleport to="body">
    <Transition name="del-popup">
      <div v-if="delTarget" class="del-popup-mask" @click.self="closeDelPopup">
        <div class="del-popup-card">
          <img v-if="delTarget.img" class="del-popup-thumb" :src="delTarget.img" :alt="delTarget.name" />
          <div class="del-popup-icon" v-else>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>
          </div>
          <div class="del-popup-title">删除这张照片？</div>
          <div class="del-popup-name" :title="delTarget.name">{{ delTarget.name.split('/').pop() }}</div>
          <div class="del-popup-hint">照片将移入回收站，可随时找回</div>
          <div class="del-popup-actions">
            <button class="dpa-btn dpa-cancel" @click="closeDelPopup">取消</button>
            <button class="dpa-btn dpa-danger" @click="confirmDelete">删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { store } from '../store'
import { getThumbnailUrl, getFullPhotoUrl, uploadPhoto, uploadLibraryPhotos, trashPhotos } from '../api/photos'

// ===== 一个组件两种模式：/ 照片库（全部照片）、/mobile 手机照片（只显示竖版/方形，卡片用竖屏比例） =====
const route = useRoute()
const isPhoneMode = computed(() => route.path === '/mobile')

// ===== 顶部导航由全局 App 顶栏提供，本页不再自带 =====

// ===== 卡片数据：真实照片（每页 12 张，不足补占位卡保持版面整齐） =====
const PH_TOTAL = 12
const PAGE_SIZE = PH_TOTAL   // 每「页」= 12 张，仅用于分页定位（列表不再按页截断）
const allPhotos = ref([])   // 全量照片（含后端零模型归类：取向 / 分辨率档 / 主题 / 主色系）
const page = ref(1)         // 当前所在页（随滚动位置自动更新）
const gridEl = ref(null)
const showTop = ref(false)
let scrollLock = 0          // 点击页码后的短时锁定：避免平滑滚动过程中页码“回跳”
const iconDownload = '<svg class="el-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
const iconView = '<svg class="el-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
const iconRes = '<svg class="el-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></svg>'
const iconSize = '<svg class="el-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/><path d="M3 9v6"/><path d="M21 9v6"/></svg>'

function photoTags(name) {
  const base = name.replace(/\.[^.]+$/, '').replace(/^【[^】]*】/, '')
  const tags = base.split(/[-_\s]+/).filter(Boolean)
  return (tags.length ? tags : ['照片']).slice(0, 4)
}

function fmtSize(b) {
  if (!b && b !== 0) return ''
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return Math.round(b / 1024) + ' KB'
  return (b / 1024 / 1024).toFixed(1) + ' MB'
}

// 每个底部单元格 = 图标 + 数值（与 index.html 结构一致）
function metaCell(key, icon, val) {
  return { key, html: icon + '<span class="cval">' + (val == null || val === '' ? '—' : val) + '</span>' }
}

function buildMeta(photo) {
  const res = (photo.width || photo.width === 0) && (photo.height || photo.height === 0)
    ? photo.width + 'x' + photo.height
    : ''
  return [
    metaCell('dl', iconDownload, '0'),
    metaCell('views', iconView, '0'),
    metaCell('res', iconRes, res),
    metaCell('size', iconSize, fmtSize(photo.size))
  ]
}

// ===== 数据加载：detail（尺寸/时间/大小）+ analyze（取向/分辨率档/主题/主色系） =====
function tierOf(w, h) {
  const m = Math.max(w || 0, h || 0)
  if (m >= 3840) return '4K'
  if (m >= 2560) return '2K'
  if (m >= 1920) return '1080P'
  return 'SD'
}

async function loadPhotos() {
  let detail = []
  let analysis = {}
  try {
    const [r1, r2] = await Promise.all([
      fetch('/api/photos/detail'),
      fetch('/api/photos/analyze').catch(() => null)
    ])
    detail = await r1.json()
    if (r2 && r2.ok) {
      const j = await r2.json()
      analysis = j.items || {}
    }
  } catch (e) {
    console.error(e)
  }
  allPhotos.value = (Array.isArray(detail) ? detail : []).map(p => {
    const a = analysis[p.name] || {}
    return {
      name: p.name,
      size: p.size,
      width: p.width,
      height: p.height,
      date: p.date,
      year: p.year,
      month: p.month,
      timestamp: p.timestamp,
      tags: photoTags(p.name),
      orientation: a.orientation || (p.width > p.height ? 'landscape' : p.width < p.height ? 'portrait' : 'square'),
      tier: a.tier || tierOf(p.width, p.height),
      theme: a.theme || '其他',
      color: a.color || ''
    }
  })
}

// ===== 排序 / 筛选 / 搜索 → 结果集 =====
const selected = ref({ sort: 'latest', type: '', category: '', resolution: '', color: '' })
const appliedQuery = ref('')

const SORTERS = {
  latest: (a, b) => b.timestamp - a.timestamp,
  oldest: (a, b) => a.timestamp - b.timestamp,
  largest: (a, b) => b.size - a.size,
  smallest: (a, b) => a.size - b.size
}

// 色系圆点：与后端 _classify_pixel 的十二色系对应（下拉「色系」选项文字后显示颜色圆点）
const COLOR_DOTS = {
  黑: '#2b2b30',
  白: '#f5f5f5',
  灰: '#9a9aa2',
  棕: '#8b5a2b',
  红: '#e5484d',
  橙: '#f0833c',
  黄: '#f2c94c',
  绿: '#3ecf6e',
  青: '#3ecfc0',
  蓝: '#4d7df0',
  紫: '#8b5cf6',
  粉: '#f175b6'
}

// 相册页 / 手机照片页 按目录隔离：
//   - 相册首页：照片库全部照片（不含 手机照片/ 子目录，那是手机照片页专用的）
//   - 手机照片页：仅显示 手机照片/ 目录里的照片
const isPhoneLib = p => p.name.startsWith('手机照片/')
const phoneScoped = computed(() => (isPhoneMode.value
  ? allPhotos.value.filter(isPhoneLib)
  : allPhotos.value.filter(p => !isPhoneLib(p))))

const filtered = computed(() => {
  const s = selected.value
  const q = appliedQuery.value.toLowerCase()
  const list = phoneScoped.value.filter(p => {
    if (s.type && p.orientation !== s.type) return false
    if (s.category && p.theme !== s.category) return false
    if (s.resolution && p.tier !== s.resolution) return false
    if (s.color && p.color !== s.color) return false
    if (q && !(p.name.toLowerCase().includes(q) || p.tags.some(t => t.toLowerCase().includes(q)))) return false
    return true
  })
  return list.sort(SORTERS[s.sort] || SORTERS.latest)
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE_SIZE)))

// 「页」只用于定位：列表一次性全部渲染（可一直往下滚），点页码滚动到对应位置即「翻页」
// 结果集变化时换 key 触发网格过渡（页码不参与，否则点页码会重播动画）
const gridKey = computed(() => [
  selected.value.sort, selected.value.type, selected.value.category,
  selected.value.resolution, selected.value.color,
  appliedQuery.value, isPhoneMode.value ? 'phone' : 'all'
].join('|'))

// 页码窗口：固定「9 段」模板（任何页段数、栏宽一致，用户要求固定最大状态）。
// 省略号智能出现：起始区连续 1..7（前面不带 …），中间区前/后各有 …，末尾区连续到底
const pageWindow = computed(() => {
  const total = totalPages.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const cur = page.value
  if (cur <= 7) {
    // 起始区：1 2 3 4 5 6 7 … total（9 块）
    return [1, 2, 3, 4, 5, 6, 7, '...', total]
  }
  if (cur >= total - 6) {
    // 末尾区：1 … total-6 … total（9 块，末段连续到底）
    const arr = [1, '...']
    for (let i = total - 6; i <= total; i++) arr.push(i)
    return arr
  }
  // 中间区：1 … cur-2 cur-1 cur cur+1 cur+2 … total（9 块）
  return [1, '...', cur - 2, cur - 1, cur, cur + 1, cur + 2, '...', total]
})

// 结果集变化（筛选 / 搜索 / 切换页面规模）→ 回到第 1 页并滚回顶部
// 删除照片也会触发 filtered 变化，但**不应**回顶：只移除那张卡片、停在原滚动位置
let suppressReset = false
watch(filtered, () => {
  if (suppressReset) { suppressReset = false; return }
  scrollLock = Date.now() + 500
  renderLimit.value = INITIAL_BATCH  // 新结果集从首屏重新分批渲染
  page.value = 1
  window.scrollTo({ top: 0, behavior: 'auto' })
})

function toCard(p) {
  return {
    img: getThumbnailUrl(p.name),
    name: p.name,
    alt: p.name,
    tags: p.tags,
    meta: buildMeta(p),
    real: true
  }
}

// 一次性渲染全部结果（不按页截断，可一直往下滚）
const wallpapers = computed(() => filtered.value.map(toCard))

// ===== 分批渲染（性能优化）：先渲染首屏，滚动接近底部再增量追加 =====
// 列表仍可一直滚到底（最终全部渲染），但首屏只生成 BATCH_SIZE 张卡片，
// 减少初始 DOM 数量与图片请求数；slice 保序，视图索引即全量索引（openViewer(i) 不受影响）
const BATCH_SIZE = 96
const INITIAL_BATCH = 96
const renderLimit = ref(INITIAL_BATCH)
const visibleWallpapers = computed(() => wallpapers.value.slice(0, renderLimit.value))

function maybeLoadMore() {
  if (renderLimit.value >= wallpapers.value.length) return
  // 距底部 900px 内 → 追加一批；若追加后仍接近底部（如停在底部），由下方 watch 继续补齐
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 900) {
    renderLimit.value = Math.min(wallpapers.value.length, renderLimit.value + BATCH_SIZE)
  }
}
// 追加渲染后若还在底部附近（未触发新的 scroll 事件），下一帧继续补
watch(renderLimit, () => {
  if (renderLimit.value < wallpapers.value.length) nextTick(maybeLoadMore)
})

const bgImageEl = ref(null)
let bgTimer = null
function flashBg(photo) {
  // index.html 原版彩蛋：点击照片 → 背景闪现 3s
  if (!bgImageEl.value || !photo.img) return
  bgImageEl.value.style.backgroundImage = `url(${photo.img})`
  bgImageEl.value.classList.add('active')
  clearTimeout(bgTimer)
  bgTimer = setTimeout(() => bgImageEl.value?.classList.remove('active'), 3000)
}

// ===== 搜索 / 筛选 =====
const searchQuery = ref('')
const searchFocused = ref(false)
const searchLoading = ref(false)
const showResults = ref(false)
const filterExpanded = ref(true)
const openFilter = ref(null)
let searchTimer = null

// 输入防抖后应用搜索词（本地匹配文件名 / 标签，零模型）
function onSearchInput() {
  searchLoading.value = true
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    searchLoading.value = false
    appliedQuery.value = searchQuery.value.trim()
    page.value = 1
    if (searchQuery.value.length > 0) showResults.value = true
  }, 400)
}

// 搜索建议：优先命中标签，其次命中文件名
const searchSuggestions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return []
  const out = []
  const seen = new Set()
  for (const p of allPhotos.value) {
    for (const t of p.tags) {
      const k = t.toLowerCase()
      if (k.includes(q) && !seen.has(k)) { seen.add(k); out.push({ label: t, query: t }) }
    }
  }
  for (const p of allPhotos.value) {
    if (out.length >= 6) break
    if (p.name.toLowerCase().includes(q) && !seen.has(p.name)) {
      seen.add(p.name)
      out.push({ label: p.name, query: p.name })
    }
  }
  return out.slice(0, 6)
})

function applySuggestion(r) {
  searchQuery.value = r.query
  appliedQuery.value = r.query.trim()
  page.value = 1
  showResults.value = false
}

function toggleFilter(i) {
  openFilter.value = openFilter.value === i ? null : i
}

// 失焦后稍延迟再收起建议面板，避免点击建议项时面板先消失
function onSearchBlur() {
  searchFocused.value = false
  setTimeout(() => {
    showResults.value = false
    searchLoading.value = false
  }, 200)
}

// 5 组筛选的图标与标签沿用原版（结构不变）
const ICON_TYPE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>'
const ICON_CATEGORY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/></svg>'
const ICON_RES = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/></svg>'
const ICON_COLOR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>'

const OPTION_LABELS = {
  type: { landscape: '电脑壁纸', portrait: '手机壁纸', square: '方形壁纸' },
  resolution: { '4K': '4K 及以上', '2K': '2K', '1080P': '1080P', SD: '其他' },
  sort: { latest: '最新上传', oldest: '最早上传', largest: '文件最大', smallest: '文件最小' }
}
const ORDER = {
  type: ['landscape', 'portrait', 'square'],
  category: ['人物', '风景', '动漫', '游戏', '动物', '城市', '极简', '其他'],
  resolution: ['4K', '2K', '1080P', 'SD'],
  color: ['红', '橙', '黄', '绿', '青', '蓝', '紫', '粉', '棕', '黑', '白', '灰']
}

function countsOf(pick) {
  const m = {}
  for (const p of phoneScoped.value) {
    const k = pick(p)
    if (!k) continue
    m[k] = (m[k] || 0) + 1
  }
  return m
}

// 选项由真实数据生成（带张数统计）；张数为 0 的档位不展示，避免出现空选项
function buildOptions(key, counts) {
  const opts = [{ value: '', label: '不限', count: phoneScoped.value.length, selected: selected.value[key] === '' }]
  for (const v of ORDER[key]) {
    const c = counts[v] || 0
    if (!c) continue
    opts.push({ value: v, label: (OPTION_LABELS[key] || {})[v] || v, count: c, selected: selected.value[key] === v })
  }
  return opts
}

const filters = computed(() => [
  {
    key: 'sort', label: '昨日热门', icon: '',
    options: ['latest', 'oldest', 'largest', 'smallest'].map(v => ({
      value: v, label: OPTION_LABELS.sort[v], count: null, selected: selected.value.sort === v
    }))
  },
  { key: 'type', label: '种类', icon: ICON_TYPE, options: buildOptions('type', countsOf(p => p.orientation)) },
  { key: 'category', label: '分类', icon: ICON_CATEGORY, options: buildOptions('category', countsOf(p => p.theme)) },
  { key: 'resolution', label: '分辨率', icon: ICON_RES, options: buildOptions('resolution', countsOf(p => p.tier)) },
  { key: 'color', label: '色系', icon: ICON_COLOR, options: buildOptions('color', countsOf(p => p.color)) }
])

function pickOption(key, value) {
  if (key === 'sort') selected.value.sort = value || 'latest'
  else selected.value[key] = selected.value[key] === value ? '' : value  // 再点一次取消
  page.value = 1
  openFilter.value = null
}

// ===== Go 跳页 =====
const goOverlayOpen = ref(false)
const goInput = ref('1')
function openGo() {
  goInput.value = String(page.value)
  goOverlayOpen.value = true
}
function goPage(p) {
  const n = Math.min(Math.max(1, Number(p) || 1), totalPages.value)
  page.value = n
  scrollLock = Date.now() + 900
  // 分批渲染兼容：先确保目标页已渲染（最后一页需全量），再按 DOM 定位滚动
  const need = n >= totalPages.value ? wallpapers.value.length : (n - 1) * PAGE_SIZE + 1
  const changed = renderLimit.value < need
  if (changed) renderLimit.value = Math.min(wallpapers.value.length, need + BATCH_SIZE)
  if (changed) nextTick(() => doScrollToPage(n))
  else doScrollToPage(n)
}
function doScrollToPage(n) {
  const grid = gridEl.value
  if (!grid || !grid.children.length) return
  // 先打断上一次尚未完成的浏览器平滑滚动（原地 auto 落一次）。
  // 否则连续换页/翻页时，平滑滚动进行中的新 smooth 会被浏览器忽略 → 要点好几次才生效
  window.scrollTo({ top: window.scrollY, behavior: 'auto' })
  if (n >= totalPages.value) {                      // 最后一页：直接滚到底（已确保全量渲染）
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })
    return
  }
  const el = grid.children[(n - 1) * PAGE_SIZE]     // 该页第一张卡
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - 96
  window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
}
function goConfirm() {
  const n = parseInt(goInput.value, 10)
  if (n > 0 && n <= totalPages.value) {
    goPage(n)
    goOverlayOpen.value = false
  } else {
    goInput.value = String(page.value)
  }
}

// 滚动位置 → 高亮页码；同时控制「回到顶部」按钮显隐
function onWindowScroll() {
  showTop.value = window.scrollY > 320
  const grid = gridEl.value
  if (!grid || !grid.children.length) return
  // 分批渲染：接近底部（900px 内）时追加下一批（尚未全部加载）
  if (renderLimit.value < wallpapers.value.length) {
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 900) {
      renderLimit.value = Math.min(wallpapers.value.length, renderLimit.value + BATCH_SIZE)
    }
  }
  if (Date.now() < scrollLock) return
  // 滚到底：只有「全部已加载」才判定为末页（未加载完时这是当前批次的底部，保持页码）
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
    if (renderLimit.value >= wallpapers.value.length && page.value !== totalPages.value) page.value = totalPages.value
    return
  }
  const anchor = window.scrollY + 160
  let cur = 1
  for (let i = 0; i < grid.children.length; i += PAGE_SIZE) {
    const top = grid.children[i].getBoundingClientRect().top + window.scrollY
    if (top <= anchor) cur = Math.floor(i / PAGE_SIZE) + 1
    else break
  }
  cur = Math.min(cur, totalPages.value)
  if (cur !== page.value) page.value = cur
}

function scrollTop() {
  scrollLock = Date.now() + 700
  page.value = 1
  window.scrollTo({ top: window.scrollY, behavior: 'auto' })  // 打断进行中的平滑滚动
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ===== 上传 =====
// 照片库页：沿用增强页上传（单张、临时素材、不入库）
// 手机照片页：批量上传进照片库（写入 照片库/手机照片/），带进度与结果提示
const fileInput = ref(null)
const uploading = ref(false)
const uploadPercent = ref(0)
const toast = ref('')
let toastTimer = null
function showToast(msg, ms = 3600) {
  toast.value = msg
  clearTimeout(toastTimer)
  if (ms > 0) toastTimer = setTimeout(() => { toast.value = '' }, ms)
}

// ===== 删除（移入回收站）：自定义确认弹窗 =====
const delTarget = ref(null)  // 待删除的照片卡片（含 img/name），非空即显示弹窗

function openDelPopup(photo) { delTarget.value = photo }
function closeDelPopup() { delTarget.value = null }

async function confirmDelete() {
  const photo = delTarget.value
  closeDelPopup()
  if (!photo || !photo.name) return
  try {
    const res = await trashPhotos([photo.name])
    if (res.moved && res.moved.length) {
      // 只移除这一张，抑制 filtered 变化引发的回顶，停留在原滚动位置
      suppressReset = true
      allPhotos.value = allPhotos.value.filter(p => p.name !== photo.name)
      showToast('已删除，可在回收站找回')
    } else {
      showToast('删除失败：' + ((res.failed && res.failed[0] && res.failed[0].reason) || '未知原因'))
    }
  } catch (err) {
    console.error(err)
    showToast('删除失败：' + (err.message || err))
  }
}
function onUpload() {
  if (uploading.value) return
  fileInput.value?.click()
}
// 公共上传入口：选择框（onFileChange）和拖拽（onDropFiles）都走这里
async function handleSelected(files) {
  if (!files.length) return

  if (!isPhoneMode.value) {
    // 相册首页：支持多张（多张会逐张上传，进增强素材区），供增强页使用
    const images = files.filter(f => /^image\//.test(f.type))
    if (!images.length) { alert('请上传图片文件'); return }
    let ok = 0, fail = 0
    for (const file of images) {
      try { await uploadPhoto(file); ok++ } catch (e) { fail++ }
    }
    alert(`上传完成：成功 ${ok} 张${fail ? `，失败 ${fail} 张` : ''}，可在「增强」页处理`)
    return
  }

  const images = files.filter(f => /^image\//.test(f.type) || /\.(hei[cf])$/i.test(f.name))
  if (!images.length) { showToast('没有可上传的图片文件'); return }
  uploading.value = true
  uploadPercent.value = 0
  showToast('上传中 0%', 0)
  try {
    const res = await uploadLibraryPhotos(images, p => {
      uploadPercent.value = p
      toast.value = '上传中 ' + p + '%'
    })
    await loadPhotos()
    const fails = res.failed || []
    showToast('上传完成：成功 ' + res.saved.length + ' 张' + (fails.length ? '，失败 ' + fails.length + ' 张' : ''))
    if (fails.length) console.warn('[上传失败明细]', fails)
  } catch (err) {
    console.error(err)
    showToast('上传失败：' + (err.message || err))
  } finally {
    uploading.value = false
    uploadPercent.value = 0
  }
}
async function onFileChange(e) {
  const files = [...(e.target.files || [])]
  e.target.value = ''
  await handleSelected(files)
}

// ===== 拖拽上传（绕开文件选择框：从手机/资源管理器窗口直接拖多张图片进来） =====
const dragDepth = ref(0)
const dragging = computed(() => dragDepth.value > 0)
function onDragEnter(e) {
  if (!e.dataTransfer || ![...(e.dataTransfer.types || [])].includes('Files')) return
  dragDepth.value++
}
function onDragLeave() {
  dragDepth.value = Math.max(0, dragDepth.value - 1)
}
function onDragOver(e) {
  e.preventDefault()
}
async function onDropFiles(e) {
  e.preventDefault()
  dragDepth.value = 0
  const files = [...(e.dataTransfer?.files || [])]
  await handleSelected(files)
}

// ---------- 大图查看层（恢复自备份实现；覆盖层，不参与页面布局） ----------
const viewerOpen = ref(false)
const viewerList = ref([])
const viewerIndex = ref(0)
const viewerLoading = ref(true)
const vZoom = ref(1)
const vPanX = ref(0)
const vPanY = ref(0)
const vCardEl = ref(null)
const vImgEl = ref(null)
const ZOOM_STEP = 1.25
const ZOOM_MIN = 0.3
const ZOOM_MAX = 10
let vPanning = false
let vPanSX = 0, vPanSY = 0, vPanPX = 0, vPanPY = 0

const viewerPhoto = computed(() => viewerList.value[viewerIndex.value] || null)
// 查看方向旋转（0/90/180/270，顺时针），用于手机库横屏照片立起查看
const vRotate = ref(0)
const vImgStyle = computed(() => ({
  transform: `translate(calc(-50% + ${vPanX.value}px), calc(-50% + ${vPanY.value}px)) scale(${vZoom.value}) rotate(${vRotate.value}deg)`
}))

// ── 旋转 90°：宽高互换，CSS max 约束已对 v-rot 关闭，按自然尺寸算 contain 缩放（整图可见）──
// 旋转后图片中心不变，旋转本身不改变 pan 语义；缩放/拖拽由 vClamp 按旋转后的可视尺寸约束
function fitViewerToCard() {
  const img = vImgEl.value
  const card = vCardEl.value
  const axisSwapped = vRotate.value === 90 || vRotate.value === 270
  if (!axisSwapped) return 1
  if (img && card) {
    const iw = img.naturalWidth, ih = img.naturalHeight
    if (iw && ih) {
      const r = card.getBoundingClientRect()
      // 旋转后：视觉宽 = 自然高、视觉高 = 自然宽 → contain 适配容器
      return Math.min((r.width * 0.92) / ih, (r.height * 0.9) / iw)
    }
  }
  return 1
}
function applyViewerFit() {
  stopZoomAnim()
  zoomTarget = null
  vZoom.value = fitViewerToCard()
  vPanX.value = 0; vPanY.value = 0
}
function rotateBy(delta) {
  vRotate.value = (vRotate.value + ((delta % 360) + 360)) % 360
  applyViewerFit()
}
function vRotateLeft() { rotateBy(-90) }   // 左旋（逆时针）
function vRotateRight() { rotateBy(90) }   // 右旋（顺时针）

function openViewer(i) {
  const photo = wallpapers.value[i]
  if (!photo || !photo.real) return // 占位卡不打开大图
  const realList = wallpapers.value.filter(p => p.real)
  viewerList.value = realList
  viewerIndex.value = Math.max(0, realList.findIndex(p => p.name === photo.name))
  viewerOpen.value = true
  resetViewer()
  flashBg(photo) // 保留原彩蛋：背景闪现
}
function closeViewer() { stopZoomAnim(); viewerOpen.value = false }
function viewerPrev() { if (viewerIndex.value > 0) { viewerIndex.value--; resetViewer() } }
function viewerNext() { if (viewerIndex.value < viewerList.value.length - 1) { viewerIndex.value++; resetViewer() } }
function resetViewer() {
  stopZoomAnim()
  viewerLoading.value = true
  vZoom.value = 1; vPanX.value = 0; vPanY.value = 0
  vRotate.value = 0  // 切换照片 / 打开查看器时回到正立
  zoomTarget = null
}
function vLoaded() { viewerLoading.value = false }

// ===== 地图式平滑缩放：目标值 + 每帧插值动画（滚轮连续映射，缩放带平滑过渡） =====
// 锚点换算：图片是 top/left:50% + translate(-50% + pan) scale(zoom)，**图片中心与容器中心重合**，
//   pan 即「图片中心相对容器中心的位移」；鼠标相对容器中心的偏移 cx 就是它在图片上的偏移。
//   设 cx = (clientX - rect.left) - 容器宽/2，缩放后保持该点在光标下不动：pan' = cx - (cx - pan) * (next/old)
//   ⚠️ 不能用 (容器宽 - 图片宽)/2：那会多减半个图片宽，导致缩放时图片朝固定方向偏移（不跟光标）。
const ZOOM_SENS = 0.004  // 滚轮灵敏度：缩放倍率 = 2^(±deltaY*sens)，随滚动量连续变化
let zoomTarget = null   // 动画目标缩放
let panTX = 0, panTY = 0 // 动画目标平移
let zoomRaf = null      // 缩放动画帧

function requestZoom(next, clientX, clientY) {
  const card = vCardEl.value
  if (!card) return
  const old = vZoom.value
  if (next === old) return
  const rect = card.getBoundingClientRect()
  // 锚点 = 光标相对「容器中心」的偏移（图片中心与容器中心重合，pan 即图片中心的位移）
  const cx = (clientX - rect.left) - rect.width / 2
  const cy = (clientY - rect.top) - rect.height / 2
  const ratio = next / old
  panTX = cx - (cx - vPanX.value) * ratio
  panTY = cy - (cy - vPanY.value) * ratio
  zoomTarget = next
  startZoomAnim()
}

function startZoomAnim() {
  if (zoomRaf) return
  const step = () => {
    const k = 0.32  // 每帧插值系数：越大越跟手，越小越顺滑
    if (Math.abs(zoomTarget - vZoom.value) < 0.001 &&
        Math.abs(panTX - vPanX.value) < 0.4 &&
        Math.abs(panTY - vPanY.value) < 0.4) {
      vZoom.value = zoomTarget
      vPanX.value = panTX
      vPanY.value = panTY
      zoomRaf = null
      return
    }
    vZoom.value += (zoomTarget - vZoom.value) * k
    vPanX.value += (panTX - vPanX.value) * k
    vPanY.value += (panTY - vPanY.value) * k
    vClamp()
    zoomRaf = requestAnimationFrame(step)
  }
  zoomRaf = requestAnimationFrame(step)
}

function stopZoomAnim() {
  if (zoomRaf) {
    cancelAnimationFrame(zoomRaf)
    zoomRaf = null
    if (zoomTarget != null) {
      vZoom.value = zoomTarget
      vPanX.value = panTX
      vPanY.value = panTY
      vClamp()
    }
  }
}

// 缩放控制条按钮：以图片当前中心为不动点
function zoomCenter(next) {
  const card = vCardEl.value
  const rect = card ? card.getBoundingClientRect() : { left: 0, top: 0, width: innerWidth, height: innerHeight }
  // 传入「图片中心」的视口坐标 = 容器中心 + 当前 pan（锚点即图片中心 → 缩放时 pan 不变）
  requestZoom(next, rect.left + rect.width / 2 + vPanX.value,
               rect.top + rect.height / 2 + vPanY.value)
}
function vZoomIn() { zoomCenter(Math.min(vZoom.value * ZOOM_STEP, ZOOM_MAX)) }
function vZoomOut() { zoomCenter(Math.max(vZoom.value / ZOOM_STEP, ZOOM_MIN)) }
// 适应屏幕：正立 = CSS 适应（zoom 1）；旋转 90/270 = 按 contain 缩放（否则原始像素会溢出裁切"不完整"）
function vZoomReset() { applyViewerFit() }
function vWheelZoom(e) {
  // 连续缩放：倍数随滚动量指数变化（地图手感，而非 1.25 倍跳变）
  const f = Math.pow(2, -e.deltaY * ZOOM_SENS)
  const next = e.deltaY > 0
    ? Math.max(vZoom.value * f, ZOOM_MIN)
    : Math.min(vZoom.value * f, ZOOM_MAX)
  requestZoom(next, e.clientX, e.clientY)
}
function vClamp() {
  const img = vImgEl.value
  const card = vCardEl.value
  if (!img || !card) return
  // 旋转 90/270 后宽高互换：可视宽 = 原图高、可视高 = 原图宽，边界按互换后的尺寸约束
  const axisSwapped = vRotate.value === 90 || vRotate.value === 270
  const visW = axisSwapped ? img.clientHeight : img.clientWidth
  const visH = axisSwapped ? img.clientWidth : img.clientHeight
  const halfW = Math.max(0, visW * vZoom.value - card.clientWidth) / 2
  const halfH = Math.max(0, visH * vZoom.value - card.clientHeight) / 2
  vPanX.value = Math.max(-halfW, Math.min(halfW, vPanX.value))
  vPanY.value = Math.max(-halfH, Math.min(halfH, vPanY.value))
}
function vPanStart(e) {
  // 正立时 zoom>1 才允许拖；旋转 90/270 时只要超过 contain 适配值（整图已满屏）即可拖
  const noPanThreshold = (vRotate.value === 90 || vRotate.value === 270) ? fitViewerToCard() : 1
  if (vZoom.value <= noPanThreshold) return
  if (e.target.closest('.viewer-top, .viewer-bottom, .v-nav')) return
  stopZoomAnim()  // 拖拽时立即落到目标位置，避免缩放动画与拖拽互相干扰
  vPanning = true
  vPanSX = e.clientX; vPanSY = e.clientY
  vPanPX = vPanX.value; vPanPY = vPanY.value
  document.addEventListener('mousemove', vPanMove)
  document.addEventListener('mouseup', vPanEnd)
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'grabbing'
}
function vPanMove(e) {
  if (!vPanning) return
  vPanX.value = vPanPX + (e.clientX - vPanSX)
  vPanY.value = vPanPY + (e.clientY - vPanSY)
}
function vPanEnd() {
  vPanning = false
  document.removeEventListener('mousemove', vPanMove)
  document.removeEventListener('mouseup', vPanEnd)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
  vClamp()
}
function onViewerKey(e) {
  if (!viewerOpen.value) return
  if (e.key === 'Escape') closeViewer()
  else if (e.key === 'ArrowLeft') viewerPrev()
  else if (e.key === 'ArrowRight') viewerNext()
}

// ===== 挂载 / 卸载 =====
// 点击下拉以外区域时关闭筛选展开状态
function onDocClick(e) {
  if (openFilter.value !== null && !e.target.closest('.search-dropdown-container')) openFilter.value = null
}

onMounted(async () => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onViewerKey)
  window.addEventListener('scroll', onWindowScroll, { passive: true })
  window.addEventListener('dragenter', onDragEnter)
  window.addEventListener('dragover', onDragOver)
  window.addEventListener('dragleave', onDragLeave)
  window.addEventListener('drop', onDropFiles)
  await loadPhotos()
  onWindowScroll()
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onViewerKey)
  window.removeEventListener('scroll', onWindowScroll)
  window.removeEventListener('dragenter', onDragEnter)
  window.removeEventListener('dragover', onDragOver)
  window.removeEventListener('dragleave', onDragLeave)
  window.removeEventListener('drop', onDropFiles)
  clearTimeout(bgTimer)
  clearTimeout(searchTimer)
  clearTimeout(toastTimer)
})
</script>

<style scoped>
/* ===== 相册页样式（主体 + 导航 + 搜索栏 + 分页 + Go） ===== */
.ps-album-page {
  position: relative;
  width: 100%;
  min-height: 100vh;
  background: #262626;
  display: flex;
  flex-direction: column;
}
/* 拖拽上传遮罩（teleport 到 body） */
.drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 14, 25, 0.72);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.drop-overlay-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 44px 72px;
  border: 2px dashed rgba(255,255,255,0.45);
  border-radius: 20px;
  background: rgba(255,255,255,0.06);
}
.drop-icon {
  font-size: 42px;
  line-height: 1;
  color: #a78bfa;
  animation: drop-bounce 1.2s ease-in-out infinite;
}
.drop-title {
  font-size: 17px;
  font-weight: 600;
  color: #fff;
}
.drop-sub {
  font-size: 12px;
  color: rgba(255,255,255,0.55);
}
@keyframes drop-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
/* 细腻背景纹理：中心微亮径向渐变 + 顶部泛光，避免纯黑平板感 */
.bg-texture {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 80% 55% at 50% -10%, rgba(255, 255, 255, 0.055), transparent 60%),
    radial-gradient(ellipse 60% 45% at 85% 110%, rgba(139, 92, 246, 0.05), transparent 55%),
    radial-gradient(ellipse 60% 45% at 10% 105%, rgba(120, 160, 255, 0.05), transparent 55%);
}
.page-root { background: transparent; }

/* 背景闪现层 */
.page-bg-image {
  position: fixed; inset: 0; z-index: -1;
  background-size: cover; background-position: center;
  filter: blur(12px) brightness(0.35);
  opacity: 0; transition: opacity 0.6s ease;
  pointer-events: none;
}
.page-bg-image.active { opacity: 1; }

/* ===== 顶部导航 ===== */
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
  display: flex;
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
  transition: all 0.9s cubic-bezier(0.98, -0.65, 0.265, 1.55), background-color 0.5s;
  position: absolute;
  background-color: var(--main-bg-tw);
  box-shadow: 0 0 10px var(--color-background-soft);
  border-radius: 1rem;
  left: 0;
}
.twoTopLable {
  z-index: 1;
  border-radius: 100px;
  flex-grow: 1;
  justify-content: center;
  align-items: center;
  height: 100%;
  position: relative;
  display: flex;
  text-decoration: none;
  cursor: pointer;
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
  width: 0.44rem;
  height: 0.44rem;
  fill: var(--color-text);
}
.tabCss .top-nav-text {
  white-space: nowrap;
  font-size: 0.3rem;
  font-weight: 500;
  position: relative;
}
.tabCss h1, .tabCss span:not(.top-nav-text):not(.new-tab) {
  white-space: nowrap;
  font-size: 0.3rem;
  font-weight: 500;
}
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
.main-top .header-tab-tight-top {
  width: 3.5rem;
}
/* lableEnd */
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
/* switch */
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
.switch.switch-checked { background-color: #2f2f2f; }
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
/* navbar 登录区 */
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
.navbar .topDiv.processing .processing-indicator { display: flex; }
.navbar .spinner {
  border: 2px solid #f3f3f3;
  border-top: 2px solid var(--color-text-darkgray-cale);
  border-radius: 50%;
  width: 20px;
  height: 20px;
  animation: 1s linear infinite spin;
}
@keyframes spin { to { transform: rotate(1turn); } }
/* center-div 登录下拉 */
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
.navbar .center-div .partition { width: 100%; height: 15%; }
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
.navbar .center-div .center-div-2 .weix {
  width: 0.5rem; height: 0.5rem;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23fff' d='M8.5 4C4.36 4 1 6.69 1 10c0 1.89 1.08 3.56 2.78 4.66L3 17l2.5-1.32c.95.27 1.97.42 3 .42.18 0 .36-.01.54-.02-.34-.7-.54-1.48-.54-2.3 0-3.04 2.91-5.5 6.5-5.5.18 0 .36.01.54.03C14.78 6.08 11.94 4 8.5 4z'/%3E%3C/svg%3E") 0 0/cover;
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

/* ===== 主内容区 ===== */
.main-content {
  justify-content: center;
  align-items: stretch;
  min-width: 100%;
  max-width: 100%;
  height: auto;
  display: flex;
  position: relative;
  top: 0;
  z-index: 1;
  /* 给左侧竖排分页留出空间（分页是 fixed 浮层，避免卡片被压住） */
  padding-left: 96px;
}
.main-content .middleViewCom {
  margin-top: 20px;
  margin-bottom: 20px;
  position: relative;
  /* 原版是靠「12 张卡片的固有内容宽度」把这一层撑满的（标签数量多且长，固有宽度 > 视口宽）。
     我们的照片名拆出的标签更短，固有宽度只有 ~1239px，网格会自行缩窄（卡片 266px）。
     这里显式撑满可用宽度，卡片回到 ~306px，网格铺满整屏。 */
  width: 100%;
}
.pc-wallpaper-main {
  flex-direction: column;
  flex-grow: 1;
  justify-content: space-around;
  margin-top: 15px;
  align-items: center;
  width: 100%;
  display: flex;
}
.pc-wallpaper-main .pc-container-dad { width: 100%; }
/* ===== 列表切换过渡（页码 / 筛选 / 搜索变化时） =====
   进：整块网格淡入 + 轻微上浮；出：仅淡出并脱离文档流，
   避免切换瞬间网格塌陷把分页顶上顶下（每页固定 12 张，高度不变） */
.page-swap-enter-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.page-swap-leave-active {
  position: absolute;
  left: 0;
  right: 0;
  top: auto;
  pointer-events: none;
  transition: opacity 0.14s ease;
}
.page-swap-enter-from { opacity: 0; transform: translateY(12px); }
.page-swap-leave-to { opacity: 0; }
.pc-wallpaper-main .home-container {
  z-index: 3;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1.2vw;
  width: 100%;
  font-weight: 500;
  display: flex;
}

/* ===== 卡片 ===== */
.card {
  aspect-ratio: 1 / 0.7;
  background-color: #ffffff1a;
  border: none;
  border-top: 1px solid #ffffff80;
  border-left: 1px solid #ffffff80;
  border-radius: 15px;
  justify-content: center;
  align-items: center;
  width: 21.5%;
  animation-name: slideTop;
  display: flex;
  position: relative;
  overflow: hidden;
  box-shadow: 20px 20px 50px #00000080;
  cursor: pointer;
  transition: transform 0.3s;
}
.card:hover { transform: scale(1.02); }

/* 删除按钮：hover 卡片时右上角浮现（手机库同布局） */
.card-del {
  position: absolute; top: 10px; right: 10px; z-index: 6;
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: none; cursor: pointer;
  background: rgba(15, 15, 25, 0.55); color: #fff;
  backdrop-filter: blur(4px);
  opacity: 0; transform: scale(0.85);
  transition: opacity 0.18s, transform 0.18s, background 0.18s;
}
.card:hover .card-del { opacity: 1; transform: scale(1); }
.card-del:hover { background: #e5484d; }
.card-del svg { width: 15px; height: 15px; }

/* ===== 删除确认弹窗：居中毛玻璃 ===== */
.del-popup-mask {
  position: fixed; inset: 0; z-index: 5000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(8, 8, 16, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.del-popup-card {
  width: min(340px, 84vw);
  padding: 26px 24px 20px;
  border-radius: 18px;
  background: rgba(28, 28, 42, 0.72);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
  display: flex; flex-direction: column; align-items: center; text-align: center;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s;
}
.del-popup-thumb {
  width: 116px; height: 116px; object-fit: cover;
  border-radius: 14px; margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.del-popup-icon {
  width: 116px; height: 116px; border-radius: 14px; margin-bottom: 16px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(229, 72, 77, 0.12); color: #e5484d;
}
.del-popup-icon svg { width: 40px; height: 40px; }
.del-popup-title { font-size: 16px; font-weight: 600; color: #fff; }
.del-popup-name {
  margin-top: 6px; max-width: 100%;
  font-size: 12px; color: rgba(255, 255, 255, 0.55);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.del-popup-hint { margin-top: 8px; font-size: 12px; color: rgba(255, 255, 255, 0.45); }
.del-popup-actions {
  margin-top: 22px; width: 100%;
  display: flex; gap: 12px;
}
.dpa-btn {
  flex: 1; padding: 10px 0;
  border-radius: 12px; border: none;
  font-size: 14px; cursor: pointer; transition: all 0.2s;
}
.dpa-cancel {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.85);
}
.dpa-cancel:hover { background: rgba(255, 255, 255, 0.16); }
.dpa-danger { background: #e5484d; color: #fff; font-weight: 600; }
.dpa-danger:hover { background: #f03d42; }
.del-popup-mask.light .del-popup-card { border-color: rgba(0, 0, 0, 0.08); }
.del-popup-enter-active, .del-popup-leave-active { transition: opacity 0.2s; }
.del-popup-enter-active .del-popup-card, .del-popup-leave-active .del-popup-card { transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s; }
.del-popup-enter-from .del-popup-card, .del-popup-leave-to .del-popup-card { transform: scale(0.92); opacity: 0; }
.del-popup-enter-from, .del-popup-leave-to { opacity: 0; }

/* 亮色主题适配 */
.ps-album-page.light .del-popup-card {
  background: rgba(245, 245, 250, 0.78);
  border-color: rgba(0, 0, 0, 0.1);
}
.ps-album-page.light .del-popup-title { color: #222; }
.ps-album-page.light .del-popup-name { color: rgba(0, 0, 0, 0.55); }
.ps-album-page.light .del-popup-hint { color: rgba(0, 0, 0, 0.45); }
.ps-album-page.light .dpa-cancel { background: rgba(0, 0, 0, 0.06); color: #333; }
.ps-album-page.light .dpa-cancel:hover { background: rgba(0, 0, 0, 0.12); }
@keyframes slideTop {
  0% { opacity: 0; transform: translate(10%, 50%) scale(0.8); }
  to { opacity: 1; transform: translate(0); }
}
.card .resource-container {
  border-radius: 10px;
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  justify-content: center;
  align-items: center;
  display: flex;
}
.card .resource-container img {
  object-fit: cover;
  color: transparent;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  transition: transform 0.3s, opacity 0.25s ease-in;
  display: block;
}
.card:hover .resource-container img { transform: scale(1.1); }
/* 占位卡：无图渐变块 */
.ph-media {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #2a2a31, #1a1a21 55%, #26262e);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.28);
  font-size: 0.26rem;
  letter-spacing: 2px;
}
.ph-media span {
  padding: 0.1rem 0.24rem;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
}
.card .card-content {
  opacity: 0;
  background-color: var(--card-background-webkit);
  border-radius: 1.8vw;
  flex-direction: column;
  align-items: center;
  width: 90%;
  height: 80%;
  display: flex;
  overflow: hidden;
  transform: translateY(150px);
  transition: opacity 0.5s, transform 0.5s !important;
  position: relative;
  z-index: 2;
}
.card:hover .card-content {
  box-shadow: 0 0 15px var(--fc-background-webkit);
  transform: translateY(0);
  opacity: 1 !important;
}
.card .labelDiv {
  width: 90%;
  height: 70%;
  text-shadow: 2px 2px 8px var(--fc-background-webkit);
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  display: flex;
  overflow: auto;
}
.card .labelDiv span {
  color: var(--font-color-dark);
  border: 1px solid #ccc;
  border-radius: 50%;
  padding: 2%;
  font-size: 12px;
  font-weight: 500;
  justify-content: center;
  align-items: center;
  display: flex;
  box-shadow: inset 0 0 10px #00000080;
}
.card .card--button {
  justify-content: center;
  width: 100%;
  display: flex;
  position: absolute;
  bottom: 15%;
}
.card .col-card {
  width: 3rem;
  height: 0.9rem;
  font-weight: 500;
  position: relative;
}
.ps-bottom-nav-end {
  display: inline-flex;
  color: var(--vt-c-text-dark-1) !important;
  justify-content: center;
  align-items: center;
  position: relative;
  text-decoration: none;
}
.ps-bottom-nav-end__face {
  box-sizing: border-box;
  width: 100%;
  box-shadow: 0 0 10px var(--fc-background-webkit);
  background: var(--ps-bg-bag);
  color: inherit;
  border: 2px solid #fff;
  border-radius: 50px;
  padding: 0.15rem;
  font-size: 0.3rem;
  font-weight: 500;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}
.ps-bottom-nav-end:active:not(.disabled) .ps-bottom-nav-end__face {
  transform: scale(0.85);
}
.card .card-bottom {
  background-color: var(--card-bottom-bg);
  white-space: nowrap;
  justify-content: space-around;
  width: 100%;
  height: 10%;
  font-size: 100%;
  display: flex;
  position: absolute;
  bottom: 0;
}
.card .card-bottom div {
  width: 23%;
  color: var(--fc-background-webkit);
  justify-content: center;
  align-items: center;
  padding: 5px;
  display: flex;
  gap: 3px;
}

/* ===== 搜索栏 ===== */
.search-bar-container {
  z-index: 1000;
  align-items: center;
  gap: 7.5px;
  display: flex;
  position: fixed;
  bottom: 5vh;
  left: 50%;
  transform: translate(-50%);
}
.search-bar-container.is-sticky {
  z-index: 999;
  justify-content: center;
  width: 100%;
  padding-top: 0.2rem;
  position: sticky;
  bottom: 0.3rem;
  left: auto;
  transform: none;
}
.search-bar-wrapper {
  --filter-expanded-width: 1200px;
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  pointer-events: all;
  background: #403f3f54;
  border-radius: 300px;
  justify-content: center;
  align-items: center;
  width: max-content;
  max-width: calc(100vw - 0.4rem);
  height: 1rem;
  padding: 0.12rem 0.2rem;
  transition: all 0.3s;
  display: flex;
  overflow: visible;
  box-shadow: 0 0 20px #000000a3;
}
.search-bar-wrapper .search-main-row {
  justify-content: flex-start;
  align-items: center;
  width: 100%;
  height: 100%;
  display: flex;
}
.search-input-container {
  -webkit-user-select: none;
  user-select: none;
  flex: 1;
  min-width: 0;
  height: 100%;
  position: relative;
  display: flex;
}
.search-input-wrapper {
  background: #ffffff26;
  border: 1px solid #fff3;
  border-radius: 30px;
  align-items: center;
  width: 3.5rem;
  height: 100%;
  padding: 0 0.3rem;
  transition: all 0.2s;
  display: flex;
  position: relative;
  box-shadow: 0 2px 8px #0000001a;
}
.search-input-wrapper.is-focused {
  background: #fff3;
  border-color: #ffffff4d;
  box-shadow: 0 0 25px #8b96ff63;
}
.search-input {
  color: #ffffffe6;
  background: transparent;
  border: none;
  outline: none;
  flex: 1;
  height: 100%;
  padding: 0;
  font-size: 0.24rem;
  font-family: inherit;
}
.search-input::placeholder { color: #ffffff80; }
.search-loading {
  flex-shrink: 0;
  justify-content: center;
  align-items: center;
  width: 0.3rem;
  height: 0.3rem;
  margin-left: 0.1rem;
  display: none;
  position: absolute;
  top: 50%;
  right: 5%;
  transform: translateY(-50%);
}
.loading-spinner {
  border: 2px solid #fff3;
  border-top-color: #fffc;
  border-radius: 50%;
  width: 0.2rem;
  height: 0.2rem;
  animation: 0.6s linear infinite spin;
}
.search-results {
  z-index: 10001;
  scrollbar-width: thin;
  scrollbar-color: #fff3 transparent;
  background: #00000073;
  backdrop-filter: blur(15px);
  border-radius: 12px;
  max-height: 300px;
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  right: 0;
  overflow: hidden auto;
  box-shadow: 0 8px 32px #0000006e;
  display: none;
}
.search-results.show { display: block; }
.search-results .search-result-item {
  color: #ffffffe6;
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
  padding: 0.2rem 0.3rem;
  font-size: 0.22rem;
  transition: background-color 0.2s;
}
.search-results .search-result-item:hover { background-color: #ffffff1a; }
.search-results .search-result-item.is-empty {
  color: #ffffff80;
  cursor: default;
}
.search-results .search-result-item.is-empty:hover { background-color: transparent; }
/* filter-options */
.search-bar-wrapper .filter-options {
  max-width: min(var(--filter-expanded-width, 1200px), 100vw - 40px);
  height: 100%;
  opacity: 1;
  will-change: max-width, opacity, transform;
  flex-shrink: 0;
  justify-content: space-around;
  align-items: center;
  gap: 0.15rem;
  margin-left: 0.2rem;
  transition: max-width 0.55s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s, transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex;
  overflow: visible;
  transform: translateZ(0);
}
.search-bar-wrapper .filter-options.is-collapsed {
  opacity: 0;
  pointer-events: none;
  margin-left: 0;
  overflow: hidden;
  transform: translate(25px);
  max-width: 0 !important;
}
.search-dropdown-container {
  width: 100%;
  height: 100%;
  justify-content: center;
  align-items: center;
  display: flex;
  position: relative;
}
.search-dropdown-trigger {
  height: 85%;
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
  background-color: #ffffff1a;
  border: 1px solid #fff3;
  border-radius: 100px;
  padding: 0 0.1rem;
  transition: background 0.2s;
  justify-content: center;
  align-items: center;
  display: flex;
  position: relative;
}
.search-dropdown-trigger:hover,
.search-dropdown-trigger.is-open {
  background-color: #ffffff26;
  border-color: #ffffff4d;
}
.trigger-content {
  flex: 1;
  justify-content: center;
  align-items: center;
  gap: 7.5px;
  display: flex;
}
.trigger-icon {
  color: #ffffffb3;
  flex-shrink: 0;
  width: 0.2rem;
  height: 0.2rem;
  display: flex;
}
.trigger-icon svg { width: 100%; height: 100%; }
.trigger-text {
  color: #ffffffe6;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 0.22rem;
  font-weight: 400;
  overflow: hidden;
}
/* ===== 下拉面板 =====
   绝对定位浮层，不参与文档流，不影响搜索栏与页面布局。
   差异说明：参考样式用 left/right:0 让面板跟随容器宽度，但本页筛选容器只有 ~55px（按钮按内容撑开），
   按容器宽度会把选项挤成竖排，故改为「以触发按钮为中心、按内容自适应宽度 + 最小不小于按钮宽度」。 */
.search-dropdown-content {
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  /* 原版 #00000040，这里与站内搜索建议面板（.search-results）取同一底色，保证两者观感一致、文字可读 */
  background: #00000073;
  border-radius: 12px;
  min-height: 30px;
  overflow: hidden;
  box-shadow: 0 8px 32px #0000006e;
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  right: auto;
  transform: translateX(-50%);
  width: max-content;
  min-width: 2.3rem; /* 短标签时也留出余量，让右侧张数贴右对齐（原版 space-between 的意图） */
  max-width: 4.2rem; /* 放宽以容纳「色系」的文字+圆点+张数三栏，避免横向滚动 */
  z-index: 10000;
  display: none;
}
.search-dropdown-content.show { display: block; }
.dropdown-options {
  max-height: 350px;
  padding: 10px 0;
  overflow-y: auto;
}
.dropdown-options::-webkit-scrollbar { width: 4px; }
.dropdown-options::-webkit-scrollbar-track { background: transparent; }
.dropdown-options::-webkit-scrollbar-thumb { background: #ffffff4d; border-radius: 2px; }
.dropdown-options::-webkit-scrollbar-thumb:hover { background: #ffffff80; }
.dropdown-option {
  color: #ffffffe6;
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
  justify-content: space-between;
  align-items: center;
  gap: 0.12rem;  /* 三栏仅留小间距，紧凑不散 */
  padding: 0.25rem 0.4rem;
  font-size: 0.24rem;
  transition: background-color 0.2s;
  display: flex;
}
.dropdown-option:hover { background-color: #ffffff1a; }
.dropdown-option.is-selected {
  color: #fff;
  background-color: #ffffff26;
}
/* 三栏网格：文字固定列宽 + 圆点紧跟 + 张数贴右，保证所有圆点在同一竖线上（不再随数字宽度漂移）
   列宽收窄：总宽控制在面板 max-width 内，避免横向滚动 */
.dropdown-option .option-text {
  flex: 0 0 0.95rem;
  white-space: nowrap;
}
/* 色系圆点：纯白描边 + 深色外圈，深/浅色点在深浅面板上轮廓都一致（高明度色也不"隐形"）；
   间距由 .dropdown-option 的 gap 统一控制 */
.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid #ffffff;
  box-shadow: 0 0 0 1.5px rgba(0, 0, 0, 0.42), inset 0 0 2px rgba(0, 0, 0, 0.18);
  flex-shrink: 0;
}
.color-dot.is-mute {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.55);
  border-width: 2px;
  box-shadow: inset 0 0 2px rgba(255, 255, 255, 0.15);
}
/* 右侧张数：真实统计（数据来自后端）；定宽 + 右对齐，个位/多位数字右缘基准统一 */
.dropdown-option .option-count {
  color: #ffffff8c;
  flex-shrink: 0;
  font-size: 0.2rem;
  font-variant-numeric: tabular-nums;
  min-width: 0.7rem;
  text-align: right;
  margin-left: auto;
}
.dropdown-option.is-selected .option-count { color: #ffffffcc; }
.upload-button-wrapper {
  flex-shrink: 0;
  height: 100%;
  position: relative;
  /* 与左侧筛选按钮区隔开，避免贴紧（原「积」徽标已去掉） */
  margin-left: 0.14rem;
}
.upload-button {
  width: 1.2rem;
  height: 100%;
  cursor: pointer;
  border: 1px dashed #ffffff80;
  border-radius: 8px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 0.03rem;
  padding: 0.05rem;
  transition: all 0.2s;
  display: flex;
}
.upload-button:hover {
  background-color: #80808080;
  border-color: #ffffffcc;
}
.upload-button .upload-icon {
  object-fit: contain;
  width: 0.38rem;
  height: 0.38rem;
}
.upload-button .upload-text {
  color: #ffffffe6;
  white-space: nowrap;
  font-size: 0.16rem;
  line-height: 1;
}
/* collapse */
.collapse-button {
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  cursor: pointer;
  pointer-events: all;
  color: #ffffffe6;
  background: #00000030;
  border-radius: 50%;
  flex-shrink: 0;
  justify-content: center;
  align-items: center;
  padding: 0.4rem;
  transition: all 0.3s;
  display: flex;
  box-shadow: 0 0 10px #95adffbf;
}
.collapse-button:hover { background: #0000004d; }
.desktop-collapse-button { width: 0.7rem; height: 0.7rem; }
.desktop-collapse-button svg {
  width: 12px;
  height: 12px;
  transition: transform 0.3s;
}
.desktop-collapse-button.is-collapsed svg { transform: rotate(180deg); }

/* ===== 分页 ===== */
.page-main .ps-pagination {
  text-align: center;
  max-width: 100vw;
  text-shadow: 2px 2px 10px var(--fc-background-webkit);
  justify-content: center;
  align-items: center;
  margin-top: 0.3rem;
  margin-bottom: 10px;
  font-size: 0.3rem;
  display: flex;
  position: relative;
  color: var(--vt-c-text-dark-1) !important;
}
.page-main .ps-pagination .page-content {
  background: transparent;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  max-width: 80vw;
  height: auto;
  display: flex;
}
.page-main .ps-pagination a,
.page-main .ps-pagination div {
  text-align: center;
  margin: 0 var(--page-margin);
  background-color: var(--ps-bg-bag);
  color: inherit;
  cursor: inherit;
  text-decoration: none;
  transition: background-color 0.2s;
  display: inline-block;
}
.page-main .ps-pagination .nav-btn {
  aspect-ratio: 1;
  border-radius: 10px;
  min-width: 0.7rem;
  line-height: 0.7rem;
}
.page-main .ps-pagination .current,
.page-main .ps-pagination .isDefault {
  aspect-ratio: 1;
  border-radius: 50%;
  min-width: 0.7rem;
  margin-bottom: 10px;
  line-height: 0.7rem;
  text-align: center;
}
.page-main .ps-pagination .current {
  background-color: var(--ps-bg-bag);
  font-weight: 500;
  box-shadow: inset 0 0 5px var(--font-color-dark) !important;
}
/* ===== 分页交互（去掉点击缩放与当前页弹出动画：换页时不整栏跳动，仅保留每个按钮独立的 hover 背景反馈） ===== */
.page-main .ps-pagination a,
.page-main .ps-pagination div {
  transition: background-color 0.2s;
}
.page-main .ps-pagination .disabled {
  opacity: 0.35;
  pointer-events: none;
}
.page-main .ps-pagination .ellipsis {
  cursor: default;
  min-width: auto;
  aspect-ratio: unset;
  margin-bottom: 10px;
  background: transparent !important;
}
.page-main .ps-pagination a:not(.disabled):not(.ellipsis):not(.page-content):hover,
.page-main .ps-pagination div:not(.disabled):not(.ellipsis):not(.page-content):hover {
  background-color: var(--color-background-webkit) !important;
}

/* ===== 分页改为「左侧竖排」浮层：点页码平滑滚动到对应位置（列表不切分） =====
   放在左侧、离浏览器边缘留距离；竖向排列，页数多时竖列内部可滚动 */
.page-main {
  position: fixed;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 35;
  max-height: 74vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 6px;
  border-radius: 18px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.34);
  scrollbar-width: none;
}
.page-main::-webkit-scrollbar { width: 0; height: 0; }
.page-main .ps-pagination { text-align: center; }
.page-main .ps-pagination .page-content {
  flex-direction: column;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
}
.page-main .ps-pagination a,
.page-main .ps-pagination div {
  margin: 0 !important;
}
.page-main .ps-pagination .current,
.page-main .ps-pagination .isDefault,
.page-main .ps-pagination .ellipsis {
  margin-bottom: 0;
}

/* ===== Go 跳页对话框 ===== */
.ps-pagination-go-overlay {
  box-sizing: border-box;
  z-index: 2000;
  place-items: center;
  min-height: 100dvh;
  padding: 14px;
  position: fixed;
  overflow: hidden;
  background: var(--ps-go-overlay) !important;
  backdrop-filter: blur(8px) saturate(84%);
  -webkit-backdrop-filter: blur(8px) saturate(84%);
  overscroll-behavior: contain;
  touch-action: none;
  width: 100%;
  height: 100%;
  display: none;
  inset: 0;
}
.ps-pagination-go-overlay.show { display: grid; }
.ps-pagination-go-dialog {
  box-sizing: border-box;
  color: var(--ps-go-text);
  backdrop-filter: blur(24px) saturate(120%);
  -webkit-backdrop-filter: blur(24px) saturate(120%);
  position: relative;
  overflow: hidden;
  border: 1px solid var(--ps-go-line-strong) !important;
  background: var(--ps-go-surface) !important;
  box-shadow: var(--ps-go-shadow) !important;
  border-radius: 24px !important;
  width: min(360px, 100% - 24px);
  margin: 0;
  padding: 0;
}
.ps-pagination-go-form {
  width: 100%;
  margin: 0;
  padding: 17px;
  position: relative;
}
.ps-pagination-go-close {
  z-index: 2;
  width: 30px;
  height: 30px;
  color: var(--ps-go-faint);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 50%;
  place-items: center;
  padding: 0;
  font-size: 19px;
  line-height: 1;
  transition: color 0.18s, background 0.18s, transform 0.18s;
  display: grid;
  position: absolute;
  top: 10px;
  right: 10px;
  cursor: pointer;
}
.ps-pagination-go-close:hover {
  color: var(--ps-go-text);
  background: rgba(255,255,255,0.07);
  transform: rotate(4deg);
}
.ps-pagination-go-header {
  text-align: left;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  margin-bottom: 15px;
  padding-right: 31px;
  display: flex;
}
.ps-pagination-go-header h3 {
  color: var(--ps-go-text);
  letter-spacing: -0.02em;
  margin: 0;
  font-size: 16px;
  font-weight: 770;
  line-height: 1.3;
}
.ps-pagination-go-header p {
  color: var(--ps-go-muted);
  margin: 4px 0 0;
  font-size: 11px;
  line-height: 1.4;
}
.ps-pagination-go-current {
  border: 1px solid var(--ps-go-line);
  max-width: 130px;
  color: var(--ps-go-faint);
  background: rgba(255,255,255,0.025);
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 999px;
  flex: none;
  padding: 5px 8px;
  font-size: 9px;
  line-height: 1.2;
  overflow: hidden;
}
.ps-pagination-go-command {
  border: 1px solid var(--ps-go-line);
  background: var(--ps-go-surface-deep);
  min-height: 52px;
  box-shadow: var(--ps-go-inner);
  border-radius: 18px;
  grid-template-columns: 36px minmax(76px, 1fr) 36px 72px;
  align-items: center;
  gap: 6px;
  padding: 6px;
  display: grid;
}
.ps-pagination-go-step {
  width: 36px;
  height: 36px;
  color: var(--ps-go-muted);
  background: rgba(255,255,255,0.035);
  border: 1px solid var(--ps-go-line);
  border-radius: 50%;
  place-items: center;
  padding: 0;
  font-size: 17px;
  line-height: 1;
  display: grid;
  transition: color 0.18s, background 0.18s, border-color 0.18s, transform 0.18s;
  cursor: pointer;
}
.ps-pagination-go-step:hover {
  color: var(--ps-go-text);
  border-color: var(--ps-go-line-strong);
  background: rgba(255,255,255,0.08);
  transform: scale(1.045);
}
.ps-pagination-go-input-wrap {
  cursor: text;
  border-radius: 10px;
  place-items: center;
  min-width: 0;
  height: 36px;
  padding: 0 4px;
  display: grid;
}
.ps-pagination-go-input {
  width: 100%;
  min-width: 0;
  height: 100%;
  color: var(--ps-go-text);
  font-feature-settings: "tnum";
  font-variant-numeric: tabular-nums;
  text-align: center;
  letter-spacing: -0.04em;
  cursor: text;
  caret-color: var(--ps-go-text);
  background: transparent;
  border: 0;
  outline: 0;
  padding: 0;
  font-size: 26px;
  font-weight: 800;
  line-height: 36px;
}
.ps-pagination-go-confirm {
  width: 72px;
  min-width: 0;
  height: 36px;
  color: var(--ps-go-accent-text);
  background: var(--ps-go-accent);
  white-space: nowrap;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 0 9px;
  font-size: 11px;
  font-weight: 770;
  box-shadow: 0 6px 14px #00000029;
  transition: filter 0.18s, transform 0.18s;
  cursor: pointer;
}
.ps-pagination-go-confirm:hover {
  filter: brightness(1.06);
  transform: translateY(-1px);
}
.ps-pagination-go-confirm span {
  margin-left: 2px;
  transition: transform 0.18s;
  display: inline-block;
}
.ps-pagination-go-confirm:hover span { transform: translate(2px); }
.ps-pagination-go-foot {
  color: var(--ps-go-faint);
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin: 10px 5px 0;
  font-size: 9.5px;
  line-height: 1.3;
  display: flex;
}
.ps-pagination-go-foot kbd {
  border: 1px solid var(--ps-go-line);
  background: rgba(255,255,255,0.025);
  font: inherit;
  border-radius: 5px;
  padding: 2px 6px;
}

/* ===== 响应式（对照真实站点 TopView/homeView 断点做自适应：窄屏导航折行整宽，文字仅在手机级才退化为图标） ===== */
@media screen and (max-width: 1100px) {
  /* 导航换行到整宽第二行，所有 tab 等分完整保留文字 */
  .main-top .header-top-view {
    flex-grow: 1;
    order: 3;
    overflow: visible;
    width: 100% !important;
  }
  .main-top .header-top-view .TopBody {
    width: 100% !important;
    min-width: 100% !important;
  }
  .main-top .header-tab-tight-top,
  .main-top .logo { margin-bottom: 0.25rem; }
}
@media (max-width: 800px) {
  .card { width: 46% !important; }
  .card .card-bottom div:nth-child(3),
  .card .card-bottom div:nth-child(4) { display: none !important; }
  .card .card--button { bottom: 35% !important; }
  .card .card-content { border-radius: 20px !important; }
  .lableEnd { display: none; }
  .switch { display: none; }
}
/* 极窄：5 个 tab 装不下文字时退化为图标式胶囊，仅保留选中项文字 */
@media (max-width: 620px) {
  .TopBody .top-nav-text { display: none !important; }
}

/* ===== 大图查看层（fixed 覆盖层，全部 px 尺寸，不参与页面布局；z-index 高于页面所有层） ===== */
.viewer-fade-enter-active, .viewer-fade-leave-active { transition: opacity 0.25s; }
.viewer-fade-enter-from, .viewer-fade-leave-to { opacity: 0; }

.viewer {
  position: fixed;
  inset: 0;
  z-index: 100000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(5, 5, 10, 0.55);
  color: #fff;
}
.viewer-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}
.viewer-bg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: blur(24px) saturate(1.25);
  transform: scale(1.2);
}
.viewer-top {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 22px;
}
.viewer-meta { min-width: 0; max-width: 60%; }
.viewer-name { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.viewer-date { font-size: 12px; opacity: 0.5; margin-top: 2px; }
.viewer-close {
  width: 40px; height: 40px;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.85);
  font-size: 14px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(8px);
  transition: all 0.3s;
}
.viewer-close:hover { background: rgba(255,255,255,0.2); transform: scale(1.08); }

.v-card {
  /* 卡片高度变量：旋转 90/270 时图片按「卡高」约束宽（宽高互换），随断点同步 */
  --v-card-h: min(74vh, 720px);
  position: relative;
  width: min(84vw, 1200px);
  height: var(--v-card-h);
  /* 整体上移：底部缩放控制条不再压住放大后的图片下部（滚轮放大拖动时不遮挡） */
  margin-top: -2.5vh;
  overflow: hidden;
  cursor: grab;
  user-select: none;
}
.v-card img {
  position: absolute;
  top: 50%;
  left: 50%;
  max-width: 92%;
  max-height: 92%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
  transition: opacity 0.3s;
  cursor: grab;
  border-radius: 8px;
}
/* 旋转 90/270：CSS 的 max 百分比只对原轴生效（旋转后视觉轴互换会失效导致裁切），
   改为去掉 max 约束，由 JS vRotate90 按自然尺寸计算适配缩放（contain） */
.v-card img.v-rot {
  max-width: none;
  max-height: none;
}
.v-card img.loading { opacity: 0; }

.v-loading {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: rgba(255,255,255,0.5);
  font-size: 13px;
}
.v-spin-circle {
  width: 44px; height: 44px;
  border-radius: 50%;
  border: 3px solid rgba(108, 99, 255, 0.15);
  border-top-color: #6c63ff;
  animation: v-spin 0.8s linear infinite;
  display: flex;
  align-items: center;
  justify-content: center;
}
.v-spin-circle svg { width: 14px; height: 14px; }
@keyframes v-spin { to { transform: rotate(360deg); } }

.v-hint {
  /* 提示文字固定贴在底部缩放控制条（− 百分比 +）正上方：它只提示操作，不随图片卡片移动 */
  position: fixed;
  bottom: 78px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  opacity: 0.4;
  z-index: 21;
  pointer-events: none;
  white-space: nowrap;
  text-align: center;
}

.v-nav {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 20;
  width: 48px; height: 48px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  color: #fff;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(8px);
  transition: all 0.3s;
}
.v-nav.prev { left: 28px; }
.v-nav.next { right: 28px; }
.v-nav svg { width: 22px; height: 22px; }
.v-nav:hover:not(:disabled) { background: rgba(255,255,255,0.2); transform: translateY(-50%) scale(1.08); }
.v-nav:disabled { opacity: 0.25; cursor: not-allowed; }

.viewer-bottom {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  z-index: 20;
  display: flex;
  justify-content: center;
  padding: 16px 16px 20px;
  pointer-events: none;
}
.v-zoom {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px;
  border-radius: 12px;
  background: rgba(20, 20, 30, 0.75);
  border: 1px solid rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
  pointer-events: auto;
}
.v-zoom button {
  width: 30px; height: 30px;
  border: none; border-radius: 8px;
  background: transparent;
  color: rgba(255,255,255,0.7);
  font-size: 16px; line-height: 1;
  cursor: pointer;
}
.v-zoom button:hover:not(:disabled) { background: rgba(255,255,255,0.15); color: #fff; }
.v-zoom button:disabled { opacity: 0.25; cursor: not-allowed; }
.v-zoom .v-fit { font-size: 13px; display: inline-flex; align-items: center; justify-content: center; }
.v-zoom .v-fit svg { width: 15px; height: 15px; }
.v-val { min-width: 48px; text-align: center; font-size: 12px; font-variant-numeric: tabular-nums; color: #fff; }
.v-sep { width: 1px; height: 18px; margin: 0 3px; background: rgba(255,255,255,0.12); }

@media (max-width: 800px) {
  .v-card { --v-card-h: 72vh; width: 94vw; height: 72vh; }
}

/* ===== 空态提示（无结果时） ===== */
.grid-empty {
  width: 100%;
  padding: 96px 20px;
  text-align: center;
  color: #ffffffb3;
}
.grid-empty p { font-size: 15px; }
.grid-empty .hint { font-size: 13px; color: #ffffff73; margin-top: 8px; }

/* ===== 右侧悬浮按钮（火箭回顶 / 手机照片页额外的批量上传） =====
   固定在屏幕右侧垂直居中，浮在内容之上，不参与文档流 */
.side-actions {
  position: fixed;
  right: 26px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}
.side-btn {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.38);
  color: #ffffffe6;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s, transform 0.18s, opacity 0.2s;
}
.side-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.18);
  transform: translateY(-2px);
}
.side-btn:active:not(:disabled) { transform: translateY(0) scale(0.94); }
.side-btn:disabled { opacity: 0.5; cursor: default; }
.side-btn svg { width: 30px; height: 30px; }
/* 火箭未出现时保留占位，仅淡出并禁用点击 */
.side-btn.is-hidden { opacity: 0; pointer-events: none; }

/* 上传进度 / 结果提示：贴在按钮组左侧，同样垂直居中 */
.side-toast {
  position: fixed;
  right: 108px;               /* 26 + 64 + 18，紧贴按钮组左缘 */
  top: 50%;
  transform: translateY(-50%);
  z-index: 41;
  max-width: 262px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #ffffffe6;
  font-size: 13px;
  line-height: 1.5;
}
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity 0.22s, transform 0.22s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translate(12px, -50%); }

/* ===== 手机照片页（/mobile）：沿用同一套布局，只把卡片换成竖屏比例、每行多放几张 ===== */
.ps-album-page.is-phone .card {
  aspect-ratio: 1080 / 2340;   /* 手机竖屏比例，竖版照片基本不裁切 */
  width: 13.5%;
}
/* 手机竖卡细长：hover 面板内标签云/按钮/底部信息条容易重叠，针对性收紧 */
.ps-album-page.is-phone .card .card-content { height: 92%; }
.ps-album-page.is-phone .card .labelDiv { height: 52%; }
.ps-album-page.is-phone .card .labelDiv span { font-size: 10px; padding: 1.5% 3%; }
.ps-album-page.is-phone .card .card--button { bottom: 16%; }
.ps-album-page.is-phone .card .card-bottom { height: 9%; }
.ps-album-page.is-phone .card .card-bottom div {
  width: 25%;
  padding: 3px;
  font-size: 10px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ps-album-page.is-phone .card .card-bottom .cval { font-size: 10px; }

/* ===== 窄屏适配：分页与卡片同步收窄 ===== */
@media (max-width: 1100px) {
  .main-content { padding-left: 76px; }
  .page-main { left: 14px; padding: 9px 4px; }
  .page-main .ps-pagination a,
  .page-main .ps-pagination div { min-width: 0.58rem; line-height: 0.58rem; font-size: 13px; }
  .ps-album-page.is-phone .card { width: 17%; }
}
@media (max-width: 800px) {
  .main-content { padding-left: 54px; }
  .page-main { left: 6px; padding: 7px 3px; max-height: 64vh; }
  .page-main .ps-pagination a,
  .page-main .ps-pagination div { min-width: 0.46rem; line-height: 0.46rem; font-size: 12px; }
  .side-actions { right: 12px; gap: 12px; }
  .side-btn { width: 54px; height: 54px; }
  .side-btn svg { width: 26px; height: 26px; }
  .side-toast { right: 78px; max-width: 58vw; }
  .ps-album-page.is-phone .card { width: 46% !important; }
}

/* ===== 亮色主题（昼夜替换）：相册深色 → 浅色（深色硬编码的值在这里兜底翻亮） ===== */
.ps-album-page.light { background: #f3f2f7; }
.ps-album-page.light .bg-texture {
  background:
    radial-gradient(ellipse 80% 55% at 50% -10%, rgba(255, 255, 255, 0.5), transparent 60%),
    radial-gradient(ellipse 60% 45% at 85% 110%, rgba(139, 92, 246, 0.05), transparent 55%),
    radial-gradient(ellipse 60% 45% at 10% 105%, rgba(120, 160, 255, 0.05), transparent 55%);
}
.ps-album-page.light .page-bg-image { filter: blur(14px) brightness(0.92); }

/* 底部搜索栏 */
.ps-album-page.light .search-bar-container { background: linear-gradient(180deg, rgba(243, 242, 247, 0.94), rgba(243, 242, 247, 0.72)); }
.ps-album-page.light .search-input { color: #1f2126; caret-color: #6c63ff; }
.ps-album-page.light .search-input::placeholder { color: rgba(0, 0, 0, 0.35); }
.ps-album-page.light .search-results { background: rgba(255, 255, 255, 0.96); border-color: rgba(0, 0, 0, 0.08); box-shadow: 0 12px 30px rgba(60, 60, 90, 0.18); }
.ps-album-page.light .search-result-item { color: #26272e; }
.ps-album-page.light .search-result-item:hover { background: rgba(0, 0, 0, 0.06); }
.ps-album-page.light .search-result-item.is-empty { color: rgba(0, 0, 0, 0.4); }
.ps-album-page.light .search-dropdown-trigger { color: #26272e; }
.ps-album-page.light .search-dropdown-content { background: rgba(255, 255, 255, 0.97); border-color: rgba(0, 0, 0, 0.08); box-shadow: 0 12px 30px rgba(60, 60, 90, 0.2); }
.ps-album-page.light .dropdown-option { color: rgba(0, 0, 0, 0.66); }
.ps-album-page.light .color-dot { border-color: rgba(255, 255, 255, 0.92); box-shadow: 0 0 0 1.5px rgba(0, 0, 0, 0.18), inset 0 0 2px rgba(0, 0, 0, 0.12); }
.ps-album-page.light .color-dot.is-mute { border-color: rgba(0, 0, 0, 0.28); box-shadow: inset 0 0 2px rgba(0, 0, 0, 0.1); }
.ps-album-page.light .dropdown-option:hover,
.ps-album-page.light .dropdown-option.is-selected { color: #1f2126; background: rgba(108, 99, 255, 0.08); }
.ps-album-page.light .dropdown-option .option-count { color: rgba(0, 0, 0, 0.4); }
.ps-album-page.light .upload-button { color: #1f2126; background: rgba(0, 0, 0, 0.05); }
.ps-album-page.light .upload-icon { stroke: #26272e; }
.ps-album-page.light .collapse-button { color: rgba(0, 0, 0, 0.5); }
.ps-album-page.light .loading-spinner { border-color: rgba(0, 0, 0, 0.15); border-top-color: #6c63ff; }

/* 左侧分页 */
.ps-album-page.light .page-main .ps-pagination .current,
.ps-album-page.light .page-main .ps-pagination .isDefault,
.ps-album-page.light .page-main .ps-pagination .ellipsis,
.ps-album-page.light .page-main .ps-pagination .nav-btn { color: #26272e !important; }
.ps-album-page.light .page-main .ps-pagination .current { color: #6c63ff !important; background: rgba(108, 99, 255, 0.12); }
.ps-album-page.light .page-main .nav-btn { background: rgba(0, 0, 0, 0.05); }
.ps-album-page.light .nav-btn.disabled { opacity: 0.38; }

/* 右侧悬浮按钮 */
.ps-album-page.light .side-btn { background: rgba(255, 255, 255, 0.75); color: #34353d; box-shadow: 0 4px 14px rgba(60, 60, 90, 0.18); }
</style>

<style>
/* ===== v-html 注入的 SVG 无法命中 scoped 规则，这里全局兜底（与 index.html 一致） ===== */
.tabCss .tab-nuxt-link .el-icon svg {
  width: 0.44rem;
  height: 0.44rem;
  fill: var(--color-text);
}
.trigger-icon svg { width: 100%; height: 100%; }
.card .card-bottom .cval {
  font-size: 12px;
  line-height: 1;
  color: inherit;
  white-space: nowrap;
}
</style>
