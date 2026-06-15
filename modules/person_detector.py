# ============================================================
# SmartShoppingCart/modules/person_detector.py
# Handles person detection using YOLOv8
# - Detects all persons in frame
# - Lock onto specific customer
# - Click to select customer
# - Switch customer option
# - Visual bounding boxes
# ============================================================

import cv2
import logging
import time
import numpy as np
from datetime import datetime

from config import (
    YOLO_MODEL,
    DETECTION_CONFIDENCE,
    PERSON_CLASS_ID,
    CV_GREEN, CV_RED, CV_BLUE,
    CV_WHITE, CV_YELLOW,
    CV_ORANGE, CV_CYAN,
    VIDEO_WIDTH, VIDEO_HEIGHT
)

logger = logging.getLogger(__name__)

# ── Try importing YOLO ────────────────────────────────────────
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("YOLOv8 available")
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("YOLOv8 not installed; using simulation mode")


class PersonDetector:
    """
    Person Detection Module
    ───────────────────────
    Detects people in video frames using YOLOv8
    Allows locking onto a specific customer
    Supports click-to-select and manual switching
    """

    def __init__(self):
        # ── Model ─────────────────────────────────────────────
        self.model           = None
        self.model_loaded    = False

        # ── Detection Results ─────────────────────────────────
        self.detected_persons = []       # All detected persons
        self.person_count     = 0        # Number of persons

        # ── Locked Customer ───────────────────────────────────
        self.locked_person    = None     # Currently locked person
        self.locked_person_id = None     # ID of locked person
        self.is_locked        = False    # Lock state

        # ── Click Selection ───────────────────────────────────
        self.click_position   = None     # Mouse click position
        self.click_detected   = False    # New click pending

        # ── Switch Customer ───────────────────────────────────
        self.switch_requested = False    # Flag to switch customer
        self.person_index     = 0        # Current person index

        # ── Visual Settings ───────────────────────────────────
        self.show_all_boxes   = True     # Show all person boxes
        self.show_labels      = True     # Show person labels
        self.locked_color     = CV_GREEN # Color for locked person
        self.other_color      = CV_BLUE  # Color for others

        # ── Statistics ────────────────────────────────────────
        self.total_detections = 0
        self.frames_processed = 0
        self.lock_timestamp   = None

        # ── Load Model ────────────────────────────────────────
        self._load_model()

        print("✅ PersonDetector initialized")

    # =========================================================
    # MODEL LOADING
    # =========================================================

    def _load_model(self):
        """Load YOLOv8 model"""
        if not YOLO_AVAILABLE:
            print("⚠️  Running in simulation mode")
            return

        try:
            print(f"📦 Loading {YOLO_MODEL}...")
            # Auto downloads if not present
            self.model       = YOLO(YOLO_MODEL)
            self.model_loaded = True
            print(f"✅ {YOLO_MODEL} loaded successfully")
        except Exception as e:
            print(f"❌ Model load failed: {e}")
            print("⚠️  Switching to simulation mode")
            self.model_loaded = False

    # =========================================================
    # MAIN DETECTION FUNCTION
    # =========================================================

    def detect_persons(self, frame):
        """
        Detect all persons in a video frame

        Args:
            frame: OpenCV BGR frame

        Returns:
            list of detected person dicts
        """
        if frame is None:
            return []

        self.frames_processed += 1
        self.detected_persons  = []

        if self.model_loaded and YOLO_AVAILABLE:
            persons = self._yolo_detect(frame)
        else:
            persons = self._simulate_detect(frame)

        self.detected_persons = persons
        self.person_count     = len(persons)
        self.total_detections += self.person_count

        # ── Handle Click Selection ────────────────────────────
        if self.click_detected and self.click_position:
            self._process_click_selection()
            self.click_detected = False

        # ── Handle Switch Request ─────────────────────────────
        if self.switch_requested:
            self._process_switch()
            self.switch_requested = False

        # ── Update Locked Person ──────────────────────────────
        if self.is_locked:
            self._update_locked_person()

        return self.detected_persons

    # =========================================================
    # YOLO DETECTION
    # =========================================================

    def _yolo_detect(self, frame):
        """Run YOLOv8 detection on frame"""
        persons = []

        try:
            results = self.model(
                frame,
                conf    = DETECTION_CONFIDENCE,
                classes = [PERSON_CLASS_ID],
                verbose = False
            )

            for result in results:
                boxes = result.boxes

                if boxes is None:
                    continue

                for i, box in enumerate(boxes):
                    # Get bounding box
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf            = float(box.conf[0])
                    cls             = int(box.cls[0])

                    if cls != PERSON_CLASS_ID:
                        continue

                    # Calculate center
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    w  = x2 - x1
                    h  = y2 - y1

                    person = {
                        "id"         : i,
                        "bbox"       : (x1, y1, x2, y2),
                        "center"     : (cx, cy),
                        "width"      : w,
                        "height"     : h,
                        "confidence" : round(conf, 2),
                        "is_locked"  : False,
                        "area"       : w * h
                    }

                    persons.append(person)

        except Exception as e:
            print(f"⚠️  YOLO detection error: {e}")

        return persons

    # =========================================================
    # SIMULATION MODE
    # =========================================================

    def _simulate_detect(self, frame):
        """
        Simulate person detection for testing
        Creates fake bounding boxes
        """
        h, w = frame.shape[:2]
        persons = []

        # Simulate 2 people in frame
        sim_persons = [
            {
                "id"         : 0,
                "bbox"       : (50, 50, 200, 400),
                "center"     : (125, 225),
                "width"      : 150,
                "height"     : 350,
                "confidence" : 0.95,
                "is_locked"  : False,
                "area"       : 52500
            },
            {
                "id"         : 1,
                "bbox"       : (w - 250, 50, w - 50, 400),
                "center"     : (w - 150, 225),
                "width"      : 200,
                "height"     : 350,
                "confidence" : 0.88,
                "is_locked"  : False,
                "area"       : 70000
            }
        ]

        return sim_persons

    # =========================================================
    # CUSTOMER LOCKING
    # =========================================================

    def lock_person(self, person):
        """
        Lock onto a specific person as the customer

        Args:
            person: person dict from detected_persons
        """
        if not person:
            return False

        self.locked_person    = person.copy()
        self.locked_person_id = person["id"]
        self.is_locked        = True
        self.lock_timestamp   = datetime.now().strftime("%H:%M:%S")

        print(f"🔒 Customer LOCKED - Person ID: {person['id']}")
        print(f"   Position : {person['center']}")
        print(f"   Confidence: {person['confidence']}")
        return True

    def unlock_person(self):
        """Unlock current customer"""
        if self.is_locked:
            print(f"🔓 Customer UNLOCKED - Person ID: {self.locked_person_id}")

        self.locked_person    = None
        self.locked_person_id = None
        self.is_locked        = False
        self.lock_timestamp   = None
        return True

    def _update_locked_person(self):
        """
        Update locked person position based on new detections
        Match by closest bounding box position
        """
        if not self.locked_person or not self.detected_persons:
            return

        locked_center = self.locked_person["center"]
        best_match    = None
        min_distance  = float("inf")

        for person in self.detected_persons:
            # Calculate distance from last known position
            cx, cy   = person["center"]
            lx, ly   = locked_center
            distance = ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5

            if distance < min_distance:
                min_distance = distance
                best_match   = person

        # Update if close enough (person hasnt moved too far)
        if best_match and min_distance < 200:
            self.locked_person           = best_match.copy()
            self.locked_person["is_locked"] = True
            self.locked_person_id        = best_match["id"]

            # Mark in detected list
            for p in self.detected_persons:
                if p["id"] == best_match["id"]:
                    p["is_locked"] = True
        else:
            # Person lost - keep last known position
            print("⚠️  Locked customer temporarily lost - searching...")

    # =========================================================
    # CLICK TO SELECT
    # =========================================================

    def set_click(self, x, y):
        """
        Register a mouse click for person selection

        Args:
            x, y: click coordinates
        """
        self.click_position = (x, y)
        self.click_detected = True
        print(f"🖱️  Click registered at ({x}, {y})")

    def _process_click_selection(self):
        """Find person at click position and lock them"""
        if not self.click_position:
            return

        cx, cy = self.click_position

        for person in self.detected_persons:
            x1, y1, x2, y2 = person["bbox"]

            # Check if click is inside bounding box
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                print(f"🖱️  Person selected by click!")
                self.lock_person(person)
                return

        print("🖱️  No person found at click position")
        # If clicked outside all boxes - unlock
        self.unlock_person()

    # =========================================================
    # SWITCH CUSTOMER
    # =========================================================

    def request_switch(self):
        """Request to switch to next detected person"""
        self.switch_requested = True
        print("�� Customer switch requested")

    def _process_switch(self):
        """Switch lock to next person in detected list"""
        if not self.detected_persons:
            print("⚠️  No persons detected to switch to")
            return

        if len(self.detected_persons) == 1:
            print("⚠️  Only one person detected")
            self.lock_person(self.detected_persons[0])
            return

        # Move to next person
        self.person_index = (self.person_index + 1) % len(self.detected_persons)
        next_person       = self.detected_persons[self.person_index]

        print(f"🔄 Switching to Person {self.person_index}")
        self.lock_person(next_person)

    def lock_nearest_person(self):
        """Automatically lock the person closest to camera center"""
        if not self.detected_persons:
            print("⚠️  No persons to lock")
            return False

        # Find largest bounding box (closest to camera)
        largest = max(self.detected_persons, key=lambda p: p["area"])
        self.lock_person(largest)
        return True

    def lock_first_person(self):
        """Lock the first detected person"""
        if self.detected_persons:
            self.lock_person(self.detected_persons[0])
            return True
        return False

    # =========================================================
    # DRAWING / VISUAL OVERLAY
    # =========================================================

    def draw_detections(self, frame):
        """
        Draw all detection boxes and locked customer UI

        Args:
            frame: OpenCV frame

        Returns:
            frame with overlays
        """
        if frame is None:
            return frame

        # ── Draw All Detected Persons ─────────────────────────
        for person in self.detected_persons:
            self._draw_person_box(frame, person)

        # ── Draw Locked Customer Panel ────────────────────────
        self._draw_lock_panel(frame)

        # ── Draw Person Count ─────────────────────────────────
        self._draw_person_count(frame)

        # ── Draw Controls Help ────────────────────────────────
        self._draw_controls_help(frame)

        return frame

    def _draw_person_box(self, frame, person):
        """Draw bounding box for a person"""
        x1, y1, x2, y2 = person["bbox"]
        is_locked       = person.get("is_locked", False)

        # ── Colors Based on Lock State ────────────────────────
        if is_locked:
            box_color   = CV_GREEN
            label_bg    = (0, 180, 0)
            label       = f"CUSTOMER [LOCKED]"
            thickness   = 3
        else:
            box_color   = CV_BLUE
            label_bg    = (180, 0, 0)
            label       = f"Person {person['id'] + 1}"
            thickness   = 2

        # ── Draw Bounding Box ─────────────────────────────────
        cv2.rectangle(frame,
                      (x1, y1),
                      (x2, y2),
                      box_color,
                      thickness)

        # ── Draw Corner Accents For Locked ────────────────────
        if is_locked:
            self._draw_lock_corners(frame, x1, y1, x2, y2)

        # ── Draw Label Background ─────────────────────────────
        label_size, _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, 2
        )
        lw, lh = label_size

        cv2.rectangle(frame,
                      (x1, y1 - lh - 10),
                      (x1 + lw + 10, y1),
                      label_bg, -1)

        # ── Draw Label Text ───────────────────────────────────
        cv2.putText(frame, label,
                    (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_WHITE, 2)

        # ── Draw Confidence ───────────────────────────────────
        conf_text = f"{int(person['confidence'] * 100)}%"
        cv2.putText(frame, conf_text,
                    (x1 + 5, y2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, box_color, 1)

        # ── Draw Center Point ─────────────────────────────────
        cx, cy = person["center"]
        cv2.circle(frame, (cx, cy), 5, box_color, -1)

    def _draw_lock_corners(self, frame, x1, y1, x2, y2):
        """Draw animated corner brackets for locked person"""
        length    = 25
        thickness = 3
        color     = CV_GREEN

        # Animated pulse using time
        pulse = int(abs(np.sin(time.time() * 3)) * 5)

        # Top-left
        cv2.line(frame, (x1 - pulse, y1), (x1 + length, y1), color, thickness)
        cv2.line(frame, (x1, y1 - pulse), (x1, y1 + length), color, thickness)

        # Top-right
        cv2.line(frame, (x2 + pulse, y1), (x2 - length, y1), color, thickness)
        cv2.line(frame, (x2, y1 - pulse), (x2, y1 + length), color, thickness)

        # Bottom-left
        cv2.line(frame, (x1 - pulse, y2), (x1 + length, y2), color, thickness)
        cv2.line(frame, (x1, y2 + pulse), (x1, y2 - length), color, thickness)

        # Bottom-right
        cv2.line(frame, (x2 + pulse, y2), (x2 - length, y2), color, thickness)
        cv2.line(frame, (x2, y2 + pulse), (x2, y2 - length), color, thickness)

    def _draw_lock_panel(self, frame):
        """Draw locked customer info panel"""
        h, w = frame.shape[:2]

        if self.is_locked and self.locked_person:
            # ── Locked Panel ──────────────────────────────────
            panel_x = w - 280
            panel_y = 10

            # Background
            cv2.rectangle(frame,
                          (panel_x - 5, panel_y - 5),
                          (w - 10, panel_y + 120),
                          (0, 60, 0), -1)

            cv2.rectangle(frame,
                          (panel_x - 5, panel_y - 5),
                          (w - 10, panel_y + 120),
                          CV_GREEN, 2)

            # Title
            cv2.putText(frame,
                        "🔒 CUSTOMER LOCKED",
                        (panel_x, panel_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, CV_GREEN, 2)

            # Details
            cx, cy = self.locked_person["center"]
            cv2.putText(frame,
                        f"Position : ({cx}, {cy})",
                        (panel_x, panel_y + 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, CV_WHITE, 1)

            cv2.putText(frame,
                        f"Confidence: {int(self.locked_person['confidence']*100)}%",
                        (panel_x, panel_y + 65),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, CV_WHITE, 1)

            cv2.putText(frame,
                        f"Locked at : {self.lock_timestamp}",
                        (panel_x, panel_y + 85),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, CV_WHITE, 1)

            cv2.putText(frame,
                        "Press S to switch customer",
                        (panel_x, panel_y + 110),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, CV_YELLOW, 1)
        else:
            # ── No Lock Panel ─────────────────────────────────
            panel_x = w - 260
            panel_y = 10

            cv2.rectangle(frame,
                          (panel_x - 5, panel_y - 5),
                          (w - 10, panel_y + 70),
                          (60, 0, 0), -1)

            cv2.rectangle(frame,
                          (panel_x - 5, panel_y - 5),
                          (w - 10, panel_y + 70),
                          CV_RED, 2)

            cv2.putText(frame,
                        "NO CUSTOMER LOCKED",
                        (panel_x, panel_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, CV_RED, 2)

            cv2.putText(frame,
                        "Click on person to lock",
                        (panel_x, panel_y + 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, CV_YELLOW, 1)

            cv2.putText(frame,
                        "Press L to auto-lock",
                        (panel_x, panel_y + 65),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, CV_YELLOW, 1)

    def _draw_person_count(self, frame):
        """Draw number of detected persons"""
        h, w = frame.shape[:2]

        text = f"People Detected: {self.person_count}"
        cv2.putText(frame, text,
                    (10, h - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_WHITE, 2)

    def _draw_controls_help(self, frame):
        """Draw keyboard controls help"""
        h, w = frame.shape[:2]

        controls = [
            "L = Auto Lock",
            "S = Switch Person",
            "U = Unlock",
            "Click = Select Person"
        ]

        y_start = h - 110
        for i, ctrl in enumerate(controls):
            cv2.putText(frame, ctrl,
                        (10, y_start + (i * 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, CV_CYAN, 1)

    # =========================================================
    # GETTERS
    # =========================================================

    def get_locked_person(self):
        """Get currently locked person"""
        return self.locked_person

    def get_locked_bbox(self):
        """Get bounding box of locked person"""
        if self.locked_person:
            return self.locked_person["bbox"]
        return None

    def get_locked_center(self):
        """Get center position of locked person"""
        if self.locked_person:
            return self.locked_person["center"]
        return None

    def get_all_persons(self):
        """Get all detected persons"""
        return self.detected_persons

    def get_stats(self):
        """Get detection statistics"""
        return {
            "total_detections" : self.total_detections,
            "frames_processed" : self.frames_processed,
            "current_persons"  : self.person_count,
            "is_locked"        : self.is_locked,
            "locked_id"        : self.locked_person_id,
            "lock_timestamp"   : self.lock_timestamp
        }


# =========================================================
# MOUSE CALLBACK SETUP HELPER
# =========================================================

def setup_mouse_callback(window_name, detector):
    """
    Setup mouse click callback for person selection

    Args:
        window_name : OpenCV window name
        detector    : PersonDetector instance
    """
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            detector.set_click(x, y)

    cv2.setMouseCallback(window_name, mouse_callback)
    print(f"✅ Mouse callback set for window: {window_name}")


# =========================================================
# QUICK TEST
# =========================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   PERSON DETECTOR - MODULE TEST")
    print("=" * 55)

    detector = PersonDetector()

    # Create test frame
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    test_frame[:] = (30, 30, 30)

    print("\n🧪 Test 1: Detect persons in frame")
    persons = detector.detect_persons(test_frame)
    print(f"   Detected: {len(persons)} persons")

    print("\n🧪 Test 2: Lock first person")
    result = detector.lock_first_person()
    print(f"   Lock result: {result}")
    print(f"   Is locked  : {detector.is_locked}")

    print("\n🧪 Test 3: Get locked person info")
    locked = detector.get_locked_person()
    if locked:
        print(f"   Person ID  : {locked['id']}")
        print(f"   Center     : {locked['center']}")
        print(f"   Confidence : {locked['confidence']}")

    print("\n🧪 Test 4: Switch customer")
    detector.request_switch()
    detector.detect_persons(test_frame)
    print(f"   New locked ID: {detector.locked_person_id}")

    print("\n🧪 Test 5: Unlock")
    detector.unlock_person()
    print(f"   Is locked: {detector.is_locked}")

    print("\n🧪 Test 6: Click selection simulation")
    detector.set_click(125, 225)
    detector.detect_persons(test_frame)
    print(f"   Is locked after click: {detector.is_locked}")

    print("\n🧪 Test 7: Stats")
    stats = detector.get_stats()
    for key, val in stats.items():
        print(f"   {key:<22} : {val}")

    print("\n🧪 Test 8: Draw overlays")
    frame_with_overlay = detector.draw_detections(test_frame)
    print(f"   Frame shape: {frame_with_overlay.shape}")
    print(f"   ✅ Overlay drawn successfully")

    print("\n" + "=" * 55)
    print("✅ PERSON DETECTOR TEST COMPLETE")
    print("=" * 55)
