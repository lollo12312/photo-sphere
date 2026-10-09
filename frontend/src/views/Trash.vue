<template>
  <div class="trash-page" :class="{ light: !store.darkTheme }">
    <div class="trash-head">
      <div class="trash-title">
        <h1>🗑 回收站</h1>
        <span class="trash-count">{{ items.length }} 张</span>
      </div>
      <div class="trash-actions">
        <label class="select-all">
          <input type="checkbox" :checked="allSelected && items.length > 0" @change="toggleAll" />
          <span>全选</span>
        </label>
        <button class="act-btn restore-btn" :disabled="!selectedCount" @click="restoreSelected">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8l2-2 2 2"/><path d="M5 6v8a5 5 0 0 0 10 0v-1"/><path d="M13 2h4a2 2 0 0 1 2 2v4"/></svg>
          恢复（{{ selectedCount }}）
        </button>
        <button class="act-btn purge-btn" :disabled="!selectedCount" @click="purgeSelected">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>
          彻底删除（{{ selectedCount }}）
        </button>
      </div>
    </div>

    <div v-if="items.length" class="trash-grid">
      <div
        v-for="item in items" :key="item.name"
        class="trash-card" :class="{ selected: selected.has(item.name) }"
        @click="toggle(item)"
      >
        <img :src="getThumbnailUrl(item.name)" :alt="item.original" loading="lazy" draggable="false" />
        <div class="trash-mask">
          <div class="t-origin" :title="item.original">{{ item.original }}</div>
          <div class="t-sub">{{ item.folder || '照片库根目录' }} · {{ item.date }} · {{ fmtSize(item.size) }}</div>
        </div>
        <span class="t-check">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
        </span>
      </div>
    </div>

    <div v-else-if="loaded" class="trash-empty">
      <div class="ph-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
      </div>
      <p>回收站空空如也</p>
      <p class="hint">在「电脑库」或「手机库」里删除的照片会出现在这里</p>
    </div>
    <div v-else class="trash-empty">
      <p>加载中...</p>
    </div>

    <Transition name="toast-fade">
      <div v-if="toast" class="trash-toast">{{ toast }}</div>
    </Transition>

    <!-- 彻底删除确认：居中毛玻璃弹窗 -->
    <Transition name="del-popup">
      <div v-if="purgeNames.length" class="del-popup-mask" @click.self="purgeNames = []">
        <div class="del-popup-card">
          <div class="del-popup-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>
          </div>
          <div class="del-popup-title">彻底删除 {{ purgeNames.length }} 张照片？</div>
          <div class="del-popup-hint">删除后无法找回！请确认是否继续</div>
          <div class="del-popup-actions">
            <button class="dpa-btn dpa-cancel" @click="purgeNames = []">取消</button>
            <button class="dpa-btn dpa-danger" @click="doPurge">彻底删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getThumbnailUrl, fetchTrashList, restoreTrashPhotos, purgeTrashPhotos } from '../api/photos'
import { store } from '../store'

const items = ref([])
const loaded = ref(false)
const selected = ref(new Set())
const toast = ref('')
let toastTimer = null

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3600)
}

const selectedCount = computed(() => selected.value.size)
const allSelected = computed(() => items.value.length > 0 && selected.value.size === items.value.length)

function fmtSize(b) {
  if (!b && b !== 0) return ''
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return Math.round(b / 1024) + ' KB'
  return (b / 1024 / 1024).toFixed(1) + ' MB'
}

async function load() {
  try {
    items.value = await fetchTrashList()
  } catch (e) {
    console.error(e)
    items.value = []
  } finally {
    loaded.value = true
  }
}

function toggle(item) {
  const s = new Set(selected.value)
  if (s.has(item.name)) s.delete(item.name)
  else s.add(item.name)
  selected.value = s
}

function toggleAll() {
  if (allSelected.value) selected.value = new Set()
  else selected.value = new Set(items.value.map(i => i.name))
}

async function restoreSelected() {
  const names = [...selected.value]
  if (!names.length) return
  try {
    const res = await restoreTrashPhotos(names)
    const okCount = res.restored ? res.restored.length : 0
    const fails = res.failed || []
    selected.value = new Set()
    await load()
    showToast('已恢复 ' + okCount + ' 张' + (fails.length ? '，失败 ' + fails.length + ' 张' : ''))
    if (fails.length) console.warn('[恢复失败明细]', fails)
  } catch (err) {
    console.error(err)
    showToast('恢复失败：' + (err.message || err))
  }
}

// 彻底删除：先弹确认（居中毛玻璃），确认后执行
const purgeNames = ref([])

function purgeSelected() {
  const names = [...selected.value]
  if (!names.length) return
  purgeNames.value = names
}

async function doPurge() {
  const names = purgeNames.value
  purgeNames.value = []
  if (!names.length) return
  try {
    const res = await purgeTrashPhotos(names)
    const okCount = res.purged ? res.purged.length : 0
    const fails = res.failed || []
    selected.value = new Set()
    await load()
    showToast('已彻底删除 ' + okCount + ' 张' + (fails.length ? '，失败 ' + fails.length + ' 张' : ''))
    if (fails.length) console.warn('[彻底删除失败明细]', fails)
  } catch (err) {
    console.error(err)
    showToast('删除失败：' + (err.message || err))
  }
}

onMounted(() => { load() })
onUnmounted(() => { clearTimeout(toastTimer) })
</script>

<style scoped>
.trash-page {
  width: 100%;
  height: 100%;
  min-height: 100dvh;
  background: #14141e;
  color: #eee;
  display: flex;
  flex-direction: column;
  padding: 0 4vw 78px;
  box-sizing: border-box;
}
.trash-page.light {
  background: #f7f7fb;
  color: #222;
}

/* 头部 */
.trash-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 78px 0 22px;
  flex-wrap: wrap;
}
.trash-title { display: flex; align-items: baseline; gap: 12px; }
.trash-title h1 { font-size: 22px; font-weight: 600; }
.trash-count { font-size: 13px; opacity: 0.55; }
.trash-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.select-all {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; opacity: 0.8; cursor: pointer;
  margin-right: 6px;
}
.select-all input { width: 15px; height: 15px; cursor: pointer; }
.act-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 20px;
  border: 1px solid #2a2a3a; background: #1e1e2e;
  color: #ddd; font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.act-btn svg { width: 15px; height: 15px; }
.act-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.restore-btn:hover:not(:disabled) { background: #2563eb; border-color: #2563eb; color: #fff; }
.purge-btn:hover:not(:disabled) { background: #e5484d; border-color: #e5484d; color: #fff; }
.trash-page.light .select-all { opacity: 0.75; }

/* 网格 */
.trash-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}
.trash-card {
  position: relative;
  aspect-ratio: 4 / 3;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff18;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  transition: transform 0.2s, box-shadow 0.2s;
}
.trash-card:hover { transform: translateY(-3px); }
.trash-card img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
}
.trash-mask {
  position: absolute; left: 0; right: 0; bottom: 0;
  padding: 26px 10px 8px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.78), transparent);
}
.t-origin {
  font-size: 12px; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.t-sub { font-size: 11px; color: rgba(255, 255, 255, 0.6); margin-top: 2px; }
.t-check {
  position: absolute; top: 8px; left: 8px;
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  color: transparent; border: 2px solid rgba(255, 255, 255, 0.55);
  transition: all 0.15s;
}
.t-check svg { width: 12px; height: 12px; }
.trash-card.selected { box-shadow: 0 0 0 2px #6c63ff, 0 8px 24px rgba(0, 0, 0, 0.35); }
.trash-card.selected .t-check {
  background: #6c63ff; border-color: #6c63ff; color: #fff;
}

/* 空态 */
.trash-empty {
  flex: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 10px; color: rgba(255, 255, 255, 0.5);
}
.trash-empty .ph-icon svg { width: 44px; height: 44px; opacity: 0.4; }
.trash-empty p { font-size: 15px; margin: 0; }
.trash-empty .hint { font-size: 12px; opacity: 0.6; }
.trash-page.light .trash-empty { color: rgba(0, 0, 0, 0.45); }

/* toast */
.trash-toast {
  position: fixed; right: 20px; top: 88px; z-index: 300;
  padding: 10px 18px; border-radius: 10px;
  background: rgba(15, 15, 25, 0.85); color: #fff;
  font-size: 13px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
}
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity 0.22s, transform 0.22s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translate(12px, -50%); }

/* ===== 彻底删除确认弹窗：居中毛玻璃（与相册删除确认同风格） ===== */
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
}
.del-popup-icon {
  width: 96px; height: 96px; border-radius: 16px; margin-bottom: 16px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(229, 72, 77, 0.12); color: #e5484d;
}
.del-popup-icon svg { width: 38px; height: 38px; }
.del-popup-title { font-size: 16px; font-weight: 600; color: #fff; }
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
.del-popup-enter-active, .del-popup-leave-active { transition: opacity 0.2s; }
.del-popup-enter-active .del-popup-card, .del-popup-leave-active .del-popup-card { transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s; }
.del-popup-enter-from .del-popup-card, .del-popup-leave-to .del-popup-card { transform: scale(0.92); opacity: 0; }
.del-popup-enter-from, .del-popup-leave-to { opacity: 0; }
.trash-page.light .del-popup-card {
  background: rgba(245, 245, 250, 0.8);
  border-color: rgba(0, 0, 0, 0.1);
}
.trash-page.light .del-popup-title { color: #222; }
.trash-page.light .del-popup-hint { color: rgba(0, 0, 0, 0.45); }
.trash-page.light .dpa-cancel { background: rgba(0, 0, 0, 0.06); color: #333; }
.trash-page.light .dpa-cancel:hover { background: rgba(0, 0, 0, 0.12); }
</style>