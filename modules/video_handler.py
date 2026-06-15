# ============================================================
# SmartShoppingCart/modules/video_handler.py
# Video Input Handler Module
# - Webcam live feed support
# - Recorded video file support
# - Frame preprocessing pipeline
# - FPS control and monitoring
# - Input mode switching
# - Frame buffering
# - Resolution management
# ============================================================

import cv2
import sys
import os
import time
import numpy as np
from datetime import datetime
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    WEBCAM_INDEX,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    SAMPLE_VIDEO_PATH,
    INPUT_MODE,
    CAMERA_WINDOW,
    CV_GREEN, CV_RED, CV_WHITE,
    CV_YELLOW, CV_CYAN, CV_ORANGE,
    CV_BLACK
)


# ============================================================
# VIDEO SOURCE ENUM
# ============================================================
class VideoSource:
    WEBCAM  = "webcam"
    VIDEO   = "video"
    IMAGE   = "image"


# ============================================================
# FRAME INFO CLASS
# ============================================================
class FrameInfo:
    """Stores metadata about each frame"""

    def __init__(self, frame, frame_number, timestamp,
                 source, fps):
        self.frame        = frame
        self.frame_number = frame_number
        self.timestamp    = timestamp
        self.source       = source
        self.fps          = fps
        self.width        = frame.shape[1] if frame is not None else 0
        self.height       = frame.shape[0] if frame is not None else 0
        self.processed    = False

    def to_dict(self):
        return {
            "frame_number" : self.frame_number,
            "timestamp"    : self.timestamp,
            "source"       : self.source,
            "fps"          : self.fps,
            "width"        : self.width,
            "height"       : self.height,
            "processed"    : self.processed
        }


# ============================================================
# MAIN VIDEO HANDLER CLASS
# ============================================================

class VideoHandler:
    """
    Video Input Handler Module
    ──────────────────────────
    Manages all video input sources
    Supports webcam and recorded video
    Handles frame preprocessing
    Controls FPS and resolution
    Provides frame statistics
    """

    def __init__(self, source=INPUT_MODE,
                 video_path=None,
                 webcam_index=WEBCAM_INDEX):

        # ── Source Settings ───────────────────────────────────
        self.source        = source
        self.video_path    = video_path or SAMPLE_VIDEO_PATH
        self.webcam_index  = webcam_index

        # ── Capture Object ────────────────────────────────────
        self.cap           = None
        self.is_open       = False

        # ── Frame Settings ────────────────────────────────────
        self.target_width  = VIDEO_WIDTH
        self.target_height = VIDEO_HEIGHT
        self.target_fps    = VIDEO_FPS

        # ── Frame Tracking ────────────────────────────────────
        self.frame_count   = 0
        self.frame_skip    = 0            # Skip N frames
        self.frame_buffer  = deque(maxlen=5)

        # ── FPS Monitoring ────────────────────────────────────
        self.fps_history   = deque(maxlen=30)
        self.last_fps_time = time.time()
        self.current_fps   = 0.0
        self.target_delay  = 1.0 / VIDEO_FPS

        # ── Video File Info ───────────────────────────────────
        self.total_frames  = 0
        self.video_fps     = 0
        self.video_dur     = 0
        self.loop_video    = True         # Loop video file

        # ── Preprocessing Flags ───────────────────────────────
        self.flip_h        = False        # Horizontal flip
        self.flip_v        = False        # Vertical flip
        self.enhance        = False       # Image enhancement
        self.denoise       = False        # Noise reduction
        self.brightness    = 0            # Brightness adj
        self.contrast      = 1.0         # Contrast adj

        # ── State ─────────────────────────────────────────────
        self.is_paused     = False
        self.is_recording  = False
        self.writer        = None

        # ── Statistics ────────────────────────────────────────
        self.start_time    = datetime.now()
        self.dropped_frames= 0
        self.total_read    = 0

        print(f"✅ VideoHandler initialized")
        print(f"   Source  : {source}")
        print(f"   Target  : {VIDEO_WIDTH}x{VIDEO_HEIGHT} @ {VIDEO_FPS}fps")

    # =========================================================
    # OPEN / CLOSE
    # =========================================================

    def open(self):
        """
        Open video source

        Returns:
            True if opened successfully
        """
        if self.source == VideoSource.WEBCAM:
            return self._open_webcam()
        elif self.source == VideoSource.VIDEO:
            return self._open_video_file()
        else:
            print(f"❌ Unknown source: {self.source}")
            return False

    def _open_webcam(self):
        """Open webcam capture"""
        print(f"📷 Opening webcam {self.webcam_index}...")

        self.cap = cv2.VideoCapture(self.webcam_index)

        if not self.cap.isOpened():
            print(f"❌ Cannot open webcam {self.webcam_index}")
            print("   Trying index 1...")
            self.cap = cv2.VideoCapture(1)

            if not self.cap.isOpened():
                print("❌ No webcam found")
                return False

        # ── Set Properties ────────────────────────────────────
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.target_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        self.cap.set(cv2.CAP_PROP_FPS,          self.target_fps)

        # ── Read actual properties ────────────────────────────
        actual_w   = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.is_open    = True
        print(f"✅ Webcam opened")
        print(f"   Resolution : {actual_w}x{actual_h}")
        print(f"   FPS        : {actual_fps}")

        return True

    def _open_video_file(self):
        """Open recorded video file"""
        print(f"🎬 Opening video: {self.video_path}")

        if not os.path.exists(self.video_path):
            print(f"❌ Video file not found: {self.video_path}")
            print("   Falling back to webcam...")
            self.source = VideoSource.WEBCAM
            return self._open_webcam()

        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            print(f"❌ Cannot open video: {self.video_path}")
            return False

        # ── Get Video Properties ──────────────────────────────
        self.total_frames = int(
            self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )
        self.video_fps    = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_dur    = (
            self.total_frames / self.video_fps
            if self.video_fps > 0 else 0
        )

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.is_open = True
        print(f"✅ Video file opened")
        print(f"   Resolution : {actual_w}x{actual_h}")
        print(f"   FPS        : {self.video_fps:.1f}")
        print(f"   Frames     : {self.total_frames}")
        print(f"   Duration   : {self.video_dur:.1f}s")

        return True

    def close(self):
        """Release video capture"""
        if self.cap:
            self.cap.release()
            self.cap    = None
            self.is_open = False

        if self.writer:
            self.writer.release()
            self.writer = None

        print("✅ VideoHandler closed")

    def switch_source(self, new_source, video_path=None):
        """
        Switch between webcam and video file

        Args:
            new_source : VideoSource.WEBCAM or VideoSource.VIDEO
            video_path : path to video file if switching to video
        """
        print(f"🔄 Switching source: {self.source} → {new_source}")

        self.close()
        self.source      = new_source
        self.frame_count = 0

        if video_path:
            self.video_path = video_path

        success = self.open()
        if success:
            print(f"✅ Switched to {new_source}")
        return success

    # =========================================================
    # FRAME READING
    # =========================================================

    def read_frame(self):
        """
        Read next frame from source

        Returns:
            FrameInfo object or None if failed
        """
        if not self.is_open or not self.cap:
            return None

        if self.is_paused:
            # Return last buffered frame
            if self.frame_buffer:
                return self.frame_buffer[-1]
            return None

        # ── FPS Control ───────────────────────────────────────
        self._fps_control()

        # ── Read Frame ────────────────────────────────────────
        ret, frame = self.cap.read()

        if not ret:
            if self.source == VideoSource.VIDEO and self.loop_video:
                # Loop video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return None
                print("🔄 Video looped")
            else:
                return None

        self.total_read  += 1
        self.frame_count += 1

        # ── Skip Frames ───────────────────────────────────────
        if self.frame_skip > 0:
            for _ in range(self.frame_skip):
                self.cap.read()

        # ── Preprocess Frame ──────────────────────────────────
        frame = self._preprocess(frame)

        # ── Update FPS ────────────────────────────────────────
        self._update_fps()

        # ── Build FrameInfo ───────────────────────────────────
        frame_info = FrameInfo(
            frame        = frame,
            frame_number = self.frame_count,
            timestamp    = datetime.now().strftime("%H:%M:%S.%f")[:-3],
            source       = self.source,
            fps          = self.current_fps
        )

        # ── Buffer Frame ──────────────────────────────────────
        self.frame_buffer.append(frame_info)

        return frame_info

    def read(self):
        """
        Simple read - returns just the frame
        Returns:
            (success, frame) tuple like cv2.VideoCapture.read()
        """
        info = self.read_frame()
        if info and info.frame is not None:
            return True, info.frame
        return False, None

    # =========================================================
    # FRAME PREPROCESSING
    # =========================================================

    def _preprocess(self, frame):
        """
        Apply preprocessing pipeline to frame

        Args:
            frame: raw OpenCV frame

        Returns:
            processed frame
        """
        if frame is None:
            return None

        # ── Resize ────────────────────────────────────────────
        h, w = frame.shape[:2]
        if w != self.target_width or h != self.target_height:
            frame = cv2.resize(
                frame,
                (self.target_width, self.target_height),
                interpolation = cv2.INTER_LINEAR
            )

        # ── Flip ──────────────────────────────────────────────
        if self.flip_h and self.flip_v:
            frame = cv2.flip(frame, -1)
        elif self.flip_h:
            frame = cv2.flip(frame, 1)
        elif self.flip_v:
            frame = cv2.flip(frame, 0)

        # ── Brightness / Contrast ─────────────────────────────
        if self.brightness != 0 or self.contrast != 1.0:
            frame = cv2.convertScaleAbs(
                frame,
                alpha = self.contrast,
                beta  = self.brightness
            )

        # ── Denoise ───────────────────────────────────────────
        if self.denoise:
            frame = cv2.fastNlMeansDenoisingColored(
                frame, None, 10, 10, 7, 21
            )

        # ── Enhance ───────────────────────────────────────────
        if self.enhance:
            frame = self._enhance_frame(frame)

        return frame

    def _enhance_frame(self, frame):
        """Enhance frame for better barcode detection"""
        # Convert to LAB color space
        lab   = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(
            clipLimit   = 2.0,
            tileGridSize= (8, 8)
        )
        l     = clahe.apply(l)

        # Merge and convert back
        lab   = cv2.merge((l, a, b))
        frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return frame

    def get_gray_frame(self, frame):
        """Convert frame to grayscale"""
        if frame is not None:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return None

    def get_resized_frame(self, frame, scale=0.5):
        """Get resized version of frame"""
        if frame is not None:
            h, w = frame.shape[:2]
            return cv2.resize(
                frame,
                (int(w * scale), int(h * scale))
            )
        return None

    # =========================================================
    # FPS CONTROL
    # =========================================================

    def _fps_control(self):
        """Control frame rate for video files"""
        if self.source == VideoSource.VIDEO:
            target_delay = 1.0 / max(1, self.video_fps)
            elapsed      = time.time() - self.last_fps_time

            if elapsed < target_delay:
                sleep_time = target_delay - elapsed
                time.sleep(max(0, sleep_time - 0.001))

    def _update_fps(self):
        """Calculate current FPS"""
        current_time = time.time()
        elapsed      = current_time - self.last_fps_time

        if elapsed > 0:
            instant_fps = 1.0 / elapsed
            self.fps_history.append(instant_fps)
            self.current_fps = sum(self.fps_history) / len(
                self.fps_history
            )

        self.last_fps_time = current_time

    def set_fps(self, fps):
        """Set target FPS"""
        self.target_fps   = max(1, fps)
        self.target_delay = 1.0 / self.target_fps
        print(f"🔄 Target FPS set to {fps}")

    # =========================================================
    # PLAYBACK CONTROL
    # =========================================================

    def pause(self):
        """Pause video playback"""
        self.is_paused = True
        print("⏸️  Video paused")

    def resume(self):
        """Resume video playback"""
        self.is_paused = False
        print("▶️  Video resumed")

    def toggle_pause(self):
        """Toggle pause state"""
        if self.is_paused:
            self.resume()
        else:
            self.pause()

    def seek(self, frame_number):
        """Seek to specific frame (video files only)"""
        if self.source == VideoSource.VIDEO and self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.frame_count = frame_number
            print(f"⏩ Seeked to frame {frame_number}")

    def seek_percent(self, percent):
        """Seek to percentage of video (0-100)"""
        if self.total_frames > 0:
            frame_num = int(
                self.total_frames * percent / 100
            )
            self.seek(frame_num)

    def restart(self):
        """Restart video from beginning"""
        if self.source == VideoSource.VIDEO:
            self.seek(0)
            print("⏮️  Video restarted")

    def get_position(self):
        """Get current playback position"""
        if not self.cap:
            return 0, 0

        pos_frames = int(
            self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        )
        pos_ms     = self.cap.get(cv2.CAP_PROP_POS_MSEC)

        return pos_frames, pos_ms / 1000.0

    def get_progress_percent(self):
        """Get playback progress as percentage"""
        if self.total_frames > 0:
            pos, _ = self.get_position()
            return min(100, (pos / self.total_frames) * 100)
        return 0

    # =========================================================
    # RECORDING
    # =========================================================

    def start_recording(self, output_path=None):
        """Start recording output frames"""
        if not output_path:
            ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                "output", f"recording_{ts}.mp4"
            )

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            output_path,
            fourcc,
            self.target_fps,
            (self.target_width, self.target_height)
        )
        self.is_recording = True
        print(f"🔴 Recording started: {output_path}")

    def write_frame(self, frame):
        """Write frame to recording"""
        if self.is_recording and self.writer:
            self.writer.write(frame)

    def stop_recording(self):
        """Stop recording"""
        if self.writer:
            self.writer.release()
            self.writer       = None
            self.is_recording = False
            print("⏹️  Recording stopped")

    # =========================================================
    # VISUAL OVERLAY
    # =========================================================

    def draw_video_info(self, frame):
        """
        Draw video info overlay on frame

        Args:
            frame: OpenCV frame

        Returns:
            frame with overlay
        """
        if frame is None:
            return frame

        h, w = frame.shape[:2]

        # ── FPS Display ───────────────────────────────────────
        fps_color = (
            CV_GREEN if self.current_fps >= self.target_fps * 0.8
            else CV_YELLOW if self.current_fps >= self.target_fps * 0.5
            else CV_RED
        )

        cv2.putText(frame,
                    f"FPS: {self.current_fps:.1f}",
                    (w - 110, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, fps_color, 1)

        # ── Source Badge ──────────────────────────────────────
        source_label = (
            "LIVE CAM" if self.source == VideoSource.WEBCAM
            else "VIDEO FILE"
        )
        source_color = (
            CV_RED if self.source == VideoSource.WEBCAM
            else CV_CYAN
        )

        cv2.rectangle(frame,
                      (w - 120, 5),
                      (w - 5, 28),
                      (0, 0, 0), -1)

        cv2.putText(frame, source_label,
                    (w - 115, 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, source_color, 1)

        # ── Frame Counter ─────────────────────────────────────
        cv2.putText(frame,
                    f"Frame: {self.frame_count}",
                    (w - 120, h - 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, CV_WHITE, 1)

        # ── Progress Bar (video only) ─────────────────────────
        if self.source == VideoSource.VIDEO:
            self._draw_progress_bar(frame, w, h)

        # ── Recording Indicator ───────────────────────────────
        if self.is_recording:
            self._draw_recording_indicator(frame)

        # ── Pause Indicator ───────────────────────────────────
        if self.is_paused:
            self._draw_pause_indicator(frame, w, h)

        # ── Timestamp ─────────────────────────────────────────
        ts = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, ts,
                    (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, CV_WHITE, 1)

        return frame

    def _draw_progress_bar(self, frame, w, h):
        """Draw video progress bar"""
        progress = self.get_progress_percent()
        bar_w    = w - 20
        filled   = int(bar_w * progress / 100)

        # Background
        cv2.rectangle(frame,
                      (10, h - 6),
                      (w - 10, h - 2),
                      (80, 80, 80), -1)

        # Filled
        if filled > 0:
            cv2.rectangle(frame,
                          (10, h - 6),
                          (10 + filled, h - 2),
                          CV_CYAN, -1)

        # Percentage
        pos, dur = self.get_position()
        cv2.putText(frame,
                    f"{progress:.0f}%  {dur:.0f}s/{self.video_dur:.0f}s",
                    (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, CV_WHITE, 1)

    def _draw_recording_indicator(self, frame):
        """Draw red recording dot"""
        # Blinking dot
        if int(time.time() * 2) % 2 == 0:
            cv2.circle(frame, (20, 20), 8, CV_RED, -1)

        cv2.putText(frame, "REC",
                    (32, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, CV_RED, 2)

    def _draw_pause_indicator(self, frame, w, h):
        """Draw pause overlay"""
        # Semi transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay,
                      (0, 0), (w, h),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        # Pause symbol
        cv2.rectangle(frame,
                      (w//2 - 30, h//2 - 40),
                      (w//2 - 10, h//2 + 40),
                      CV_WHITE, -1)
        cv2.rectangle(frame,
                      (w//2 + 10, h//2 - 40),
                      (w//2 + 30, h//2 + 40),
                      CV_WHITE, -1)

        cv2.putText(frame, "PAUSED",
                    (w//2 - 50, h//2 + 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, CV_WHITE, 2)

    # =========================================================
    # PREPROCESSING SETTINGS
    # =========================================================

    def set_flip(self, horizontal=False, vertical=False):
        """Set flip settings"""
        self.flip_h = horizontal
        self.flip_v = vertical
        print(f"�� Flip: H={horizontal} V={vertical}")

    def set_brightness(self, value):
        """Set brightness adjustment (-100 to 100)"""
        self.brightness = max(-100, min(100, value))

    def set_contrast(self, value):
        """Set contrast multiplier (0.5 to 3.0)"""
        self.contrast = max(0.5, min(3.0, value))

    def toggle_enhance(self):
        """Toggle image enhancement"""
        self.enhance = not self.enhance
        state = "ON" if self.enhance else "OFF"
        print(f"🔄 Enhancement: {state}")

    def toggle_denoise(self):
        """Toggle noise reduction"""
        self.denoise = not self.denoise
        state = "ON" if self.denoise else "OFF"
        print(f"🔄 Denoise: {state}")

    def toggle_loop(self):
        """Toggle video loop"""
        self.loop_video = not self.loop_video
        state = "ON" if self.loop_video else "OFF"
        print(f"🔄 Loop: {state}")

    def set_resolution(self, width, height):
        """Change target resolution"""
        self.target_width  = width
        self.target_height = height

        if self.cap and self.source == VideoSource.WEBCAM:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        print(f"🔄 Resolution set to {width}x{height}")

    def set_frame_skip(self, n):
        """Skip N frames after each read (speed up video)"""
        self.frame_skip = max(0, n)
        print(f"🔄 Frame skip: {n}")

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_stats(self):
        """Get video handler statistics"""
        runtime = (datetime.now() - self.start_time).seconds

        pos_frames, pos_secs = self.get_position()

        return {
            "source"         : self.source,
            "is_open"        : self.is_open,
            "is_paused"      : self.is_paused,
            "is_recording"   : self.is_recording,
            "frame_count"    : self.frame_count,
            "total_read"     : self.total_read,
            "dropped_frames" : self.dropped_frames,
            "current_fps"    : round(self.current_fps, 1),
            "target_fps"     : self.target_fps,
            "resolution"     : f"{self.target_width}x{self.target_height}",
            "runtime_secs"   : runtime,
            "video_progress" : f"{self.get_progress_percent():.1f}%",
            "position_secs"  : round(pos_secs, 1),
            "loop_video"     : self.loop_video,
            "flip_h"         : self.flip_h,
            "enhance"        : self.enhance,
            "denoise"        : self.denoise
        }

    def __repr__(self):
        return (
            f"VideoHandler("
            f"source={self.source}, "
            f"fps={self.current_fps:.1f}, "
            f"frames={self.frame_count}"
            f")"
        )

    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self

    def __exit__(self, *args):
        """Context manager exit"""
        self.close()


# ============================================================
# QUICK TEST
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   VIDEO HANDLER - MODULE TEST")
    print("=" * 55)

    # ── Test 1: Initialize ────────────────────────────────────
    print("\n🧪 Test 1: Initialize VideoHandler")
    vh = VideoHandler(source=VideoSource.WEBCAM)
    print(f"   Source  : {vh.source}")
    print(f"   Target  : {vh.target_width}x{vh.target_height}")

    # ── Test 2: Open webcam ───────────────────────────────────
    print("\n🧪 Test 2: Open webcam")
    success = vh.open()
    print(f"   Opened  : {success}")
    print(f"   Is Open : {vh.is_open}")

    if success:
        # ── Test 3: Read frames ───────────────────────────────
        print("\n🧪 Test 3: Read 30 frames")
        frame_count = 0

        for i in range(30):
            ret, frame = vh.read()
            if ret:
                frame_count += 1
                # Draw info overlay
                frame = vh.draw_video_info(frame)

                cv2.imshow("Video Handler Test", frame)
                if cv2.waitKey(33) & 0xFF == ord('q'):
                    break
            else:
                print(f"   ⚠️  Frame read failed at {i}")

        print(f"   Frames read: {frame_count}")

        # ── Test 4: Preprocessing ─────────────────────────────
        print("\n🧪 Test 4: Preprocessing settings")
        vh.set_flip(horizontal=True)
        vh.set_brightness(20)
        vh.set_contrast(1.2)
        vh.toggle_enhance()

        ret, frame = vh.read()
        if ret:
            print(f"   Frame shape: {frame.shape}")
            print(f"   ✅ Preprocessing applied")

        # Reset
        vh.set_flip(False, False)
        vh.set_brightness(0)
        vh.set_contrast(1.0)
        vh.toggle_enhance()

        # ── Test 5: Pause / Resume ────────────────────────────
        print("\n🧪 Test 5: Pause and Resume")
        vh.pause()
        print(f"   Is Paused : {vh.is_paused}")
        vh.resume()
        print(f"   Is Paused : {vh.is_paused}")

        # ── Test 6: Stats ─────────────────────────────────────
        print("\n🧪 Test 6: Statistics")
        stats = vh.get_stats()
        for key, val in stats.items():
            print(f"   {key:<20} : {val}")

        # ── Test 7: Close ─────────────────────────────────────
        print("\n🧪 Test 7: Close")
        vh.close()
        print(f"   Is Open : {vh.is_open}")

    else:
        print("\n⚠️  Webcam not available")
        print("   Testing with video source simulation")

        # ── Test Stats Without Camera ─────────────────────────
        print("\n🧪 Stats Test (no camera):")
        stats = vh.get_stats()
        for key, val in stats.items():
            print(f"   {key:<20} : {val}")

    cv2.destroyAllWindows()

    print("\n" + "=" * 55)
    print("✅ VIDEO HANDLER TEST COMPLETE")
    print("=" * 55)
