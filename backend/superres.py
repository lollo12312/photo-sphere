"""
本地轻量 AI 超分辨率模块（FSRCNN / EDSR）+ 预留云端超分 API 适配层

模型存放位置： backend/models/  （首次使用自动下载）
删除方法：直接删除 models 目录下的 .pb 文件即可，或整个 models 目录。

云 API 接入（可选）：
    设置环境变量后优先走云端，未设置或失败自动回退本地模型。
    SUPER_RES_API_URL  例如 https://api.example.com/api/super_res
    SUPER_RES_API_KEY  你的 API Key
"""
import os
import io
import threading
import urllib.request

import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# 模型规范：scale -> 权重信息（FSRCNN 小且快，EDSR 质量更好）
SUPER_RES_MODELS = {
    2: {
        "label": "FSRCNN_x2",
        "file": "FSRCNN_x2.pb",
        "url": "https://github.com/opencv/opencv_extra/raw/master/testdata/dnn/superres/FSRCNN_x2.pb",
    },
    4: {
        "label": "FSRCNN_x4",
        "file": "FSRCNN_x4.pb",
        "url": "https://github.com/opencv/opencv_extra/raw/master/testdata/dnn/superres/FSRCNN_x4.pb",
    },
}

# 云端超分 API 配置（通过环境变量启用，默认关闭）
CLOUD_API_URL = os.environ.get("SUPER_RES_API_URL", "").strip()
CLOUD_API_KEY = os.environ.get("SUPER_RES_API_KEY", "").strip()

# 模型实例缓存（懒加载，只加载一次）
_sr_cache: dict[int, object] = {}
_sr_lock = threading.Lock()


def _model_path(scale: int) -> str:
    return os.path.join(MODELS_DIR, SUPER_RES_MODELS[scale]["file"])


def ensure_model(scale: int) -> str:
    """确保模型权重已下载，返回本地路径"""
    spec = SUPER_RES_MODELS[scale]
    path = _model_path(scale)
    if os.path.isfile(path):
        return path
    print(f"[SuperRes] 正在下载 {spec['label']} 权重...")
    # urlretrieve 不支持超时，改 urlopen + 写文件，避免网络卡死无限阻塞
    req = urllib.request.Request(spec["url"], headers={"User-Agent": "photo-sphere"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(path, "wb") as fh:
        fh.write(resp.read())
    size = os.path.getsize(path) / 1024
    print(f"[SuperRes] {spec['label']} 下载完成 ({size:.0f} KB) -> {path}")
    return path


def _get_sr(scale: int) -> object:
    """懒加载并缓存 dnn_superres 实例（加锁，避免线程池并发下重复加载）"""
    with _sr_lock:
        if scale in _sr_cache:
            return _sr_cache[scale]
        try:
            from cv2 import dnn_superres
            path = ensure_model(scale)
            sr = dnn_superres.DnnSuperResImpl_create()
            sr.readModel(path)
            sr.setModel(SUPER_RES_MODELS[scale]["label"].split("_")[0], scale)
            _sr_cache[scale] = sr
            return sr
        except Exception as e:
            print(f"[SuperRes] 本地模型加载失败({e})，将回退传统插值")
            return None


def _local_super_resolve(img, scale: int):
    """本地模型超分，失败回退 Lanczos 插值 + 轻锐化"""
    sr = _get_sr(scale)
    if sr is None:
        w, h = img.size
        return img.resize((w * scale, h * scale), __import__("PIL").Image.LANCZOS)

    # PIL -> OpenCV BGR ndarray
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    bgr = cv2_imdecode(buf.getvalue())
    up = sr.upsample(bgr)
    return bgr_to_pil(up)


def cv2_imdecode(data: bytes):
    import cv2
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def bgr_to_pil(bgr):
    import cv2
    from PIL import Image
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _cloud_super_resolve(img, scale: int):
    """调用云端超分 API（预留接口），失败返回 None 由调用方回退"""
    if not (CLOUD_API_URL and CLOUD_API_KEY):
        return None
    try:
        import json as _json
        import base64 as _b64
        import urllib.request as _ur

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        payload = _json.dumps({
            "image": _b64.b64encode(buf.getvalue()).decode(),
            "scale": scale,
        }).encode()
        req = _ur.Request(CLOUD_API_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CLOUD_API_KEY}",
        })
        with _ur.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode())
        b64_img = data.get("image")
        if not b64_img:
            return None
        return _b64.b64decode(b64_img)
    except Exception as e:
        print(f"[SuperRes] 云端 API 调用失败({e})，回退本地模型")
        return None


def super_resolve(img, scale: int = 1):
    """对外统一入口：scale<=1 原样返回；优先云端，回退本地"""
    scale = int(scale)
    if scale <= 1 or scale not in SUPER_RES_MODELS:
        return img
    if CLOUD_API_URL and CLOUD_API_KEY:
        cloud_result = _cloud_super_resolve(img, scale)
        # 云端返回的是 JPEG bytes；失败(空)时回退本地模型
        if cloud_result:
            import cv2
            arr = np.frombuffer(cloud_result, np.uint8)
            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if bgr is not None:
                return bgr_to_pil(bgr)
    return _local_super_resolve(img, scale)