import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MODULES_DIR = BASE_DIR / "modules"
DATABASE_DIR = BASE_DIR / "database"
ASSETS_DIR = BASE_DIR / "assets"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = BASE_DIR / "web" / "static" / "uploads"
YOLO_WEIGHTS = ASSETS_DIR / "yolo_weights"

DATABASE_PATH = str(DATABASE_DIR / "products.db")

WEBCAM_INDEX = int(os.getenv("SMARTCART_WEBCAM_INDEX", "0"))
VIDEO_WIDTH = int(os.getenv("SMARTCART_VIDEO_WIDTH", "1280"))
VIDEO_HEIGHT = int(os.getenv("SMARTCART_VIDEO_HEIGHT", "720"))
VIDEO_FPS = int(os.getenv("SMARTCART_VIDEO_FPS", "30"))
SAMPLE_VIDEO_PATH = str(ASSETS_DIR / "sample_video.mp4")

BARCODE_SCAN_DELAY = 2
BARCODE_COOLDOWN = float(os.getenv("SMARTCART_BARCODE_COOLDOWN", "3.0"))

YOLO_MODEL = os.getenv("SMARTCART_YOLO_MODEL", "yolov8n.pt")
DETECTION_CONFIDENCE = float(os.getenv("SMARTCART_DETECTION_CONFIDENCE", "0.5"))
PERSON_CLASS_ID = 0

MAX_TRACKING_AGE = int(os.getenv("SMARTCART_MAX_TRACKING_AGE", "30"))
TRACKING_IOU = float(os.getenv("SMARTCART_TRACKING_IOU", "0.3"))

DASHBOARD_TITLE = "Smart Shopping Cart"
DASHBOARD_WIDTH = 500
DASHBOARD_HEIGHT = 700
DASHBOARD_BG_COLOR = "#1a1a2e"
DASHBOARD_FG_COLOR = "#ffffff"
ACCENT_COLOR = "#e94560"
SUCCESS_COLOR = "#0f9b58"
WARNING_COLOR = "#f5a623"

MAX_CART_ITEMS = int(os.getenv("SMARTCART_MAX_CART_ITEMS", "50"))
TAX_RATE = float(os.getenv("SMARTCART_TAX_RATE", "0.08"))
CURRENCY_SYMBOL = os.getenv("SMARTCART_CURRENCY_SYMBOL", "$")

LOG_FILE = str(LOGS_DIR / "cart_session.log")
LOG_LEVEL = os.getenv("SMARTCART_LOG_LEVEL", "INFO")

SUMMARY_OUTPUT = str(OUTPUT_DIR / "summary_report.txt")

CAMERA_WINDOW = "Smart Cart - Camera View"
DASHBOARD_WINDOW = "Smart Cart - Dashboard"

# ── Colors for OpenCV (BGR Format) ───────────────────────────
CV_RED               = (0, 0, 255)
CV_GREEN             = (0, 255, 0)
CV_BLUE              = (255, 0, 0)
CV_WHITE             = (255, 255, 255)
CV_YELLOW            = (0, 255, 255)
CV_ORANGE            = (0, 165, 255)
CV_CYAN              = (255, 255, 0)
CV_BLACK             = (0, 0, 0)

INPUT_MODE = os.getenv("SMARTCART_INPUT_MODE", "webcam")

for directory in (DATABASE_DIR, LOGS_DIR, OUTPUT_DIR, UPLOAD_DIR):
    directory.mkdir(parents=True, exist_ok=True)
