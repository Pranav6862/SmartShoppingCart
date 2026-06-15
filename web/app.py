# ============================================================
# SmartShoppingCart/web/app.py
# Flask Web Server - Enhanced UI + Robot Status
# ============================================================

import logging
import os
import sys
import math
import threading
import time
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from datetime import datetime
from flask import (
    Flask, render_template,
    Response, request, jsonify
)
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from config import (
    CURRENCY_SYMBOL,
    TAX_RATE,
    BARCODE_COOLDOWN,
    LOG_LEVEL,
    UPLOAD_DIR,
)
from modules.barcode_scanner  import BarcodeScanner
from modules.person_detector  import PersonDetector
from modules.customer_tracker import CustomerTracker
from modules.smart_cart       import SmartCart
from modules.video_handler    import VideoHandler, VideoSource

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# FLASK SETUP
# ============================================================

app = Flask(
    __name__,
    template_folder = "templates",
    static_folder   = "static"
)
app.config["SECRET_KEY"]           = os.getenv("SMARTCART_SECRET_KEY", "dev-smartcart-change-me")
app.config["UPLOAD_FOLDER"]        = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"]   = 500 * 1024 * 1024

socketio = SocketIO(
    app,
    cors_allowed_origins = "*",
    async_mode          = "threading"
)

ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
MAX_CUSTOMER_NAME_LENGTH = 80

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# ============================================================
# ROBOT STATUS SYSTEM
# ============================================================

class RobotStatus:
    """Simulates robot hardware status"""

    def __init__(self):
        self.start_time       = time.time()
        self.is_active        = False

        # ── Drive System ──────────────────────────────────────
        self.motor_left_speed  = 0       # -100 to 100
        self.motor_right_speed = 0
        self.is_moving         = False
        self.direction         = "idle"  # forward/backward/left/right/idle
        self.total_distance    = 0.0     # meters
        self.wheel_rpm         = 0

        # ── Sensors ───────────────────────────────────────────
        self.ultrasonic_front  = 999.0   # cm
        self.ultrasonic_left   = 999.0
        self.ultrasonic_right  = 999.0
        self.obstacle_detected = False
        self.obstacle_dir      = None

        # ── Power System ──────────────────────────────────────
        self.battery_level     = 87.0    # percent
        self.battery_voltage   = 12.4    # volts
        self.current_draw      = 0.0     # amps
        self.power_status      = "normal"

        # ── Camera Mount ──────────────────────────────────────
        self.camera_pan        = 0       # degrees -90 to 90
        self.camera_tilt       = 0       # degrees -45 to 45
        self.camera_active     = False

        # ── Navigation ────────────────────────────────────────
        self.position_x        = 0.0
        self.position_y        = 0.0
        self.heading           = 0.0     # degrees 0-360
        self.target_x          = None
        self.target_y          = None
        self.following_customer= False

        # ── System Health ─────────────────────────────────────
        self.cpu_temp          = 42.0    # celsius
        self.cpu_usage         = 35.0    # percent
        self.ram_usage         = 48.0    # percent
        self.uptime            = 0       # seconds

        # ── Alerts ────────────────────────────────────────────
        self.alerts            = []
        self.error_count       = 0

        # ── Simulate Updates ──────────────────────────────────
        self._sim_thread = threading.Thread(
            target=self._simulate_loop,
            daemon=True
        )
        self._sim_thread.start()

    def activate(self, customer_locked=False):
        """Activate robot when session starts"""
        self.is_active         = True
        self.camera_active     = True
        self.following_customer= customer_locked
        self.direction         = "following" if customer_locked else "idle"
        self.alerts            = []

    def deactivate(self):
        """Deactivate robot"""
        self.is_active         = False
        self.camera_active     = False
        self.following_customer= False
        self.motor_left_speed  = 0
        self.motor_right_speed = 0
        self.is_moving         = False
        self.direction         = "idle"
        self.wheel_rpm         = 0
        self.current_draw      = 0.0

    def set_following(self, following, locked_id=None):
        """Update following state"""
        self.following_customer = following
        if following:
            self.direction         = "following"
            self.motor_left_speed  = 45
            self.motor_right_speed = 45
            self.is_moving         = True
        else:
            self.direction         = "idle"
            self.motor_left_speed  = 0
            self.motor_right_speed = 0
            self.is_moving         = False

    def _simulate_loop(self):
        """Simulate robot sensor data"""
        t = 0
        while True:
            t    += 0.1
            self.uptime = int(time.time() - self.start_time)

            if self.is_active:
                # ── Battery drain ─────────────────────────────
                self.battery_level = max(
                    5.0,
                    self.battery_level - 0.002
                )
                self.battery_voltage = 9.0 + (
                    self.battery_level / 100.0 * 3.6
                )

                # ── Ultrasonic sensors ────────────────────────
                if self.following_customer:
                    self.ultrasonic_front = 80 + math.sin(t) * 30
                    self.ultrasonic_left  = 120 + math.cos(t * 0.7) * 40
                    self.ultrasonic_right = 110 + math.sin(t * 0.5) * 35
                else:
                    self.ultrasonic_front = 999
                    self.ultrasonic_left  = 999
                    self.ultrasonic_right = 999

                # ── Obstacle detection ────────────────────────
                self.obstacle_detected = self.ultrasonic_front < 30
                if self.obstacle_detected:
                    self.obstacle_dir = "front"
                    if "Obstacle detected!" not in [a["msg"] for a in self.alerts]:
                        self.alerts.append({
                            "msg"  : "Obstacle detected!",
                            "type" : "warning",
                            "time" : datetime.now().strftime("%H:%M:%S")
                        })
                else:
                    self.obstacle_dir = None

                # ── Motor simulation ──────────────────────────
                if self.following_customer:
                    noise = math.sin(t * 3) * 5
                    self.motor_left_speed  = 45 + noise
                    self.motor_right_speed = 45 - noise
                    self.wheel_rpm         = 120 + math.sin(t) * 20
                    self.current_draw      = 2.4 + abs(noise) * 0.1
                    self.total_distance   += 0.001
                    # Update position
                    self.position_x += math.cos(
                        math.radians(self.heading)
                    ) * 0.001
                    self.position_y += math.sin(
                        math.radians(self.heading)
                    ) * 0.001
                    self.heading = (
                        self.heading + math.sin(t * 0.2) * 0.5
                    ) % 360
                else:
                    self.wheel_rpm    = 0
                    self.current_draw = 0.4

                # ── System metrics ────────────────────────────
                base_cpu = 55 if self.following_customer else 35
                self.cpu_usage  = base_cpu + math.sin(t * 0.5) * 10
                self.ram_usage  = 48 + math.sin(t * 0.3) * 8
                self.cpu_temp   = 42 + (self.cpu_usage * 0.3) + \
                                  math.sin(t * 0.2) * 2

                # ── Power status ──────────────────────────────
                if self.battery_level < 20:
                    self.power_status = "critical"
                    if not any(a["msg"] == "Low battery!" for a in self.alerts):
                        self.alerts.append({
                            "msg"  : "Low battery!",
                            "type" : "critical",
                            "time" : datetime.now().strftime("%H:%M:%S")
                        })
                elif self.battery_level < 40:
                    self.power_status = "warning"
                else:
                    self.power_status = "normal"

                # ── Camera pan/tilt simulation ────────────────
                if self.following_customer:
                    self.camera_pan  = math.sin(t * 0.3) * 15
                    self.camera_tilt = -10 + math.sin(t * 0.2) * 5

            time.sleep(0.1)

    def get_status(self):
        """Get full robot status dict"""
        return {
            "is_active"         : self.is_active,
            "is_moving"         : self.is_moving,
            "following_customer": self.following_customer,
            "direction"         : self.direction,

            "motors" : {
                "left"    : round(self.motor_left_speed, 1),
                "right"   : round(self.motor_right_speed, 1),
                "rpm"     : round(self.wheel_rpm, 1)
            },

            "sensors" : {
                "front"   : round(self.ultrasonic_front, 1),
                "left"    : round(self.ultrasonic_left, 1),
                "right"   : round(self.ultrasonic_right, 1),
                "obstacle": self.obstacle_detected,
                "obs_dir" : self.obstacle_dir
            },

            "power" : {
                "battery" : round(self.battery_level, 1),
                "voltage" : round(self.battery_voltage, 2),
                "current" : round(self.current_draw, 2),
                "status"  : self.power_status
            },

            "camera" : {
                "active"  : self.camera_active,
                "pan"     : round(self.camera_pan, 1),
                "tilt"    : round(self.camera_tilt, 1)
            },

            "navigation" : {
                "x"       : round(self.position_x, 3),
                "y"       : round(self.position_y, 3),
                "heading" : round(self.heading, 1),
                "distance": round(self.total_distance, 3)
            },

            "system" : {
                "cpu_temp"  : round(self.cpu_temp, 1),
                "cpu_usage" : round(self.cpu_usage, 1),
                "ram_usage" : round(self.ram_usage, 1),
                "uptime"    : self.uptime
            },

            "alerts"      : self.alerts[-5:],
            "error_count" : self.error_count
        }


# ============================================================
# GLOBAL STATE
# ============================================================

class AppState:
    def __init__(self):
        self.robot = RobotStatus()
        self.reset()

    def reset(self):
        self.video_handler     = None
        self.barcode_scanner   = None
        self.person_detector   = None
        self.customer_tracker  = None
        self.smart_cart        = None
        self.is_running        = False
        self.is_paused         = False
        self.source_mode       = None
        self.video_path        = None
        self.customer_name     = "Customer"
        self.frame_thread      = None
        self.current_frame     = None
        self.lock              = threading.Lock()
        self.frame_count       = 0
        self.fps               = 0.0
        self.last_scan_msg     = ""


state = AppState()


# ============================================================
# HELPERS
# ============================================================

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def json_payload():
    return request.get_json(silent=True) or {}


def api_error(message, status=400, **extra):
    payload = {"success": False, "message": message}
    payload.update(extra)
    return jsonify(payload), status


def sanitize_customer_name(name):
    clean = " ".join((name or "Customer").strip().split())
    return (clean or "Customer")[:MAX_CUSTOMER_NAME_LENGTH]


def stop_current_session(wait=True):
    state.is_running = False
    state.is_paused = False
    if wait and state.frame_thread and state.frame_thread.is_alive():
        state.frame_thread.join(timeout=2.0)
    if state.video_handler:
        state.video_handler.close()
        state.video_handler = None
    state.robot.deactivate()


def get_cart_data():
    if not state.smart_cart:
        return {
            "items"       : [],
            "subtotal"    : 0.0,
            "tax"         : 0.0,
            "total"       : 0.0,
            "item_count"  : 0,
            "unique_items": 0,
            "currency"    : CURRENCY_SYMBOL,
            "tax_rate"    : f"{int(TAX_RATE*100)}%"
        }
    totals = state.smart_cart.get_totals()
    return {
        "items"        : state.smart_cart.get_items(),
        "subtotal"     : totals["subtotal"],
        "tax"          : totals["tax"],
        "total"        : totals["total"],
        "item_count"   : totals["item_count"],
        "unique_items" : totals["unique_items"],
        "currency"     : CURRENCY_SYMBOL,
        "tax_rate"     : f"{int(TAX_RATE*100)}%",
        "session_id"   : state.smart_cart.session_id,
        "customer"     : state.smart_cart.customer_name
    }


def get_system_status():
    tracker_locked = False
    tracker_id     = None
    scan_ready     = True
    scan_cooldown  = 0.0
    people_count   = 0

    if state.customer_tracker:
        s              = state.customer_tracker.get_stats()
        tracker_locked = s["is_locked"]
        tracker_id     = s["locked_id"]
        people_count   = s["active_tracks"]

    if state.barcode_scanner:
        scan_ready    = state.barcode_scanner.is_ready_to_scan()
        scan_cooldown = state.barcode_scanner.get_cooldown_remaining()

    return {
        "is_running"     : state.is_running,
        "is_paused"      : state.is_paused,
        "source_mode"    : state.source_mode,
        "fps"            : round(state.fps, 1),
        "frame_count"    : state.frame_count,
        "tracker_locked" : tracker_locked,
        "tracker_id"     : tracker_id,
        "people_count"   : people_count,
        "scan_ready"     : scan_ready,
        "scan_cooldown"  : round(scan_cooldown, 1),
        "robot"          : state.robot.get_status()
    }


# ============================================================
# FRAME PROCESSING
# ============================================================

def process_frames():
    fps_times = []

    while state.is_running:
        try:
            if state.is_paused:
                time.sleep(0.05)
                continue

            if not state.video_handler:
                time.sleep(0.1)
                continue

            ret, frame = state.video_handler.read()

            if not ret or frame is None:
                time.sleep(0.05)
                continue

            t_start = time.time()

            # ── Barcode ───────────────────────────────────────
            # We scan the FULL resolution frame first for maximum barcode clarity!
            if state.barcode_scanner:
                scan_results = state.barcode_scanner.scan_frame(frame)
                if scan_results:
                    any_added = False
                    for scan_result in scan_results:
                        result = state.smart_cart.add_item_by_barcode(
                            scan_result["barcode"]
                        )
                        state.last_scan_msg = result["message"]
                        
                        # Emit to UI
                        socketio.emit("cart_update",  get_cart_data())
                        socketio.emit("scan_result", {
                            "success" : result["success"],
                            "message" : result["message"],
                            "barcode" : scan_result["barcode"]
                        })

                        if result["success"]:
                            any_added = True
                            # Stop processing further barcodes if we successfully added one
                            break
                            
                    if not any_added:
                        # If none of the barcodes were valid (e.g. hallucinated grid lines),
                        # reset the cooldown so the scanner doesn't sleep for 2 seconds
                        # and can instantly try the next frame to find the real barcode!
                        state.barcode_scanner.reset_cooldown()
                        
                frame = state.barcode_scanner.draw_scan_overlay(frame)

            # Resize the frame down to 854x480 to save CPU during person detection and streaming
            frame = cv2.resize(frame, (854, 480))

            # ── Persons ───────────────────────────────────────
            if state.person_detector:
                persons = state.person_detector.detect_persons(frame)

                if state.customer_tracker:
                    result = state.customer_tracker.update(frame, persons)
                    frame  = state.customer_tracker.draw_tracks(frame)

                    # Update robot following state
                    t_stats = state.customer_tracker.get_stats()
                    state.robot.set_following(
                        t_stats["is_locked"],
                        t_stats["locked_id"]
                    )

                frame = state.person_detector.draw_detections(frame)

            frame = _draw_overlay(frame)

            fps_times.append(time.time())
            fps_times = [t for t in fps_times if time.time() - t < 1.0]
            state.fps = len(fps_times)

            with state.lock:
                state.current_frame = frame.copy()
                state.frame_count  += 1

            if state.frame_count % 8 == 0:
                socketio.emit("status_update", get_system_status())

            elapsed = time.time() - t_start
            time.sleep(max(0, 0.033 - elapsed))

        except Exception:
            logger.exception("Frame processing error")
            time.sleep(0.1)


def _draw_overlay(frame):
    h, w = frame.shape[:2]

    # Top bar
    cv2.rectangle(frame, (0, 0), (w, 36), (10, 10, 20), -1)
    cv2.putText(frame, "SMART CART  |  AI VISION",
                (12, 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 1)

    fps_color = (
        (0, 230, 118) if state.fps >= 20 else
        (255, 193, 7) if state.fps >= 10 else
        (100, 100, 255)
    )
    cv2.putText(frame, f"{state.fps:.0f} FPS",
                (w - 80, 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, fps_color, 1)

    # Bottom bar
    if state.smart_cart:
        totals = state.smart_cart.get_totals()
        cv2.rectangle(frame, (0, h - 36), (w, h), (10, 10, 20), -1)
        cv2.putText(
            frame,
            f"Items: {totals['item_count']}   "
            f"Total: {CURRENCY_SYMBOL}{totals['total']:.2f}",
            (12, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55, (255, 215, 0), 1
        )

    return frame


# ============================================================
# MJPEG STREAM
# ============================================================

def generate_frames():
    while True:
        with state.lock:
            frame = state.current_frame

        if frame is not None:
            ret, buf = cv2.imencode(
                ".jpg", frame,
                [cv2.IMWRITE_JPEG_QUALITY, 82]
            )
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buf.tobytes()
                    + b"\r\n"
                )
        else:
            blank = np.zeros((480, 854, 3), dtype=np.uint8)
            blank[:] = (8, 8, 18)
            cv2.putText(blank,
                "Waiting for video source...",
                (240, 240), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (60, 60, 100), 2)
            ret, buf = cv2.imencode(".jpg", blank)
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buf.tobytes()
                    + b"\r\n"
                )
        time.sleep(0.033)


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/api/start", methods=["POST"])
def api_start():
    global state
    try:
        data          = json_payload()
        source_mode   = data.get("mode", "webcam")
        customer_name = sanitize_customer_name(data.get("customer", "Customer"))
        video_path    = data.get("video_path", None)

        if source_mode not in {VideoSource.WEBCAM, VideoSource.VIDEO}:
            return api_error("Unsupported video source")

        if state.is_running:
            stop_current_session()

        state.reset()
        state.source_mode   = source_mode
        state.customer_name = customer_name

        if source_mode == "webcam":
            state.video_handler = VideoHandler(source=VideoSource.WEBCAM)
        else:
            if not video_path:
                return api_error("Video file is required")
            upload_root = Path(app.config["UPLOAD_FOLDER"]).resolve()
            resolved_video = Path(video_path).resolve()
            if upload_root not in resolved_video.parents or not resolved_video.exists():
                return api_error("Video file not found")
            state.video_path    = str(resolved_video)
            state.video_handler = VideoHandler(
                source=VideoSource.VIDEO, video_path=str(resolved_video)
            )

        if not state.video_handler.open():
            return api_error("Failed to open video source", status=503)

        state.barcode_scanner  = BarcodeScanner(cooldown=BARCODE_COOLDOWN)
        state.person_detector  = PersonDetector()
        state.customer_tracker = CustomerTracker()
        state.smart_cart       = SmartCart(customer_name)

        state.is_running   = True
        state.frame_thread = threading.Thread(
            target=process_frames, daemon=True
        )
        state.frame_thread.start()

        # Activate robot
        state.robot.activate()

        return jsonify({
            "success"    : True,
            "message"    : f"Started with {source_mode}",
            "session_id" : state.smart_cart.session_id,
            "customer"   : customer_name,
            "mode"       : source_mode
        })

    except Exception as e:
        logger.exception("Failed to start session")
        return api_error(str(e), status=500)


@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_current_session()
    return jsonify({"success": True, "message": "System stopped"})


@app.route("/api/pause", methods=["POST"])
def api_pause():
    if not state.is_running:
        return api_error("System is not running", status=409)
    state.is_paused = not state.is_paused
    return jsonify({
        "success": True,
        "paused" : state.is_paused,
        "message": "paused" if state.is_paused else "resumed"
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    if not state.smart_cart or not state.barcode_scanner:
        return api_error("System not started", status=409)

    data    = json_payload()
    barcode = str(data.get("barcode", "")).strip()

    if not barcode:
        return api_error("Barcode is required")

    sim = state.barcode_scanner.simulate_scan(barcode)
    if not sim:
        cd = state.barcode_scanner.get_cooldown_remaining()
        return api_error(f"Scanner cooling down: {cd:.1f}s", status=429)

    result = state.smart_cart.add_item_by_barcode(barcode)
    socketio.emit("cart_update",  get_cart_data())
    socketio.emit("scan_result", {
        "success": result["success"],
        "message": result["message"],
        "barcode": barcode
    })
    return jsonify({
        "success": result["success"],
        "message": result["message"],
        "cart"   : get_cart_data()
    })


@app.route("/api/cart/increment", methods=["POST"])
def api_increment():
    if not state.smart_cart:
        return api_error("System not started", status=409)
    data   = json_payload()
    result = state.smart_cart.increment_item(data.get("barcode"))
    socketio.emit("cart_update", get_cart_data())
    return jsonify(result)


@app.route("/api/cart/decrement", methods=["POST"])
def api_decrement():
    if not state.smart_cart:
        return api_error("System not started", status=409)
    data   = json_payload()
    result = state.smart_cart.decrement_item(data.get("barcode"))
    socketio.emit("cart_update", get_cart_data())
    return jsonify(result)


@app.route("/api/cart/remove", methods=["POST"])
def api_remove():
    if not state.smart_cart:
        return api_error("System not started", status=409)
    data   = json_payload()
    result = state.smart_cart.remove_item(
        data.get("barcode"), remove_all=True
    )
    socketio.emit("cart_update", get_cart_data())
    return jsonify(result)


@app.route("/api/cart/clear", methods=["POST"])
def api_clear():
    if not state.smart_cart:
        return api_error("System not started", status=409)
    result = state.smart_cart.clear_cart()
    socketio.emit("cart_update", get_cart_data())
    return jsonify(result)


@app.route("/api/cart/checkout", methods=["POST"])
def api_checkout():
    if not state.smart_cart:
        return api_error("System not started", status=409)
    result = state.smart_cart.checkout()
    if result["success"]:
        socketio.emit("checkout_complete", {
            "receipt": result.get("receipt", {}),
            "totals" : result.get("totals", {})
        })
    return jsonify(result)


@app.route("/api/cart/undo", methods=["POST"])
def api_undo():
    if not state.smart_cart:
        return api_error("System not started", status=409)
    result = state.smart_cart.undo_last_action()
    socketio.emit("cart_update", get_cart_data())
    return jsonify(result)


@app.route("/api/tracker/lock", methods=["POST"])
def api_lock():
    if not state.customer_tracker:
        return api_error("System not started", status=409)
    locked = state.customer_tracker.lock_largest_track()
    if locked:
        state.robot.set_following(True)
    return jsonify({
        "success"  : locked,
        "message"  : "Customer locked" if locked else "No person found",
        "locked_id": state.customer_tracker.locked_track_id
    })


@app.route("/api/tracker/unlock", methods=["POST"])
def api_unlock():
    if not state.customer_tracker:
        return api_error("System not started", status=409)
    state.customer_tracker.unlock_track()
    state.robot.set_following(False)
    return jsonify({"success": True, "message": "Unlocked"})


@app.route("/api/tracker/switch", methods=["POST"])
def api_switch():
    if not state.customer_tracker:
        return api_error("System not started", status=409)
    state.customer_tracker.switch_track()
    return jsonify({"success": True})


@app.route("/api/robot/status")
def api_robot_status():
    return jsonify(state.robot.get_status())


@app.route("/api/status")
def api_status():
    return jsonify(get_system_status())


@app.route("/api/cart")
def api_cart():
    return jsonify(get_cart_data())


@app.route("/api/products")
def api_products():
    try:
        from database.db_manager import DatabaseManager
        products = DatabaseManager().get_all_products()
        return jsonify({"success": True, "products": products})
    except Exception:
        logger.exception("Failed to load products")
        return api_error("Unable to load products", status=500)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "video" not in request.files:
        return api_error("No file uploaded")

    file = request.files["video"]
    if file.filename == "":
        return api_error("No file selected")

    if not allowed_file(file.filename):
        return api_error("Invalid file type")

    original  = secure_filename(file.filename)
    stem, ext = os.path.splitext(original)
    filename  = f"{stem[:80]}-{uuid4().hex[:10]}{ext.lower()}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    return jsonify({
        "success"  : True,
        "message"  : f"Uploaded: {filename}",
        "path"     : save_path,
        "filename" : filename
    })


# ============================================================
# SOCKETIO
# ============================================================

@socketio.on("connect")
def on_connect():
    emit("status_update", get_system_status())
    emit("cart_update",   get_cart_data())


@socketio.on("request_status")
def on_request_status():
    emit("status_update", get_system_status())
    emit("cart_update",   get_cart_data())


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  SMART SHOPPING CART - WEB SERVER")
    print("  URL: http://localhost:5001")
    print("=" * 50 + "\n")

    socketio.run(
        app,
        host         = "0.0.0.0",
        port         = 5001,
        debug        = False,
        use_reloader = False,
        allow_unsafe_werkzeug=True
    )
