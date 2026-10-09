# Photo Sphere · 照片回忆相册

本地运行的照片管理与浏览应用：把本机照片文件夹变成一个 3D 照片球体、时间轴相册与手机端 H5，附带照片增强（超分辨率 / 人像优化）与回收站。

## 功能

- **相册**：电脑库 / 手机库分库浏览；按种类、分类、分辨率、色系筛选，支持搜索、分页、大图查看（地图式缩放 / 旋转 / 拖拽）
- **3D 照片球体**：照片贴在可旋转球体上，张数可调，超出设定值时随机抽样
- **时间轴**：年 → 月两级折叠，电脑库 / 手机库双 Tab
- **照片增强**：三档增强、FSRCNN 2x / 4x 超分、人像优化（磨皮 / 锐化 / 提亮 / 背景虚化 / 暗角）
- **回收站**：删除的照片可恢复或彻底删除
- **手机端 H5**（`/wx/`）：独立轻量页面，可在手机浏览器浏览 / 上传 / 删除（局域网访问）
- **暗色 / 亮色主题**、流星背景

## 技术栈

- 前端：Vue 3 + Vite + Vue Router + Three.js
- 后端：Python FastAPI + Pillow + OpenCV

## 快速开始

### 1. 后端（端口 8000）

```bash
cd backend
pip install -r requirements.txt
python main.py
```

首次启动会预生成照片缩略图缓存（`backend/cache/`），照片较多时需要等待一会儿。

### 2. 前端（端口 3000）

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:3000

> 也可以只用后端：`cd frontend && npm run build` 后由后端在 http://127.0.0.1:8000 直接托管全部页面。

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| :--- | :--- | :--- |
| `PHOTOS_DIR` | `D:\LOLLO\Pictures` | **照片库根目录**，指向你自己的照片文件夹；手机照片目录 / 回收站自动建在它下面 |
| `PORTAL_HOST` | `127.0.0.1` | 监听地址；设为 `0.0.0.0` 允许局域网 / 手机访问 |
| `PORTAL_TOKEN` | 空（不校验） | 写操作令牌（上传 / 删除 / 恢复 / 彻底删除）；设置后写接口需带 `?token=xxx` |
| `SUPER_RES_API_URL` / `SUPER_RES_API_KEY` | 空 | 可选：云端超分 API，配置后优先走云端、失败回退本地模型 |

Windows PowerShell 示例：

```powershell
$env:PHOTOS_DIR="D:\MyPhotos"; python main.py
```

## 目录结构

```
backend/          FastAPI 服务
  routers/photos.py   全部接口（列表/缩略图/上传/回收站/增强/归类）
  portrait.py         人像优化管线
  superres.py         超分辨率（本地模型 / 云端 API 适配）
  config.py           路径与配置（PHOTOS_DIR 等）
frontend/         Vue3 前端
  src/views/          相册 / 球体 / 时间轴 / 增强 / 回收站等页面
  public/wx/          手机端 H5（构建后由后端 /wx/ 托管）
PROJECT.md        详细开发文档与功能记录
```

## 说明

- **照片库（个人照片）不进入本仓库**：请通过 `PHOTOS_DIR` 指向本机照片目录
- `backend/cache/`（缩略图缓存）、`backend/uploads/`（增强临时素材）为运行时数据，启动后自动重建，已加入 `.gitignore`
- 照片库内部约定：`手机照片/` 子目录 = 手机库；`.trash/` 子目录 = 回收站（扫描时自动跳过）
- 支持格式：JPG / PNG / GIF / BMP / WebP / HEIC / HEIF

更多实现细节（地图式缩放、缓存策略、人像管线参数等）见 [PROJECT.md](PROJECT.md)。