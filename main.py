# ============================================================
# SmartShoppingCart/main.py
# Main Integration File - Runs Everything Together
# - Connects all modules
# - Camera view + Dashboard side by side
# - Full keyboard controls
# - Barcode scanning pipeline
# - Person detection and tracking
# - Smart cart management
# - Live dashboard display
# - Session summary on exit
# ============================================================

import cv2
import sys
import os
import time
import numpy as np
from datetime import datetime

# ── Add project root to path ──────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

# ── Import Config ─────────────────────────────────────────────
from config import (
    CAMERA_WINDOW,
    DASHBOARD_WINDOW,
    DASHBOARD_WIDTH,
    DASHBOARD_HEIGHT,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    INPUT_MODE,
    SAMPLE_VIDEO_PATH,
    CV_GREEN, CV_RED, CV_WHITE,
    CV_YELLOW, CV_CYAN, CV_ORANGE,
    CV_BLUE, CV_BLACK,
    CURRENCY_SYMBOL
)

# ── Import All Modules ────────────────────────────────────────
from modules.barcode_scanner  import BarcodeScanner
from modules.person_detector  import PersonDetector, setup_mouse_callback
from modules.customer_tracker import CustomerTracker
from modules.smart_cart       import SmartCart
from modules.dashboard        import Dashboard
from modules.video_handler    import VideoHandler, VideoSource


# ============================================================
# KEYBOARD CONTROLS REFERENCE
# ============================================================
CONTROLS = {
    "Q"     : "Quit application",
    "SPACE" : "Pause / Resume video",
    "L"     : "Auto lock nearest person",
    "U"     : "Unlock current customer",
    "S"     : "Switch to next person",
    "B"     : "Simulate barcode scan (test)",
    "C"     : "Clear cart",
    "Z"     : "Undo last action",
    "E"     : "Toggle image enhancement",
    "F"     : "Toggle horizontal flip",
    "R"     : "Start / Stop recording",
    "T"     : "Toggle trail display",
    "H"     : "Show / Hide help overlay",
    "1"     : "Simulate scan: Coca Cola",
    "2"     : "Simulate scan: Doritos",
    "3"     : "Simulate scan: Pepsi",
    "4"     : "Simulate scan: Kelloggs",
    "5"     : "Simulate scan: Red Bull",
    "W"     : "Scroll cart up",
    "X"     : "Scroll cart down",
    "ENTER" : "Checkout"
}

# ── Quick scan test barcodes ──────────────────────────────────
TEST_BARCODES = {
    ord('1'): "049000028911",   # Coca Cola
    ord('2'): "028400090179",   # Doritos
    ord('3'): "049000006582",   # Pepsi
    ord('4'): "038000596148",   # Corn Flakes
    ord('5'): "078000053401",   # Red Bull
    ord('6'): "070847811169",   # Tropicana OJ
    ord('7'): "041570037607",   # Oreo
    ord('8'): "030100301023",   # Pringles
    ord('9'): "013800152015",   # DiGiorno Pizza
}


# ============================================================
# MAIN APPLICATION CLASS
# ============================================================

class SmartShoppingCartApp:
    """
    Main Application
    ────────────────
    Integrates all modules into a complete
    Smart Shopping Cart system
    """

    def __init__(self, input_mode=INPUT_MODE,
                 video_path=None,
                 customer_name="Customer"):

        print("\n" + "=" * 60)
        print("      SMART SHOPPING CART SYSTEM")
        print("      AI Powered Retail Experience")
        print("=" * 60)

        # ── Settings ──────────────────────────────────────────
        self.input_mode    = input_mode
        self.video_path    = video_path
        self.customer_name = customer_name

        # ── Application State ─────────────────────────────────
        self.is_running    = False
        self.is_paused     = False
        self.show_help     = False
        self.show_debug    = False

        # ── All Module Instances ──────────────────────────────
        self.video_handler = None
        self.barcode_scanner = None
        self.person_detector = None
        self.customer_tracker = None
        self.smart_cart      = None
        self.dashboard       = None

        # ── Window Names ──────────────────────────────────────
        self.cam_window   = CAMERA_WINDOW
        self.dash_window  = "Smart Cart - Dashboard"
        self.combo_window = "Smart Shopping Cart System"

        # ── Combined View ─────────────────────────────────────
        self.use_combined = True    # Single window mode
        self.combined_frame = None

        # ── Performance ───────────────────────────────────────
        self.loop_fps      = 0.0
        self.loop_times    = []
        self.frame_count   = 0
        self.start_time    = datetime.now()

        # ── Last scan result for display ──────────────────────
        self.last_scan_result  = None
        self.last_scan_time    = 0

        print("\n✅ App instance created")

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def initialize(self):
        """Initialize all modules"""
        print("\n📦 Initializing modules...")

        try:
            # ── 1. Video Handler ──────────────────────────────
            print("\n  [1/6] Video Handler...")
            self.video_handler = VideoHandler(
                source      = self.input_mode,
                video_path  = self.video_path
            )
            if not self.video_handler.open():
                print("  ❌ Video handler failed - trying webcam")
                self.video_handler = VideoHandler(
                    source = VideoSource.WEBCAM
                )
                if not self.video_handler.open():
                    print("  ❌ No video source available")
                    print("  ℹ️  Running in dashboard-only mode")
            print("  ✅ Video Handler ready")

            # ── 2. Barcode Scanner ────────────────────────────
            print("\n  [2/6] Barcode Scanner...")
            self.barcode_scanner = BarcodeScanner(cooldown=2.0)
            print("  ✅ Barcode Scanner ready")

            # ── 3. Person Detector ────────────────────────────
            print("\n  [3/6] Person Detector...")
            self.person_detector = PersonDetector()
            print("  ✅ Person Detector ready")

            # ── 4. Customer Tracker ───────────────────────────
            print("\n  [4/6] Customer Tracker...")
            self.customer_tracker = CustomerTracker()
            print("  ✅ Customer Tracker ready")

            # ── 5. Smart Cart ─────────────────────────────────
            print("\n  [5/6] Smart Cart...")
            self.smart_cart = SmartCart(
                customer_name=self.customer_name
            )
            print("  ✅ Smart Cart ready")

            # ── 6. Dashboard ──────────────────────────────────
            print("\n  [6/6] Dashboard...")
            self.dashboard = Dashboard(
                width  = DASHBOARD_WIDTH,
                height = DASHBOARD_HEIGHT
            )
            print("  ✅ Dashboard ready")

            print("\n" + "=" * 60)
            print("✅ ALL MODULES INITIALIZED SUCCESSFULLY")
            print("=" * 60)
            return True

        except Exception as e:
            print(f"\n❌ Initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # =========================================================
    # WINDOW SETUP
    # =========================================================

    def setup_windows(self):
        """Create and configure OpenCV windows"""
        print("\n📺 Setting up windows...")

        if self.use_combined:
            # ── Single Combined Window ────────────────────────
            cv2.namedWindow(
                self.combo_window,
                cv2.WINDOW_NORMAL
            )
            combined_w = VIDEO_WIDTH + DASHBOARD_WIDTH
            combined_h = max(VIDEO_HEIGHT, DASHBOARD_HEIGHT)
            cv2.resizeWindow(
                self.combo_window,
                combined_w,
                combined_h
            )
            print(f"  ✅ Combined window: {combined_w}x{combined_h}")

            # ── Mouse callback for camera area ────────────────
            def combined_mouse_cb(event, x, y, flags, param):
                # Camera area click (left side)
                if x < VIDEO_WIDTH:
                    if event == cv2.EVENT_LBUTTONDOWN:
                        self.person_detector.set_click(x, y)

                # Dashboard area click (right side)
                else:
                    dash_x = x - VIDEO_WIDTH
                    if event == cv2.EVENT_LBUTTONDOWN:
                        result = self.dashboard.handle_click(
                            dash_x, y, self.smart_cart
                        )
                        if result:
                            self._handle_cart_result(result)

                    elif event == cv2.EVENT_MOUSEMOVE:
                        dash_x = x - VIDEO_WIDTH
                        for btn in self.dashboard.buttons:
                            btn.hovered = btn.contains(
                                dash_x, y
                            )

            cv2.setMouseCallback(
                self.combo_window,
                combined_mouse_cb
            )
            print("  ✅ Mouse callback set")

        else:
            # ── Separate Windows ──────────────────────────────
            cv2.namedWindow(self.cam_window,  cv2.WINDOW_NORMAL)
            cv2.namedWindow(self.dash_window, cv2.WINDOW_NORMAL)

            cv2.resizeWindow(
                self.cam_window, VIDEO_WIDTH, VIDEO_HEIGHT
            )
            cv2.resizeWindow(
                self.dash_window,
                DASHBOARD_WIDTH,
                DASHBOARD_HEIGHT
            )

            setup_mouse_callback(
                self.cam_window,
                self.person_detector
            )
            self.dashboard.setup_mouse(
                self.dash_window,
                self.smart_cart
            )

        print("✅ Windows ready\n")

    # =========================================================
    # MAIN LOOP
    # =========================================================

    def run(self):
        """Main application loop"""

        if not self.initialize():
            print("❌ Failed to initialize. Exiting.")
            return

        self.setup_windows()
        self._print_controls()

        self.is_running = True
        print("\n🚀 Smart Shopping Cart RUNNING")
        print("   Press H for help overlay")
        print("   Press Q to quit\n")

        try:
            while self.is_running:
                loop_start = time.time()

                # ── Read Frame ────────────────────────────────
                ret, frame = self.video_handler.read()

                if not ret or frame is None:
                    frame = self._create_blank_frame()

                # ── Process Frame ─────────────────────────────
                frame = self._process_frame(frame)

                # ── Render Dashboard ──────────────────────────
                dash_frame = self.dashboard.render(
                    cart    = self.smart_cart,
                    scanner = self.barcode_scanner,
                    tracker = self.customer_tracker
                )

                # ── Combine Views ─────────────────────────────
                combined = self._combine_frames(
                    frame, dash_frame
                )

                # ── Show Windows ──────────────────────────────
                if self.use_combined:
                    cv2.imshow(self.combo_window, combined)
                else:
                    cv2.imshow(self.cam_window,  frame)
                    cv2.imshow(self.dash_window, dash_frame)

                # ── Record if active ──────────────────────────
                if self.video_handler.is_recording:
                    self.video_handler.write_frame(combined)

                # ── Handle Keys ───────────────────────────────
                key = cv2.waitKey(1) & 0xFF
                self._handle_key(key)

                # ── FPS Tracking ──────────────────────────────
                loop_time = time.time() - loop_start
                self.loop_times.append(loop_time)
                if len(self.loop_times) > 30:
                    self.loop_times.pop(0)
                avg = sum(self.loop_times) / len(self.loop_times)
                self.loop_fps = 1.0 / avg if avg > 0 else 0

                self.frame_count += 1

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")

        finally:
            self._shutdown()

    # =========================================================
    # FRAME PROCESSING PIPELINE
    # =========================================================

    def _process_frame(self, frame):
        """
        Full frame processing pipeline

        1. Draw video info overlay
        2. Scan barcode
        3. Detect persons
        4. Update tracker
        5. Draw all overlays
        6. Draw help if needed
        """
        if frame is None:
            return self._create_blank_frame()

        # ── Step 1: Video Info Overlay ────────────────────────
        frame = self.video_handler.draw_video_info(frame)

        # ── Step 2: Barcode Scanning ──────────────────────────
        scan_result = self.barcode_scanner.scan_frame(frame)

        if scan_result:
            self._handle_scan(scan_result)
            frame = self.barcode_scanner.draw_barcode_highlight(
                frame, scan_result
            )

        # ── Step 3: Draw Scan Overlay ─────────────────────────
        frame = self.barcode_scanner.draw_scan_overlay(frame)

        # ── Step 4: Person Detection ──────────────────────────
        persons = self.person_detector.detect_persons(frame)

        # ── Step 5: Customer Tracking ─────────────────────────
        track_result = self.customer_tracker.update(
            frame, persons
        )

        # ── Step 6: Draw Person Detections ───────────────────
        frame = self.person_detector.draw_detections(frame)

        # ── Step 7: Draw Tracking Overlays ────────────────────
        frame = self.customer_tracker.draw_tracks(frame)

        # ── Step 8: Draw App Info ─────────────────────────────
        frame = self._draw_app_info(frame)

        # ── Step 9: Draw Help Overlay ─────────────────────────
        if self.show_help:
            frame = self._draw_help_overlay(frame)

        # ── Step 10: Draw Debug Info ──────────────────────────
        if self.show_debug:
            frame = self._draw_debug_overlay(frame)

        return frame

    # =========================================================
    # SCAN HANDLER
    # =========================================================

    def _handle_scan(self, scan_result):
        """Process a successful barcode scan"""
        barcode = scan_result["barcode"]

        # ── Add to cart ───────────────────────────────────────
        result = self.smart_cart.add_item_by_barcode(barcode)

        # ── Store last result ─────────────────────────────────
        self.last_scan_result = result
        self.last_scan_time   = time.time()

        if result["success"]:
            product = result.get("product")
            if product:
                print(
                    f"🛒 Added: {product['name']}"
                    f" | Total: "
                    f"{CURRENCY_SYMBOL}"
                    f"{result['totals']['total']}"
                )
        else:
            print(f"⚠️  Scan failed: {result['message']}")

    def _handle_cart_result(self, result):
        """Handle result from dashboard button click"""
        if not result:
            return

        if result.get("success"):
            if result.get("receipt"):
                # Checkout was triggered
                self._show_checkout_screen(result)
        else:
            print(f"⚠️  Cart action: {result.get('message')}")

    # =========================================================
    # OVERLAY DRAWING
    # =========================================================

    def _draw_app_info(self, frame):
        """Draw application info on camera frame"""
        h, w = frame.shape[:2]

        # ── App Title Bar ─────────────────────────────────────
        cv2.rectangle(frame,
                      (0, 0),
                      (w, 35),
                      (0, 0, 0), -1)

        cv2.putText(frame,
                    "SMART SHOPPING CART  |  AI Vision System",
                    (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_WHITE, 1)

        # ── Loop FPS ─────────────────────────────────────────
        fps_color = (
            CV_GREEN if self.loop_fps >= 20
            else CV_YELLOW if self.loop_fps >= 10
            else CV_RED
        )

        cv2.putText(frame,
                    f"APP FPS: {self.loop_fps:.1f}",
                    (w - 160, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, fps_color, 1)

        # ── Cart Summary Bar ──────────────────────────────────
        totals = self.smart_cart.get_totals()

        cv2.rectangle(frame,
                      (0, h - 38),
                      (w, h),
                      (0, 0, 0), -1)

        summary = (
            f"Cart: {totals['item_count']} items"
            f"  |  Subtotal: {CURRENCY_SYMBOL}{totals['subtotal']:.2f}"
            f"  |  Tax: {CURRENCY_SYMBOL}{totals['tax']:.2f}"
            f"  |  TOTAL: {CURRENCY_SYMBOL}{totals['total']:.2f}"
        )

        cv2.putText(frame, summary,
                    (10, h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, CV_YELLOW, 1)

        # ── Tracking Status Bar ───────────────────────────────
        tracker_stats = self.customer_tracker.get_stats()

        if tracker_stats["is_locked"]:
            lock_text  = f"TRACKING: Customer #{tracker_stats['locked_id']}"
            lock_color = CV_GREEN
        else:
            lock_text  = "TRACKING: No customer locked  [Press L to lock]"
            lock_color = CV_RED

        cv2.putText(frame, lock_text,
                    (10, h - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, lock_color, 1)

        # ── Last Scan Result ──────────────────────────────────
        if self.last_scan_result:
            age = time.time() - self.last_scan_time
            if age < 3.0:
                alpha     = 1.0 - age / 3.0
                intensity = int(255 * alpha)

                if self.last_scan_result["success"]:
                    color = (0, intensity, 0)
                    msg   = (
                        f"ADDED: "
                        f"{self.last_scan_result.get('product', {}).get('name', '')}"
                    )
                else:
                    color = (0, 0, intensity)
                    msg   = f"NOT FOUND: {self.last_scan_result.get('barcode', '')}"

                cv2.putText(frame, msg,
                            (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, color, 2)

        return frame

    def _draw_help_overlay(self, frame):
        """Draw keyboard controls help overlay"""
        h, w      = frame.shape[:2]
        overlay   = frame.copy()
        panel_w   = 400
        panel_h   = min(h - 80, len(CONTROLS) * 22 + 60)
        panel_x   = (w - panel_w) // 2
        panel_y   = (h - panel_h) // 2

        # Background
        cv2.rectangle(overlay,
                      (panel_x - 10, panel_y - 10),
                      (panel_x + panel_w + 10, panel_y + panel_h + 10),
                      (10, 10, 30), -1)

        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Border
        cv2.rectangle(frame,
                      (panel_x - 10, panel_y - 10),
                      (panel_x + panel_w + 10, panel_y + panel_h + 10),
                      CV_CYAN, 2)

        # Title
        cv2.putText(frame,
                    "KEYBOARD CONTROLS",
                    (panel_x + 80, panel_y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, CV_CYAN, 2)

        cv2.line(frame,
                 (panel_x, panel_y + 35),
                 (panel_x + panel_w, panel_y + 35),
                 CV_CYAN, 1)

        # Controls list
        for i, (key, desc) in enumerate(CONTROLS.items()):
            y = panel_y + 55 + i * 20

            cv2.putText(frame,
                        f"[{key}]",
                        (panel_x + 5, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.42, CV_YELLOW, 1)

            cv2.putText(frame, desc,
                        (panel_x + 75, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.42, CV_WHITE, 1)

        cv2.putText(frame,
                    "Press H to close",
                    (panel_x + 110, panel_y + panel_h),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, CV_CYAN, 1)

        return frame

    def _draw_debug_overlay(self, frame):
        """Draw debug information overlay"""
        h, w    = frame.shape[:2]
        debug_x = 10
        debug_y = 90

        debug_info = [
            f"Frame     : {self.frame_count}",
            f"App FPS   : {self.loop_fps:.1f}",
            f"Video FPS : {self.video_handler.current_fps:.1f}",
            f"Tracks    : {len(self.customer_tracker.active_tracks)}",
            f"Locked ID : {self.customer_tracker.locked_track_id}",
            f"Scans     : {self.barcode_scanner.successful_scans}",
            f"Cart Items: {self.smart_cart.get_item_count()}",
            f"Total     : {CURRENCY_SYMBOL}{self.smart_cart.get_total()}"
        ]

        for i, info in enumerate(debug_info):
            cv2.putText(frame, info,
                        (debug_x, debug_y + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, CV_CYAN, 1)

        return frame

    # =========================================================
    # FRAME COMBINING
    # =========================================================

    def _combine_frames(self, cam_frame, dash_frame):
        """
        Combine camera and dashboard into single frame

        Args:
            cam_frame  : processed camera frame
            dash_frame : rendered dashboard frame

        Returns:
            combined frame
        """
        try:
            # ── Resize camera frame to match dashboard height ──
            target_h = DASHBOARD_HEIGHT
            cam_h, cam_w = cam_frame.shape[:2]

            if cam_h != target_h:
                scale   = target_h / cam_h
                new_w   = int(cam_w * scale)
                cam_frame = cv2.resize(
                    cam_frame,
                    (new_w, target_h)
                )

            # ── Resize dashboard to target height ─────────────
            dash_h, dash_w = dash_frame.shape[:2]
            if dash_h != target_h:
                dash_frame = cv2.resize(
                    dash_frame,
                    (DASHBOARD_WIDTH, target_h)
                )

            # ── Horizontal Stack ──────────────────────────────
            combined = np.hstack([cam_frame, dash_frame])

            # ── Divider Line ──────────────────────────────────
            cam_new_w = cam_frame.shape[1]
            cv2.line(combined,
                     (cam_new_w, 0),
                     (cam_new_w, target_h),
                     CV_CYAN, 2)

            return combined

        except Exception as e:
            print(f"⚠️  Frame combine error: {e}")
            return cam_frame

    def _create_blank_frame(self):
        """Create blank frame when no video available"""
        frame = np.zeros(
            (VIDEO_HEIGHT, VIDEO_WIDTH, 3),
            dtype=np.uint8
        )
        frame[:] = (20, 20, 35)

        h, w = frame.shape[:2]

        cv2.putText(frame,
                    "NO VIDEO SOURCE",
                    (w // 2 - 120, h // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, CV_RED, 2)

        cv2.putText(frame,
                    "Press 1-9 to simulate barcode scans",
                    (w // 2 - 180, h // 2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_YELLOW, 1)

        cv2.putText(frame,
                    "Press H for help",
                    (w // 2 - 80, h // 2 + 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_CYAN, 1)

        return frame

    # =========================================================
    # KEYBOARD HANDLER
    # =========================================================

    def _handle_key(self, key):
        """Handle all keyboard inputs"""
        if key == 255 or key == -1:
            return

        # ── Q - Quit ──────────────────────────────────────────
        if key == ord('q') or key == ord('Q'):
            print("\n👋 Quit requested")
            self.is_running = False

        # ── SPACE - Pause/Resume ──────────────────────────────
        elif key == ord(' '):
            self.video_handler.toggle_pause()
            self.is_paused = self.video_handler.is_paused

        # ── H - Help ──────────────────────────────────────────
        elif key == ord('h') or key == ord('H'):
            self.show_help = not self.show_help
            state = "ON" if self.show_help else "OFF"
            print(f"ℹ️  Help overlay: {state}")

        # ── D - Debug ─────────────────────────────────────────
        elif key == ord('d') or key == ord('D'):
            self.show_debug = not self.show_debug
            state = "ON" if self.show_debug else "OFF"
            print(f"🔧 Debug overlay: {state}")

        # ── L - Lock nearest person ───────────────────────────
        elif key == ord('l') or key == ord('L'):
            locked = self.customer_tracker.lock_largest_track()
            if not locked:
                self.person_detector.lock_nearest_person()
            print(f"🔒 Auto-lock triggered")

        # ── U - Unlock ────────────────────────────────────────
        elif key == ord('u') or key == ord('U'):
            self.customer_tracker.unlock_track()
            self.person_detector.unlock_person()
            print(f"🔓 Customer unlocked")

        # ── S - Switch person ─────────────────────────────────
        elif key == ord('s') or key == ord('S'):
            switched = self.customer_tracker.switch_track()
            if not switched:
                self.person_detector.request_switch()
            print(f"🔄 Switching customer")

        # ── W - Scroll up ─────────────────────────────────────
        elif key == ord('w') or key == ord('W'):
            self.dashboard.handle_scroll(-1, self.smart_cart)

        # ── X - Scroll down ───────────────────────────────────
        elif key == ord('x') or key == ord('X'):
            self.dashboard.handle_scroll(1, self.smart_cart)

        # ── Z - Undo ──────────────────────────────────────────
        elif key == ord('z') or key == ord('Z'):
            result = self.smart_cart.undo_last_action()
            print(f"↩️  Undo: {result['message']}")

        # ── C - Clear cart ────────────────────────────────────
        elif key == ord('c') or key == ord('C'):
            result = self.smart_cart.clear_cart()
            print(f"🗑️  {result['message']}")

        # ── E - Enhancement ───────────────────────────────────
        elif key == ord('e') or key == ord('E'):
            self.video_handler.toggle_enhance()

        # ── F - Flip ──────────────────────────────────────────
        elif key == ord('f') or key == ord('F'):
            self.video_handler.set_flip(
                horizontal = not self.video_handler.flip_h
            )

        # ── T - Trail ─────────────────────────────────────────
        elif key == ord('t') or key == ord('T'):
            self.customer_tracker.toggle_trail()

        # ── R - Recording ─────────────────────────────────────
        elif key == ord('r') or key == ord('R'):
            if self.video_handler.is_recording:
                self.video_handler.stop_recording()
            else:
                self.video_handler.start_recording()

        # ── ENTER - Checkout ──────────────────────────────────
        elif key == 13:
            result = self.smart_cart.checkout()
            if result["success"]:
                self._show_checkout_screen(result)
                self.is_running = False

        # ── 1-9 - Simulate Barcode Scans ─────────────────────
        elif key in TEST_BARCODES:
            barcode = TEST_BARCODES[key]
            sim_result = self.barcode_scanner.simulate_scan(barcode)

            if sim_result:
                self._handle_scan(sim_result)
            else:
                remaining = self.barcode_scanner.get_cooldown_remaining()
                print(f"⏳ Scanner cooldown: {remaining}s remaining")

    # =========================================================
    # CHECKOUT SCREEN
    # =========================================================

    def _show_checkout_screen(self, result):
        """Display checkout summary screen"""
        receipt = result.get("receipt", {})
        totals  = result.get("totals", {})

        # ── Create checkout frame ─────────────────────────────
        frame = np.zeros(
            (DASHBOARD_HEIGHT, VIDEO_WIDTH + DASHBOARD_WIDTH, 3),
            dtype=np.uint8
        )
        frame[:] = (10, 20, 10)

        h, w = frame.shape[:2]

        # ── Title ─────────────────────────────────────────────
        cv2.putText(frame,
                    "CHECKOUT COMPLETE!",
                    (w // 2 - 200, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.5, CV_GREEN, 3)

        # ── Receipt lines ─────────────────────────────────────
        lines = receipt.get("lines", [])
        for i, line in enumerate(lines[:30]):
            cv2.putText(frame, line,
                        (w // 2 - 200, 130 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, CV_WHITE, 1)

        # ── Thank you message ─────────────────────────────────
        cv2.putText(frame,
                    "Thank you for shopping!",
                    (w // 2 - 150, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, CV_YELLOW, 2)

        cv2.putText(frame,
                    "Press any key to exit",
                    (w // 2 - 120, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_CYAN, 1)

        cv2.imshow(self.combo_window, frame)
        cv2.waitKey(0)

    # =========================================================
    # SHUTDOWN
    # =========================================================

    def _shutdown(self):
        """Clean shutdown of all modules"""
        print("\n" + "=" * 60)
        print("   SHUTTING DOWN...")
        print("=" * 60)

        self.is_running = False

        # ── Generate Session Summary ──────────────────────────
        self._print_session_summary()

        # ── Close Video ───────────────────────────────────────
        if self.video_handler:
            self.video_handler.close()

        # ── Close Windows ─────────────────────────────────────
        cv2.destroyAllWindows()

        print("\n✅ Smart Shopping Cart shutdown complete")
        print("   Goodbye!\n")

    def _print_session_summary(self):
        """Print session summary to terminal"""
        print("\n📊 SESSION SUMMARY")
        print("-" * 40)

        if self.smart_cart:
            stats  = self.smart_cart.get_stats()
            totals = self.smart_cart.get_totals()

            print(f"  Session ID    : {stats['session_id']}")
            print(f"  Customer      : {stats['customer']}")
            print(f"  Items Added   : {stats['items_added']}")
            print(f"  Items Removed : {stats['items_removed']}")
            print(f"  Unique Items  : {stats['unique_items']}")
            print(f"  Total Items   : {stats['total_items']}")
            print(f"  Subtotal      : {CURRENCY_SYMBOL}{totals['subtotal']:.2f}")
            print(f"  Tax           : {CURRENCY_SYMBOL}{totals['tax']:.2f}")
            print(f"  TOTAL         : {CURRENCY_SYMBOL}{totals['total']:.2f}")
            print(f"  Scans         : {stats['scan_count']}")
            print(f"  Unknown Scans : {stats['unknown_scans']}")

        if self.customer_tracker:
            t_stats = self.customer_tracker.get_stats()
            print(f"\n  Tracking")
            print(f"  Frames Tracked: {t_stats['locked_frames']}")
            print(f"  Lost Events   : {t_stats['lost_events']}")
            print(f"  Recovered     : {t_stats['recovered_events']}")

        runtime = (datetime.now() - self.start_time).seconds
        print(f"\n  Runtime       : {runtime}s")
        print(f"  App FPS (avg) : {self.loop_fps:.1f}")
        print(f"  Total Frames  : {self.frame_count}")
        print("-" * 40)

    def _print_controls(self):
        """Print controls to terminal"""
        print("\n" + "=" * 60)
        print("   KEYBOARD CONTROLS")
        print("=" * 60)
        for key, desc in CONTROLS.items():
            print(f"  [{key:<6}] {desc}")
        print("=" * 60 + "\n")


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    """Application entry point"""

    import argparse

    parser = argparse.ArgumentParser(
        description="AI Smart Shopping Cart System"
    )

    parser.add_argument(
        "--mode",
        type    = str,
        default = "webcam",
        choices = ["webcam", "video"],
        help    = "Input mode: webcam or video"
    )

    parser.add_argument(
        "--video",
        type    = str,
        default = None,
        help    = "Path to video file (if mode=video)"
    )

    parser.add_argument(
        "--customer",
        type    = str,
        default = "Customer",
        help    = "Customer name for session"
    )

    parser.add_argument(
        "--width",
        type    = int,
        default = None,
        help    = "Override camera width"
    )

    parser.add_argument(
        "--height",
        type    = int,
        default = None,
        help    = "Override camera height"
    )

    args = parser.parse_args()

    # ── Create and run app ────────────────────────────────────
    app = SmartShoppingCartApp(
        input_mode    = args.mode,
        video_path    = args.video,
        customer_name = args.customer
    )

    app.run()


if __name__ == "__main__":
    main()
