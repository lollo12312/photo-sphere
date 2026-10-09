const API_BASE = '/api'

export async function fetchPhotoList() {
  const res = await fetch(`${API_BASE}/photos`)
  if (!res.ok) throw new Error('Failed to fetch photo list')
  return res.json()
}

// 上传本地照片（增强页素材：只进 uploads 临时目录，不入照片库），返回 { upload_id, original_name, size }
export async function uploadPhoto(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/photos/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

// 手机照片页：批量上传到照片库（写入 照片库/手机照片/），支持进度回调
// 注意：与上面的 uploadPhoto 用途完全不同，不要混用
export function uploadLibraryPhotos(files, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/photos/library/upload`)
    xhr.upload.onprogress = e => {
      if (onProgress && e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)) } catch (err) { reject(err) }
      } else {
        reject(new Error(`上传失败（HTTP ${xhr.status}）`))
      }
    }
    xhr.onerror = () => reject(new Error('网络错误，请检查是否连上了电脑的局域网地址'))
    xhr.send(form)
  })
}

export function getThumbnailUrl(filename) {
  return `${API_BASE}/photos/thumbnail/${encodeURIComponent(filename)}`
}

export function getFullPhotoUrl(filename) {
  return `/photos/${encodeURIComponent(filename)}`
}

// 上传照片的原图 URL
export function getUploadPhotoUrl(uploadId) {
  return `/uploads/${encodeURIComponent(uploadId)}`
}

// ===== 回收站 =====
async function postJSON(path, data) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error(`请求失败（HTTP ${res.status}）`)
  return res.json()
}

// 删除照片（移入回收站），names 为照片相对路径数组
export function trashPhotos(names) {
  return postJSON('/photos/trash', { names })
}

// 回收站列表
export async function fetchTrashList() {
  const res = await fetch(`${API_BASE}/photos/trash/list`)
  if (!res.ok) throw new Error('Failed to fetch trash list')
  return res.json()
}

// 恢复回收站照片（移回原目录）
export function restoreTrashPhotos(names) {
  return postJSON('/photos/trash/restore', { names })
}

// 彻底删除回收站照片（不可找回）
export function purgeTrashPhotos(names) {
  return postJSON('/photos/trash/purge', { names })
}