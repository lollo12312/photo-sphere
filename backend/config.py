import os

# 照片库根目录：优先读环境变量 PHOTOS_DIR（方便别人 clone 后指向自己的照片目录），
# 未设置时用默认路径；手机照片目录 / 回收站都自动建在它下面
PHOTOS_DIR = os.environ.get("PHOTOS_DIR", r"D:\LOLLO\Pictures")

# ===== 公众号 H5 访问令牌（可选）=====
# 自测玩可忽略（保持空则不校验）；想让「局域网/手机也能访问」时设一个：
#   1) 启动时设环境变量 PORTAL_TOKEN=你的口令（如 PORTAL_TOKEN=abc123 python main.py）
#   2) 前端 H5 用 URL ?token=abc123 打开，或在小程序/公众号页面里带上 token
#   3) 所有照片库写接口（上传/删除/恢复/彻底删除）校验 token，读接口不校验（网页浏览无感）
# 注意：设了 token 后，桌面浏览器（Vue Web）调用写接口同样需要带 token（?token=xxx）
PORTAL_TOKEN = os.environ.get("PORTAL_TOKEN", "").strip()

# ===== 两个上传目录，用途完全不同，不要混用 =====
# 1) UPLOADS_DIR：增强页的临时素材（「上传照片 → 增强/超分/人像」），**不入照片库**，相册里看不到
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 2) PHONE_DIR：手机照片页的批量上传目录，位于**照片库内**（PHOTOS_DIR/手机照片/），
#    扫描后即在相册/时间轴/手机页可见，用户也能在资源管理器里管理
PHONE_DIR = os.path.join(PHOTOS_DIR, "手机照片")
try:
    os.makedirs(PHONE_DIR, exist_ok=True)
except Exception:
    pass

# 3) TRASH_DIR：回收站（照片库内 .trash/ 子目录）。
#    `.` 开头的目录会被 _scan_photo_paths 跳过，相册/球体/时间轴自动看不到；
#    删除 = 移入这里（保留原相对路径），恢复 = 移回，彻底删除 = 物理移除
TRASH_DIR = os.path.join(PHOTOS_DIR, ".trash")
try:
    os.makedirs(TRASH_DIR, exist_ok=True)
except Exception as e:
    print(f"[Trash] 创建回收站目录失败：{e}")

THUMBNAIL_SIZE = (480, 0)  # (width, height) — height=0 means auto aspect ratio
# 含 HEIC/HEIF（iPhone 默认格式），由 routers/photos.py 里注册的 pillow-heif 负责解码
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif")