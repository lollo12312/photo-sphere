import os
import glob
import io
import json
import time
import colorsys
import threading
import hashlib
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Query, Depends
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageFilter

from config import PHOTOS_DIR, UPLOADS_DIR, PHONE_DIR, TRASH_DIR, ALLOWED_EXTENSIONS, THUMBNAIL_SIZE, PORTAL_TOKEN

# HEIC/HEIF 支持（iPhone 默认格式）：需要 pillow-heif，缺失时自动降级（HEIC 文件会打不开）
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_SUPPORT = True
except Exception as _e:  # pragma: no cover
    HEIF_SUPPORT = False
    print(f"[HEIF] pillow-heif 未安装，HEIC/HEIF 照片无法解码：{_e}")

router = APIRouter(prefix="/api", tags=["photos"])

# 磁盘缓存目录，缓存生成的缩略图和增强结果
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 内存缓存（热数据）—— LRU：满 _CACHE_MAX 时淘汰最旧的一条，而不是全清（全清会让全库缩略图重新生成）
_thumbnail_cache: "OrderedDict[str, bytes]" = OrderedDict()
_CACHE_MAX = 200
_cache_lock = threading.Lock()  # 保护 _thumbnail_cache / _detail_cache（端点改 def 后运行在线程池，需防竞态）

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 单文件上传上限 200MB，防止超大文件占满内存/磁盘


def check_portal_token(token: str = Query(default="", alias="token")) -> None:
    """写接口令牌校验：配置了 PORTAL_TOKEN 时必须匹配，否则 403。

    读接口（列表/缩略图/原图）不校验，保证手机/网页浏览无感；写操作（上传/删除/恢复/彻底删除）需带 ?token=xxx。
    未配置 PORTAL_TOKEN 时直接放行（旧行为，个人本机自测不受影响）。
    """
    if PORTAL_TOKEN and token != PORTAL_TOKEN:
        raise HTTPException(403, "token 无效，写操作被拒绝（网页浏览不受影响）")


def _mem_get(key: str) -> bytes | None:
    with _cache_lock:
        data = _thumbnail_cache.get(key)
        if data is not None:
            _thumbnail_cache.move_to_end(key)  # 命中刷新：最近使用的排到末尾
        return data


def _mem_put(key: str, data: bytes) -> None:
    with _cache_lock:
        if key in _thumbnail_cache:
            _thumbnail_cache.move_to_end(key)
        _thumbnail_cache[key] = data
        while len(_thumbnail_cache) > _CACHE_MAX:
            _thumbnail_cache.popitem(last=False)  # 淘汰最久未用的


def _cached_response(data: bytes, cache_hours: int = 24, extra: dict | None = None) -> Response:
    """返回带 HTTP 缓存头的响应，让浏览器也参与缓存；extra 追加自定义头（如人像检测数）"""
    headers = {
        "Cache-Control": f"public, max-age={cache_hours * 3600}, immutable",
        "Expires": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
    }
    if extra:
        headers.update({k: str(v) for k, v in extra.items()})
    return Response(content=data, media_type="image/jpeg", headers=headers)


def _write_meta(cache_path: str, meta: dict) -> None:
    """把生成时的附加信息（如人像检测结果）与缓存图片一起存盘，命中缓存时也能返回"""
    try:
        with open(cache_path + ".json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
    except Exception:
        pass


def _read_meta(cache_path: str) -> dict:
    try:
        with open(cache_path + ".json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_cache_path(cache_type: str, filename: str, params: str = "") -> str:
    """生成缓存文件路径：type_filename_hashparams"""
    # 用 hash 避免文件名特殊字符问题
    key = f"{cache_type}_{filename}_{params}_{THUMBNAIL_SIZE[0]}"
    hash_key = hashlib.md5(key.encode()).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"{hash_key}.jpg")


def _read_cache(cache_path: str) -> bytes | None:
    """读取磁盘缓存，如果存在返回 bytes"""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return f.read()
        except Exception:
            pass
    return None


def _write_cache(cache_path: str, data: bytes) -> None:
    """写入磁盘缓存"""
    try:
        with open(cache_path, "wb") as f:
            f.write(data)
    except Exception:
        pass


def _safe_join(base: str, filename: str) -> str:
    """拼接文件路径并校验其在 base 目录内，防止路径穿越读取任意文件"""
    full = os.path.abspath(os.path.join(base, filename))
    base_abs = os.path.abspath(base)
    if full != base_abs and not full.startswith(base_abs + os.sep):
        raise HTTPException(404, "Not found")
    return full


def _abs_photo_path(filename: str) -> str | None:
    """把相对路径（如 手机照片/IMG_1.jpg）转成绝对路径，并校验其位于照片目录内"""
    base = os.path.abspath(PHOTOS_DIR)
    full = os.path.abspath(os.path.join(base, str(filename).replace("/", os.sep)))
    if full != base and not full.startswith(base + os.sep):
        return None
    return full


def generate_thumbnail(filename: str) -> bytes | None:
    """生成单张缩略图，返回 bytes 或 None（filename 为相对照片库的相对路径）"""
    filepath = _abs_photo_path(filename)
    if not filepath or not os.path.isfile(filepath):
        return None
    try:
        img = Image.open(filepath)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        thumb_w = THUMBNAIL_SIZE[0]
        if thumb_w >= w:
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=120))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        else:
            thumb_h = int(h * (thumb_w / w))
            img_small = img.resize((thumb_w, thumb_h), Image.LANCZOS)
            img_small = img_small.filter(ImageFilter.UnsharpMask(radius=0.8, percent=120))
            buf = io.BytesIO()
            img_small.save(buf, format="JPEG", quality=80)
            return buf.getvalue()
    except Exception:
        return None


def _gen_thumb_to_cache(name: str) -> bool:
    """单张缩略图生成并写盘（供并发预生成使用）"""
    data = generate_thumbnail(name)
    if data is not None:
        _write_cache(_get_cache_path("thumb", name), data)
        return True
    return False


def pre_generate_thumbnails():
    """启动时预生成所有缩略图到磁盘缓存（并发：PIL 打开各自文件无共享状态，线程安全）"""
    photos = _scan_photos()
    todo = [name for name in photos if not os.path.exists(_get_cache_path("thumb", name))]
    if not todo:
        print(f"[Cache] 缩略图预生成: 全部已缓存（{len(photos)} 张）")
        return
    workers = min(8, max(2, (os.cpu_count() or 4) // 2))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        ex.map(_gen_thumb_to_cache, todo)
    generated = sum(1 for _ in todo)  # ex.map 已全部完成
    print(f"[Cache] 缩略图预生成完成: {generated} 张新生成（{workers} 并发）, {len(photos) - generated} 张已缓存")


def _scan_photo_paths() -> list[str]:
    """递归扫描照片目录，返回**相对路径**列表（POSIX 风格，如 手机照片/IMG_1.jpg），按修改时间倒序

    用相对路径而不是纯文件名：既支持子目录（手机照片/、Camera Roll/ 等），
    也避免不同子目录里的同名文件互相覆盖。跳过 $ / . 开头的系统目录（如 $RECYCLE.BIN）。
    """
    files = []
    for ext in ALLOWED_EXTENSIONS:
        files.extend(glob.glob(os.path.join(PHOTOS_DIR, "**", f"*{ext}"), recursive=True))
    out = []
    for f in files:
        if not os.path.isfile(f):
            continue
        rel = os.path.relpath(f, PHOTOS_DIR)
        if any(p.startswith(("$", ".")) for p in rel.split(os.sep)):
            continue
        out.append((os.path.getmtime(f), rel.replace(os.sep, "/")))
    out.sort(key=lambda x: x[0], reverse=True)
    return [rel for _, rel in out]


def _scan_photos() -> list[str]:
    """扫描照片目录（递归），返回按修改时间倒序的相对路径列表"""
    return _scan_photo_paths()


def _scan_photos_with_details() -> list[dict]:
    """扫描照片目录（递归），返回带详细信息的列表（含大小和尺寸）"""
    result = []
    for rel in _scan_photo_paths():
        f = os.path.join(PHOTOS_DIR, rel.replace("/", os.sep))
        mtime = os.path.getmtime(f)
        dt = datetime.fromtimestamp(mtime)
        w, h = 0, 0
        try:
            with Image.open(f) as img:
                w, h = img.size
        except Exception:
            pass
        result.append({
            "name": rel,
            "folder": os.path.dirname(rel),
            "date": dt.strftime("%Y-%m-%d"),
            "year": str(dt.year),
            "month": str(dt.month),
            "timestamp": mtime,
            "size": os.path.getsize(f),
            "width": w,
            "height": h,
        })
    return result


# 详情扫描要逐张打开图片取尺寸，48 张 4K 图约 2 秒；相册页会同时请求 detail 与 analyze，这里短期缓存共享同一次扫描
_detail_cache: dict = {"ts": 0.0, "data": None}
_DETAIL_TTL = 30  # 秒


def _scan_photos_with_details_cached() -> list[dict]:
    with _cache_lock:
        if _detail_cache["data"] is not None and time.time() - _detail_cache["ts"] < _DETAIL_TTL:
            return _detail_cache["data"]
    data = _scan_photos_with_details()
    with _cache_lock:
        _detail_cache["ts"] = time.time()
        _detail_cache["data"] = data
    return data


@router.get("/photos")
def list_photos():
    """获取照片文件名列表"""
    return _scan_photos()


@router.get("/photos/detail")
def list_photos_detail():
    """获取照片详细信息（含日期）"""
    return _scan_photos_with_details_cached()


# ===== 零模型照片归类（L1）：取向 / 分辨率档 / 主题 / 主色系 =====
# 完全不需要模型文件与网络：取向与分辨率来自像素尺寸，主题来自文件名关键词，主色系来自缩略图 HSV 分桶众数
_ANALYZE_CACHE = os.path.join(CACHE_DIR, "analyze.json")

# 主题关键词字典（按文件名匹配；列表顺序即优先级，先命中者胜出）
_THEME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("人物", ("人物", "人像", "美女", "明星", "女孩", "男孩", "少女", "写真", "女神", "情侣", "宝宝")),
    ("动漫", ("动漫", "二次元", "插画", "卡通", "漫画", "手绘", "可爱", "萌")),
    ("游戏", ("游戏", "电竞", "英雄联盟", "原神", "王者")),
    ("动物", ("猫", "狗", "鸟", "动物", "宠物", "兔", "熊", "狐", "鱼", "马")),
    ("城市", ("城市", "建筑", "街道", "楼", "桥", "都市", "车", "道路", "室内", "工业")),
    ("风景", ("风景", "大海", "海", "山", "天空", "云", "日落", "日出", "夕阳", "傍晚", "落日",
              "夜景", "星空", "星", "森林", "草原", "雪", "花", "湖", "河", "瀑布", "沙漠", "光", "树", "叶")),
    ("极简", ("简单", "简约", "极简", "纯色", "抽象", "线条", "几何", "文字")),
]


def _classify_pixel(h: float, s: float, v: float) -> str:
    """单个像素的 HSV（h: 0-360, s/v: 0-1）→ 12 色系之一"""
    if v < 0.16:
        return "黑"
    if s < 0.14:
        return "白" if v > 0.88 else "灰"
    if 10 <= h < 50 and v < 0.62:
        return "棕"
    if h < 15 or h >= 345:
        return "红"
    if h < 40:
        return "橙"
    if h < 70:
        return "黄"
    if h < 160:
        return "绿"
    if h < 200:
        return "青"
    if h < 255:
        return "蓝"
    if h < 290:
        return "紫"
    return "粉"


def _photo_color_family(name: str) -> str:
    """主色系：用已缓存的 480px 缩略图缩到 48x48 后按 HSV 分桶取加权众数

    权重设计：中性色（黑/灰/白）降权 —— 壁纸常有大片暗底，直接按像素数取众数会全被判成「灰」；
    有彩色按饱和度加权，让画面的「特征色」胜出，更接近人眼对这张图色系的判断。
    """
    path = _get_cache_path("thumb", name)
    if not os.path.exists(path):
        data = generate_thumbnail(name)
        if data is None:
            return ""
        _write_cache(path, data)
    try:
        with Image.open(path) as im:
            small = im.convert("RGB").resize((48, 48), Image.BILINEAR)
            px = small.load()
        counts: dict[str, float] = {}
        for y in range(48):
            for x in range(48):
                r, g, b = px[x, y]
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                fam = _classify_pixel(h * 360, s, v)
                weight = 0.25 if fam in ("黑", "灰", "白") else (0.6 + 2.0 * s)
                counts[fam] = counts.get(fam, 0.0) + weight
    except Exception:
        return ""
    return max(counts, key=counts.get) if counts else ""


def _orientation_of(w: int, h: int) -> str:
    """取向：横屏（电脑壁纸）/ 竖屏（手机壁纸）/ 方形"""
    if not w or not h or w == h:
        return "square"
    return "landscape" if w > h else "portrait"


def _resolution_tier(w: int, h: int) -> str:
    """按长边分档：4K 及以上 / 2K / 1080P / 其他"""
    m = max(w or 0, h or 0)
    if m >= 3840:
        return "4K"
    if m >= 2560:
        return "2K"
    if m >= 1920:
        return "1080P"
    return "SD"


def _theme_of(name: str) -> str:
    """主题：按文件名关键词归类，未命中归入「其他」"""
    for theme, keys in _THEME_RULES:
        if any(k in name for k in keys):
            return theme
    return "其他"


@router.get("/photos/analyze")
def analyze_photos():
    """零模型照片归类：取向 + 分辨率档 + 主题 + 主色系
    结果按「文件名 + 修改时间 + 大小」缓存到 cache/analyze.json，未变化的照片不重复计算
    """
    photos = _scan_photos_with_details_cached()
    cache: dict[str, dict] = {}
    if os.path.exists(_ANALYZE_CACHE):
        try:
            with open(_ANALYZE_CACHE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    items: dict[str, dict] = {}
    changed = 0
    for p in photos:
        name = p["name"]
        stamp = f"{int(p['timestamp'])}_{p['size']}"
        hit = cache.get(name)
        if hit and hit.get("stamp") == stamp:
            items[name] = {k: v for k, v in hit.items() if k != "stamp"}
            continue
        entry = {
            "orientation": _orientation_of(p["width"], p["height"]),
            "tier": _resolution_tier(p["width"], p["height"]),
            "theme": _theme_of(name),
            "color": _photo_color_family(name),
        }
        cache[name] = dict(entry, stamp=stamp)
        items[name] = entry
        changed += 1

    # 清理已删除照片的缓存条目：不只在新/变照片时才写（否则「只删不增」会留下陈旧条目）
    keep = {p["name"] for p in photos}
    pruned = {k: v for k, v in cache.items() if k in keep}
    if changed or len(pruned) != len(cache):
        try:
            with open(_ANALYZE_CACHE, "w", encoding="utf-8") as f:
                json.dump(pruned, f, ensure_ascii=False)
        except Exception:
            pass

    return {"total": len(items), "items": items}


@router.get("/photos/categories")
def list_categories():
    """获取分类列表，按文件名首字母分组"""
    files = _scan_photos()
    groups = {}
    for name in files:
        key = name[0].upper() if name else "?"
        if key not in groups:
            groups[key] = 0
        groups[key] += 1
    categories = [{"name": k, "count": v} for k, v in sorted(groups.items())]
    return {"categories": categories, "total": len(files)}


@router.get("/photos/thumbnail/{filename:path}")
def get_thumbnail(filename: str):
    """获取缩略图（480px 宽，保持比例，JPEG 格式）"""
    filepath = _safe_join(PHOTOS_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(404, "Photo not found")

    # 1) 内存缓存
    mem = _mem_get(filename)
    if mem is not None:
        return _cached_response(mem, cache_hours=24)

    # 2) 磁盘缓存
    cache_path = _get_cache_path("thumb", filename)
    cached = _read_cache(cache_path)
    if cached is not None:
        _mem_put(filename, cached)
        return _cached_response(cached, cache_hours=24)

    # 3) 生成缩略图
    try:
        img = Image.open(filepath)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        w, h = img.size
        thumb_w = THUMBNAIL_SIZE[0]
        if thumb_w >= w:
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=120))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            data = buf.getvalue()
        else:
            thumb_h = int(h * (thumb_w / w))
            img_small = img.resize((thumb_w, thumb_h), Image.LANCZOS)
            img_small = img_small.filter(ImageFilter.UnsharpMask(radius=0.8, percent=120))
            buf = io.BytesIO()
            img_small.save(buf, format="JPEG", quality=80)
            data = buf.getvalue()

        # 写入内存 + 磁盘缓存
        _mem_put(filename, data)
        _write_cache(cache_path, data)

        return _cached_response(data, cache_hours=24)

    except Exception as e:
        raise HTTPException(500, f"Thumbnail error: {e}")


@router.post("/photos/upload")
def upload_photo(file: UploadFile = File(...)):
    """上传本地照片用于增强，保存到 uploads 目录，返回 upload_id"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext or 'unknown'}")
    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"文件过大（上限 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB）")
    # 唯一文件名：时间戳 + 随机串，避免覆盖
    unique = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(((file.filename or '') + str(time.time())).encode()).hexdigest()[:8]}{ext}"
    save_path = os.path.join(UPLOADS_DIR, unique)
    with open(save_path, "wb") as f:
        f.write(content)
    return {"upload_id": unique, "original_name": file.filename, "size": len(content)}


# ===== 照片库批量上传（手机照片页专用）=====
# 与上面的 /photos/upload 完全分开，不要混用：
#   /photos/upload          → backend/uploads/，增强页的临时素材，**不入照片库**
#   /photos/library/upload  → PHOTOS_DIR/手机照片/，**进照片库**，扫描后相册/时间轴/手机页都能看到
@router.post("/photos/library/upload")
def upload_library_photos(files: list[UploadFile] = File(...), _: None = Depends(check_portal_token)):
    """批量上传照片到照片库（手机照片目录），逐张返回结果

    - 支持同时上传多张（前端「批量上传」）
    - 支持 HEIC/HEIF（已注册 pillow-heif；未安装则记为失败并提示）
    - 自动去重命名（同名时追加 -1/-2…），不会覆盖已有照片
    """
    saved: list[dict] = []
    failed: list[dict] = []
    for f in files:
        raw = f.filename or ""
        ext = os.path.splitext(raw)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            failed.append({"name": raw, "reason": f"不支持的格式 {ext or '（无扩展名）'}"})
            continue
        try:
            content = f.file.read()
            if not content:
                failed.append({"name": raw, "reason": "空文件"})
                continue
            if len(content) > MAX_UPLOAD_BYTES:
                failed.append({"name": raw, "reason": f"文件过大（上限 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB）"})
                continue
            # 校验能否解码（HEIC 依赖 pillow-heif），避免把坏文件写进照片库
            with Image.open(io.BytesIO(content)) as im:
                w, h = im.size
            stem = os.path.splitext(os.path.basename(raw))[0]
            stem = "".join(c for c in stem if c not in '\\/:*?"<>|').strip() or "photo"
            target = os.path.join(PHONE_DIR, f"{stem}{ext}")
            i = 1
            while os.path.exists(target):
                target = os.path.join(PHONE_DIR, f"{stem}-{i}{ext}")
                i += 1
            with open(target, "wb") as out:
                out.write(content)
            saved.append({
                "name": os.path.relpath(target, PHOTOS_DIR).replace("\\", "/"),
                "size": len(content),
                "width": w,
                "height": h,
            })
        except Exception as e:
            failed.append({"name": raw, "reason": f"无法识别为图片（{str(e)[:50]}）"})

    # 让扫描缓存失效，上传完立刻能在列表里看到（否则最多 30 秒后才会出现）
    if saved:
        with _cache_lock:
            _detail_cache["data"] = None
    return {"saved": saved, "failed": failed, "total": len(files)}


@router.get("/photos/enhance/{filename:path}")
def enhance_photo(filename: str, level: int = 2, scale: int = 1, preview: int = 0,
                        upload_id: str = "", portrait: int = 0,
                        skin: float = 1, sharpen: float = 1, brighten: float = 1,
                        bgblur: float = 1, vignette: float = 1):
    """增强照片画质 + 可选超分放大, level: 1-轻量 2-标准 3-极致, scale: 1/2/4 放大倍数
    preview=1: 返回预览图（最大边 2400px，前端显示用，避免浏览器内存爆炸）
    preview=0: 返回全尺寸图（下载用）
    upload_id: 非空则从上传目录读取该照片，否则从相册目录读取
    portrait=1: 额外做人像优化（磨皮/五官锐化/肤色校正/背景虚化，纯传统 CV；定位见 PORTRAIT_DETECTOR）
                响应头 X-Portrait-Subjects 返回定位到的人像数量，X-Portrait-Mode 返回定位方式
    skin/sharpen/brighten/bgblur/vignette: 人像优化各工序强度倍率（0~2，默认 1）
    """
    base_dir = UPLOADS_DIR if upload_id else PHOTOS_DIR
    filepath = _safe_join(base_dir, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(404, "Photo not found")

    # 磁盘缓存（按 filename + level + scale + preview + portrait + 人像强度参数 缓存）
    # v2：管线版本号（增强先于超分 + 人像算法升级），改管线时递增使旧缓存失效
    cache_key = f"u{upload_id or 'lib'}_{filename}_v2"
    fxkey = (f"k{skin:.1f}{sharpen:.1f}{brighten:.1f}{bgblur:.1f}{vignette:.1f}"
             if portrait else "")
    cache_path = _get_cache_path("enhance", cache_key, f"l{level}s{scale}p{preview}pt{portrait}{fxkey}")
    cached = _read_cache(cache_path)
    if cached is not None:
        meta = _read_meta(cache_path)
        extra = ({"X-Portrait-Subjects": meta.get("subjects", ""),
                  "X-Portrait-Mode": meta.get("mode", "")} if portrait else None)
        return _cached_response(cached, cache_hours=72, extra=extra)

    try:
        img = Image.open(filepath)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # 顺序：先在原分辨率做画质增强（锐化保留真实细节），再超分放大，最后轻锐化补偿插值柔化
        img = _apply_enhancement(img, level)
        from superres import super_resolve
        img = super_resolve(img, scale)
        if scale > 1:
            img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=70, threshold=2))

        # 可选：人像优化（纯传统 CV，不依赖任何模型文件/网络）
        subjects = -1
        pmode = ""
        if portrait:
            try:
                from portrait import enhance_portrait
                img, subjects, pmode = enhance_portrait(
                    img, level=level,
                    max_out=2400 if preview else None,   # 预览路径不回写大图，省时
                    fx={"skin": skin, "sharpen": sharpen, "brighten": brighten,
                        "bgblur": bgblur, "vignette": vignette},
                )
            except Exception as e:
                print(f"[Portrait] 人像优化失败({e})，返回基础增强结果")
                subjects = -1

        # 预览模式：缩到最大边 2400px，前端加载轻量
        if preview:
            max_len = 2400
            w, h = img.size
            if max(w, h) > max_len:
                ratio = max_len / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        data = buf.getvalue()

        # 写入磁盘缓存（附带人像检测数，命中缓存时也能返回同样的响应头）
        _write_cache(cache_path, data)
        _write_meta(cache_path, {"subjects": subjects, "mode": pmode,
                                 "portrait": portrait, "level": level})

        extra = ({"X-Portrait-Subjects": subjects, "X-Portrait-Mode": pmode}
                 if portrait else None)
        return _cached_response(data, cache_hours=72, extra=extra)
    except Exception as e:
        raise HTTPException(500, f"Enhance error: {e}")


def _apply_enhancement(img, level: int):
    """按级别增强图片：锐化 + 对比度 + 饱和度（三档差异明显）"""
    from PIL import ImageEnhance

    if level == 1:
        # 轻量级：轻微锐化 + 轻度通透感，几乎不改变原图
        img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=80, threshold=3))
        img = ImageEnhance.Contrast(img).enhance(1.06)
        img = ImageEnhance.Color(img).enhance(1.04)
    elif level == 2:
        # 标准级：明显锐化 + 画面对比度提升，细节更清晰
        img = img.filter(ImageFilter.UnsharpMask(radius=1.8, percent=160, threshold=3))
        img = ImageEnhance.Contrast(img).enhance(1.12)
        img = ImageEnhance.Color(img).enhance(1.08)
        img = ImageEnhance.Brightness(img).enhance(1.02)
    else:
        # 极致级：强锐化 + 去噪 + 高对比度 + 饱和，适合模糊/细节照片
        img = img.filter(ImageFilter.UnsharpMask(radius=2.6, percent=260, threshold=2))
        img = ImageEnhance.Contrast(img).enhance(1.18)
        img = ImageEnhance.Color(img).enhance(1.12)
        img = ImageEnhance.Brightness(img).enhance(1.03)
        # 极致级最后的柔化平滑，抑制强锐化产生的噪点
        img = img.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=3))

    return img


# ===== 回收站（.trash）：删除 → 移入；恢复 → 移回；彻底删除 → 物理移除 =====
# 照片库内文件用相对路径（如 手机照片/IMG_1.jpg）；回收站内文件统一用 `.trash/` 前缀的相对路径
# 便于复用现有缩略图/原图接口（它们按相对路径 _safe_join 到 PHOTOS_DIR 内）


def _abs_trash_path(rel: str) -> str | None:
    """把回收站内相对路径（相对 TRASH_DIR，如 手机照片/IMG_1.jpg）转成绝对路径并校验在其中"""
    base = os.path.abspath(TRASH_DIR)
    full = os.path.abspath(os.path.join(base, rel.replace("/", os.sep)))
    if full != base and not full.startswith(base + os.sep):
        return None
    return full


def _drop_thumb_cache(rel: str) -> None:
    """清掉某相对路径的缩略图缓存（内存 + 磁盘）

    照片被移入回收站 / 恢复 / 彻底删除后，原路径的缓存不会再被访问；
    不清就会变成磁盘孤儿（每张约 20–200KB），这里顺手回收。
    """
    key = str(rel).replace("\\", "/")
    with _cache_lock:
        _thumbnail_cache.pop(key, None)
    try:
        p = _get_cache_path("thumb", key)
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


@router.post("/photos/trash")
def trash_photos(names: list[str] = Body(..., embed=True), _: None = Depends(check_portal_token)):
    """把选中的照片移入回收站（保留原相对路径，扫描器自动跳过 .trash，各页面立即消失）"""
    moved: list[str] = []
    failed: list[dict] = []
    trash_abs = os.path.abspath(TRASH_DIR)
    for name in names:
        rel = str(name).replace("\\", "/")
        # 防御：已在回收站内的路径不再二次移入（否则会嵌套成 .trash/.trash/…，original 路径错乱）
        if rel.startswith(".trash/"):
            failed.append({"name": name, "reason": "该文件已在回收站"})
            continue
        src = _abs_photo_path(name)
        if not src or not os.path.isfile(src):
            failed.append({"name": name, "reason": "文件不存在"})
            continue
        dst = os.path.abspath(os.path.join(TRASH_DIR, rel.replace("/", os.sep)))
        # 防御：目标必须落在回收站目录内
        if not dst.startswith(trash_abs + os.sep):
            failed.append({"name": name, "reason": "无效路径"})
            continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)  # 同盘移动，原子
            moved.append(name)
            _drop_thumb_cache(rel)
        except Exception as e:
            print(f"[Trash] move failed: {e!r} | src={src!r} | dst={dst!r} | trash_dir={TRASH_DIR!r}")
            failed.append({"name": name, "reason": str(e)[:200]})
    if moved:
        with _cache_lock:
            _detail_cache["data"] = None
    return {"moved": moved, "failed": failed}


@router.get("/photos/trash/list")
def list_trash():
    """列出回收站照片：name 带 .trash/ 前缀（可直接用于缩略图/原图接口），original 为原相对路径"""
    items: list[dict] = []
    for root, _dirs, files in os.walk(TRASH_DIR):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, TRASH_DIR).replace(os.sep, "/")
            try:
                mtime = os.path.getmtime(full)
                size = os.path.getsize(full)
            except OSError:
                continue
            dt = datetime.fromtimestamp(mtime)
            items.append({
                "name": f".trash/{rel}",
                "original": rel,
                "folder": os.path.dirname(rel),
                "date": dt.strftime("%Y-%m-%d"),
                "timestamp": mtime,
                "size": size,
            })
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items


@router.post("/photos/trash/restore")
def restore_photos(names: list[str] = Body(..., embed=True), _: None = Depends(check_portal_token)):
    """把回收站照片移回原目录；原位置已有同名照片时自动追加 -1/-2…（不覆盖）"""
    restored: list[dict] = []
    failed: list[dict] = []
    for n in names:
        name = n.replace("\\", "/")
        if not name.startswith(".trash/"):
            failed.append({"name": n, "reason": "无效路径"})
            continue
        rel = name[len(".trash/"):]  # 原相对路径（相对照片库根目录）
        src = _abs_trash_path(rel.replace("/", os.sep))
        if not src or not os.path.isfile(src):
            failed.append({"name": n, "reason": "文件不存在"})
            continue
        target = os.path.join(PHOTOS_DIR, rel.replace("/", os.sep))
        if os.path.exists(target):
            stem, ext = os.path.splitext(os.path.basename(rel))
            folder = os.path.dirname(target)
            i = 1
            while True:
                cand = os.path.join(folder, f"{stem}-{i}{ext}")
                if not os.path.exists(cand):
                    target = cand
                    break
                i += 1
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            os.replace(src, target)
            restored.append({
                "name": n,
                "restored": os.path.relpath(target, PHOTOS_DIR).replace(os.sep, "/"),
            })
            _drop_thumb_cache(n)  # 回收站路径的缩略图缓存已无用
        except Exception as e:
            failed.append({"name": n, "reason": str(e)[:80]})
    if restored:
        with _cache_lock:
            _detail_cache["data"] = None
    return {"restored": restored, "failed": failed}


@router.post("/photos/trash/purge")
def purge_photos(names: list[str] = Body(..., embed=True), _: None = Depends(check_portal_token)):
    """彻底删除回收站中的照片（不可找回）"""
    purged: list[str] = []
    failed: list[dict] = []
    for n in names:
        name = n.replace("\\", "/")
        if not name.startswith(".trash/"):
            failed.append({"name": n, "reason": "无效路径"})
            continue
        rel = name[len(".trash/"):]
        full = _abs_trash_path(rel.replace("/", os.sep))
        if not full or not os.path.isfile(full):
            failed.append({"name": n, "reason": "文件不存在"})
            continue
        try:
            os.remove(full)
            purged.append(n)
            _drop_thumb_cache(n)  # 清掉回收站路径的缩略图缓存，避免磁盘孤儿
        except Exception as e:
            failed.append({"name": n, "reason": str(e)[:80]})
    return {"purged": purged, "failed": failed}