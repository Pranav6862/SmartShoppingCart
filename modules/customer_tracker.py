# ============================================================
# SmartShoppingCart/modules/customer_tracker.py
# Handles smooth customer tracking between frames
# - DeepSORT based tracking
# - Track ID persistence across frames
# - Lost customer recovery
# - Smooth bounding box interpolation
# - Track history trail
# ============================================================

import cv2
import logging
import time
import numpy as np
from datetime import datetime
from collections import deque

from config import (
    MAX_TRACKING_AGE,
    TRACKING_IOU,
    CV_GREEN, CV_RED, CV_BLUE,
    CV_WHITE, CV_YELLOW,
    CV_ORANGE, CV_CYAN,
    VIDEO_WIDTH, VIDEO_HEIGHT
)

logger = logging.getLogger(__name__)

# ── Try importing DeepSORT ────────────────────────────────────
try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
    DEEPSORT_AVAILABLE = True
    logger.info("DeepSORT available")
except ImportError:
    DEEPSORT_AVAILABLE = False
    logger.warning("DeepSORT not installed; using simple tracker")


# ============================================================
# SIMPLE TRACKER (Fallback if DeepSORT not available)
# ============================================================

class SimpleTracker:
    """
    Simple IOU based tracker as fallback
    when DeepSORT is not installed
    """

    def __init__(self):
        self.tracks      = {}
        self.next_id     = 0
        self.max_age     = MAX_TRACKING_AGE

    def update(self, detections):
        """
        Update tracks with new detections

        Args:
            detections: list of [x1,y1,x2,y2,conf] lists

        Returns:
            list of [x1,y1,x2,y2,track_id] lists
        """
        if not detections:
            # Age all tracks
            to_delete = []
            for tid in self.tracks:
                self.tracks[tid]["age"] += 1
                if self.tracks[tid]["age"] > self.max_age:
                    to_delete.append(tid)
            for tid in to_delete:
                del self.tracks[tid]
            return []

        results = []

        # Simple nearest neighbor matching
        used_detections = set()

        for tid, track in list(self.tracks.items()):
            best_iou  = TRACKING_IOU
            best_det  = None
            best_idx  = -1

            for i, det in enumerate(detections):
                if i in used_detections:
                    continue

                iou = self._compute_iou(track["bbox"], det[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_det = det
                    best_idx = i

            if best_det is not None:
                self.tracks[tid]["bbox"] = best_det[:4]
                self.tracks[tid]["age"]  = 0
                used_detections.add(best_idx)
                results.append(best_det[:4] + [tid])
            else:
                self.tracks[tid]["age"] += 1
                if self.tracks[tid]["age"] <= self.max_age:
                    results.append(
                        self.tracks[tid]["bbox"] + [tid]
                    )

        # Create new tracks for unmatched detections
        for i, det in enumerate(detections):
            if i not in used_detections:
                self.tracks[self.next_id] = {
                    "bbox" : det[:4],
                    "age"  : 0
                }
                results.append(det[:4] + [self.next_id])
                self.next_id += 1

        # Remove old tracks
        to_delete = [
            tid for tid, t in self.tracks.items()
            if t["age"] > self.max_age
        ]
        for tid in to_delete:
            del self.tracks[tid]

        return results

    def _compute_iou(self, box1, box2):
        """Compute IOU between two boxes"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0

        area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
        area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0.0


# ============================================================
# MAIN CUSTOMER TRACKER CLASS
# ============================================================

class CustomerTracker:
    """
    Customer Tracking Module
    ────────────────────────
    Tracks customers across video frames
    Maintains track ID persistence
    Handles lost and recovered tracks
    Provides smooth bounding box updates
    """

    def __init__(self):
        # ── Tracker Backend ───────────────────────────────────
        self.tracker         = None
        self.tracker_type    = None
        self._init_tracker()

        # ── All Tracks ────────────────────────────────────────
        self.active_tracks   = {}        # All active track data
        self.track_history   = {}        # Position history per track

        # ── Locked Customer Track ─────────────────────────────
        self.locked_track_id  = None     # Track ID of customer
        self.locked_track     = None     # Full track data
        self.is_locked        = False    # Lock state

        # ── Lost Track Recovery ───────────────────────────────
        self.lost_track_id    = None     # Last lost track ID
        self.lost_position    = None     # Last known position
        self.lost_since       = None     # When track was lost
        self.max_lost_frames  = 60       # Frames before giving up
        self.lost_frame_count = 0        # Current lost frames

        # ── Smooth Tracking ───────────────────────────────────
        self.smooth_factor    = 0.7      # Smoothing (0=none, 1=max)
        self.prev_bbox        = None     # Previous bounding box

        # ── Trail Settings ────────────────────────────────────
        self.trail_length     = 30       # Number of trail points
        self.show_trail       = True     # Show movement trail

        # ── Statistics ────────────────────────────────────────
        self.total_frames     = 0
        self.locked_frames    = 0
        self.lost_events      = 0
        self.recovered_events = 0
        self.session_start    = datetime.now()

        # ── State ─────────────────────────────────────────────
        self.tracking_active  = True

        print("✅ CustomerTracker initialized")
        print(f"   Backend  : {self.tracker_type}")
        print(f"   Max Age  : {MAX_TRACKING_AGE} frames")

    # =========================================================
    # TRACKER INITIALIZATION
    # =========================================================

    def _init_tracker(self):
        """Initialize tracking backend"""
        if DEEPSORT_AVAILABLE:
            try:
                self.tracker = DeepSort(
                    max_age            = MAX_TRACKING_AGE,
                    n_init             = 3,
                    nms_max_overlap    = 1.0,
                    max_cosine_distance= 0.3,
                    nn_budget          = None,
                    override_track_class = None,
                    embedder           = "mobilenet",
                    half               = True,
                    bgr                = True,
                    embedder_gpu       = False,
                    embedder_model_name= None,
                    embedder_wts       = None,
                    polygon            = False,
                    today              = None
                )
                self.tracker_type = "DeepSORT"
                print("✅ DeepSORT tracker initialized")
            except Exception as e:
                print(f"⚠️  DeepSORT init failed: {e}")
                self._use_simple_tracker()
        else:
            self._use_simple_tracker()

    def _use_simple_tracker(self):
        """Fall back to simple IOU tracker"""
        self.tracker      = SimpleTracker()
        self.tracker_type = "SimpleIOU"
        print("✅ Simple IOU tracker initialized")

    # =========================================================
    # MAIN UPDATE FUNCTION
    # =========================================================

    def update(self, frame, detections):
        """
        Update tracker with new frame detections

        Args:
            frame      : current video frame
            detections : list of person dicts from PersonDetector

        Returns:
            dict with tracking results
        """
        if not self.tracking_active or frame is None:
            return self._empty_result()

        self.total_frames += 1

        # ── Format Detections ─────────────────────────────────
        formatted = self._format_detections(detections)

        # ── Run Tracker ───────────────────────────────────────
        tracks = self._run_tracker(frame, formatted)

        # ── Update Active Tracks ──────────────────────────────
        self._update_active_tracks(tracks)

        # ── Update Trail History ──────────────────────────────
        self._update_trail_history()

        # ── Handle Locked Customer ────────────────────────────
        if self.is_locked:
            self._update_locked_track()
            self.locked_frames += 1

        # ── Build Result ──────────────────────────────────────
        return {
            "tracks"        : self.active_tracks,
            "locked_track"  : self.locked_track,
            "is_locked"     : self.is_locked,
            "locked_id"     : self.locked_track_id,
            "track_count"   : len(self.active_tracks),
            "lost"          : self._is_customer_lost()
        }

    def _format_detections(self, detections):
        """Convert PersonDetector output to tracker format"""
        formatted = []

        for person in detections:
            x1, y1, x2, y2 = person["bbox"]
            conf            = person["confidence"]

            if self.tracker_type == "DeepSORT":
                # DeepSORT format: ([x1,y1,w,h], conf, class)
                w = x2 - x1
                h = y2 - y1
                formatted.append(
                    ([x1, y1, w, h], conf, "person")
                )
            else:
                # Simple format: [x1,y1,x2,y2,conf]
                formatted.append([x1, y1, x2, y2, conf])

        return formatted

    def _run_tracker(self, frame, formatted):
        """Run the tracker backend"""
        tracks = []

        try:
            if self.tracker_type == "DeepSORT":
                raw_tracks = self.tracker.update_tracks(
                    formatted, frame=frame
                )
                for track in raw_tracks:
                    if not track.is_confirmed():
                        continue
                    tid  = track.track_id
                    ltrb = track.to_ltrb()
                    x1   = int(ltrb[0])
                    y1   = int(ltrb[1])
                    x2   = int(ltrb[2])
                    y2   = int(ltrb[3])
                    tracks.append({
                        "track_id"  : tid,
                        "bbox"      : (x1, y1, x2, y2),
                        "center"    : ((x1+x2)//2, (y1+y2)//2),
                        "width"     : x2 - x1,
                        "height"    : y2 - y1,
                        "is_locked" : False,
                        "age"       : track.age
                    })
            else:
                raw_tracks = self.tracker.update(formatted)
                for t in raw_tracks:
                    x1, y1, x2, y2 = int(t[0]),int(t[1]),int(t[2]),int(t[3])
                    tid = int(t[4])
                    tracks.append({
                        "track_id"  : tid,
                        "bbox"      : (x1, y1, x2, y2),
                        "center"    : ((x1+x2)//2, (y1+y2)//2),
                        "width"     : x2 - x1,
                        "height"    : y2 - y1,
                        "is_locked" : False,
                        "age"       : 0
                    })
        except Exception as e:
            print(f"⚠️  Tracker update error: {e}")

        return tracks

    # =========================================================
    # TRACK MANAGEMENT
    # =========================================================

    def _update_active_tracks(self, tracks):
        """Update active tracks dictionary"""
        # Mark all as inactive first
        new_tracks = {}

        for track in tracks:
            tid = track["track_id"]

            # Apply smoothing to bbox
            if tid in self.active_tracks:
                track["bbox"] = self._smooth_bbox(
                    self.active_tracks[tid]["bbox"],
                    track["bbox"]
                )

            # Mark locked
            if tid == self.locked_track_id:
                track["is_locked"] = True

            new_tracks[tid] = track

            # Init trail
            if tid not in self.track_history:
                self.track_history[tid] = deque(
                    maxlen=self.trail_length
                )

        self.active_tracks = new_tracks

    def _update_trail_history(self):
        """Add current centers to trail history"""
        for tid, track in self.active_tracks.items():
            if tid in self.track_history:
                self.track_history[tid].append(
                    track["center"]
                )

    def _smooth_bbox(self, prev_bbox, new_bbox):
        """Apply exponential smoothing to bounding box"""
        if prev_bbox is None:
            return new_bbox

        alpha = 1 - self.smooth_factor

        x1 = int(alpha * new_bbox[0] + self.smooth_factor * prev_bbox[0])
        y1 = int(alpha * new_bbox[1] + self.smooth_factor * prev_bbox[1])
        x2 = int(alpha * new_bbox[2] + self.smooth_factor * prev_bbox[2])
        y2 = int(alpha * new_bbox[3] + self.smooth_factor * prev_bbox[3])

        return (x1, y1, x2, y2)

    # =========================================================
    # LOCKED CUSTOMER MANAGEMENT
    # =========================================================

    def lock_track(self, track_id):
        """
        Lock onto a specific track ID

        Args:
            track_id: ID of track to lock
        """
        if track_id in self.active_tracks:
            self.locked_track_id = track_id
            self.locked_track    = self.active_tracks[track_id].copy()
            self.locked_track["is_locked"] = True
            self.is_locked       = True
            self.lost_frame_count = 0

            print(f"🔒 Track LOCKED: ID {track_id}")
            print(f"   Position: {self.locked_track['center']}")
            return True

        print(f"❌ Track ID {track_id} not found")
        return False

    def lock_largest_track(self):
        """Lock onto the largest (closest) person track"""
        if not self.active_tracks:
            print("⚠️  No tracks to lock")
            return False

        largest = max(
            self.active_tracks.values(),
            key=lambda t: t["width"] * t["height"]
        )
        return self.lock_track(largest["track_id"])

    def lock_first_track(self):
        """Lock onto the first available track"""
        if self.active_tracks:
            first_id = list(self.active_tracks.keys())[0]
            return self.lock_track(first_id)
        return False

    def unlock_track(self):
        """Unlock current customer"""
        print(f"🔓 Track UNLOCKED: ID {self.locked_track_id}")
        self.locked_track_id  = None
        self.locked_track     = None
        self.is_locked        = False
        self.lost_frame_count = 0

    def switch_track(self):
        """Switch to next available track"""
        if not self.active_tracks:
            print("⚠️  No tracks available")
            return False

        track_ids = list(self.active_tracks.keys())

        if len(track_ids) == 1:
            return self.lock_track(track_ids[0])

        if self.locked_track_id in track_ids:
            current_idx = track_ids.index(self.locked_track_id)
            next_idx    = (current_idx + 1) % len(track_ids)
        else:
            next_idx = 0

        next_id = track_ids[next_idx]
        print(f"🔄 Switching track: {self.locked_track_id} → {next_id}")
        return self.lock_track(next_id)

    def _update_locked_track(self):
        """Update locked track with latest position"""
        if self.locked_track_id in self.active_tracks:
            # Track found - update position
            self.locked_track = self.active_tracks[
                self.locked_track_id
            ].copy()
            self.locked_track["is_locked"] = True
            self.lost_frame_count = 0

            # Update in active tracks
            self.active_tracks[
                self.locked_track_id
            ]["is_locked"] = True
        else:
            # Track lost
            self._handle_lost_track()

    def _handle_lost_track(self):
        """Handle when locked track is temporarily lost"""
        self.lost_frame_count += 1

        if self.lost_frame_count == 1:
            # First frame lost
            self.lost_track_id = self.locked_track_id
            self.lost_position = (
                self.locked_track["center"]
                if self.locked_track else None
            )
            self.lost_since    = time.time()
            self.lost_events  += 1
            print(f"⚠️  Customer lost! Searching... (ID: {self.locked_track_id})")

        elif self.lost_frame_count > self.max_lost_frames:
            # Give up searching
            print(f"❌ Customer permanently lost after {self.max_lost_frames} frames")
            self.unlock_track()

        else:
            # Try to recover by proximity
            self._attempt_recovery()

    def _attempt_recovery(self):
        """Try to re-lock based on last known position"""
        if not self.lost_position or not self.active_tracks:
            return

        lx, ly       = self.lost_position
        best_id      = None
        min_distance = 150  # Max pixels to consider recovery

        for tid, track in self.active_tracks.items():
            cx, cy   = track["center"]
            distance = ((cx - lx)**2 + (cy - ly)**2)**0.5

            if distance < min_distance:
                min_distance = distance
                best_id      = tid

        if best_id is not None:
            print(f"✅ Customer recovered! New ID: {best_id}")
            self.recovered_events += 1
            self.lost_frame_count  = 0
            self.lock_track(best_id)

    def _is_customer_lost(self):
        """Check if locked customer is currently lost"""
        return (
            self.is_locked and
            self.locked_track_id not in self.active_tracks and
            self.lost_frame_count > 0
        )

    # =========================================================
    # DRAWING / VISUAL OVERLAY
    # =========================================================

    def draw_tracks(self, frame):
        """
        Draw all tracking overlays on frame

        Args:
            frame: OpenCV frame

        Returns:
            frame with tracking visuals
        """
        if frame is None:
            return frame

        # ── Draw Trail ────────────────────────────────────────
        if self.show_trail:
            self._draw_trails(frame)

        # ── Draw All Tracks ───────────────────────────────────
        for tid, track in self.active_tracks.items():
            self._draw_track_box(frame, track)

        # ── Draw Locked Customer Info ─────────────────────────
        self._draw_tracking_panel(frame)

        # ── Draw Lost Warning ─────────────────────────────────
        if self._is_customer_lost():
            self._draw_lost_warning(frame)

        # ── Draw Track Stats ──────────────────────────────────
        self._draw_track_stats(frame)

        return frame

    def _draw_trails(self, frame):
        """Draw movement trail for each track"""
        for tid, history in self.track_history.items():
            if len(history) < 2:
                continue

            is_locked = (tid == self.locked_track_id)
            color     = CV_GREEN if is_locked else CV_BLUE

            points = list(history)
            for i in range(1, len(points)):
                # Fade older points
                alpha     = i / len(points)
                thickness = max(1, int(3 * alpha))

                fade_color = tuple(
                    int(c * alpha) for c in color
                )

                cv2.line(frame,
                         points[i-1],
                         points[i],
                         fade_color,
                         thickness)

    def _draw_track_box(self, frame, track):
        """Draw bounding box for a track"""
        x1, y1, x2, y2 = track["bbox"]
        tid             = track["track_id"]
        is_locked       = track.get("is_locked", False)

        # ── Colors ────────────────────────────────────────────
        if is_locked:
            color     = CV_GREEN
            thickness = 3
            label     = f"CUSTOMER #{tid}"
        else:
            color     = CV_ORANGE
            thickness = 2
            label     = f"Person #{tid}"

        # ── Draw Box ──────────────────────────────────────────
        cv2.rectangle(frame,
                      (x1, y1),
                      (x2, y2),
                      color, thickness)

        # ── Draw Label ────────────────────────────────────────
        label_size, _ = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55, 2
        )
        lw, lh = label_size

        cv2.rectangle(frame,
                      (x1, y1 - lh - 8),
                      (x1 + lw + 8, y1),
                      color, -1)

        cv2.putText(frame, label,
                    (x1 + 4, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, CV_WHITE, 2)

        # ── Draw Center ───────────────────────────────────────
        cx, cy = track["center"]
        cv2.circle(frame, (cx, cy), 5, color, -1)

        # ── Draw Track ID ─────────────────────────────────────
        cv2.putText(frame, f"#{tid}",
                    (x2 - 30, y2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1)

    def _draw_tracking_panel(self, frame):
        """Draw tracking info panel"""
        h, w = frame.shape[:2]

        panel_x = 10
        panel_y = 100
        pw      = 240
        ph      = 130

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay,
                      (panel_x, panel_y),
                      (panel_x + pw, panel_y + ph),
                      (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Border
        border_color = CV_GREEN if self.is_locked else CV_RED
        cv2.rectangle(frame,
                      (panel_x, panel_y),
                      (panel_x + pw, panel_y + ph),
                      border_color, 2)

        # Title
        title = "TRACKING ACTIVE" if self.is_locked else "NO LOCK"
        cv2.putText(frame, title,
                    (panel_x + 8, panel_y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, border_color, 2)

        # Details
        lines = [
            f"Backend  : {self.tracker_type}",
            f"Tracks   : {len(self.active_tracks)}",
            f"Locked ID: {self.locked_track_id or 'None'}",
            f"Lost     : {self.lost_events} events",
            f"Recovered: {self.recovered_events}"
        ]

        for i, line in enumerate(lines):
            cv2.putText(frame, line,
                        (panel_x + 8, panel_y + 45 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4, CV_WHITE, 1)

    def _draw_lost_warning(self, frame):
        """Draw warning when customer is lost"""
        h, w = frame.shape[:2]

        # Flashing red border
        if int(time.time() * 2) % 2 == 0:
            cv2.rectangle(frame,
                          (0, 0),
                          (w, h),
                          CV_RED, 8)

        # Warning text
        text = "⚠ CUSTOMER LOST - SEARCHING..."
        text_size, _ = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8, 2
        )
        tx = (w - text_size[0]) // 2
        ty = 80

        cv2.rectangle(frame,
                      (tx - 10, ty - 30),
                      (tx + text_size[0] + 10, ty + 10),
                      CV_RED, -1)

        cv2.putText(frame, text,
                    (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, CV_WHITE, 2)

        # Frames lost counter
        cv2.putText(frame,
                    f"Lost for {self.lost_frame_count} frames",
                    (tx, ty + 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, CV_YELLOW, 1)

    def _draw_track_stats(self, frame):
        """Draw tracking statistics"""
        h, w = frame.shape[:2]

        stats = f"Frames: {self.total_frames} | Locked: {self.locked_frames}"
        cv2.putText(frame, stats,
                    (10, h - 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, CV_CYAN, 1)

    # =========================================================
    # LOCKED CUSTOMER POSITION
    # =========================================================

    def get_locked_position(self):
        """Get current position of locked customer"""
        if self.locked_track:
            return self.locked_track.get("center")
        return None

    def get_locked_bbox(self):
        """Get bounding box of locked customer"""
        if self.locked_track:
            return self.locked_track.get("bbox")
        return None

    def get_locked_track(self):
        """Get full locked track data"""
        return self.locked_track

    def get_all_tracks(self):
        """Get all active tracks"""
        return self.active_tracks

    # =========================================================
    # STATISTICS & STATE
    # =========================================================

    def get_stats(self):
        """Get full tracker statistics"""
        runtime = (datetime.now() - self.session_start).seconds

        return {
            "tracker_type"    : self.tracker_type,
            "total_frames"    : self.total_frames,
            "locked_frames"   : self.locked_frames,
            "active_tracks"   : len(self.active_tracks),
            "is_locked"       : self.is_locked,
            "locked_id"       : self.locked_track_id,
            "lost_events"     : self.lost_events,
            "recovered_events": self.recovered_events,
            "lost_frame_count": self.lost_frame_count,
            "runtime_seconds" : runtime,
            "smooth_factor"   : self.smooth_factor
        }

    def reset(self):
        """Reset tracker state"""
        self.active_tracks    = {}
        self.track_history    = {}
        self.locked_track_id  = None
        self.locked_track     = None
        self.is_locked        = False
        self.lost_frame_count = 0
        self.total_frames     = 0
        self.locked_frames    = 0
        self.lost_events      = 0
        self.recovered_events = 0
        self._init_tracker()
        print("🔄 CustomerTracker reset complete")

    def toggle_trail(self):
        """Toggle trail display"""
        self.show_trail = not self.show_trail
        state = "ON" if self.show_trail else "OFF"
        print(f"🔄 Trail display: {state}")

    def _empty_result(self):
        """Return empty result dict"""
        return {
            "tracks"       : {},
            "locked_track" : None,
            "is_locked"    : False,
            "locked_id"    : None,
            "track_count"  : 0,
            "lost"         : False
        }


# =========================================================
# QUICK TEST
# =========================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   CUSTOMER TRACKER - MODULE TEST")
    print("=" * 55)

    tracker = CustomerTracker()

    # Simulated detections
    mock_detections = [
        {
            "id"         : 0,
            "bbox"       : (50, 50, 200, 400),
            "center"     : (125, 225),
            "confidence" : 0.95,
            "is_locked"  : False,
            "area"       : 52500
        },
        {
            "id"         : 1,
            "bbox"       : (900, 50, 1100, 400),
            "center"     : (1000, 225),
            "confidence" : 0.88,
            "is_locked"  : False,
            "area"       : 70000
        }
    ]

    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    test_frame[:] = (30, 30, 30)

    print("\n🧪 Test 1: Update tracker with detections")
    result = tracker.update(test_frame, mock_detections)
    print(f"   Tracks found : {result['track_count']}")
    print(f"   Is locked    : {result['is_locked']}")

    print("\n🧪 Test 2: Lock largest track")
    locked = tracker.lock_largest_track()
    print(f"   Lock result  : {locked}")
    print(f"   Locked ID    : {tracker.locked_track_id}")

    print("\n🧪 Test 3: Update after lock")
    result2 = tracker.update(test_frame, mock_detections)
    print(f"   Is locked    : {result2['is_locked']}")
    print(f"   Locked ID    : {result2['locked_id']}")

    print("\n🧪 Test 4: Switch track")
    tracker.switch_track()
    print(f"   New locked ID: {tracker.locked_track_id}")

    print("\n🧪 Test 5: Get locked position")
    pos = tracker.get_locked_position()
    print(f"   Position     : {pos}")

    print("\n🧪 Test 6: Draw tracking overlay")
    frame_out = tracker.draw_tracks(test_frame)
    print(f"   Frame shape  : {frame_out.shape}")
    print(f"   ✅ Overlay drawn")

    print("\n🧪 Test 7: Toggle trail")
    tracker.toggle_trail()
    tracker.toggle_trail()

    print("\n🧪 Test 8: Tracker stats")
    stats = tracker.get_stats()
    for key, val in stats.items():
        print(f"   {key:<22} : {val}")

    print("\n🧪 Test 9: Unlock")
    tracker.unlock_track()
    print(f"   Is locked    : {tracker.is_locked}")

    print("\n🧪 Test 10: Reset")
    tracker.reset()
    print(f"   Tracks after reset: {len(tracker.active_tracks)}")

    print("\n" + "=" * 55)
    print("✅ CUSTOMER TRACKER TEST COMPLETE")
    print("=" * 55)
