<template>
  <div ref="container" class="meteor-container" :class="{ hidden: !store.meteorEnabled }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { store } from '../store'

const container = ref(null)

// 配置
const METEOR_COUNT = 50
const TRAIL_LENGTH = 5
const RANGE = 40

let scene, camera, renderer, meteorMesh, meteorGeometry
let meteorPositions, meteorColors, meteorVelocities, meteorLifetimes
let animFrameId = null
let clock

function initMeteorShower() {
  const el = container.value
  if (!el) return

  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100)
  camera.position.z = 10

  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x000000, 0)
  el.appendChild(renderer.domElement)

  const totalPoints = METEOR_COUNT * TRAIL_LENGTH
  meteorPositions = new Float32Array(totalPoints * 3)
  meteorColors = new Float32Array(totalPoints * 3)
  meteorVelocities = []
  meteorLifetimes = new Float32Array(METEOR_COUNT)

  for (let i = 0; i < METEOR_COUNT; i++) {
    const speed = 12 + Math.random() * 20
    const angle = Math.PI / 4 + (Math.random() - 0.5) * 0.6
    meteorVelocities.push({
      vx: Math.cos(angle) * speed * 0.25,
      vy: -Math.sin(angle) * speed,
      vz: (Math.random() - 0.5) * 1.5
    })
    resetMeteor(i)
  }

  meteorGeometry = new THREE.BufferGeometry()
  meteorGeometry.setAttribute('position', new THREE.BufferAttribute(meteorPositions, 3))
  meteorGeometry.setAttribute('color', new THREE.BufferAttribute(meteorColors, 3))

  const mat = new THREE.PointsMaterial({
    size: 0.08, color: 0xffffff, transparent: true,
    opacity: 0.7, blending: THREE.AdditiveBlending,
    sizeAttenuation: true, depthWrite: false,
    vertexColors: true
  })
  meteorMesh = new THREE.Points(meteorGeometry, mat)
  scene.add(meteorMesh)

  clock = new THREE.Clock()
  animate()
}

function resetMeteor(idx) {
  const base = idx * TRAIL_LENGTH * 3
  meteorPositions[base] = (Math.random() - 0.5) * RANGE * 2
  meteorPositions[base + 1] = 18 + Math.random() * 12
  meteorPositions[base + 2] = (Math.random() - 0.5) * 15 - 5
  meteorLifetimes[idx] = 0
  // 随机分散尾迹初始位置
  for (let j = 1; j < TRAIL_LENGTH; j++) {
    const idx2 = base + j * 3
    meteorPositions[idx2] = meteorPositions[base] + (Math.random() - 0.5) * 2
    meteorPositions[idx2 + 1] = meteorPositions[base + 1] + Math.random() * 3
    meteorPositions[idx2 + 2] = meteorPositions[base + 2] + (Math.random() - 0.5) * 1
  }
}

function updateMeteors(delta) {
  if (!meteorPositions) return

  for (let i = 0; i < METEOR_COUNT; i++) {
    const base = i * TRAIL_LENGTH * 3
    const vel = meteorVelocities[i]
    meteorLifetimes[i] += delta
    const life = meteorLifetimes[i]
    const fadeIn = Math.min(1, life * 2.5)
    const fadeOut = Math.max(0, 1 - (life - 2.5) / 2)

    // 尾迹跟随
    for (let j = TRAIL_LENGTH - 1; j > 0; j--) {
      const idx = base + j * 3
      const prev = base + (j - 1) * 3
      meteorPositions[idx] = meteorPositions[prev]
      meteorPositions[idx + 1] = meteorPositions[prev + 1]
      meteorPositions[idx + 2] = meteorPositions[prev + 2]
    }

    // 头部移动
    meteorPositions[base] += vel.vx * delta
    meteorPositions[base + 1] += vel.vy * delta
    meteorPositions[base + 2] += vel.vz * delta

    // 颜色渐变
    for (let j = 0; j < TRAIL_LENGTH; j++) {
      const alpha = Math.pow(1 - j / TRAIL_LENGTH, 2) * fadeIn * fadeOut
      const cidx = (i * TRAIL_LENGTH + j) * 3
      meteorColors[cidx] = alpha * 0.85
      meteorColors[cidx + 1] = alpha * 0.85
      meteorColors[cidx + 2] = alpha
    }

    if (meteorPositions[base + 1] < -18 || life > 5) {
      resetMeteor(i)
    }
  }

  meteorGeometry.attributes.position.needsUpdate = true
  meteorGeometry.attributes.color.needsUpdate = true
}

function animate() {
  animFrameId = requestAnimationFrame(animate)
  updateMeteors(clock.getDelta())
  renderer.render(scene, camera)
}

function onResize() {
  if (!renderer) return
  renderer.setSize(window.innerWidth, window.innerHeight)
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
}

onMounted(() => {
  initMeteorShower()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
  renderer?.dispose()
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.meteor-container {
  position: fixed; inset: 0; z-index: 1;
  pointer-events: none;
}
.meteor-container :deep(canvas) {
  pointer-events: none !important;
}
.meteor-container.hidden {
  display: none;
}
</style>