# ============================================================
# SmartShoppingCart/modules/barcode_scanner.py
# Handles all barcode scanning operations
# - Scans barcodes from camera frames
# - 2 second cooldown between scans
# - Duplicate scan prevention
# - Visual feedback on frame
# ============================================================

import cv2
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Add pyzbar with error handling
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar not installed; using simulation mode")

from config import (
    BARCODE_COOLDOWN,
    CV_GREEN, CV_RED, CV_WHITE,
    CV_YELLOW, CV_CYAN, CV_ORANGE
)


class BarcodeScanner:
    """
    Barcode Scanner Module
    ─────────────────────
    Scans product barcodes from video frames
    with 2 second cooldown and duplicate prevention
    """

    def __init__(self, cooldown=BARCODE_COOLDOWN):
        # ── Cooldown Settings ─────────────────────────────────
        self.cooldown           = cooldown       # Seconds between scans
        self.last_scan_time     = 0              # Timestamp of last scan
        self.last_scanned_code  = None           # Last barcode scanned
        self.cooldown_active    = False          # Is cooldown running

        # ── Scan Statistics ───────────────────────────────────
        self.total_scans        = 0
        self.successful_scans   = 0
        self.failed_scans       = 0
        self.scan_history       = []             # List of all scans

        # ── Visual Feedback ───────────────────────────────────
        self.scan_flash_time    = 0              # For green flash effect
        self.scan_flash_duration= 0.5            # How long flash shows
        self.last_result        = None           # Last scan result dict

        # ── Scanner State ─────────────────────────────────────
        self.is_active          = True
        self.scan_region        = None           # Optional scan region

        print(f"✅ BarcodeScanner initialized")
        print(f"   Cooldown    : {self.cooldown} seconds")
        print(f"   Mode        : {'pyzbar' if PYZBAR_AVAILABLE else 'simulation'}")

    # =========================================================
    # MAIN SCAN FUNCTION
    # =========================================================

    def scan_frame(self, frame):
        """
        Main function - scan a video frame for barcodes
        
        Args:
            frame: OpenCV video frame (numpy array)
            
        Returns:
            dict with scan result or None
        """
        if frame is None or not self.is_active:
            return None

        current_time = time.time()

        # ── Check Cooldown ────────────────────────────────────
        time_since_last = current_time - self.last_scan_time
        
        if time_since_last < self.cooldown:
            # Still in cooldown - dont scan
            self.cooldown_active = True
            return None
        
        self.cooldown_active = False

        # ── Crop Frame For Scanning ───────────────────────────
        # Crop to the exact center "SCAN BARCODE HERE" box to avoid hallucinations
        h, w = frame.shape[:2]
        box_w   = int(w * 0.5)
        box_h   = int(h * 0.25)
        box_x   = (w - box_w) // 2
        box_y   = (h - box_h) // 2
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Ensure we don't go out of bounds
        gray_crop = gray[max(0, box_y):min(h, box_y+box_h), max(0, box_x):min(w, box_x+box_w)]

        # ── Detect Barcodes ───────────────────────────────────
        all_barcodes = []
        is_flipped_list = []

        # 1. Normal grayscale
        b1 = self._detect_barcodes(gray_crop)
        if b1:
            all_barcodes.extend(b1)
            is_flipped_list.extend([False] * len(b1))

        # 2. Flipped grayscale
        gray_flipped = cv2.flip(gray_crop, 1)
        b2 = self._detect_barcodes(gray_flipped)
        if b2:
            all_barcodes.extend(b2)
            is_flipped_list.extend([True] * len(b2))
            
        # 3. Otsu thresholding
        _, thresh = cv2.threshold(gray_crop, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        b3 = self._detect_barcodes(thresh)
        if b3:
            all_barcodes.extend(b3)
            is_flipped_list.extend([False] * len(b3))
            
        # 4. Flipped Otsu
        thresh_flipped = cv2.flip(thresh, 1)
        b4 = self._detect_barcodes(thresh_flipped)
        if b4:
            all_barcodes.extend(b4)
            is_flipped_list.extend([True] * len(b4))

        if not all_barcodes:
            return None

        # ── Process All Valid Barcodes ───────────────────────
        results = []
        for barcode, is_flipped in zip(all_barcodes, is_flipped_list):
            barcode_data = self._extract_barcode_data(barcode)

            if not barcode_data:
                continue

            # Adjust polygon coordinates to account for flip AND crop
            poly = barcode_data.get("polygon", [])
            new_poly = []
            for x, y in poly:
                # 1. Un-flip if necessary
                if is_flipped:
                    x = box_w - x
                # 2. Add crop offset back
                x += box_x
                y += box_y
                new_poly.append((x, y))
            barcode_data["polygon"] = new_poly
            
            # Adjust rect coordinates
            if barcode_data["rect"]:
                r = barcode_data["rect"]
                import collections
                Rect = collections.namedtuple('Rect', ['left', 'top', 'width', 'height'])
                
                left = r.left
                if is_flipped:
                    left = box_w - r.left - r.width
                    
                # Add crop offset back
                barcode_data["rect"] = Rect(left + box_x, r.top + box_y, r.width, r.height)

            barcode_value = barcode_data["value"]
            barcode_type  = barcode_data["type"]

            # ── Build Result ──────────────────────────────────
            result = {
                "barcode"    : barcode_value,
                "type"       : barcode_type,
                "timestamp"  : datetime.now().strftime("%H:%M:%S"),
                "success"    : True,
                "polygon"    : barcode_data.get("polygon", []),
                "rect"       : barcode_data.get("rect", None)
            }
            results.append(result)

        if not results:
            return None

        # Update state using the first result for visual feedback
        self.last_scan_time    = current_time
        self.last_scanned_code = results[0]["barcode"]
        self.total_scans      += 1
        self.successful_scans += 1
        self.scan_flash_time   = current_time
        self.last_result       = results[0]
        self.scan_history.extend(results)

        print(f"📦 Barcodes Scanned: {[r['barcode'] for r in results]}")
        return results

    # =========================================================
    # BARCODE DETECTION
    # =========================================================

    def _detect_barcodes(self, gray_frame):
        """Detect barcodes in grayscale frame"""

        if PYZBAR_AVAILABLE:
            # ── Real Barcode Detection ─────────────────────────
            try:
                barcodes = pyzbar.decode(gray_frame)
                return barcodes
            except Exception as e:
                print(f"⚠️  Scan error: {e}")
                return []
        else:
            # ── Simulation Mode ────────────────────────────────
            return []

    def _extract_barcode_data(self, barcode):
        """Extract data from detected barcode object"""
        try:
            if PYZBAR_AVAILABLE:
                value   = barcode.data.decode("utf-8").strip()
                btype   = barcode.type
                polygon = [(p.x, p.y) for p in barcode.polygon]
                rect    = barcode.rect

                if not value:
                    return None

                return {
                    "value"  : value,
                    "type"   : btype,
                    "polygon": polygon,
                    "rect"   : rect
                }
            else:
                return None
        except Exception as e:
            print(f"⚠️  Barcode extraction error: {e}")
            return None

    # =========================================================
    # MANUAL / SIMULATION SCAN
    # =========================================================

    def simulate_scan(self, barcode_value, barcode_type="EAN13"):
        """
        Manually trigger a scan (for testing without camera)
        
        Args:
            barcode_value : barcode string
            barcode_type  : type of barcode
            
        Returns:
            dict with scan result or None if in cooldown
        """
        current_time     = time.time()
        time_since_last  = current_time - self.last_scan_time

        # ── Check Cooldown ────────────────────────────────────
        if time_since_last < self.cooldown:
            remaining = round(self.cooldown - time_since_last, 1)
            print(f"⏳ Cooldown active - {remaining}s remaining")
            return None

        # ── Process Scan ──────────────────────────────────────
        self.last_scan_time    = current_time
        self.last_scanned_code = barcode_value
        self.total_scans      += 1
        self.successful_scans += 1
        self.scan_flash_time   = current_time

        result = {
            "barcode"   : barcode_value,
            "type"      : barcode_type,
            "timestamp" : datetime.now().strftime("%H:%M:%S"),
            "success"   : True,
            "polygon"   : [],
            "rect"      : None
        }

        self.last_result = result
        self.scan_history.append(result)

        print(f"📦 [SIM] Barcode Scanned: {barcode_value}")
        return result

    def reset_cooldown(self):
        """Reset the cooldown timer instantly (used when a scanned barcode is invalid)"""
        self.last_scan_time = 0

    # =========================================================
    # VISUAL OVERLAY FUNCTIONS
    # =========================================================

    def draw_scan_overlay(self, frame):
        """
        Draw scanning UI on video frame
        
        Args:
            frame: OpenCV frame
            
        Returns:
            frame with overlay drawn
        """
        if frame is None:
            return frame

        h, w = frame.shape[:2]
        current_time = time.time()

        # ── Draw Scan Region Box ──────────────────────────────
        self._draw_scan_region(frame, w, h)

        # ── Draw Cooldown Bar ─────────────────────────────────
        self._draw_cooldown_bar(frame, w, h, current_time)

        # ── Draw Flash Effect After Scan ──────────────────────
        self._draw_scan_flash(frame, w, h, current_time)

        # ── Draw Last Scanned Info ────────────────────────────
        self._draw_last_scan_info(frame, w, h)

        # ── Draw Scanner Status ───────────────────────────────
        self._draw_scanner_status(frame)

        return frame

    def _draw_scan_region(self, frame, w, h):
        """Draw the barcode scan region box"""
        # Center scan box
        box_w   = int(w * 0.5)
        box_h   = int(h * 0.25)
        box_x   = (w - box_w) // 2
        box_y   = (h - box_h) // 2

        color = CV_GREEN if not self.cooldown_active else CV_YELLOW

        # Draw main rectangle
        cv2.rectangle(frame,
                      (box_x, box_y),
                      (box_x + box_w, box_y + box_h),
                      color, 2)

        # Draw corner accents
        corner_len = 20
        corner_thickness = 3

        corners = [
            # Top-left
            [(box_x, box_y + corner_len), (box_x, box_y), (box_x + corner_len, box_y)],
            # Top-right
            [(box_x + box_w - corner_len, box_y), (box_x + box_w, box_y), (box_x + box_w, box_y + corner_len)],
            # Bottom-left
            [(box_x, box_y + box_h - corner_len), (box_x, box_y + box_h), (box_x + corner_len, box_y + box_h)],
            # Bottom-right
            [(box_x + box_w - corner_len, box_y + box_h), (box_x + box_w, box_y + box_h), (box_x + box_w, box_y + box_h - corner_len)]
        ]

        for corner in corners:
            for i in range(len(corner) - 1):
                cv2.line(frame, corner[i], corner[i+1], CV_GREEN, corner_thickness)

        # Scan line (animated)
        scan_y = box_y + int((time.time() * 100) % box_h)
        cv2.line(frame,
                 (box_x + 5, scan_y),
                 (box_x + box_w - 5, scan_y),
                 CV_GREEN, 1)

        # Label
        cv2.putText(frame,
                    "SCAN BARCODE HERE",
                    (box_x + 10, box_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, color, 2)

    def _draw_cooldown_bar(self, frame, w, h, current_time):
        """Draw cooldown progress bar"""
        time_since = current_time - self.last_scan_time
        
        if time_since >= self.cooldown:
            # Ready to scan
            label = "READY TO SCAN"
            color = CV_GREEN
            fill  = w - 20
        else:
            # In cooldown
            progress = time_since / self.cooldown
            fill     = int((w - 20) * progress)
            label    = f"NEXT SCAN IN: {round(self.cooldown - time_since, 1)}s"
            color    = CV_YELLOW

        # Background bar
        cv2.rectangle(frame,
                      (10, h - 30),
                      (w - 10, h - 10),
                      (50, 50, 50), -1)

        # Progress fill
        cv2.rectangle(frame,
                      (10, h - 30),
                      (10 + fill, h - 10),
                      color, -1)

        # Label
        cv2.putText(frame, label,
                    (15, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, CV_WHITE, 1)

    def _draw_scan_flash(self, frame, w, h, current_time):
        """Draw green flash when item is scanned"""
        time_since_flash = current_time - self.scan_flash_time

        if time_since_flash < self.scan_flash_duration:
            # Green border flash
            thickness = int(10 * (1 - time_since_flash / self.scan_flash_duration))
            cv2.rectangle(frame,
                          (0, 0),
                          (w, h),
                          CV_GREEN,
                          thickness)

            # SUCCESS text
            cv2.putText(frame, "✓ ITEM ADDED!",
                        (w // 2 - 80, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, CV_GREEN, 2)

    def _draw_last_scan_info(self, frame, w, h):
        """Show last scanned barcode info"""
        if self.last_scanned_code:
            text = f"Last: {self.last_scanned_code}"
            cv2.putText(frame, text,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, CV_CYAN, 1)

    def _draw_scanner_status(self, frame):
        """Draw scanner active/inactive status"""
        status = "SCANNER: ON" if self.is_active else "SCANNER: OFF"
        color  = CV_GREEN if self.is_active else CV_RED

        cv2.putText(frame, status,
                    (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1)

        # Scan count
        cv2.putText(frame,
                    f"Scans: {self.successful_scans}",
                    (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, CV_WHITE, 1)

    def draw_barcode_highlight(self, frame, result):
        """Highlight detected barcode location on frame"""
        if not result or not PYZBAR_AVAILABLE:
            return frame

        polygon = result.get("polygon", [])
        rect    = result.get("rect", None)

        if polygon and len(polygon) > 0:
            # Draw polygon around barcode
            import numpy as np
            pts = np.array(polygon, dtype=np.int32)
            cv2.polylines(frame, [pts], True, CV_GREEN, 3)

        if rect:
            # Draw barcode value text
            x, y = rect.left, rect.top
            cv2.putText(frame,
                        result["barcode"],
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, CV_GREEN, 2)

        return frame

    # =========================================================
    # COOLDOWN MANAGEMENT
    # =========================================================

    def get_cooldown_remaining(self):
        """Get remaining cooldown time in seconds"""
        elapsed   = time.time() - self.last_scan_time
        remaining = max(0, self.cooldown - elapsed)
        return round(remaining, 2)

    def is_ready_to_scan(self):
        """Check if scanner is ready (cooldown finished)"""
        return (time.time() - self.last_scan_time) >= self.cooldown

    def reset_cooldown(self):
        """Manually reset cooldown (force ready)"""
        self.last_scan_time = 0
        self.cooldown_active = False
        print("🔄 Cooldown reset - Ready to scan")

    # =========================================================
    # SCANNER CONTROL
    # =========================================================

    def toggle_scanner(self):
        """Toggle scanner on/off"""
        self.is_active = not self.is_active
        status = "ON" if self.is_active else "OFF"
        print(f"🔄 Scanner turned {status}")
        return self.is_active

    def pause_scanner(self):
        """Pause scanning"""
        self.is_active = False
        print("⏸️  Scanner paused")

    def resume_scanner(self):
        """Resume scanning"""
        self.is_active = True
        print("▶️  Scanner resumed")

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_stats(self):
        """Get scanner statistics"""
        return {
            "total_scans"      : self.total_scans,
            "successful_scans" : self.successful_scans,
            "failed_scans"     : self.failed_scans,
            "last_barcode"     : self.last_scanned_code,
            "cooldown_remaining": self.get_cooldown_remaining(),
            "is_active"        : self.is_active,
            "is_ready"         : self.is_ready_to_scan()
        }

    def get_scan_history(self):
        """Get complete scan history"""
        return self.scan_history

    def clear_history(self):
        """Clear scan history"""
        self.scan_history = []
        print("🗑️  Scan history cleared")

    def reset(self):
        """Full reset of scanner state"""
        self.last_scan_time    = 0
        self.last_scanned_code = None
        self.cooldown_active   = False
        self.total_scans       = 0
        self.successful_scans  = 0
        self.failed_scans      = 0
        self.scan_history      = []
        self.last_result       = None
        print("🔄 Scanner fully reset")


# =========================================================
# QUICK TEST
# =========================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   BARCODE SCANNER - MODULE TEST")
    print("=" * 55)

    scanner = BarcodeScanner(cooldown=2.0)

    # Test 1: Simulate scan
    print("\n🧪 Test 1: First scan")
    result = scanner.simulate_scan("049000028911")
    print(f"   Result: {result}")

    # Test 2: Immediate second scan (should fail - cooldown)
    print("\n🧪 Test 2: Immediate rescan (should be blocked)")
    result2 = scanner.simulate_scan("049000028911")
    print(f"   Result: {result2}")

    # Test 3: Check cooldown
    print(f"\n🧪 Test 3: Cooldown remaining")
    print(f"   Remaining: {scanner.get_cooldown_remaining()}s")
    print(f"   Is Ready : {scanner.is_ready_to_scan()}")

    # Test 4: Wait and scan again
    print("\n🧪 Test 4: Wait 2 seconds and scan again...")
    time.sleep(2.1)
    result3 = scanner.simulate_scan("028400090179")
    print(f"   Result: {result3}")

    # Test 5: Stats
    print(f"\n🧪 Test 5: Scanner Stats")
    stats = scanner.get_stats()
    for key, val in stats.items():
        print(f"   {key:<22} : {val}")

    # Test 6: Toggle
    print(f"\n🧪 Test 6: Toggle Scanner")
    scanner.toggle_scanner()
    result4 = scanner.simulate_scan("049000028911")
    print(f"   Scan while OFF: {result4}")
    scanner.toggle_scanner()

    print("\n" + "=" * 55)
    print("✅ BARCODE SCANNER TEST COMPLETE")
    print("=" * 55)
