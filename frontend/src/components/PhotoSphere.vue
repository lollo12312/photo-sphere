<template>
  <div ref="container" class="sphere-container">
    <!-- 加载 -->
    <div class="loader" :class="{ 'loader-hidden': !showLoader }">
      <div class="spinner"></div>
      <p>加载照片球体...</p>
      <div class="progress-bar">
        <div class="progress-bar-inner" :style="{ width: progress + '%' }"></div>
      </div>
    </div>

    <!-- 信息 -->
    <div class="info">
      <h1>✦ 3D 照片球体</h1>
      <p>拖拽旋转 · 滚轮缩放 · 点击照片查看</p>
    </div>

    <!-- 提示 -->
    <div class="hint">
      <span>🖱 拖拽旋转</span>
      <span>🔍 滚轮缩放</span>
      <span>👆 点击查看</span>
    </div>

    <!-- 控制面板（由全局顶栏「设置」按钮控制） -->
    <div class="panel-overlay" :class="{ active: store.panelOpen }" @click.stop="store.panelOpen = false">
      <div class="panel" :class="{ active: store.panelOpen }" @click.stop>
        <h3>控制面板</h3>
        <div class="panel-item">
          <label>粒子</label>
          <button class="panel-toggle" :class="{ on: showParticles }" @click="toggleParticles">{{ showParticles ? '开' : '关' }}</button>
        </div>
        <div class="panel-item">
          <label>流星雨</label>
          <button class="panel-toggle" :class="{ on: store.meteorEnabled }" @click="toggleMeteor">{{ store.meteorEnabled ? '开' : '关' }}</button>
        </div>
        <div class="panel-item">
          <label>主题</label>
          <button class="panel-toggle" @click="toggleTheme">{{ store.darkTheme ? '暗色' : '亮色' }}</button>
        </div>
        <div class="panel-item">
          <label>照片数量</label>
          <div class="panel-count">
            <button @click="changeCount(-5)" :disabled="sphereCount <= SPHERE_COUNT_MIN">−</button>
            <span>{{ sphereCount }}</span>
            <button @click="changeCount(5)" :disabled="sphereCount >= SPHERE_COUNT_MAX">+</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 幻灯片按钮 -->
    <button class="slideshow-btn" :class="{ active: slideshowActive }" @click.stop="toggleSlideshow">
      <svg v-if="!slideshowActive" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
      <svg v-else viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
    </button>

    <!-- 背景暗角效果 -->
    <div class="vignette"></div>

    <!-- 模态框 -->
    <div class="modal-overlay" :class="{ active: showModal }" @click="closeOnBg">
      <img v-if="modalImg" class="modal-bg" :src="modalBgSrc" alt="" aria-hidden="true" />
      <div class="modal-content" :class="{ active: showModal }">
        <div class="modal-img-wrapper" ref="modalImgWrapper" @wheel="onModalWheel">
          <img
            v-if="modalImg"
            :src="modalImg"
            alt="photo"
            ref="modalImgEl"
            :style="modalImgStyle"
            @mousedown="onModalDragStart"
          />
        </div>
        <button class="modal-prev" @click.stop="prevPhoto">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="modal-next" @click.stop="nextPhoto">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
      <button class="modal-close" @click="closeModal">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { fetchPhotoList, getFullPhotoUrl, getThumbnailUrl } from '../api/photos'
import { store } from '../store'

// ─── 状态 ───────────────────────────────────────
const container = ref(null)
const loading = ref(true)
const showLoader = ref(true)
const progress = ref(0)
const showModal = ref(false)
const modalImg = ref('')
const modalImgEl = ref(null)
const modalImgWrapper = ref(null)
const modalZoom = ref(1)
const modalPanX = ref(0)
const modalPanY = ref(0)
const modalIndex = ref(-1)
const showParticles = ref(true)
const slideshowActive = ref(false)
let slideshowTimer = null
let particlesMesh = null

const modalImgStyle = computed(() => ({
  transform: `translate(calc(-50% + ${modalPanX.value}px), calc(-50% + ${modalPanY.value}px)) scale(${modalZoom.value})`,
  cursor: modalZoom.value > 1 ? 'grab' : 'default'
}))

// 弹窗模糊背景：用当前照片的缩略图即可
const modalBgSrc = computed(() => {
  const f = photoFiles[modalIndex.value]
  return f ? getThumbnailUrl(f) : ''
})
const SPHERE_RADIUS = 6.2

// ─── Three.js 变量 ──────────────────────────────
let scene, camera, renderer, controls
let photoMeshes = []
let raycaster, pointer
let hoveredObject = null
let photoFiles = []
let animFrameId = null
let bgTexture = null
let lastBgFile = null

// ─── 初始化场景 ─────────────────────────────────
function initScene() {
  scene = new THREE.Scene()
  // 背景随「昼夜替换」主题：深空(暗色) / 浅空(亮色)
  scene.background = new THREE.Color(store.darkTheme ? 0x0a0a0f : 0xe9e8f0)

  // 尺寸取容器（= 顶栏之下的剩余高度），而不是 window，避免整页滚动 / 球心偏移
  const cw0 = (container.value && container.value.clientWidth) || window.innerWidth
  const ch0 = (container.value && container.value.clientHeight) || window.innerHeight
  camera = new THREE.PerspectiveCamera(55, cw0 / ch0, 0.1, 100)
  camera.position.set(0, 0, 20)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(cw0, ch0)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  container.value.prepend(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.12
  controls.minDistance = 1.8
  controls.maxDistance = 35
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.3
  controls.zoomSpeed = 0.8
  controls.rotateSpeed = 0.6
  controls.target.set(0, 0, 0)

  const ambient = new THREE.AmbientLight(0xffffff, 0.5)
  scene.add(ambient)
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.8)
  dirLight.position.set(5, 10, 7)
  scene.add(dirLight)
  const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.5)
  dirLight2.position.set(-5, -3, -5)
  scene.add(dirLight2)
  const rimLight = new THREE.DirectionalLight(0xffffff, 0.3)
  rimLight.position.set(-3, 5, -8)
  scene.add(rimLight)

  // 粒子
  const count = 800
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count * 3; i++) positions[i] = (Math.random() - 0.5) * 60
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const mat = new THREE.PointsMaterial({
    size: 0.06, color: 0x8888ff, transparent: true, opacity: 0.5,
    blending: THREE.AdditiveBlending, sizeAttenuation: true
  })
  particlesMesh = new THREE.Points(geo, mat)
  scene.add(particlesMesh)

  raycaster = new THREE.Raycaster()
  pointer = new THREE.Vector2()

  renderer.domElement.addEventListener('pointermove', onPointerMove)
  renderer.domElement.addEventListener('click', onClick)
  window.addEventListener('resize', onResize)
  document.addEventListener('keydown', onKeydown)
}

// ─── 创建照片球体 ───────────────────────────────
async function createPhotoSphere() {
  const gen = ++sphereGen  // 本批次代数
  const group = new THREE.Group()
  const positions = []
  const goldenRatio = (1 + Math.sqrt(5)) / 2

  for (let i = 0; i < photoFiles.length; i++) {
    const theta = Math.acos(1 - 2 * (i + 0.5) / photoFiles.length)
    const phi = 2 * Math.PI * i / goldenRatio
    positions.push({
      x: SPHERE_RADIUS * Math.sin(theta) * Math.cos(phi),
      y: SPHERE_RADIUS * Math.sin(theta) * Math.sin(phi),
      z: SPHERE_RADIUS * Math.cos(theta)
    })
  }

  // 并发加载控制：最多同时加载 6 张
  const MAX_CONCURRENT = 6
  const loadQueue = [...positions.keys()]
  let loaded = 0

  const loadNext = () => {
    if (loadQueue.length === 0) return Promise.resolve()
    const idx = loadQueue.shift()
    const pos = positions[idx]

    return new Promise((resolve) => {
      const file = photoFiles[idx % photoFiles.length]
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => {
        // 球体已被重建（数量调整），丢弃这张过期照片
        if (gen !== sphereGen) { resolve(); return }
        const texture = new THREE.Texture(img)
        texture.minFilter = THREE.LinearFilter
        texture.magFilter = THREE.LinearFilter
        texture.generateMipmaps = false
        texture.colorSpace = THREE.SRGBColorSpace
        texture.needsUpdate = true

        const aspect = img.naturalWidth / img.naturalHeight
        const planeW = 1.9
        const planeH = planeW / aspect

        const geo = new THREE.PlaneGeometry(planeW, planeH)
        const mat = new THREE.MeshStandardMaterial({
          map: texture, roughness: 0.2, metalness: 0.02,
          side: THREE.DoubleSide
        })
        const mesh = new THREE.Mesh(geo, mat)
        mesh.position.set(pos.x, pos.y, pos.z)
        mesh.lookAt(0, 0, 0)
        mesh.userData = { index: idx % photoFiles.length, img }

        group.add(mesh)
        photoMeshes.push(mesh)

        loaded++
        progress.value = Math.round((loaded / photoFiles.length) * 100)
        resolve()
      }
      img.onerror = () => resolve()
      img.src = `/api/photos/thumbnail/${encodeURIComponent(file)}`
    }).then(loadNext)
  }

  // 启动并发加载
  const initial = Array.from({ length: Math.min(MAX_CONCURRENT, loadQueue.length) }, loadNext)
  await Promise.all(initial)

  // 本批次已被更新的重建取代：收尾（加场景 / 关加载器）交给新批次，避免提前关掉加载动画
  if (gen !== sphereGen) return

  scene.add(group)
  // 先渲染一帧再淡出加载器，避免闪光
  renderer.render(scene, camera)
  loading.value = false
  setTimeout(() => { showLoader.value = false }, 600)
}

// ─── 交互 ───────────────────────────────────────
function onPointerMove(event) {
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)
  const intersects = raycaster.intersectObjects(photoMeshes)

  if (hoveredObject && hoveredObject !== (intersects.length ? intersects[0].object : null)) {
    hoveredObject.scale.set(1, 1, 1)
    hoveredObject = null
    renderer.domElement.style.cursor = 'default'
  }
  if (intersects.length > 0) {
    const obj = intersects[0].object
    if (obj !== hoveredObject) {
      hoveredObject = obj
      obj.scale.set(1.12, 1.12, 1.12)
      renderer.domElement.style.cursor = 'pointer'
    }
  }
}

function onClick() {
  raycaster.setFromCamera(pointer, camera)
  const intersects = raycaster.intersectObjects(photoMeshes)
  if (intersects.length > 0) {
    openPhotoByMesh(intersects[0].object)
  }
}

function openPhotoByMesh(mesh) {
  const filename = photoFiles[mesh.userData.index]
  if (!filename) return

  // 幻灯片播放中点击 → 停止自动播放
  if (slideshowActive.value) {
    stopSlideshow()
  }

  controls.autoRotate = false
  modalIndex.value = mesh.userData.index
  modalImg.value = getFullPhotoUrl(filename)
  resetModalView()
  showModal.value = true
  setBackground(filename)
}

function switchPhoto(delta) {
  const len = photoFiles.length
  modalIndex.value = ((modalIndex.value + delta) % len + len) % len
  const filename = photoFiles[modalIndex.value]
  modalImg.value = getFullPhotoUrl(filename)
  resetModalView()
  setBackground(filename)
  // 更新球体高亮
  if (photoMeshes[modalIndex.value]) {
    photoMeshes[modalIndex.value].scale.set(1.12, 1.12, 1.12)
  }
}

function prevPhoto() { switchPhoto(-1) }
function nextPhoto() { switchPhoto(1) }

function onKeydown(e) {
  if (e.key === 'Escape') { closeModal(); store.panelOpen = false; stopSlideshow() }
  if (showModal.value) {
    if (e.key === 'ArrowLeft') switchPhoto(-1)
    if (e.key === 'ArrowRight') switchPhoto(1)
  }
  if (e.key === ' ') { e.preventDefault(); toggleSlideshow() }
}

function closeOnBg(e) {
  if (e.target.classList.contains('modal-overlay')) closeModal()
}

function closeModal() {
  stopModalZoomAnim()  // 关闭时停掉缩放动画帧
  showModal.value = false
  controls.autoRotate = true
  // 重置球体高亮
  photoMeshes.forEach(m => m.scale.set(1, 1, 1))
}

// ─── 模态框缩放 + 拖拽（地图式：光标锚定 + 指数连续映射 + 每帧插值平滑 + 边界约束） ───
const MODAL_ZOOM_MIN = 0.3
const MODAL_ZOOM_MAX = 10
const MODAL_ZOOM_SENS = 0.004   // 滚轮灵敏度：缩放倍率 = 2^(-deltaY*sens)，随滚动量连续变化
let modalZoomTarget = 1
let modalPanTX = 0, modalPanTY = 0
let modalZoomRaf = null

function resetModalView() {
  stopModalZoomAnim()
  modalZoom.value = 1
  modalPanX.value = 0
  modalPanY.value = 0
  modalZoomTarget = 1
  modalPanTX = 0
  modalPanTY = 0
}

function clampModalPan() {
  const img = modalImgEl.value
  const wrap = modalImgWrapper.value
  if (!img || !wrap) return
  const halfW = Math.max(0, img.clientWidth * modalZoom.value - wrap.clientWidth) / 2
  const halfH = Math.max(0, img.clientHeight * modalZoom.value - wrap.clientHeight) / 2
  modalPanX.value = Math.max(-halfW, Math.min(halfW, modalPanX.value))
  modalPanY.value = Math.max(-halfH, Math.min(halfH, modalPanY.value))
}

function startModalZoomAnim() {
  if (modalZoomRaf) return
  const step = () => {
    const k = 0.32  // 每帧插值系数：越大越跟手，越小越顺滑
    if (Math.abs(modalZoomTarget - modalZoom.value) < 0.001 &&
        Math.abs(modalPanTX - modalPanX.value) < 0.4 &&
        Math.abs(modalPanTY - modalPanY.value) < 0.4) {
      modalZoom.value = modalZoomTarget
      modalPanX.value = modalPanTX
      modalPanY.value = modalPanTY
      modalZoomRaf = null
      return
    }
    modalZoom.value += (modalZoomTarget - modalZoom.value) * k
    modalPanX.value += (modalPanTX - modalPanX.value) * k
    modalPanY.value += (modalPanTY - modalPanY.value) * k
    clampModalPan()
    modalZoomRaf = requestAnimationFrame(step)
  }
  modalZoomRaf = requestAnimationFrame(step)
}

function stopModalZoomAnim() {
  if (modalZoomRaf) {
    cancelAnimationFrame(modalZoomRaf)
    modalZoomRaf = null
    modalZoom.value = modalZoomTarget
    modalPanX.value = modalPanTX
    modalPanY.value = modalPanTY
    clampModalPan()
  }
}

// 以光标为锚点请求缩放：光标下的图像点保持不动（地图手感）
// 图片是 top/left:50% + translate(-50% + pan) scale(zoom)，图片中心与容器中心重合，
// 因此锚点 = 光标相对「容器中心」的偏移（不能用 (容器宽-图片宽)/2，那会多减半个图片宽）
function requestModalZoom(next, clientX, clientY) {
  const wrap = modalImgWrapper.value
  if (!wrap) return
  const old = modalZoom.value
  if (next === old) return
  const rect = wrap.getBoundingClientRect()
  const cx = (clientX - rect.left) - rect.width / 2
  const cy = (clientY - rect.top) - rect.height / 2
  const ratio = next / old
  modalPanTX = cx - (cx - modalPanX.value) * ratio
  modalPanTY = cy - (cy - modalPanY.value) * ratio
  modalZoomTarget = next
  startModalZoomAnim()
}

function onModalWheel(e) {
  e.preventDefault()
  const f = Math.pow(2, -e.deltaY * MODAL_ZOOM_SENS)
  const next = e.deltaY > 0
    ? Math.max(modalZoom.value * f, MODAL_ZOOM_MIN)
    : Math.min(modalZoom.value * f, MODAL_ZOOM_MAX)
  requestModalZoom(next, e.clientX, e.clientY)
}

let modalDragging = false, modalDragStartX = 0, modalDragStartY = 0
let modalPanStartX = 0, modalPanStartY = 0

function onModalDragStart(e) {
  if (modalZoom.value <= 1) return
  stopModalZoomAnim()  // 拖拽时立即落到目标位置，避免缩放动画与拖拽互相干扰
  modalDragging = true
  modalDragStartX = e.clientX
  modalDragStartY = e.clientY
  modalPanStartX = modalPanX.value
  modalPanStartY = modalPanY.value
  document.addEventListener('mousemove', onModalDragMove)
  document.addEventListener('mouseup', onModalDragEnd)
}

function onModalDragMove(e) {
  if (!modalDragging) return
  modalPanX.value = modalPanStartX + (e.clientX - modalDragStartX)
  modalPanY.value = modalPanStartY + (e.clientY - modalDragStartY)
}

function onModalDragEnd() {
  modalDragging = false
  document.removeEventListener('mousemove', onModalDragMove)
  document.removeEventListener('mouseup', onModalDragEnd)
  clampModalPan()  // 松手后把图片收回边界内
}

// ─── 幻灯片播放 ─────────────────────────────────
function toggleSlideshow() {
  if (slideshowActive.value) {
    stopSlideshow()
  } else {
    startSlideshow()
  }
}

function startSlideshow() {
  slideshowActive.value = true
  controls.autoRotate = true
  slideshowTimer = setInterval(() => {
    const len = photoFiles.length
    const idx = Math.floor(Math.random() * len)
    setBackground(photoFiles[idx])
  }, 10000)
}

function stopSlideshow() {
  slideshowActive.value = false
  if (slideshowTimer) {
    clearInterval(slideshowTimer)
    slideshowTimer = null
  }
}

// ─── 控制面板 ───────────────────────────────────
function toggleParticles() {
  showParticles.value = !showParticles.value
  if (particlesMesh) particlesMesh.visible = showParticles.value
}

function toggleTheme() {
  store.darkTheme = !store.darkTheme
}

function toggleMeteor() {
  store.meteorEnabled = !store.meteorEnabled
}

// ─── 照片数量 / 随机抽样 ─────────────────────────
const SPHERE_COUNT_MIN = 10
const SPHERE_COUNT_MAX = 200
const SPHERE_COUNT_KEY = 'sphere-photo-count'
// 从 localStorage 读回上次设定的数量（刷新 / 重开页面后保留）
function loadSphereCount() {
  try {
    const n = Number(localStorage.getItem(SPHERE_COUNT_KEY))
    if (n >= SPHERE_COUNT_MIN && n <= SPHERE_COUNT_MAX) return n
  } catch { /* 隐私模式等场景下忽略 */ }
  return store.spherePhotoCount || 60
}
const sphereCount = ref(loadSphereCount())
let photoPool = []  // 电脑库照片池（球体只取电脑照片，不含 手机照片/）
let sphereGen = 0   // 球体重建代数：重建时自增，过期异步加载直接丢弃，防止新旧子集照片混入

// 电脑照片超过设定数量时，随机抽取子集构成球体
function sampleSpherePhotos(pool) {
  if (pool.length <= sphereCount.value) return [...pool]
  const arr = [...pool]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr.slice(0, sphereCount.value)
}

function changeCount(delta) {
  const next = Math.max(SPHERE_COUNT_MIN, Math.min(SPHERE_COUNT_MAX, sphereCount.value + delta))
  if (next === sphereCount.value) return
  sphereCount.value = next
  store.spherePhotoCount = next
  try { localStorage.setItem(SPHERE_COUNT_KEY, String(next)) } catch { /* 忽略写入失败 */ }
  rebuildSphere()
}

// 数量变化后重建球体（重新随机抽样 + 重排分布）
async function rebuildSphere() {
  const wasSlideshow = slideshowActive.value
  stopSlideshow()
  closeModal()
  for (const m of photoMeshes) {
    scene.remove(m)
    m.geometry.dispose()
    m.material.dispose()
    m.material.map?.dispose()
  }
  photoMeshes = []
  photoFiles = sampleSpherePhotos(photoPool)
  if (photoFiles.length === 0) photoFiles = ['placeholder']
  progress.value = 0
  createPhotoSphere()
  if (wasSlideshow) startSlideshow()
  if (photoFiles.length > 0) {
    setBackground(photoFiles[Math.floor(Math.random() * photoFiles.length)])
  }
}

function onResize() {
  const w = (container.value && container.value.clientWidth) || window.innerWidth
  const h = (container.value && container.value.clientHeight) || window.innerHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

// ─── 背景纹理 ───────────────────────────────────

function setBackground(filename) {
  lastBgFile = filename
  const url = getFullPhotoUrl(filename)
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    // 用 canvas 绘制照片 + 四边留空，直接作为 scene.background
    const canvas = document.createElement('canvas')
    const cw = window.innerWidth
    const ch = window.innerHeight
    const NAV_H = 56 // 底部导航栏高度
    canvas.width = cw
    canvas.height = ch
    const ctx = canvas.getContext('2d')

    // 底色随主题（暗色深空 / 亮色浅空）
    ctx.fillStyle = store.darkTheme ? '#0a0a0f' : '#e9e8f0'
    ctx.fillRect(0, 0, cw, ch)

    // 有效区域：排除底部导航栏
    const effH = ch - NAV_H
    const margin = 0.025
    const imgW = cw * (1 - margin * 2)
    const imgH = effH * (1 - margin * 2)
    const aspect = img.naturalWidth / img.naturalHeight
    let drawW, drawH
    if (aspect > imgW / imgH) {
      drawW = imgW
      drawH = imgW / aspect
    } else {
      drawH = imgH
      drawW = imgH * aspect
    }
    const dx = (cw - drawW) / 2
    const dy = (effH - drawH) / 2

    // 阴影层（立体投影）
    ctx.shadowColor = 'rgba(0,0,0,0.5)'
    ctx.shadowBlur = 40
    ctx.shadowOffsetX = 0
    ctx.shadowOffsetY = 8

    // 圆角矩形裁剪
    const radius = 16
    ctx.beginPath()
    ctx.moveTo(dx + radius, dy)
    ctx.lineTo(dx + drawW - radius, dy)
    ctx.quadraticCurveTo(dx + drawW, dy, dx + drawW, dy + radius)
    ctx.lineTo(dx + drawW, dy + drawH - radius)
    ctx.quadraticCurveTo(dx + drawW, dy + drawH, dx + drawW - radius, dy + drawH)
    ctx.lineTo(dx + radius, dy + drawH)
    ctx.quadraticCurveTo(dx, dy + drawH, dx, dy + drawH - radius)
    ctx.lineTo(dx, dy + radius)
    ctx.quadraticCurveTo(dx, dy, dx + radius, dy)
    ctx.closePath()
    ctx.clip()

    ctx.drawImage(img, dx, dy, drawW, drawH)

    if (bgTexture) bgTexture.dispose()
    bgTexture = new THREE.CanvasTexture(canvas)
    bgTexture.minFilter = THREE.LinearFilter
    bgTexture.magFilter = THREE.LinearFilter
    bgTexture.colorSpace = THREE.SRGBColorSpace
    scene.background = bgTexture
  }
  img.src = url
}

// 主题切换时重绘背景（有幻灯片背景就重画，否则切纯色）
function applyThemeBg() {
  if (!scene) return
  if (lastBgFile) {
    setBackground(lastBgFile)
  } else {
    if (bgTexture) { bgTexture.dispose(); bgTexture = null }
    scene.background = new THREE.Color(store.darkTheme ? 0x0a0a0f : 0xe9e8f0)
  }
}
watch(() => store.darkTheme, applyThemeBg)

// ─── 动画循环 ───────────────────────────────────
function animate() {
  animFrameId = requestAnimationFrame(animate)
  controls.update()

  if (controls.autoRotate && hoveredObject) {
    hoveredObject.scale.set(1, 1, 1)
    hoveredObject = null
    renderer.domElement.style.cursor = 'default'
  }
  renderer.render(scene, camera)
}

// ─── 生命周期 ───────────────────────────────────
onMounted(async () => {
  try {
    if (store.photoList.length > 0) {
      photoPool = store.photoList.filter(f => !f.startsWith('手机照片/'))
    } else {
      const list = await fetchPhotoList()
      store.photoList = list
      photoPool = list.filter(f => !f.startsWith('手机照片/'))
    }
    // 只展示电脑库照片；超出设定数量时随机抽样子集
    // 抽样结果做会话缓存：照片总数未变时复用上次子集（切页往返更快、子集稳定不随机跳变）
    if (store.sphereSampleCache && store.sphereSampleCache.total === photoPool.length) {
      photoFiles = store.sphereSampleCache.files
    } else {
      photoFiles = sampleSpherePhotos(photoPool)
      store.sphereSampleCache = { total: photoPool.length, files: photoFiles }
    }
    if (photoFiles.length === 0) photoFiles = ['placeholder']
  } catch {
    photoFiles = ['placeholder']
  }

  initScene()
  await createPhotoSphere()
  animate()

  // 首次加载随机选一张作为背景
  if (photoFiles.length > 0) {
    const randIdx = Math.floor(Math.random() * photoFiles.length)
    setBackground(photoFiles[randIdx])
  }

  // 处理从其他页面跳转过来的照片
  if (store.navigateToSphere && store.currentPhoto) {
    const idx = photoFiles.indexOf(store.currentPhoto)
    if (idx >= 0) {
      const mesh = photoMeshes[idx]
      if (mesh) {
        openPhotoByMesh(mesh)
      }
    }
    store.navigateToSphere = false
  }
})

onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
  if (slideshowTimer) clearInterval(slideshowTimer)  // 清理幻灯片定时器，防止切页后仍在跑
  document.removeEventListener('mousemove', onModalDragMove)
  document.removeEventListener('mouseup', onModalDragEnd)
  renderer?.dispose()
  window.removeEventListener('resize', onResize)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.sphere-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

/* 加载（只在球体内容区内遮罩，顶部导航保持常驻，不随球体一起加载） */
.loader {
  position: absolute; inset: 0; z-index: 20;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: #0a0a0f;
  transition: opacity 0.6s ease;
}
.loader-hidden {
  opacity: 0;
  pointer-events: none;
}
.loader .spinner {
  width: 48px; height: 48px;
  border: 3px solid rgba(255,255,255,0.08);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.loader p {
  margin-top: 20px; font-size: 14px; color: rgba(255,255,255,0.4);
  letter-spacing: 1px;
}
.progress-bar {
  margin-top: 16px; width: 200px; height: 3px;
  background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden;
}
.progress-bar-inner {
  height: 100%; width: 0%;
  background: linear-gradient(90deg, #6c6cff, #ff6c9f);
  border-radius: 2px; transition: width 0.3s ease;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 背景暗角 */
.vignette {
  position: fixed; inset: 0; z-index: 5;
  pointer-events: none;
  background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.6) 100%);
  opacity: 0.7;
}

/* 信息：左下角，与背景照片左边对齐（canvas 内照片左边缘 = 视口 2.5% 处）；标题+副标题并排一行 */
.info {
  position: fixed;
  left: 2.5vw;
  bottom: 30px;
  z-index: 10;
  display: flex;
  align-items: baseline;
  gap: 14px;
  max-width: 60vw;
  text-align: left;
  pointer-events: none;
  opacity: 0;
  animation: fadeIn 1s ease 0.5s forwards;
}
.info h1 {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
  background: linear-gradient(135deg, #f5f5f7, #a0a0b0);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.info p {
  font-size: 14px;
  color: rgba(255,255,255,0.45);
  margin-top: 0;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

/* 提示 */
.hint {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 10; font-size: 13px; color: rgba(255,255,255,0.3);
  text-align: center; pointer-events: none; opacity: 0;
  animation: fadeIn 1s ease 1s forwards; letter-spacing: 0.5px;
}
.hint span { display: inline-block; margin: 0 12px; }
@keyframes fadeIn { to { opacity: 1; } }

/* 幻灯片按钮 */
.slideshow-btn {
  position: fixed; bottom: 24px; right: 24px; z-index: 20;
  width: 48px; height: 48px; border-radius: 50%;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.1);
  color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; animation: fadeIn 1s ease 1.5s forwards;
  transition: all 0.3s ease;
}
.slideshow-btn:hover { background: rgba(255,255,255,0.15); transform: scale(1.08); }
.slideshow-btn.active { background: #6c63ff; border-color: #6c63ff; }
.slideshow-btn svg { width: 22px; height: 22px; }

/* 控制面板 */
.panel-overlay {
  position: fixed; inset: 0; z-index: 150;
  background: rgba(0,0,0,0.3);
  backdrop-filter: blur(4px);
  opacity: 0; pointer-events: none; transition: opacity 0.3s ease;
}
.panel-overlay.active { opacity: 1; pointer-events: auto; }
.panel {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: #14141e; border-radius: 20px 20px 0 0;
  padding: 24px 24px 80px;
  transform: translateY(100%); transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 151;
}
.panel.active { transform: translateY(0); }
.panel h3 { font-size: 16px; font-weight: 600; margin-bottom: 20px; color: #eee; }
.panel-item {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.panel-item label { font-size: 14px; color: #999; }
.panel-toggle {
  padding: 6px 16px; border-radius: 20px;
  border: 1px solid #2a2a3a; background: #1a1a2a;
  color: #999; font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.panel-toggle.on { background: #6c63ff; color: #fff; border-color: #6c63ff; }
.panel-toggle:hover { opacity: 0.8; }
.panel-count {
  display: flex; align-items: center; gap: 12px;
}
.panel-count button {
  width: 30px; height: 30px; border-radius: 50%;
  border: 1px solid #2a2a3a; background: #1a1a2a;
  color: #eee; font-size: 16px; line-height: 1; cursor: pointer; transition: all 0.2s;
}
.panel-count button:hover:not(:disabled) { background: #6c63ff; border-color: #6c63ff; }
.panel-count button:disabled { opacity: 0.3; cursor: not-allowed; }
.panel-count span {
  min-width: 44px; text-align: center;
  font-size: 15px; color: #eee; font-weight: 600;
}

/* 模态框 */
.modal-overlay {
  position: fixed; inset: 0; z-index: 400;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.45);
  opacity: 0; pointer-events: none; transition: opacity 0.5s ease;
}
.modal-overlay.active { opacity: 1; pointer-events: auto; }

/* 弹窗模糊背景：当前照片模糊铺满 */
.modal-bg {
  position: absolute;
  inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  filter: blur(24px) saturate(1.25);
  transform: scale(1.2);
}

.modal-content {
  position: relative;
  z-index: 1;
  max-width: 80vw; max-height: 80vh;
  transform: scale(0.85) translateY(20px);
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-content.active { transform: scale(1) translateY(0); }
.modal-img-wrapper {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  max-width: 80vw; max-height: 80vh;
  width: 80vw; height: 80vh;
  display: flex; align-items: center; justify-content: center;
}
.modal-img-wrapper img {
  position: absolute;
  top: 50%; left: 50%;
  max-width: 90%; max-height: 90%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
  transition: none;
  border-radius: 8px;
}

/* 模态框左右切换按钮 */
.modal-prev, .modal-next {
  position: fixed; top: 50%; transform: translateY(-50%);
  z-index: 410; width: 48px; height: 48px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s ease; opacity: 0; pointer-events: none;
}
.modal-overlay.active .modal-prev,
.modal-overlay.active .modal-next { opacity: 1; pointer-events: auto; }
.modal-prev:hover, .modal-next:hover {
  background: rgba(255,255,255,0.2); transform: translateY(-50%) scale(1.08);
}
.modal-prev { left: 24px; }
.modal-next { right: 24px; }
.modal-prev svg, .modal-next svg { width: 24px; height: 24px; }

.modal-close {
  position: fixed; top: 64px; right: 24px; z-index: 410;
  width: 44px; height: 44px; border-radius: 50%;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s ease; opacity: 0; pointer-events: none;
}
.modal-overlay.active .modal-close { opacity: 1; pointer-events: auto; }
.modal-close:hover { background: rgba(255,255,255,0.2); transform: scale(1.08); }
.modal-close svg { width: 20px; height: 20px; }

@media (max-width: 768px) {
  .info h1 { font-size: 18px; }
  .info p { font-size: 12px; }
  .info { bottom: 26px; }
  .hint { font-size: 11px; bottom: 64px; }  /* 上移避开左下角标题 */
  .hint span { margin: 0 8px; }
  .modal-content { max-width: 92vw; max-height: 70vh; }
  .modal-img-wrapper { max-width: 92vw; max-height: 70vh; }
  .modal-img-wrapper img { max-width: 92vw; max-height: 70vh; }
  .modal-prev, .modal-next { width: 36px; height: 36px; }
  .modal-prev { left: 12px; }
  .modal-next { right: 12px; }
}
</style>

<style>
/* ===== 亮色主题（昼夜替换）：球体页 UI 翻亮；3D 场景底色由 JS（scene.background）切换 ===== */
.app-shell.light .sphere-container { background: #e9e8f0; }
.app-shell.light .vignette { opacity: 0.35; }
.app-shell.light .info h1 { background: linear-gradient(135deg, #3f3f4b, #8a8a9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.app-shell.light .info p { color: rgba(30, 30, 40, 0.5); }
.app-shell.light .hint { color: rgba(30, 30, 40, 0.42); }
.app-shell.light .slideshow-btn { background: rgba(0, 0, 0, 0.06); border-color: rgba(0, 0, 0, 0.1); color: #33343c; }
.app-shell.light .slideshow-btn:hover { background: rgba(0, 0, 0, 0.12); }
.app-shell.light .slideshow-btn.active { background: #6c63ff; border-color: #6c63ff; color: #fff; }
.app-shell.light .panel { background: #f7f7fb; border-top: 1px solid rgba(0, 0, 0, 0.08); }
.app-shell.light .panel h3 { color: #26272e; }
.app-shell.light .panel-item label { color: #6a6b76; }
.app-shell.light .panel-toggle { border-color: rgba(0, 0, 0, 0.12); background: #fff; color: #565763; }
.app-shell.light .panel-toggle.on { background: #6c63ff; border-color: #6c63ff; color: #fff; }
.app-shell.light .panel-count button { border-color: rgba(0, 0, 0, 0.12); background: #fff; color: #26272e; }
.app-shell.light .panel-count span { color: #26272e; }
</style>