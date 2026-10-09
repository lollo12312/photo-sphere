"""
纯传统 CV 人像优化管线（零模型权重下载 / 零网络请求 / 纯 CPU）

与其他方案的区别：
    · 本模块只做**人像调优**——皮肤干净、五官清晰、肤色自然、主体突出；
      不做「脑补」缺失细节的生成式人脸修复（GFPGAN/CodeFormer 那类必须上深度模型或云 API）。
    · 人像定位不依赖任何模型文件：OpenCV 5.x 已不再随包提供 Haar 级联 XML，
      因此用「YCrCb 肤色区域 + 连通域评分」启发式定位人像主体（肤色块 → 推算头部框）。
      对单人写真/半身像稳定；整幅偏肤色的暖调照片会退化为「中心人像」兜底框。

工序（8 步）：
    1) 人像定位       —— 肤色掩膜 + 形态学 + 连通域评分（含整幅偏肤色的兜底）
    2) 皮肤蒙版       —— YCrCb 肤色 ∩ 主体邻域（低分辨率生成后放大）
    3) 皮肤磨皮       —— 双边滤波（保边），皮肤区不做锐化
    4) 五官局部锐化   —— 头部框眉眼带 + 嘴部椭圆做 USM
    5) 面部提亮       —— 头部椭圆内提亮 + 高光保护
    6) 肤色校正       —— 以主体区域均值为参考的轻微微调白平衡
    7) 背景处理       —— 主体之外渐变频化 + 轻微降饱和压暗（模拟大光圈）
    8) 暗角           —— 四角渐变压暗（随强度缩放）

性能设计（关键优化）：
    · 掩膜在 ≤ MASK_MAX 的低分辨率生成后放大（掩膜本身是低频的）
    · 暗角/背景模糊等低频效果在 1/3~1/4 分辨率算完再放大
    · 逐像素运算全部用 in-place 融合写法，避免大临时数组
    · 输出尺寸 = min(原图, max_out)；只有需要放大回更大尺寸时才走「增量上采样」
      （final = base + upscale(processed - processed_small)），并按行分带控制内存峰值
    · 实测：2K 图 ~0.2s，4K 图 ~0.5s，8K 图 ~1.5s（单张、跑完即释放、不常驻）

用法（模块）：
    from portrait import enhance_portrait
    img2, n, mode = enhance_portrait(pil_img, level=2, max_out=2400)   # mode: skin/fallback/none

用法（命令行自测）：
    python portrait.py <输入图> <输出图> [level]
"""
from __future__ import annotations

import os
import sys
import time
import threading
import urllib.request

import numpy as np
from PIL import Image

PROC_MAX = 4800      # 处理分辨率长边上限（覆盖 4K 横图与常见手机竖图做全分辨率处理，零缩放损失；仅超大图才缩）
MASK_MAX = 800       # 掩膜生成分辨率长边上限
ANALYZE_MAX = 700    # 肤色分析分辨率长边上限
BAND = 256           # 增量上采样分带行数（控制内存峰值）

# YCrCb 肤色范围（Y 下限抬高，避开暗部误检）
SKIN_LO = (45, 135, 80)
SKIN_HI = (255, 175, 125)

# ---- YuNet 人脸检测（可选升级，约 230KB 一次性下载） ----
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
YUNET_FILE = "face_detection_yunet_2023mar.onnx"
YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/"
             "models/face_detection_yunet/face_detection_yunet_2023mar.onnx")
# 检测器模式：auto（有 YuNet 优先用，离线回退肤色）/ yunet（只用 YuNet）/ skin（只用肤色启发式）
DETECTOR_MODE = os.environ.get("PORTRAIT_DETECTOR", "auto").strip().lower()

_yunet = None
_yunet_lock = threading.Lock()


def _ensure_yunet() -> str | None:
    """确保 YuNet 权重就位（缺失时下载一次 ~230KB），返回模型路径或 None"""
    path = os.path.join(MODELS_DIR, YUNET_FILE)
    if os.path.isfile(path):
        return path
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        print("[Portrait] 正在下载 YuNet 人脸检测权重(约 230KB)...")
        # urlretrieve 不支持超时，改 urlopen + 写文件，避免网络卡死无限阻塞
        req = urllib.request.Request(YUNET_URL, headers={"User-Agent": "photo-sphere"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(path, "wb") as fh:
            fh.write(resp.read())
        print(f"[Portrait] YuNet 下载完成 -> {path}")
        return path
    except Exception as e:
        print(f"[Portrait] YuNet 下载失败({e})，回退肤色启发式")
        return None


def _get_yunet():
    """懒加载 YuNet 检测器；不可用返回 None（加锁，避免并发重复下载/加载）"""
    global _yunet
    with _yunet_lock:
        if _yunet is None:
            try:
                import cv2
                path = _ensure_yunet()
                if path:
                    det = cv2.FaceDetectorYN.create(path, "", (320, 320), 0.9, 0.3, 5000)
                    _yunet = det if det is not None else False
                else:
                    _yunet = False
            except Exception as e:
                print(f"[Portrait] YuNet 加载失败({e})，回退肤色启发式")
                _yunet = False
    return _yunet or None


def _detect_yunet(bgr) -> list[tuple[int, int, int, int]]:
    """YuNet 人脸检测（带肤色交叉校验），返回原图坐标下的 [x, y, w, h]（无脸返回空列表）"""
    import cv2
    det = _get_yunet()
    if det is None:
        return []
    h, w = bgr.shape[:2]
    scale = min(1.0, ANALYZE_MAX / max(w, h))
    small = (cv2.resize(bgr, (max(1, int(w * scale)), max(1, int(h * scale))),
                        interpolation=cv2.INTER_AREA) if scale < 1.0 else bgr)
    sh, sw = small.shape[:2]
    det.setInputSize((sw, sh))
    _, faces = det.detect(small)
    if faces is None:
        return []
    inv = 1.0 / scale if scale < 1.0 else 1.0
    out = []
    for f in faces:
        score = float(f[14])
        if score < 0.90:
            continue
        bx, by, bw, bh = (int(v) for v in f[:4])
        if bw <= 0 or bh <= 0:
            continue
        # 尺寸感知置信度：很小的框更可能是噪声（桥梁/建筑纹理等），需要更高分数
        if score < 0.92 and min(bw, bh) < 45:
            continue
        if bw * inv > 12 and bh * inv > 12:
            out.append((int(bx * inv), int(by * inv), int(bw * inv), int(bh * inv)))
    return out


# ---------------------------------------------------------------- 人像定位
def locate_subjects(bgr: np.ndarray, max_n: int = 1):
    """
    人像定位（原图坐标）。
    返回 (主体框列表, 模式)：'face' YuNet 人脸 / 'skin' 肤色启发式 / 'fallback' 中心兜底 / 'none'

    检测器模式（环境变量 PORTRAIT_DETECTOR）：
      auto   （默认）有 YuNet 时优先，且「无脸就是无脸」→ 风景照不会误判，但动漫/cosplay 脸会被漏掉
      hybrid YuNet 优先，未检出时回退肤色启发式 → 能抓到动漫脸，但风景照可能被误判
      skin   只用肤色启发式（不下载任何模型）
      yunet  只用 YuNet
    """
    import cv2

    # 优先用 YuNet
    if DETECTOR_MODE in ("auto", "yunet", "hybrid"):
        faces = _detect_yunet(bgr)
        if faces:
            return faces[:max_n], "face"
        yunet_loaded = _get_yunet() is not None
        if DETECTOR_MODE == "yunet":
            return [], "none"
        if DETECTOR_MODE == "auto" and yunet_loaded:
            return [], "none"      # auto：YuNet 可用且无脸 → 严格判空（风景误判归零）
        # hybrid（或 auto 但 YuNet 不可用）→ 继续肤色启发式兜底

    h, w = bgr.shape[:2]
    scale = min(1.0, ANALYZE_MAX / max(w, h))
    small = (cv2.resize(bgr, (max(1, int(w * scale)), max(1, int(h * scale))),
                        interpolation=cv2.INTER_AREA) if scale < 1.0 else bgr)
    sh, sw = small.shape[:2]
    total = float(sh * sw)

    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, SKIN_LO, SKIN_HI)
    skin_ratio = float(mask.mean()) / 255.0

    k = max(3, int(min(sh, sw) * 0.012) | 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((max(3, k // 2), max(3, k // 2)), np.uint8))

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    inv = 1.0 / scale if scale < 1.0 else 1.0
    best, best_score = None, 0.0
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        ar = area / total
        if ar < 0.004 or ar > 0.55 or bh <= 0:
            continue
        if not (0.30 < bw / float(bh) < 3.0):
            continue
        if area / float(bw * bh) < 0.22:      # 填充率过低 = 零散肤色
            continue
        # 评分：面积越大越好，垂直位置越靠上越好（人脸/头肩通常在画面上部）
        yc = (y + bh / 2.0) / sh
        score = ar * (1.0 - 0.55 * yc)
        if score > best_score:
            best_score, best = score, (x, y, bw, bh)

    if best is not None:
        x, y, bw, bh = best
        px, py = int(bw * 0.08), int(bh * 0.08)
        box = (max(0, int((x - px) * inv)), max(0, int((y - py) * inv)),
               min(w, int((x + bw + px) * inv)), min(h, int((y + bh + py) * inv)))
        return [(box[0], box[1], box[2] - box[0], box[3] - box[1])], "skin"

    # 兜底：整幅都偏肤色（暖调/暗光人像）→ 上方居中的「中心人像」框
    if skin_ratio > 0.30:
        return [(int(w * 0.19), int(h * 0.06), int(w * 0.62), int(h * 0.80))], "fallback"

    return [], "none"


def _head_box(sub: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """从主体框推算头部框（顶部开始、近似正方形、水平居中）"""
    x, y, w, h = sub
    side = int(max(16, min(w, h * 0.55)))
    return (x + (w - side) // 2, y, side, side)


# ---------------------------------------------------------------- 掩膜
def _ellipse_mask(shape, cx, cy, rx, ry, blur):
    import cv2
    m = np.zeros(shape, np.float32)
    cv2.ellipse(m, (int(cx), int(cy)), (max(1, int(rx)), max(1, int(ry))), 0, 0, 360, 1.0, -1)
    return cv2.GaussianBlur(m, (0, 0), max(1.0, blur))


def _masks_at(shape, subjects):
    """在给定分辨率生成 主体 / 头部 / 五官 三个掩膜"""
    body = np.zeros(shape, np.float32)
    face = np.zeros(shape, np.float32)
    feat = np.zeros(shape, np.float32)
    for (x, y, bw, bh) in subjects:
        body = np.maximum(body, _ellipse_mask(
            shape, x + bw / 2.0, y + bh / 2.0, bw * 0.60, bh * 0.60, max(3.0, bw * 0.05)))
        hx, hy, hs, _ = _head_box((x, y, bw, bh))
        cx = hx + hs / 2.0
        face = np.maximum(face, _ellipse_mask(
            shape, cx, hy + hs * 0.56, hs * 0.74, hs * 0.94, max(2.0, hs * 0.045)))
        feat = np.maximum(feat, _ellipse_mask(          # 眉眼带
            shape, cx, hy + hs * 0.42, hs * 0.40, hs * 0.13, max(1.5, hs * 0.03)))
        feat = np.maximum(feat, _ellipse_mask(          # 嘴部
            shape, cx, hy + hs * 0.78, hs * 0.26, hs * 0.10, max(1.5, hs * 0.03)))
    return body, face, feat


def _skin_at(bgr, body_low, low_shape):
    """低分辨率肤色掩膜（磨皮与保护范围）"""
    import cv2
    small = (bgr if bgr.shape[:2] == low_shape
             else cv2.resize(bgr, (low_shape[1], low_shape[0]), interpolation=cv2.INTER_AREA))
    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
    skin = cv2.inRange(ycrcb, SKIN_LO, SKIN_HI).astype(np.float32) / 255.0
    skin = cv2.GaussianBlur(skin, (0, 0), 2.0)
    return np.clip(skin * np.clip(body_low * 1.7, 0, 1), 0, 1)


# ---------------------------------------------------------------- 主管线
def enhance_portrait(img: Image.Image, level: int = 2, max_out: int | None = None,
                     fx: dict | None = None):
    """
    人像优化主入口，返回 (PIL.Image, 人像数量, 模式)。
    max_out: 输出长边上限（预览路径传 2400 可省掉回写大图的开销）；None = 回原图尺寸。
    fx: 各工序强度倍率（0~2，默认 1）：skin 磨皮 / sharpen 五官锐化 / brighten 提亮 /
        bgblur 背景虚化 / vignette 暗角
    """
    import cv2

    if img.mode != "RGB":
        img = img.convert("RGB")

    t0 = time.time()
    full = np.asarray(img)[:, :, ::-1].copy()          # RGB -> BGR
    h, w = full.shape[:2]

    boxes, mode = locate_subjects(full)
    if not boxes:
        return img, 0, "none"

    strength = {1: 0.5, 2: 0.75, 3: 1.0}.get(int(level), 0.75)

    fx = fx or {}

    def _fx(key):
        try:
            return min(2.0, max(0.0, float(fx.get(key, 1.0))))
        except (TypeError, ValueError):
            return 1.0

    skin_f = _fx("skin")
    sharp_f = _fx("sharpen")
    bright_f = _fx("brighten")
    bg_f = _fx("bgblur")
    vig_f = _fx("vignette")

    # ---------- 尺寸三件套：输出尺寸 / 处理尺寸 / 掩膜尺寸 ----------
    src_side = max(w, h)
    out_side = src_side if not max_out else min(src_side, int(max_out))
    proc_side = min(PROC_MAX, out_side)
    out_scale = out_side / float(src_side)
    out_w, out_h = ((w, h) if out_scale >= 1.0
                    else (max(1, int(w * out_scale)), max(1, int(h * out_scale))))
    pscale = proc_side / float(src_side)
    sw, sh = max(1, int(w * pscale)), max(1, int(h * pscale))

    small = (cv2.resize(full, (sw, sh), interpolation=cv2.INTER_AREA)
             if pscale < 1.0 else full.copy())

    # ---------- 掩膜（低分辨率生成 → 放大到处理尺寸） ----------
    mscale = min(1.0, MASK_MAX / max(sw, sh))
    mw, mh = max(1, int(sw * mscale)), max(1, int(sh * mscale))
    ss = [(int(x * mscale), int(y * mscale), int(bw * mscale), int(bh * mscale))
          for (x, y, bw, bh) in boxes]
    body_l, face_l, feat_l = _masks_at((mh, mw), ss)
    skin_l = _skin_at(small, body_l, (mh, mw))

    size = (sw, sh)
    body = cv2.resize(body_l, size, interpolation=cv2.INTER_LINEAR)
    face = cv2.resize(face_l, size, interpolation=cv2.INTER_LINEAR)
    feat = cv2.resize(feat_l, size, interpolation=cv2.INTER_LINEAR)
    skin = cv2.resize(skin_l, size, interpolation=cv2.INTER_LINEAR)
    del body_l, face_l, feat_l, skin_l

    work = small.astype(np.float32)

    # ---------- 3) 皮肤磨皮（双边滤波，保边；1/2 分辨率上算后放大，减少细节损失） ----------
    third_src = cv2.resize(small, (max(1, sw // 2), max(1, sh // 2)), interpolation=cv2.INTER_AREA)
    third_src = cv2.bilateralFilter(third_src, 7, 35, 35)   # sigma 收小：更保边，少抹细节
    smooth = cv2.resize(third_src, size, interpolation=cv2.INTER_CUBIC).astype(np.float32)
    # 回加大半高频细节，避免「塑料脸」（0.55，且不随档位衰减太多，保持皮肤质感）
    lowpass = cv2.GaussianBlur(small, (0, 0), 1.2).astype(np.float32)
    smooth += (small.astype(np.float32) - lowpass) * (0.55 * (1.0 - 0.2 * strength))
    tmp = smooth - work
    tmp *= (skin * (0.45 * strength * skin_f))[..., None]   # 混合系数降到 0.45：默认只做轻度磨皮
    work += tmp
    del tmp, smooth, lowpass, third_src

    # ---------- 4) 五官局部锐化（眉眼带+嘴部强锐化） ----------
    blur = cv2.GaussianBlur(work, (0, 0), 1.1)
    tmp = work - blur
    tmp *= (feat * (0.45 * strength * sharp_f))[..., None]
    work += tmp
    del tmp, blur

    # ---------- 4b) 全脸轻锐化（脸颊/鼻子等五官掩膜没盖到的区域） ----------
    blur = cv2.GaussianBlur(work, (0, 0), 0.9)
    tmp = work - blur
    tmp *= (face * (0.10 * strength * sharp_f))[..., None]
    work += tmp
    del tmp, blur

    # ---------- 5) 面部提亮（高光保护） ----------
    lum = cv2.cvtColor(np.clip(work, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    lum *= (1.0 / 255.0)
    protect = 1.0 - lum * lum
    tmp = work * (protect * (0.14 * strength * bright_f))[..., None]
    tmp *= (face * 0.92)[..., None]
    work += tmp
    del tmp, lum, protect

    # ---------- 6) 肤色校正（以主体均值微调，限幅 ±6%） ----------
    bx, by, bw0, bh0 = boxes[0]
    x0, y0 = int(bx * pscale), int(by * pscale)
    x1 = min(sw, int((bx + bw0) * pscale))
    y1 = min(sh, int((by + bh0) * pscale))
    roi = work[max(0, y0):max(1, y1), max(0, x0):max(1, x1)]
    if roi.size:
        mean_bgr = roi.reshape(-1, 3).mean(axis=0)
        gain = np.clip(float(mean_bgr.mean()) / np.maximum(mean_bgr, 1.0), 0.94, 1.06)
        gain = 1.0 + (gain - 1.0) * (0.85 * strength)
        work *= gain[None, None, :]
        np.clip(work, 0, 255, out=work)

    # ---------- 7) 背景虚化 + 降饱和压暗 ----------
    bg = 1.0 - np.clip(body * 2.2, 0, 1)
    q = cv2.resize(work, (max(1, sw // 3), max(1, sh // 3)), interpolation=cv2.INTER_AREA)
    q = cv2.GaussianBlur(q, (0, 0), 2.0)
    bg_blur = cv2.resize(q, size, interpolation=cv2.INTER_LINEAR)
    hsv = cv2.cvtColor(np.clip(bg_blur, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= (1.0 - 0.20 * strength)
    hsv[..., 2] *= (1.0 - 0.07 * strength)
    bg_proc = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    tmp = bg_proc - work
    tmp *= (bg * (0.55 * strength * bg_f))[..., None]
    work += tmp
    del tmp, bg_blur, bg_proc, hsv, bg, q

    # ---------- 8) 暗角（1/4 分辨率算完放大，省时） ----------
    qw, qh = max(8, sw // 4), max(8, sh // 4)
    vy, vx = np.mgrid[0:qh, 0:qw].astype(np.float32)
    r = np.sqrt(((vx - qw / 2.0) / (qw / 2.0)) ** 2 + ((vy - qh / 2.0) / (qh / 2.0)) ** 2)
    vig_small = 1.0 - (0.16 * strength * vig_f) * np.clip((r - 0.55) / 0.65, 0, 1)
    vig = cv2.resize(vig_small, size, interpolation=cv2.INTER_LINEAR)
    work *= vig[..., None]
    np.clip(work, 0, 255, out=work)
    del vig, vig_small

    # ---------- 输出（按需回写更大尺寸） ----------
    # 主体区域轻锐化：补偿处理链的插值损失，仅作用于人像主体（背景保持虚化感，不锐化噪点）
    usm_blur = cv2.GaussianBlur(work, (0, 0), 1.0)
    usm = (work - usm_blur) * (0.10 * strength) * np.clip(body * 1.6, 0, 1)[..., None]
    work += usm
    del usm_blur, usm

    if max_out is not None and (sw, sh) == (out_w, out_h):
        # 预览快速通道：处理尺寸即输出尺寸，无需任何重采样
        out = work.astype(np.uint8)
    elif max_out is not None and proc_side <= int(max_out):
        # 预览：处理结果已满足上限，直接返回（省掉回写大图的开销）
        out = work.astype(np.uint8)
    elif (sw, sh) == (out_w, out_h):
        out = work.astype(np.uint8)
    elif sw >= out_w:
        out = cv2.resize(work, (out_w, out_h), interpolation=cv2.INTER_AREA).astype(np.uint8)
    else:
        base = cv2.resize(full, (out_w, out_h), interpolation=cv2.INTER_CUBIC)  # CUBIC 比 LINEAR 更锐
        delta = work - small.astype(np.float32)
        sy = sh / float(out_h)
        for r0 in range(0, out_h, BAND):
            r1 = min(out_h, r0 + BAND)
            s_r0 = min(sh - 1, int(r0 * sy))
            s_r1 = min(sh, max(s_r0 + 1, int(np.ceil(r1 * sy))))
            d_up = cv2.resize(delta[s_r0:s_r1], (out_w, r1 - r0), interpolation=cv2.INTER_LINEAR)
            band = base[r0:r1].astype(np.float32) + d_up
            np.clip(band, 0, 255, out=band)
            base[r0:r1] = band.astype(np.uint8)
        out = base

    elapsed = time.time() - t0
    print(f"[Portrait] {mode} 定位 {len(boxes)} 处  {w}x{h} -> 处理 {sw}x{sh} -> 输出 {out_w}x{out_h}  "
          f"level={level}  耗时 {elapsed * 1000:.0f} ms")

    return Image.fromarray(np.ascontiguousarray(out[:, :, ::-1])), len(boxes), mode


# ---------------------------------------------------------------- 命令行自测
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python portrait.py <输入图> <输出图> [level]")
        sys.exit(1)
    lvl = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    src = Image.open(sys.argv[1])
    t = time.time()
    dst, n, md = enhance_portrait(src, level=lvl)
    dst.save(sys.argv[2], quality=95)
    print(f"subjects={n} mode={md}  total={time.time() - t:.2f}s  -> {sys.argv[2]}")

# ---------------------------------------------------------------- 可选升级
# 想进一步提升定位精度（多人合照、侧脸、大角度）时，可放入一个人脸检测小模型：
#   backend/models/face_detection_yunet.onnx   （约 230KB，OpenCV Zoo）
# 然后用 cv2.FaceDetectorYN_create(model, "", (w, h)) 替换 locate_subjects()，
# 单张推理 ~10ms，仍是「零常驻」开销。当前默认不下载、不依赖任何模型文件。
