<template>
  <div class="enhance-page" :class="{ light: !store.darkTheme }">
    <!-- 顶部导航 -->
    <header class="enhance-header" :class="{ light: !store.darkTheme }">
      <div class="header-left">
        <div class="header-logo">
          <span class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3c7 0 9 9 9 9s-2 9-9 9-9-9-9-9 2-9 9-9z"/><circle cx="12" cy="12" r="3"/><path d="M12 9v2l1.5 1.5"/></svg>
          </span>
          <div class="logo-text">
            <h1>照片增强器</h1>
            <span class="logo-sub">AI Photo Enhancer</span>
          </div>
        </div>
        <div class="header-breadcrumb">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
          <span>图片变清晰</span>
        </div>
      </div>
      <div class="header-right">
        <div class="level-selector">
          <button
            v-for="lvl in levels" :key="lvl.value"
            class="level-btn"
            :class="{ active: enhanceLevel === lvl.value }"
            @click="enhanceLevel = lvl.value"
          >
            <span class="level-dot"></span>
            {{ lvl.label }}
          </button>
        </div>
      </div>
    </header>

    <!-- 主体 -->
    <div class="enhance-body">
      <!-- 中间：对比预览区 -->
      <main class="preview-area" ref="previewArea">
        <div v-if="!uploadId" class="preview-empty upload-zone"
          @click="pickFile"
          @dragover.prevent="dragOver = true"
          @dragleave.prevent="dragOver = false"
          @drop.prevent="onDrop"
          :class="{ 'drag-over': dragOver }"
        >
          <div class="upload-box">
            <div class="up-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"/></svg>
            </div>
            <h3>{{ uploading ? '上传中...' : (dragOver ? '松开上传' : '上传本地照片') }}</h3>
            <p>点击选择或拖拽图片到此处 · 支持 JPG/PNG/WebP 等</p>
            <span class="upload-hint">AI 一键提升画质 · 最高 4x 超分放大</span>
          </div>
        </div>

        <div v-else class="comparison-container">
          <!-- 增强完成扩散波纹 -->
          <div v-if="doneRipple > 0" :key="doneRipple" class="done-ripple">
            <span class="ripple-circle c1"></span>
            <span class="ripple-circle c2"></span>
            <span class="ripple-check">✓</span>
          </div>
          <div
            class="compare-scroll"
            ref="compareScroll"
            :class="{ panning: isPanning, 'zoom-active': zoomLevel >= ZOOM_MIN }"
            @wheel.prevent="onWheelZoom"
            @mousedown="onPanStart"
          >
            <!-- 对比标签 -->
            <div class="compare-labels">
              <div class="compare-label label-before" v-if="enhancedUrl">处理前</div>
              <div class="compare-label label-after" v-if="enhancedUrl">处理后</div>
            </div>

            <div
              class="compare-wrapper"
              ref="compareWrapper"
              :style="{
                width: naturalImgW + 'px',
                height: naturalImgH + 'px',
                transform: 'translate3d(' + panX + 'px, ' + panY + 'px, 0) scale(' + zoomLevel + ')'
              }"
              @mousemove="onCompareMove"
              @touchmove="onCompareTouch"
            >
              <!-- 增强后 -->
              <img
                v-if="enhancedUrl"
                :src="enhancedUrl"
                alt="enhanced"
                class="compare-img"
                draggable="false"
                @load="onImgLoaded"
              />
              <div
                v-if="enhancedUrl"
                class="compare-before-layer"
                :style="{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }"
              >
                <img
                  :src="getUploadPhotoUrl(uploadId)"
                  alt="original"
                  class="compare-img"
                  draggable="false"
                />
              </div>
              <!-- 对比滑块 -->
              <div
                v-if="enhancedUrl"
                class="compare-slider"
                :style="{ left: sliderPos + '%' }"
                @mousedown="onSliderDown"
              >
                <div class="slider-handle">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l-6-6 6-6M15 6l6 6-6 6"/></svg>
                </div>
              </div>

              <!-- 加载中（多层旋转光圈 + 呼吸光环 + 进度） -->
              <div v-if="enhancing || (progress > 0 && progress < 100)" class="enhance-loading">
                <div class="fx-rings">
                  <span class="fx-ring r1"></span>
                  <span class="fx-ring r2"></span>
                  <span class="fx-ring r3"></span>
                  <div class="fx-core">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.9 5.8L20 12l-6.1 3.2L12 21l-1.9-5.8L4 12l6.1-3.2z"/></svg>
                  </div>
                </div>
                <span class="loading-text">增强画质 {{ Math.round(progress) }}%</span>
                <div class="loading-bar">
                  <div class="loading-bar-inner" :style="{ width: progress + '%' }"></div>
                </div>
              </div>

              <!-- 未增强时显示原图 -->
              <img
                v-if="!enhancedUrl && !enhancing"
                :src="getUploadPhotoUrl(uploadId)"
                alt="original"
                class="compare-img"
                draggable="false"
                @load="onImgLoaded"
              />
            </div>
          </div>

          <!-- 缩放工具栏（底部居中） -->
          <div class="zoom-toolbar" v-if="uploadId">
            <button class="zoom-btn" @click="zoomOut" :disabled="zoomLevel <= ZOOM_MIN" title="缩小">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M7 11h8"/></svg>
            </button>
            <div class="zoom-info">
              <span class="zoom-val">{{ Math.round(zoomLevel * 100) }}%</span>
              <span class="zoom-dim">{{ Math.round(wrapperDisplayW) }}×{{ Math.round(wrapperDisplayH) }}</span>
            </div>
            <button class="zoom-btn" @click="zoomIn" :disabled="zoomLevel >= ZOOM_MAX" title="放大">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M11 7v8M7 11h8"/></svg>
            </button>
            <div class="zoom-divider"></div>
            <button class="zoom-btn fit-btn" @click="zoomReset" title="适应屏幕（恢复初始比例）">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
            </button>
          </div>
        </div>

        <!-- 当前照片信息条（上传照片底部，一行横排紧凑） -->
        <div v-if="uploadId" class="photo-info-bar">
          <div class="pib-item pib-name" :title="photoName || ''">{{ photoName ? photoName.slice(0, 18) + (photoName.length > 18 ? '…' : '') : '未命名' }}</div>
          <span class="pib-sep"></span>
          <div class="pib-item">
            <span class="pib-label">尺寸</span>
            <span class="pib-val">{{ naturalImgW ? naturalImgW + '×' + naturalImgH : '—' }}</span>
          </div>
          <span class="pib-sep"></span>
          <div class="pib-item" v-if="enhancedUrl && enhancedSize > 0">
            <span class="pib-label">大小</span>
            <span class="pib-val size-compare">
              <span class="size-old">{{ formatSize(originalSize) }}</span>
              <svg class="size-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
              <span class="size-new">{{ formatSize(enhancedSize) }}</span>
              <span class="size-delta" :class="{ down: enhancedSize < originalSize }">
                {{ enhancedSize >= originalSize ? '+' : '' }}{{ formatSize(Math.abs(enhancedSize - originalSize)) }}
              </span>
            </span>
          </div>
          <div class="pib-item" v-else>
            <span class="pib-label">大小</span>
            <span class="pib-val">{{ originalSize ? formatSize(originalSize) : '—' }}</span>
          </div>
          <span class="pib-sep" v-if="enhancedUrl && enhancedSize > 0"></span>
          <div class="pib-item">
            <span class="pib-label">显示</span>
            <span class="pib-val">{{ wrapperDisplayW }}×{{ wrapperDisplayH }}</span>
          </div>
          <span class="pib-sep"></span>
          <div class="pib-item">
            <span class="pib-label">级别</span>
            <span class="level-badge" :class="`level-${enhanceLevel}`">{{ levels[enhanceLevel - 1].label }}</span>
          </div>
          <div class="pib-actions">
            <button class="mini-btn" @click="pickFile" title="选择新图片，覆盖当前">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/></svg>
              <span>重新上传</span>
            </button>
            <button class="mini-btn danger" @click="clearPhoto" title="清除当前图片">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/></svg>
              <span>清除</span>
            </button>
          </div>
        </div>
      </main>

      <!-- 右侧：控制面板 -->
      <aside class="control-panel" :class="{ light: !store.darkTheme }">
        <!-- 增强操作（当前照片信息移到预览区底部的信息条） -->
        <div class="panel-card">
          <div class="panel-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M9 12l3 3 3-3M5 19h14"/></svg>
            <span>增强操作</span>
          </div>
          <div class="panel-card-body">
            <!-- 放大倍数选择 -->
            <div class="scale-row">
              <span class="scale-label">放大倍数</span>
              <div class="scale-selector">
                <button
                  v-for="s in scales" :key="s.value"
                  class="scale-btn"
                  :class="{ active: enhanceScale === s.value }"
                  @click="enhanceScale = s.value"
                >{{ s.label }}</button>
              </div>
            </div>
            <!-- 人像优化（纯传统 CV：磨皮 / 五官锐化 / 肤色校正 / 背景虚化，零模型零网络） -->
            <div class="scale-row">
              <span class="scale-label">人像优化</span>
              <div class="scale-selector">
                <button class="scale-btn" :class="{ active: !portraitMode }" @click="portraitMode = false">关</button>
                <button class="scale-btn" :class="{ active: portraitMode }" @click="turnOnPortrait">开</button>
              </div>
            </div>
            <!-- 人像优化强度（各工序 0~200%） -->
            <div v-if="portraitMode" class="fx-panel">
              <div v-for="c in fxControls" :key="c.key" class="fx-row">
                <span class="fx-label">{{ c.label }}</span>
                <input class="fx-range" type="range" min="0" max="2" step="0.1" v-model.number="fxVals[c.key]">
                <span class="fx-val">{{ Math.round(fxVals[c.key] * 100) }}%</span>
              </div>
            </div>

            <p v-if="portraitMode" class="portrait-hint">
              {{ portraitSubjects === 0
                ? '未识别到人像，本次未做额外处理'
                : (portraitLocate === 'fallback'
                  ? '未确认人脸，按中心主体处理 · 磨皮/五官锐化/背景虚化'
                  : (portraitSubjects > 0
                    ? `已定位 ${portraitSubjects} 处主体（肤色启发式）· 磨皮/五官锐化/背景虚化`
                    : '磨皮 · 五官锐化 · 肤色校正 · 背景虚化')) }}
            </p>

            <button
              class="enhance-btn"
              :class="{ processing: enhancing, completed: enhancedUrl && !enhancing }"
              :disabled="!uploadId || enhancing"
              @click="doEnhance"
            >
              <svg v-if="!enhancing && !enhancedUrl" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3c7 0 9 9 9 9s-2 9-9 9-9-9-9-9 2-9 9-9z"/><circle cx="12" cy="12" r="3"/></svg>
              <svg v-if="enhancing" class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
              <svg v-if="!enhancing && enhancedUrl" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m-6 8h10a2 2 0 002-2V6a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
              <span>{{ enhancing ? '增强中...' : (enhancedUrl ? '重新增强' : '开始增强') }}</span>
            </button>

            <!-- 处理步骤状态（类似 PhotoGrid） -->
            <div v-if="enhancing || (progress > 0 && progress < 100)" class="progress-steps">
              <div class="progress-step" :class="stepClass(1)">
                <span class="step-icon">
                  <svg v-if="step > 1" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  <svg v-else-if="step === 1" class="step-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                  <span v-else class="step-num">1</span>
                </span>
                <span class="step-name">消除模糊</span>
              </div>
              <div class="progress-step" :class="stepClass(2)">
                <span class="step-icon">
                  <svg v-if="step > 2" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  <svg v-else-if="step === 2" class="step-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                  <span v-else class="step-num">2</span>
                </span>
                <span class="step-name">增强画质</span>
              </div>
              <div class="progress-step" :class="stepClass(3)">
                <span class="step-icon">
                  <svg v-if="step > 3" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  <svg v-else-if="step === 3" class="step-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                  <span v-else class="step-num">3</span>
                </span>
                <span class="step-name">图像超分</span>
              </div>
              <div class="progress-step" :class="stepClass(4)">
                <span class="step-icon">
                  <svg v-if="step > 4" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  <svg v-else-if="step === 4" class="step-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                  <span v-else class="step-num">4</span>
                </span>
                <span class="step-name">增强细节</span>
              </div>
            </div>

            <div v-if="enhancedUrl" class="action-row">
              <button class="action-btn download-btn" :class="{ busy: downloading }" :disabled="downloading" @click="downloadEnhanced">
                <svg v-if="!downloading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M9 12l3 3 3-3M5 19h14"/></svg>
                <svg v-else class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                <span>{{ downloading ? '生成中...' : '下载' }}</span>
              </button>
              <button class="action-btn reset-btn" @click="resetCompare">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/></svg>
                <span>重置</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 增强说明 -->
        <div class="panel-card">
          <div class="panel-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
            <span>增强说明</span>
          </div>
          <div class="panel-card-body">
            <div class="level-option" :class="{ active: enhanceLevel === 1 }" @click="enhanceLevel = 1">
              <div class="level-option-icon green">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M9 12l3 3 3-3"/></svg>
              </div>
              <div class="level-option-text">
                <strong>轻量级</strong>
                <span>轻微锐化，适合清晰照片</span>
              </div>
              <div class="level-option-check" v-if="enhanceLevel === 1">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
              </div>
            </div>
            <div class="level-option" :class="{ active: enhanceLevel === 2 }" @click="enhanceLevel = 2">
              <div class="level-option-icon purple">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12M9 12l3 3 3-3M5 19h14"/></svg>
              </div>
              <div class="level-option-text">
                <strong>标准级</strong>
                <span>均衡锐化，推荐大多数照片</span>
              </div>
              <div class="level-option-check" v-if="enhanceLevel === 2">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
              </div>
            </div>
            <div class="level-option" :class="{ active: enhanceLevel === 3 }" @click="enhanceLevel = 3">
              <div class="level-option-icon orange">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              </div>
              <div class="level-option-text">
                <strong>极致级</strong>
                <span>强锐化+降噪，适合模糊照片</span>
              </div>
              <div class="level-option-check" v-if="enhanceLevel === 3">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 常驻隐藏文件选择框（上传区销毁后重新上传仍可用） -->
    <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="onFileChange" />
  </div>
</template>

<script setup>
import { ref, computed, reactive, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { store } from '../store'
import { uploadPhoto, getUploadPhotoUrl } from '../api/photos'

// 上传照片状态
const uploadId = ref('')
const photoName = ref('')
const uploading = ref(false)
const dragOver = ref(false)
const fileInput = ref(null)
const enhancedUrl = ref('')
const enhancing = ref(false)
const enhanceLevel = ref(2)
const sliderPos = ref(50)
const compareWrapper = ref(null)
const compareScroll = ref(null)
const previewArea = ref(null)
// 文件大小（原始 vs 增强后）
const originalSize = ref(0)
const enhancedSize = ref(0)
// 完成波纹触发计数
const doneRipple = ref(0)

// 缩放状态
const zoomLevel = ref(1)
const ZOOM_STEP = 1.25 // 乘法缩放系数
const ZOOM_MIN = 0.05
const ZOOM_MAX = 8

// 图片原始尺寸
const naturalImgW = ref(0)
const naturalImgH = ref(0)

const wrapperDisplayW = computed(() => Math.round(naturalImgW.value * zoomLevel.value) || 1)
const wrapperDisplayH = computed(() => Math.round(naturalImgH.value * zoomLevel.value) || 1)

const levels = [
  { value: 1, label: '轻量' },
  { value: 2, label: '标准' },
  { value: 3, label: '极致' }
]

// 放大倍数
const enhanceScale = ref(1)
const scales = [
  { value: 1, label: '1x' },
  { value: 2, label: '2x' },
  { value: 4, label: '4x' }
]

// 人像优化（纯传统 CV，零模型零网络）：-1 = 未知，0 = 未识别到人像，>0 = 已定位数量
const portraitMode = ref(false)
const portraitSubjects = ref(-1)
const portraitLocate = ref('')   // 定位方式：face / skin / fallback / none

// 人像优化各工序强度（0~2）
const fxControls = [
  { key: 'skin', label: '磨皮' },
  { key: 'sharpen', label: '五官锐化' },
  { key: 'brighten', label: '提亮' },
  { key: 'bgblur', label: '背景虚化' },
  { key: 'vignette', label: '暗角' }
]
const fxVals = reactive({ skin: 1, sharpen: 1, brighten: 1, bgblur: 1, vignette: 1 })

// 最优比例（经验值）：磨皮轻度（0.5 保质感不糊）+ 锐化拉满（1.5 清晰）+ 其余中性偏轻
const FX_BEST = { skin: 0.5, sharpen: 1.5, brighten: 1.0, bgblur: 1.0, vignette: 0.9 }

// 打开人像优化：自动填充最优比例（用户仍可再微调）
function turnOnPortrait() {
  if (!portraitMode.value) {
    Object.keys(FX_BEST).forEach(k => { fxVals[k] = FX_BEST[k] })
  }
  portraitMode.value = true
}
const fxQuery = computed(() =>
  `&skin=${fxVals.skin}&sharpen=${fxVals.sharpen}&brighten=${fxVals.brighten}` +
  `&bgblur=${fxVals.bgblur}&vignette=${fxVals.vignette}`)

// 处理进度状态（模拟进度，后端单接口无真实进度回调）
const progress = ref(0)
const step = ref(1)
const downloading = ref(false)
let progressTimer = null

function startProgress() {
  progress.value = 0
  step.value = 1
  progressTimer = setInterval(() => {
    const p = progress.value
    if (p < 20) {
      step.value = 1
      progress.value = p + 1
    } else if (p < 45) {
      step.value = 2
      progress.value = p + 0.8
    } else if (p < 80) {
      step.value = 3
      progress.value = p + 0.6
    } else if (p < 95) {
      step.value = 4
      progress.value = p + 0.3
    } else {
      clearInterval(progressTimer)
      progressTimer = null
    }
  }, 120)
}

function stopProgress(success = true) {
  clearInterval(progressTimer)
  progressTimer = null
  if (success) {
    progress.value = 100
    step.value = 4
    setTimeout(() => { progress.value = 0 }, 500)
  } else {
    progress.value = 0
  }
}

function stepClass(n) {
  return {
    done: step.value > n,
    active: step.value === n,
    pending: step.value < n
  }
}

let isDragging = false
let isPanning = false
// 平移偏移（translate3d 模式，类似地图拖拽）
const panX = ref(0)
const panY = ref(0)
let panStartX = 0
let panStartY = 0
let panStartPX = 0
let panStartPY = 0

// 上传相关
function pickFile() {
  fileInput.value?.click()
}
function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) handleFile(file)
  e.target.value = ''
}
function onDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}
async function handleFile(file) {
  if (!file || uploading.value) return
  if (!/^image\//.test(file.type)) {
    alert('请上传图片文件')
    return
  }
  uploading.value = true
  try {
    const res = await uploadPhoto(file)
    // 覆盖当前：替换为新图，清空旧增强结果
    if (enhancedUrl.value) URL.revokeObjectURL(enhancedUrl.value)
    enhancedUrl.value = ''
    enhancedSize.value = 0
    portraitSubjects.value = -1
    portraitLocate.value = ''
    uploadId.value = res.upload_id
    photoName.value = res.original_name
    originalSize.value = res.size || file.size || 0
    naturalImgW.value = 0
    naturalImgH.value = 0
    sliderPos.value = 50
    progress.value = 0
    step.value = 1
    centerScroll()
  } catch (err) {
    console.error(err)
    alert('上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// 清除当前图片，回到上传区
function clearPhoto() {
  if (enhancedUrl.value) URL.revokeObjectURL(enhancedUrl.value)
  enhancedUrl.value = ''
  enhancedSize.value = 0
  uploadId.value = ''
  photoName.value = ''
  originalSize.value = 0
  naturalImgW.value = 0
  naturalImgH.value = 0
  sliderPos.value = 50
  progress.value = 0
  step.value = 1
  zoomLevel.value = 1
  centerScroll()
}

// 文件大小格式化
function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function onImgLoaded(e) {
  const img = e.target
  naturalImgW.value = img.naturalWidth
  naturalImgH.value = img.naturalHeight
  calcFitZoom()
}

// 适应屏幕
function calcFitZoom() {
  let attempts = 0
  function tryCalc() {
    attempts++
    requestAnimationFrame(() => {
      if (!previewArea.value) return
      if (!naturalImgW.value || !naturalImgH.value) {
        if (attempts < 10) { setTimeout(tryCalc, 100) }
        return
      }
      const rect = previewArea.value.getBoundingClientRect()
      const availW = rect.width - 32
      const availH = rect.height - 80
      const scaleX = availW / naturalImgW.value
      const scaleY = availH / naturalImgH.value
      zoomLevel.value = Math.max(Math.min(scaleX, scaleY, 1), ZOOM_MIN)
      syncZoomTarget()  // 直接设值后同步动画目标，避免下次滚轮从旧目标开始
    })
  }
  tryCalc()
}

// 居中：重置平移到中心
function centerScroll() {
  panX.value = 0
  panY.value = 0
}

// 更换照片后居中
watch(uploadId, () => nextTick(() => centerScroll()))

// ===== 地图式平滑缩放：目标值 + 每帧插值（滚轮连续映射，缩放带平滑过渡） =====
const ZOOM_SENS = 0.004   // 滚轮灵敏度：缩放倍率 = 2^(-deltaY*sens)，随滚动量连续变化
let zoomTarget = 1        // 动画目标缩放
let panTX = 0, panTY = 0  // 动画目标平移
let zoomRaf = null

function startZoomAnim() {
  if (zoomRaf) return
  const step = () => {
    const k = 0.32  // 每帧插值系数：越大越跟手，越小越顺滑
    if (Math.abs(zoomTarget - zoomLevel.value) < 0.0005 &&
        Math.abs(panTX - panX.value) < 0.4 &&
        Math.abs(panTY - panY.value) < 0.4) {
      zoomLevel.value = zoomTarget
      panX.value = panTX
      panY.value = panTY
      zoomRaf = null
      return
    }
    zoomLevel.value += (zoomTarget - zoomLevel.value) * k
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
    zoomLevel.value = zoomTarget
    panX.value = panTX
    panY.value = panTY
    clampPan()
  }
}

// 把目标值同步为当前值（直接改过 zoomLevel 之后调用，避免动画从旧目标继续跑）
function syncZoomTarget() {
  zoomTarget = zoomLevel.value
  panTX = panX.value
  panTY = panY.value
}

// 以 (clientX, clientY) 为锚点请求缩放：该点下的图像保持不动（地图手感）
function requestZoom(next, clientX, clientY) {
  const el = compareScroll.value
  if (!el) return
  const old = zoomLevel.value
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
  const el = compareScroll.value
  const rect = el ? el.getBoundingClientRect() : { left: 0, top: 0, width: 0, height: 0 }
  requestZoom(next, rect.left + rect.width / 2 + panX.value, rect.top + rect.height / 2 + panY.value)
}
function zoomIn() { zoomCenter(Math.min(zoomLevel.value * ZOOM_STEP, ZOOM_MAX)) }
function zoomOut() { zoomCenter(Math.max(zoomLevel.value / ZOOM_STEP, ZOOM_MIN)) }

// 「适应屏幕」→ 恢复为刚选中照片时的适配比例 + 居中
function zoomReset() {
  stopZoomAnim()
  centerScroll()
  calcFitZoom()
  syncZoomTarget()
}

// 滚轮缩放：连续映射（地图手感，而非 1.25 倍跳变）
function onWheelZoom(e) {
  const f = Math.pow(2, -e.deltaY * ZOOM_SENS)
  const next = e.deltaY > 0
    ? Math.max(zoomLevel.value * f, ZOOM_MIN)
    : Math.min(zoomLevel.value * f, ZOOM_MAX)
  requestZoom(next, e.clientX, e.clientY)
}

async function doEnhance() {
  if (!uploadId.value || enhancing.value) return
  enhancing.value = true
  // 记录本次请求对应的照片，防止增强期间更换图片后被旧结果覆盖
  const reqUploadId = uploadId.value
  startProgress()
  try {
    // 预览模式：返回最大边 2400px 的图，避免浏览器加载超大图崩溃
    const res = await fetch(`/api/photos/enhance/${encodeURIComponent(reqUploadId)}?level=${enhanceLevel.value}&scale=${enhanceScale.value}&preview=1&upload_id=${encodeURIComponent(reqUploadId)}&portrait=${portraitMode.value ? 1 : 0}${portraitMode.value ? fxQuery.value : ''}`)
    if (!res.ok) throw new Error('Enhance failed')
    // 后端返回的人像定位结果（1 = 已定位 N 处，0 = 未识别到，空 = 未知）
    const subj = res.headers.get('X-Portrait-Subjects')
    const pmode = res.headers.get('X-Portrait-Mode')
    if (uploadId.value === reqUploadId && portraitMode.value) {
      portraitSubjects.value = (subj === null || subj === '') ? -1 : parseInt(subj, 10)
      portraitLocate.value = pmode || ''
    }
    const blob = await res.blob()
    // 期间换图了：丢弃旧结果，不覆盖新图
    if (uploadId.value !== reqUploadId) return
    if (enhancedUrl.value) URL.revokeObjectURL(enhancedUrl.value)
    enhancedUrl.value = URL.createObjectURL(blob)
    enhancedSize.value = blob.size
    sliderPos.value = 50
    // 完成扩散波纹
    doneRipple.value++
    stopProgress(true)
  } catch (e) {
    if (uploadId.value === reqUploadId) stopProgress(false)
    console.error(e)
  } finally {
    enhancing.value = false
  }
}

async function downloadEnhanced() {
  if (!uploadId.value || downloading.value) return
  downloading.value = true
  try {
    // 下载时请求全尺寸图（非预览）
    const res = await fetch(`/api/photos/enhance/${encodeURIComponent(uploadId.value)}?level=${enhanceLevel.value}&scale=${enhanceScale.value}&preview=0&upload_id=${encodeURIComponent(uploadId.value)}&portrait=${portraitMode.value ? 1 : 0}${portraitMode.value ? fxQuery.value : ''}`)
    if (!res.ok) throw new Error('Enhance failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const base = (photoName.value || uploadId.value).replace(/\.[^.]+$/, '')
    a.download = `enhanced_${base}.jpg`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch (e) {
    console.error(e)
  } finally {
    downloading.value = false
  }
}

function resetCompare() { sliderPos.value = 50 }

// 对比滑块
function onSliderDown(e) {
  isDragging = true
  document.addEventListener('mousemove', onCompareMove)
  document.addEventListener('mouseup', onSliderUp)
}
function onSliderUp() {
  isDragging = false
  document.removeEventListener('mousemove', onCompareMove)
  document.removeEventListener('mouseup', onSliderUp)
}
function onCompareMove(e) {
  if (!isDragging && e.type === 'mousemove') return
  const rect = compareWrapper.value?.getBoundingClientRect()
  if (!rect) return
  sliderPos.value = Math.max(5, Math.min(95, ((e.clientX - rect.left) / rect.width) * 100))
}
function onCompareTouch(e) {
  const touch = e.touches[0]
  if (!touch) return
  const rect = compareWrapper.value?.getBoundingClientRect()
  if (!rect) return
  sliderPos.value = Math.max(5, Math.min(95, ((touch.clientX - rect.left) / rect.width) * 100))
}

// 平移范围限制（图片不能拖出容器边界）
function clampPan() {
  const el = compareScroll.value
  if (!el) return
  const ww = wrapperDisplayW.value
  const wh = wrapperDisplayH.value
  const cw = el.clientWidth
  const ch = el.clientHeight
  const halfW = Math.max(0, ww - cw) / 2
  const halfH = Math.max(0, wh - ch) / 2
  panX.value = Math.max(-halfW, Math.min(halfW, panX.value))
  panY.value = Math.max(-halfH, Math.min(halfH, panY.value))
}

// 地图风格拖拽：mousedown → 记录起点 → mousemove 更新偏移 → mouseup 停止
function onPanStart(e) {
  const el = compareScroll.value
  if (!el || (wrapperDisplayW.value <= el.clientWidth && wrapperDisplayH.value <= el.clientHeight)) return
  if (e.target.closest('.compare-slider, .zoom-btn, .zoom-toolbar')) return
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

onMounted(() => window.addEventListener('resize', calcFitZoom))
onUnmounted(() => {
  window.removeEventListener('resize', calcFitZoom)
  clearInterval(progressTimer)   // 清理模拟进度定时器，防止切页后仍在跑
  if (zoomRaf) { cancelAnimationFrame(zoomRaf); zoomRaf = null }  // 停止缩放动画帧
  // 兜底：拖拽/滑杆/平移进行中卸载时清理监听，防止泄漏
  document.removeEventListener('mousemove', onCompareMove)
  document.removeEventListener('mouseup', onSliderUp)
  document.removeEventListener('mousemove', onPanMove)
  document.removeEventListener('mouseup', onPanEnd)
})
</script>

<style scoped>
/* ─── 全局 ─── */
.enhance-page {
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
  background: #0c0c12;
  color: #eee;
  overflow: hidden;
}
.enhance-page.light {
  background: #f4f5f9;
  color: #1a1a2e;
}

/* ─── 顶部导航 ─── */
.enhance-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: rgba(16, 16, 24, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.04);
  flex-shrink: 0;
  z-index: 10;
}
.enhance-header.light {
  background: rgba(255,255,255,0.9);
  border-bottom-color: rgba(0,0,0,0.06);
}
.header-left {
  display: flex;
  align-items: center; gap: 16px;
}
.header-logo {
  display: flex; align-items: center; gap: 10px;
}
.logo-icon {
  width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #6c63ff, #5a52e0);
  border-radius: 9px; color: #fff;
}
.logo-icon svg { width: 18px; height: 18px; }
.logo-text h1 {
  font-size: 16px; font-weight: 600; letter-spacing: 0.3px; line-height: 1.2;
}
.logo-sub {
  font-size: 10px; color: rgba(255,255,255,0.25);
  letter-spacing: 1.5px; text-transform: uppercase;
}
.light .logo-sub { color: rgba(0,0,0,0.25); }
.header-breadcrumb {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: rgba(255,255,255,0.3);
  padding: 4px 10px; border-radius: 6px;
  background: rgba(255,255,255,0.04);
}
.header-breadcrumb svg { width: 14px; height: 14px; }
.header-right { display: flex; align-items: center; gap: 10px; }
.level-selector {
  display: flex;
  background: rgba(255,255,255,0.04);
  border-radius: 10px; padding: 3px;
  border: 1px solid rgba(255,255,255,0.06);
}
.light .level-selector {
  background: rgba(0,0,0,0.04);
  border-color: rgba(0,0,0,0.06);
}
.level-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 14px; border: none; background: transparent;
  color: rgba(255,255,255,0.4); font-size: 13px;
  border-radius: 8px; cursor: pointer; transition: all 0.25s;
  font-weight: 500;
}
.light .level-btn { color: rgba(0,0,0,0.4); }
.level-btn:hover { color: rgba(255,255,255,0.7); }
.light .level-btn:hover { color: rgba(0,0,0,0.7); }
.level-btn.active {
  background: #6c63ff; color: #fff;
  box-shadow: 0 2px 8px rgba(108,99,255,0.3);
}
.level-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; opacity: 0.4; }
.level-btn.active .level-dot { opacity: 1; }

/* ─── 主体 ─── */
.enhance-body { flex: 1; display: flex; overflow: hidden; position: relative; }

/* ─── 中间预览区 ─── */
.preview-area {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 0; position: relative; min-width: 0;
  overflow: hidden;
  background: #08080e;
}
.enhance-page.light .preview-area {
  background: #e8e9f0;
}

/* 上传区 */
.upload-zone {
  width: min(520px, 80%);
  min-height: 320px;
  display: flex; align-items: center; justify-content: center;
  border: 2px dashed rgba(255,255,255,0.12);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.25s ease;
  background: rgba(255,255,255,0.02);
  color: rgba(255,255,255,0.3);
}
.upload-zone:hover, .upload-zone.drag-over {
  border-color: #6c63ff;
  background: rgba(108,99,255,0.06);
  color: rgba(255,255,255,0.6);
}
.light .upload-zone {
  border-color: rgba(0,0,0,0.12);
  color: rgba(0,0,0,0.3);
  background: rgba(0,0,0,0.02);
}
.light .upload-zone:hover, .light .upload-zone.drag-over {
  border-color: #6c63ff;
  background: rgba(108,99,255,0.06);
  color: rgba(0,0,0,0.6);
}
.upload-box { text-align: center; padding: 24px; }
.up-icon {
  width: 72px; height: 72px;
  margin: 0 auto 18px;
  border-radius: 50%;
  background: rgba(108,99,255,0.1);
  color: #8b85ff;
  display: flex; align-items: center; justify-content: center;
}
.up-icon svg { width: 34px; height: 34px; }
.upload-box h3 { font-size: 18px; font-weight: 500; margin-bottom: 8px; color: rgba(255,255,255,0.75); }
.light .upload-box h3 { color: rgba(0,0,0,0.75); }
.upload-box p { font-size: 13px; color: rgba(255,255,255,0.35); margin-bottom: 12px; }
.light .upload-box p { color: rgba(0,0,0,0.35); }
.upload-hint {
  display: inline-block; font-size: 11px; color: #8b85ff;
  padding: 4px 12px; border-radius: 20px;
  background: rgba(108,99,255,0.12);
}
.light .upload-hint { color: #6c63ff; background: rgba(108,99,255,0.1); }

/* 当前照片信息条（预览区底部，一行横排紧凑） */
.photo-info-bar {
  align-self: stretch;
  display: flex; align-items: center;
  padding: 8px 16px;
  background: rgba(16, 16, 26, 0.82);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px; color: rgba(255, 255, 255, 0.75);
  min-height: 42px;
  position: relative; z-index: 30;
}
.enhance-page.light .photo-info-bar {
  background: rgba(245, 245, 250, 0.88);
  border-top-color: rgba(0, 0, 0, 0.08);
  color: rgba(0, 0, 0, 0.65);
}
.pib-item { display: flex; align-items: center; gap: 6px; white-space: nowrap; min-width: 0; }
.pib-name { font-weight: 600; color: #fff; max-width: 220px; overflow: hidden; text-overflow: ellipsis; }
.enhance-page.light .pib-name { color: #222; }
.pib-label { opacity: 0.55; }
.pib-sep { width: 1px; height: 14px; background: rgba(255, 255, 255, 0.16); margin: 0 12px; flex-shrink: 0; }
.enhance-page.light .pib-sep { background: rgba(0, 0, 0, 0.12); }
.pib-val { white-space: nowrap; }
.pib-actions { margin-left: auto; display: flex; gap: 8px; flex-shrink: 0; }
.photo-info-bar .mini-btn {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; padding: 5px 10px; border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.14); background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.8); cursor: pointer; transition: all 0.2s;
}
.photo-info-bar .mini-btn svg { width: 13px; height: 13px; }
.photo-info-bar .mini-btn:hover { background: rgba(255, 255, 255, 0.14); }
.photo-info-bar .mini-btn.danger:hover { background: rgba(229, 72, 77, 0.85); border-color: rgba(229, 72, 77, 0.9); color: #fff; }
.enhance-page.light .photo-info-bar .mini-btn {
  border-color: rgba(0, 0, 0, 0.12); background: rgba(0, 0, 0, 0.04); color: rgba(0, 0, 0, 0.7);
}
.enhance-page.light .photo-info-bar .mini-btn:hover { background: rgba(0, 0, 0, 0.1); }
@media (max-width: 980px) {
  .photo-info-bar { flex-wrap: wrap; row-gap: 6px; }
  .pib-name { max-width: 40vw; }
}

/* 空状态 */
.preview-empty {
  text-align: center; color: rgba(255,255,255,0.2);
}
.preview-empty h3 {
  font-size: 16px; font-weight: 500; margin-bottom: 6px;
  color: rgba(255,255,255,0.3);
}
.preview-empty p { font-size: 13px; color: rgba(255,255,255,0.15); }
.light .preview-empty h3 { color: rgba(0,0,0,0.3); }
.light .preview-empty p { color: rgba(0,0,0,0.15); }
.empty-graphic {
  position: relative; width: 100px; height: 100px;
  margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;
}
.empty-ring {
  position: absolute; inset: 0; border-radius: 50%;
  border: 2px dashed rgba(255,255,255,0.06);
  animation: empty-rotate 8s linear infinite;
}
.empty-ring.inner { inset: 15px; animation-duration: 6s; animation-direction: reverse; }
@keyframes empty-rotate { to { transform: rotate(360deg); } }
.empty-icon { width: 44px; height: 44px; opacity: 0.2; position: relative; z-index: 1; }

/* ─── 对比容器 ─── */
.comparison-container {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  width: 100%; min-height: 0; position: relative;
}
.compare-scroll {
  display: flex; align-items: center; justify-content: center;
  width: 100%; flex: 1; overflow: hidden; min-height: 0;
  position: relative;
}
.compare-scroll.zoom-active { cursor: grab; }
.compare-scroll.panning { cursor: grabbing; }

/* 对比标签 */
.compare-labels {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 0; z-index: 15;
  pointer-events: none;
}
.compare-label {
  padding: 4px 16px; font-size: 12px; font-weight: 500;
  letter-spacing: 0.5px; border-radius: 6px;
  backdrop-filter: blur(12px);
}
.label-before {
  background: rgba(0,0,0,0.55);
  color: rgba(255,255,255,0.6);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px 0 0 6px;
}
.label-after {
  background: rgba(108,99,255,0.25);
  color: #b8b0ff;
  border: 1px solid rgba(108,99,255,0.2);
  border-radius: 0 6px 6px 0;
}

.compare-wrapper {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.06), 0 24px 80px rgba(0,0,0,0.5);
  background: #0a0a0f;
  user-select: none; flex-shrink: 0;
  transform-origin: center center;
  will-change: transform;
}
.compare-img {
  display: block; width: 100%; height: 100%;
  object-fit: contain; pointer-events: none;
}
.compare-before-layer {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
}
.compare-before-layer img { max-width: none; width: 100%; height: 100%; object-fit: contain; }
.compare-slider {
  position: absolute; top: 0; bottom: 0; width: 3px;
  background: #fff; cursor: ew-resize; z-index: 10;
  box-shadow: 0 0 12px rgba(0,0,0,0.5);
}
.compare-slider:hover { background: #6c63ff; }
.slider-handle {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 44px; height: 44px; border-radius: 50%;
  background: #fff;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s, box-shadow 0.2s;
}
.compare-slider:hover .slider-handle {
  transform: translate(-50%, -50%) scale(1.1);
  box-shadow: 0 6px 28px rgba(0,0,0,0.6);
}
.slider-handle svg { width: 22px; height: 22px; color: #1a1a2e; }

/* 加载中（多层旋转光圈 + 呼吸光环 + 进度条） */
.enhance-loading {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 22px;
  background: rgba(0,0,0,0.62); backdrop-filter: blur(10px);
  z-index: 20; color: rgba(255,255,255,0.85);
}
.loading-text {
  font-size: 17px; letter-spacing: 1px;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 2px 12px rgba(0,0,0,0.6);
}
/* 进度条 */
.loading-bar {
  width: 240px; height: 5px; border-radius: 4px;
  background: rgba(255,255,255,0.1);
  overflow: hidden;
}
.loading-bar-inner {
  height: 100%; width: 0%;
  background: linear-gradient(90deg, #6c6cff, #b06cff, #ff6c9f);
  background-size: 200% 100%;
  animation: bar-flow 1.2s linear infinite;
  border-radius: 4px;
  transition: width 0.25s ease;
  box-shadow: 0 0 12px rgba(140,110,255,0.7);
}
@keyframes bar-flow { to { background-position: -200% 0; } }

/* 多层光圈动画 */
.fx-rings {
  position: relative;
  width: 150px; height: 150px;
  display: flex; align-items: center; justify-content: center;
}
.fx-ring {
  position: absolute;
  border-radius: 50%;
  border-style: solid;
  border-color: transparent;
}
.fx-ring.r1 {
  inset: 0;
  border-width: 3px;
  border-top-color: #6c6cff;
  border-right-color: #6c6cff44;
  animation: fx-spin 1.4s linear infinite;
}
.fx-ring.r2 {
  inset: 16px;
  border-width: 2.5px;
  border-bottom-color: #b06cff;
  border-left-color: #b06cff44;
  animation: fx-spin 1s linear infinite reverse;
}
.fx-ring.r3 {
  inset: 32px;
  border-width: 2px;
  border-top-color: #ff6c9f;
  border-right-color: #ff6c9f33;
  animation: fx-spin 0.8s linear infinite;
}
@keyframes fx-spin { to { transform: rotate(360deg); } }
/* 中心呼吸星星 */
.fx-core {
  width: 46px; height: 46px;
  display: flex; align-items: center; justify-content: center;
  color: #c9c3ff;
  filter: drop-shadow(0 0 14px rgba(140,110,255,0.9));
  animation: fx-breath 1.6s ease-in-out infinite;
}
.fx-core svg { width: 34px; height: 34px; }
@keyframes fx-breath {
  0%, 100% { transform: scale(0.82); opacity: 0.6; }
  50% { transform: scale(1.12); opacity: 1; }
}

/* 增强完成扩散波纹 */
.done-ripple {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  z-index: 30;
  pointer-events: none;
}
.ripple-circle {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(140, 110, 255, 0.8);
  animation: ripple-out 0.9s ease-out forwards;
}
.ripple-circle.c1 { width: 80px; height: 80px; }
.ripple-circle.c2 { width: 80px; height: 80px; animation-delay: 0.18s; }
@keyframes ripple-out {
  0% { transform: scale(0.4); opacity: 1; }
  100% { transform: scale(4.2); opacity: 0; }
}
.ripple-check {
  display: flex; align-items: center; justify-content: center;
  width: 58px; height: 58px; border-radius: 50%;
  background: linear-gradient(135deg, #4CAF50, #45a049);
  color: #fff; font-size: 30px; font-weight: 700;
  box-shadow: 0 8px 30px rgba(76,175,80,0.55);
  animation: check-pop 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) forwards, check-fade 0.4s ease 1.1s forwards;
}
@keyframes check-pop {
  0% { transform: scale(0); }
  70% { transform: scale(1.15); }
  100% { transform: scale(1); }
}
@keyframes check-fade {
  to { opacity: 0; transform: scale(0.9); }
}

/* 文件大小对比（原始 → 增强） */
.size-compare {
  display: inline-flex; align-items: center; gap: 5px;
}
.size-old { opacity: 0.55; text-decoration: line-through; text-decoration-color: rgba(255,100,100,0.6); font-size: 11px; }
.size-arrow { width: 13px; height: 13px; opacity: 0.4; }
.size-new { color: #7ee787; font-weight: 600; }
.light .size-new { color: #2e9e4f; }
.size-delta {
  font-size: 10px; padding: 1px 7px; border-radius: 8px;
  background: rgba(126,231,135,0.15); color: #7ee787;
}
.size-delta.down { background: rgba(255,120,120,0.15); color: #ff9a9a; }
.light .size-delta { background: rgba(46,158,79,0.12); color: #2e9e4f; }
.light .size-delta.down { background: rgba(220,80,80,0.12); color: #c66; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 处理步骤卡片（右侧面板） */
.progress-steps {
  margin-top: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 10px;
  padding: 8px;
}
.light .progress-steps {
  background: rgba(0,0,0,0.02);
  border-color: rgba(0,0,0,0.05);
}
.progress-step {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
  transition: opacity 0.2s;
}
.progress-step.pending { opacity: 0.35; }
.progress-step.done .step-icon { color: #2ed573; background: rgba(46,213,115,0.12); }
.progress-step.active .step-icon { color: #6c63ff; background: rgba(108,99,255,0.15); }
.step-icon {
  width: 24px; height: 24px; flex-shrink: 0;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: rgba(255,255,255,0.4);
  background: rgba(255,255,255,0.05);
}
.step-icon svg { width: 13px; height: 13px; }
.step-spin { animation: spin 0.9s linear infinite; }
.step-num { font-size: 12px; font-weight: 500; }
.step-name { font-size: 12px; color: rgba(255,255,255,0.7); }
.light .step-name { color: rgba(0,0,0,0.7); }

/* ─── 缩放工具栏（底部居中，类似 PhotoGrid） ─── */
.zoom-toolbar {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px;
  background: rgba(20,20,30,0.8);
  backdrop-filter: blur(16px);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
  position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
  z-index: 15;
}
.zoom-btn {
  width: 30px; height: 30px; border: none;
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.5); border-radius: 6px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.zoom-btn:hover:not(:disabled) { background: rgba(108,99,255,0.15); color: #8b85ff; }
.zoom-btn:disabled { opacity: 0.2; cursor: not-allowed; }
.zoom-btn svg { width: 16px; height: 16px; }
.fit-btn { width: 36px; }
.zoom-info {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: rgba(255,255,255,0.5);
  min-width: 40px; justify-content: center;
}
.zoom-val { font-weight: 600; color: rgba(255,255,255,0.7); font-variant-numeric: tabular-nums; }
.zoom-dim { font-size: 10px; color: rgba(255,255,255,0.25); }
.zoom-divider { width: 1px; height: 20px; background: rgba(255,255,255,0.06); }

/* ─── 右侧控制面板 ─── */
.control-panel {
  width: 260px; flex-shrink: 0;
  background: rgba(16,16,24,0.6);
  border-left: 1px solid rgba(255,255,255,0.04);
  display: flex; flex-direction: column;
  padding: 16px 14px; gap: 12px;
  overflow-y: auto; backdrop-filter: blur(10px);
}
.control-panel.light { background: rgba(255,255,255,0.6); border-left-color: rgba(0,0,0,0.06); }
.control-panel::-webkit-scrollbar { width: 3px; }
.control-panel::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 10px; }

/* 面板卡片 */
.panel-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px; overflow: hidden;
}
.light .panel-card { background: rgba(0,0,0,0.02); border-color: rgba(0,0,0,0.04); }
.panel-card-header {
  display: flex; align-items: center; gap: 7px;
  padding: 12px 14px 8px;
  font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.4);
  letter-spacing: 0.3px; text-transform: uppercase;
}
.light .panel-card-header { color: rgba(0,0,0,0.4); }
.panel-card-header svg { width: 14px; height: 14px; opacity: 0.5; }
.header-actions {
  margin-left: auto; display: flex; align-items: center; gap: 6px;
}
.mini-btn {
  display: flex; align-items: center; gap: 3px;
  padding: 3px 8px; border: none; border-radius: 6px; cursor: pointer;
  background: rgba(108,99,255,0.12); color: #8b85ff;
  font-size: 11px; transition: all 0.2s;
}
.mini-btn:hover { background: rgba(108,99,255,0.22); color: #a8a0ff; }
.mini-btn.danger { background: rgba(255,71,87,0.1); color: #ff7a85; }
.mini-btn.danger:hover { background: rgba(255,71,87,0.2); color: #ff9aa3; }
.mini-btn svg { width: 12px; height: 12px; opacity: 1; }
.panel-card-body { padding: 0 14px 14px; }

/* 信息行 */
.info-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 6px; font-size: 12px;
}
.info-row:last-child { margin-bottom: 0; }
.info-label { color: rgba(255,255,255,0.3); }
.light .info-label { color: rgba(0,0,0,0.3); }
.info-value {
  color: rgba(255,255,255,0.6);
  max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.light .info-value { color: rgba(0,0,0,0.6); }
.level-badge {
  padding: 2px 10px; border-radius: 6px; font-weight: 500;
}
.level-badge.level-1 { background: rgba(76,175,80,0.15); color: #66bb6a; }
.level-badge.level-2 { background: rgba(108,99,255,0.15); color: #8b85ff; }
.level-badge.level-3 { background: rgba(255,152,0,0.15); color: #ffb74d; }

/* 增强按钮 */
.enhance-btn {
  width: 100%; padding: 11px 16px; border: none; border-radius: 10px;
  font-size: 14px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  background: linear-gradient(135deg, #6c63ff, #5a52e0);
  color: #fff; transition: all 0.25s;
}
.enhance-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(108,99,255,0.3);
}
.enhance-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.enhance-btn.completed { background: linear-gradient(135deg, #4CAF50, #45a049); }
.enhance-btn.processing { background: linear-gradient(135deg, #5a52e0, #4a42c0); }
.enhance-btn svg { width: 18px; height: 18px; flex-shrink: 0; }

/* 操作按钮行 */
.action-row {
  display: flex; gap: 8px; margin-top: 10px;
}
.action-btn {
  flex: 1; padding: 9px 12px; border: none; border-radius: 8px;
  font-size: 12px; font-weight: 500; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.25s;
}
.action-btn svg { width: 16px; height: 16px; flex-shrink: 0; }
.download-btn {
  background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.7);
  border: 1px solid rgba(255,255,255,0.08);
}
.light .download-btn { background: rgba(0,0,0,0.04); color: rgba(0,0,0,0.6); border-color: rgba(0,0,0,0.08); }
.download-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.download-btn.busy { opacity: 0.6; cursor: wait; }
.reset-btn {
  background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.4);
  border: 1px solid rgba(255,255,255,0.04);
}
.light .reset-btn { background: rgba(0,0,0,0.02); color: rgba(0,0,0,0.4); border-color: rgba(0,0,0,0.04); }
.reset-btn:hover { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.6); }
.spin { animation: spin 0.8s linear infinite; }

/* 放大倍数选择 */
.scale-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.scale-label { font-size: 12px; color: rgba(255,255,255,0.35); }
.light .scale-label { color: rgba(0,0,0,0.35); }
.scale-selector {
  display: flex; background: rgba(255,255,255,0.04);
  border-radius: 8px; padding: 2px;
  border: 1px solid rgba(255,255,255,0.06);
}
.light .scale-selector { background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.06); }
.scale-btn {
  padding: 4px 12px; border: none; background: transparent;
  color: rgba(255,255,255,0.4); font-size: 12px; font-weight: 500;
  border-radius: 6px; cursor: pointer; transition: all 0.25s;
}
.light .scale-btn { color: rgba(0,0,0,0.4); }
.scale-btn:hover { color: rgba(255,255,255,0.7); }
.light .scale-btn:hover { color: rgba(0,0,0,0.7); }
.scale-btn.active { background: #6c63ff; color: #fff; }

/* 人像优化提示行 */
.portrait-hint {
  font-size: 11px; line-height: 1.5;
  color: rgba(255,255,255,0.32);
  margin: -4px 0 10px;
}
.light .portrait-hint { color: rgba(0,0,0,0.32); }

/* 人像优化强度滑杆 */
.fx-panel {
  margin: -2px 0 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
}
.light .fx-panel { background: rgba(0,0,0,0.02); border-color: rgba(0,0,0,0.05); }
.fx-row { display: flex; align-items: center; gap: 10px; padding: 3px 0; }
.fx-label { width: 56px; font-size: 12px; color: rgba(255,255,255,0.5); flex-shrink: 0; }
.light .fx-label { color: rgba(0,0,0,0.5); }
.fx-range {
  flex: 1 1 0; min-width: 0; -webkit-appearance: none; appearance: none;
  height: 4px; border-radius: 2px;
  background: rgba(255,255,255,0.15); outline: none; cursor: pointer;
}
.light .fx-range { background: rgba(0,0,0,0.12); }
.fx-range::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 14px; height: 14px; border-radius: 50%;
  background: #6c63ff; border: 2px solid #fff; cursor: pointer;
}
.fx-val {
  width: 42px; flex-shrink: 0; text-align: right; font-size: 11px;
  color: rgba(255,255,255,0.6); font-variant-numeric: tabular-nums;
}
.light .fx-val { color: rgba(0,0,0,0.6); }

/* 增强选项（类似 PhotoGrid 的样式） */
.level-option {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 10px;
  cursor: pointer; transition: all 0.2s;
  margin-bottom: 4px;
  border: 1px solid transparent;
}
.level-option:last-child { margin-bottom: 0; }
.level-option:hover {
  background: rgba(255,255,255,0.03);
  border-color: rgba(255,255,255,0.06);
}
.level-option.active {
  background: rgba(108,99,255,0.06);
  border-color: rgba(108,99,255,0.15);
}
.level-option-icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.level-option-icon svg { width: 16px; height: 16px; }
.level-option-icon.green { background: rgba(76,175,80,0.12); color: #66bb6a; }
.level-option-icon.purple { background: rgba(108,99,255,0.12); color: #8b85ff; }
.level-option-icon.orange { background: rgba(255,152,0,0.12); color: #ffb74d; }
.level-option-text { flex: 1; display: flex; flex-direction: column; gap: 1px; }
.level-option-text strong { font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.7); }
.light .level-option-text strong { color: rgba(0,0,0,0.7); }
.level-option-text span { font-size: 11px; color: rgba(255,255,255,0.3); }
.light .level-option-text span { color: rgba(0,0,0,0.3); }
.level-option-check {
  width: 20px; height: 20px; border-radius: 50%;
  background: #6c63ff; display: flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0;
}
.level-option-check svg { width: 12px; height: 12px; }
</style>