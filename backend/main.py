import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from config import PHOTOS_DIR, UPLOADS_DIR
from routers.photos import router as photos_router, pre_generate_thumbnails, CACHE_DIR


# 启动时预生成所有缩略图（lifespan 替代已废弃的 @app.on_event）
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 缩略图预生成是阻塞的 PIL 操作，丢线程池执行，避免阻塞启动事件循环
    await run_in_threadpool(pre_generate_thumbnails)
    yield


# 说明：前端（dev 经 vite 代理、生产同源 :8000）始终以同源方式访问 API，
# 故不需要 CORS；若曾用 allow_origins=["*"] 反而会让任意网页跨域读取本机照片库，故直接不挂中间件。
app = FastAPI(title="Photo Sphere API", lifespan=lifespan)

# API 路由
app.include_router(photos_router)

# 缓存目录作为静态文件提供（浏览器可直接访问，不走 Python 处理）
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")

# 直接提供原图文件访问（供模态框使用）
app.mount("/photos", StaticFiles(directory=PHOTOS_DIR), name="photos")

# 用户上传照片静态访问（增强页原图预览）
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# 前端静态文件
dist_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)
if os.path.isdir(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")

if __name__ == "__main__":
    # 监听地址可控：默认仅本机（手机照片走「数据线连电脑 + 电脑浏览器上传」，无需局域网访问；
    # 也避免把整库图片暴露给同网段其它设备）。
    # 想要「手机/公众号 H5 通过局域网访问」时：PORTAL_HOST=0.0.0.0 python main.py（配合 PORTAL_TOKEN 防外人乱动）
    host = os.environ.get("PORTAL_HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=8000, reload=False)