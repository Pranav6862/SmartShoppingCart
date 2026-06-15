# ============================================================
# SmartShoppingCart/summary_generator.py
# Executive Summary Generator
# - Auto generates TXT report
# - Session statistics
# - Cart receipt
# - System performance report
# - Complete project documentation
# - Full system health check
# ============================================================

import os
import sys
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

# ── Add project root ──────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

from config import (
    DATABASE_PATH,
    OUTPUT_DIR,
    SUMMARY_OUTPUT,
    CURRENCY_SYMBOL,
    TAX_RATE,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    YOLO_MODEL,
    BARCODE_COOLDOWN
)


# ============================================================
# SUMMARY GENERATOR CLASS
# ============================================================

class SummaryGenerator:
    """
    Executive Summary Generator
    ───────────────────────────
    Generates comprehensive reports about
    the Smart Shopping Cart system session
    Outputs formatted TXT and JSON reports
    """

    def __init__(self):
        self.output_dir    = OUTPUT_DIR
        self.timestamp     = datetime.now()
        self.report_lines  = []
        self.report_data   = {}

        # ── Ensure output dir exists ──────────────────────────
        os.makedirs(self.output_dir, exist_ok=True)

        print("✅ SummaryGenerator initialized")

    # =========================================================
    # MAIN GENERATE FUNCTION
    # =========================================================

    def generate(self,
                 cart_stats    = None,
                 tracker_stats = None,
                 scanner_stats = None,
                 video_stats   = None,
                 session_id    = None):
        """
        Generate complete executive summary

        Args:
            cart_stats    : SmartCart.get_stats() dict
            tracker_stats : CustomerTracker.get_stats() dict
            scanner_stats : BarcodeScanner.get_stats() dict
            video_stats   : VideoHandler.get_stats() dict
            session_id    : session ID string

        Returns:
            dict with paths to generated files
        """
        print("\n📄 Generating executive summary...")

        self.report_lines = []
        self.report_data  = {}

        # ── Build Report Sections ─────────────────────────────
        self._add_header()
        self._add_executive_summary(cart_stats)
        self._add_session_details(cart_stats, session_id)
        self._add_cart_analysis(cart_stats)
        self._add_database_report()
        self._add_tracking_report(tracker_stats)
        self._add_scanner_report(scanner_stats)
        self._add_video_report(video_stats)
        self._add_system_config()
        self._add_performance_metrics(
            cart_stats, tracker_stats,
            scanner_stats, video_stats
        )
        self._add_recommendations()
        self._add_footer()

        # ── Save Reports ──────────────────────────────────────
        txt_path  = self._save_txt_report()
        json_path = self._save_json_report()

        print(f"\n✅ Reports generated:")
        print(f"   TXT  : {txt_path}")
        print(f"   JSON : {json_path}")

        return {
            "txt_path"  : txt_path,
            "json_path" : json_path,
            "lines"     : len(self.report_lines)
        }

    # =========================================================
    # REPORT SECTIONS
    # =========================================================

    def _add_header(self):
        """Add report header"""
        ts   = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        date = self.timestamp.strftime("%B %d, %Y")

        self._line("=" * 65)
        self._line(" " * 10 + "AI-BASED SMART SHOPPING CART SYSTEM")
        self._line(" " * 18 + "EXECUTIVE SUMMARY REPORT")
        self._line("=" * 65)
        self._line(f"  Generated   : {ts}")
        self._line(f"  Date        : {date}")
        self._line(f"  System      : Smart Shopping Cart v1.0")
        self._line(f"  Platform    : Python / OpenCV / YOLOv8")
        self._line(f"  Report Type : Post-Session Analysis")
        self._line("=" * 65)
        self._blank()

    def _add_executive_summary(self, cart_stats):
        """Add executive summary section"""
        self._section("1. EXECUTIVE SUMMARY")

        self._line(
            "  The AI-Based Smart Shopping Cart System successfully"
        )
        self._line(
            "  completed a retail session using computer vision,"
        )
        self._line(
            "  automated barcode scanning, and real-time billing."
        )
        self._blank()

        if cart_stats:
            total   = cart_stats.get("total", 0)
            items   = cart_stats.get("total_items", 0)
            unique  = cart_stats.get("unique_items", 0)
            scans   = cart_stats.get("scan_count", 0)
            runtime = cart_stats.get("runtime_secs", 0)

            self._line("  KEY HIGHLIGHTS:")
            self._line(f"  ┌─────────────────────────────────────┐")
            self._line(f"  │  Total Revenue    : {CURRENCY_SYMBOL}{total:<12.2f}    │")
            self._line(f"  │  Items Purchased  : {items:<16}│")
            self._line(f"  │  Unique Products  : {unique:<16}│")
            self._line(f"  │  Barcodes Scanned : {scans:<16}│")
            self._line(f"  │  Session Duration : {runtime}s{'':<12}│")
            self._line(f"  └─────────────────────────────────────┘")
        else:
            self._line("  No session data available")

        self._blank()

    def _add_session_details(self, cart_stats, session_id):
        """Add session details section"""
        self._section("2. SESSION DETAILS")

        sid      = session_id or (
            cart_stats.get("session_id", "N/A")
            if cart_stats else "N/A"
        )
        customer = (
            cart_stats.get("customer", "N/A")
            if cart_stats else "N/A"
        )
        runtime  = (
            cart_stats.get("runtime_secs", 0)
            if cart_stats else 0
        )

        mins = runtime // 60
        secs = runtime % 60

        self._kv("  Session ID",    sid)
        self._kv("  Customer Name", customer)
        self._kv("  Start Time",
                 self.timestamp.strftime("%H:%M:%S"))
        self._kv("  Duration",      f"{mins}m {secs}s")
        self._kv("  Status",        "Completed")
        self._blank()

        if cart_stats:
            self._line("  TRANSACTION SUMMARY:")
            self._line("  " + "-" * 40)
            self._kv("  Items Added",
                     cart_stats.get("items_added", 0))
            self._kv("  Items Removed",
                     cart_stats.get("items_removed", 0))
            self._kv("  Unknown Barcodes",
                     cart_stats.get("unknown_scans", 0))
            self._kv("  Successful Scans",
                     cart_stats.get("scan_count", 0))
            self._line("  " + "-" * 40)

            subtotal = cart_stats.get("subtotal", 0)
            tax      = cart_stats.get("tax", 0)
            total    = cart_stats.get("total", 0)

            self._kv("  Subtotal",
                     f"{CURRENCY_SYMBOL}{subtotal:.2f}")
            self._kv(f"  Tax ({int(TAX_RATE*100)}%)",
                     f"{CURRENCY_SYMBOL}{tax:.2f}")
            self._kv("  GRAND TOTAL",
                     f"{CURRENCY_SYMBOL}{total:.2f}")

        self._blank()

    def _add_cart_analysis(self, cart_stats):
        """Add cart contents analysis"""
        self._section("3. CART CONTENTS ANALYSIS")

        # ── Get items from database ───────────────────────────
        items = self._get_cart_items_from_db(
            cart_stats.get("session_id") if cart_stats else None
        )

        if items:
            self._line(
                f"  {'PRODUCT':<25}"
                f"{'QTY':>5}"
                f"{'UNIT PRICE':>12}"
                f"{'TOTAL':>10}"
            )
            self._line("  " + "-" * 55)

            for item in items:
                name  = item["product_name"][:24]
                qty   = item["quantity"]
                price = item["unit_price"]
                total = item["total_price"]

                self._line(
                    f"  {name:<25}"
                    f"{qty:>5}"
                    f"  {CURRENCY_SYMBOL}{price:>9.2f}"
                    f"  {CURRENCY_SYMBOL}{total:>7.2f}"
                )

            self._line("  " + "-" * 55)

            if cart_stats:
                sub = cart_stats.get("subtotal", 0)
                tax = cart_stats.get("tax", 0)
                tot = cart_stats.get("total", 0)

                self._line(
                    f"  {'Subtotal':<30}"
                    f"{CURRENCY_SYMBOL}{sub:>10.2f}"
                )
                self._line(
                    f"  {'Tax':<30}"
                    f"{CURRENCY_SYMBOL}{tax:>10.2f}"
                )
                self._line(
                    f"  {'TOTAL':<30}"
                    f"{CURRENCY_SYMBOL}{tot:>10.2f}"
                )

            # ── Category breakdown ────────────────────────────
            self._blank()
            self._line("  CATEGORY BREAKDOWN:")
            categories = self._get_category_breakdown_from_db(
                cart_stats.get("session_id")
                if cart_stats else None
            )

            for cat, data in categories.items():
                self._line(
                    f"  • {cat:<20}"
                    f" {data['count']} items"
                    f"  {CURRENCY_SYMBOL}{data['total']:.2f}"
                )
        else:
            self._line("  No cart items found for this session")

        self._blank()

    def _add_database_report(self):
        """Add database statistics"""
        self._section("4. DATABASE REPORT")

        try:
            conn   = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # Product stats
            cursor.execute("SELECT COUNT(*) FROM products")
            product_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT category) FROM products"
            )
            cat_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT MIN(price), MAX(price), AVG(price)"
                " FROM products"
            )
            price_stats = cursor.fetchone()

            # Session stats
            cursor.execute("SELECT COUNT(*) FROM cart_sessions")
            session_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM cart_sessions"
                " WHERE status='completed'"
            )
            completed = cursor.fetchone()[0]

            # Scan stats
            cursor.execute("SELECT COUNT(*) FROM scan_history")
            total_scans = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM scan_history"
                " WHERE scan_result='success'"
            )
            success_scans = cursor.fetchone()[0]

            conn.close()

            self._line("  PRODUCT DATABASE:")
            self._kv("  Total Products",   product_count)
            self._kv("  Categories",       cat_count)
            self._kv("  Price Range",
                     f"{CURRENCY_SYMBOL}{price_stats[0]:.2f}"
                     f" - {CURRENCY_SYMBOL}{price_stats[1]:.2f}")
            self._kv("  Average Price",
                     f"{CURRENCY_SYMBOL}{price_stats[2]:.2f}")
            self._blank()

            self._line("  SESSION DATABASE:")
            self._kv("  Total Sessions",   session_count)
            self._kv("  Completed",        completed)
            self._kv("  Active",
                     session_count - completed)
            self._blank()

            self._line("  SCAN DATABASE:")
            self._kv("  Total Scans",      total_scans)
            self._kv("  Successful",       success_scans)
            self._kv("  Failed",
                     total_scans - success_scans)

            if total_scans > 0:
                rate = (success_scans / total_scans) * 100
                self._kv("  Success Rate",
                         f"{rate:.1f}%")

            # ── Top Products ──────────────────────────────────
            self._blank()
            self._line("  TOP SCANNED PRODUCTS:")

            conn   = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ci.product_name,
                       SUM(ci.quantity) as total_qty,
                       SUM(ci.total_price) as revenue
                FROM cart_items ci
                GROUP BY ci.barcode
                ORDER BY total_qty DESC
                LIMIT 5
            ''')

            top_products = cursor.fetchall()
            conn.close()

            for i, prod in enumerate(top_products, 1):
                self._line(
                    f"  {i}. {prod[0][:25]:<25}"
                    f"  Qty:{prod[1]}"
                    f"  Rev:{CURRENCY_SYMBOL}{prod[2]:.2f}"
                )

        except Exception as e:
            self._line(f"  Database read error: {e}")

        self._blank()

    def _add_tracking_report(self, tracker_stats):
        """Add customer tracking statistics"""
        self._section("5. CUSTOMER TRACKING REPORT")

        if tracker_stats:
            self._kv("  Tracker Backend",
                     tracker_stats.get("tracker_type", "N/A"))
            self._kv("  Total Frames",
                     tracker_stats.get("total_frames", 0))
            self._kv("  Frames Tracked",
                     tracker_stats.get("locked_frames", 0))

            total  = tracker_stats.get("total_frames", 1)
            locked = tracker_stats.get("locked_frames", 0)
            rate   = (locked / max(1, total)) * 100

            self._kv("  Tracking Rate",    f"{rate:.1f}%")
            self._kv("  Lost Events",
                     tracker_stats.get("lost_events", 0))
            self._kv("  Recovered Events",
                     tracker_stats.get("recovered_events", 0))
            self._kv("  Smooth Factor",
                     tracker_stats.get("smooth_factor", 0))
            self._kv("  Locked Customer ID",
                     tracker_stats.get("locked_id", "None"))
            self._blank()

            # ── Performance rating ────────────────────────────
            if rate >= 90:
                rating = "EXCELLENT ⭐⭐⭐⭐⭐"
            elif rate >= 75:
                rating = "GOOD      ⭐⭐⭐⭐"
            elif rate >= 60:
                rating = "FAIR      ⭐⭐⭐"
            else:
                rating = "NEEDS IMPROVEMENT ⭐⭐"

            self._kv("  Tracking Quality", rating)
        else:
            self._line("  No tracking data available")

        self._blank()

    def _add_scanner_report(self, scanner_stats):
        """Add barcode scanner statistics"""
        self._section("6. BARCODE SCANNER REPORT")

        if scanner_stats:
            total   = scanner_stats.get("total_scans", 0)
            success = scanner_stats.get("successful_scans", 0)
            failed  = scanner_stats.get("failed_scans", 0)
            rate    = (
                (success / max(1, total)) * 100
            )

            self._kv("  Total Scans",      total)
            self._kv("  Successful",       success)
            self._kv("  Failed",           failed)
            self._kv("  Success Rate",     f"{rate:.1f}%")
            self._kv("  Cooldown Setting",
                     f"{BARCODE_COOLDOWN}s")
            self._kv("  Last Barcode",
                     scanner_stats.get("last_barcode", "N/A"))
            self._kv("  Scanner Active",
                     scanner_stats.get("is_active", False))
        else:
            self._line("  No scanner data available")

        self._blank()

    def _add_video_report(self, video_stats):
        """Add video input statistics"""
        self._section("7. VIDEO INPUT REPORT")

        if video_stats:
            self._kv("  Source",
                     video_stats.get("source", "N/A"))
            self._kv("  Resolution",
                     video_stats.get("resolution", "N/A"))
            self._kv("  Target FPS",
                     video_stats.get("target_fps", 0))
            self._kv("  Actual FPS",
                     video_stats.get("current_fps", 0))
            self._kv("  Total Frames",
                     video_stats.get("frame_count", 0))
            self._kv("  Dropped Frames",
                     video_stats.get("dropped_frames", 0))
            self._kv("  Enhancement",
                     video_stats.get("enhance", False))
            self._kv("  Denoise",
                     video_stats.get("denoise", False))
            self._kv("  Runtime",
                     f"{video_stats.get('runtime_secs',0)}s")
        else:
            self._line("  No video data available")

        self._blank()

    def _add_system_config(self):
        """Add system configuration section"""
        self._section("8. SYSTEM CONFIGURATION")

        self._line("  VISION SETTINGS:")
        self._kv("  YOLO Model",        YOLO_MODEL)
        self._kv("  Camera Resolution",
                 f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}")
        self._kv("  Target FPS",        VIDEO_FPS)
        self._kv("  Scan Cooldown",     f"{BARCODE_COOLDOWN}s")
        self._blank()

        self._line("  BILLING SETTINGS:")
        self._kv("  Tax Rate",
                 f"{int(TAX_RATE * 100)}%")
        self._kv("  Currency",          CURRENCY_SYMBOL)
        self._blank()

        self._line("  SOFTWARE STACK:")
        libs = [
            ("Language",     "Python 3.11"),
            ("CV Library",   "OpenCV 4.8"),
            ("Detection",    "YOLOv8 (Ultralytics)"),
            ("Tracking",     "DeepSORT / SimpleIOU"),
            ("Barcode",      "pyzbar"),
            ("Database",     "SQLite3"),
            ("UI Render",    "OpenCV imshow"),
        ]
        for name, val in libs:
            self._kv(f"  {name}", val)

        self._blank()

    def _add_performance_metrics(self, cart_stats,
                                  tracker_stats,
                                  scanner_stats,
                                  video_stats):
        """Add performance metrics section"""
        self._section("9. PERFORMANCE METRICS")

        self._line("  SYSTEM PERFORMANCE:")
        self._line("  " + "-" * 45)

        # ── Metrics ───────────────────────────────────────────
        metrics = []

        if video_stats:
            fps     = video_stats.get("current_fps", 0)
            target  = video_stats.get("target_fps", 30)
            perf    = (fps / max(1, target)) * 100
            metrics.append(("Video FPS",
                             f"{fps:.1f}/{target}",
                             perf))

        if tracker_stats:
            total  = tracker_stats.get("total_frames", 1)
            locked = tracker_stats.get("locked_frames", 0)
            perf   = (locked / max(1, total)) * 100
            metrics.append(("Tracking Rate",
                             f"{perf:.1f}%",
                             perf))

        if scanner_stats:
            total   = scanner_stats.get("total_scans", 1)
            success = scanner_stats.get("successful_scans", 0)
            perf    = (success / max(1, total)) * 100
            metrics.append(("Scan Success",
                             f"{perf:.1f}%",
                             perf))

        # ── Print metrics with bar ────────────────────────────
        for name, value, perf in metrics:
            bar_len = 20
            filled  = int(bar_len * perf / 100)
            bar     = "█" * filled + "░" * (bar_len - filled)

            if perf >= 80:
                status = "GOOD"
            elif perf >= 60:
                status = "FAIR"
            else:
                status = "POOR"

            self._line(
                f"  {name:<18} [{bar}]"
                f" {value:<10} {status}"
            )

        self._blank()

        # ── Overall Score ─────────────────────────────────────
        if metrics:
            avg_perf = sum(m[2] for m in metrics) / len(metrics)
            stars    = "⭐" * min(5, int(avg_perf / 20))

            self._line("  OVERALL SYSTEM SCORE:")
            self._line(f"  Score  : {avg_perf:.1f} / 100")
            self._line(f"  Rating : {stars}")

            if avg_perf >= 90:
                self._line("  Grade  : A+ (Excellent)")
            elif avg_perf >= 80:
                self._line("  Grade  : A  (Very Good)")
            elif avg_perf >= 70:
                self._line("  Grade  : B  (Good)")
            elif avg_perf >= 60:
                self._line("  Grade  : C  (Average)")
            else:
                self._line("  Grade  : D  (Needs Improvement)")

        self._blank()

    def _add_recommendations(self):
        """Add recommendations section"""
        self._section("10. RECOMMENDATIONS & FUTURE WORK")

        recommendations = [
            (
                "RFID Integration",
                "Add RFID readers for instant multi-item scanning",
                "HIGH"
            ),
            (
                "Mobile App",
                "Customer mobile app for digital receipts and payment",
                "HIGH"
            ),
            (
                "Face Recognition",
                "Auto customer identification using face recognition",
                "MEDIUM"
            ),
            (
                "Weight Sensors",
                "Add scale sensors to verify item quantities",
                "MEDIUM"
            ),
            (
                "Theft Detection",
                "AI model to detect unscanned item placement",
                "HIGH"
            ),
            (
                "Auto Navigation",
                "Autonomous cart movement using obstacle detection",
                "LOW"
            ),
            (
                "Discount System",
                "Coupon and loyalty points integration",
                "MEDIUM"
            ),
            (
                "Cloud Sync",
                "Real-time inventory sync with store cloud system",
                "HIGH"
            ),
            (
                "Voice Assistant",
                "Voice commands for hands-free cart management",
                "LOW"
            ),
            (
                "Multi-language",
                "Support for multiple languages on dashboard",
                "LOW"
            ),
        ]

        self._line(
            f"  {'FEATURE':<25}"
            f"{'DESCRIPTION':<40}"
            f"{'PRIORITY':>8}"
        )
        self._line("  " + "-" * 75)

        for feature, desc, priority in recommendations:
            short_desc = desc[:38]
            self._line(
                f"  {feature:<25}"
                f"{short_desc:<40}"
                f"{priority:>8}"
            )

        self._blank()
        self._line("  IMMEDIATE IMPROVEMENTS:")
        self._line("  1. Install all Python libraries for full functionality")
        self._line("  2. Test with real barcoded products")
        self._line("  3. Calibrate camera for optimal barcode detection")
        self._line("  4. Add more products to database")
        self._line("  5. Fine-tune YOLO confidence threshold")
        self._blank()

    def _add_footer(self):
        """Add report footer"""
        self._line("=" * 65)
        self._line("  REPORT END")
        self._line("=" * 65)
        self._line(
            f"  Generated by: Smart Shopping Cart System v1.0"
        )
        self._line(
            f"  Timestamp   : "
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._line(
            "  © 2024 Smart Shopping Cart - AI Retail System"
        )
        self._line("=" * 65)

    # =========================================================
    # DATABASE HELPERS
    # =========================================================

    def _get_cart_items_from_db(self, session_id):
        """Get cart items for session from database"""
        if not session_id:
            return []

        try:
            conn   = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT product_name, quantity,
                       unit_price, total_price
                FROM cart_items
                WHERE session_id = ?
                ORDER BY added_at ASC
            ''', (session_id,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "product_name" : r[0],
                    "quantity"     : r[1],
                    "unit_price"   : r[2],
                    "total_price"  : r[3]
                }
                for r in rows
            ]
        except Exception as e:
            print(f"⚠️  DB read error: {e}")
            return []

    def _get_category_breakdown_from_db(self, session_id):
        """Get category breakdown from database"""
        if not session_id:
            return {}

        try:
            conn   = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.category,
                       COUNT(ci.id)        as item_count,
                       SUM(ci.total_price) as revenue
                FROM cart_items ci
                JOIN products p ON ci.barcode = p.barcode
                WHERE ci.session_id = ?
                GROUP BY p.category
                ORDER BY revenue DESC
            ''', (session_id,))

            rows = cursor.fetchall()
            conn.close()

            return {
                row[0]: {
                    "count" : row[1],
                    "total" : row[2] or 0
                }
                for row in rows
            }
        except Exception as e:
            print(f"⚠️  Category DB error: {e}")
            return {}

    # =========================================================
    # SAVE FUNCTIONS
    # =========================================================

    def _save_txt_report(self):
        """Save report as formatted text file"""
        ts       = self.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"summary_report_{ts}.txt"
        path     = os.path.join(self.output_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.report_lines))

        # Also save as latest
        latest_path = os.path.join(
            self.output_dir, "latest_report.txt"
        )
        with open(latest_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.report_lines))

        return path

    def _save_json_report(self):
        """Save report data as JSON"""
        ts       = self.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"summary_data_{ts}.json"
        path     = os.path.join(self.output_dir, filename)

        self.report_data["generated_at"] = (
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.report_data["system"]       = "Smart Shopping Cart v1.0"
        self.report_data["report_lines"] = len(self.report_lines)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.report_data, f,
                      indent=4, default=str)

        return path

    # =========================================================
    # HELPER METHODS
    # =========================================================

    def _line(self, text=""):
        """Add a line to report"""
        self.report_lines.append(text)

    def _blank(self):
        """Add blank line"""
        self.report_lines.append("")

    def _section(self, title):
        """Add section header"""
        self.report_lines.append("")
        self.report_lines.append("  " + "─" * 60)
        self.report_lines.append(f"  {title}")
        self.report_lines.append("  " + "─" * 60)
        self.report_lines.append("")

    def _kv(self, key, value):
        """Add key-value line"""
        self.report_lines.append(f"  {key:<25} : {value}")

    def print_report(self):
        """Print report to terminal"""
        print("\n".join(self.report_lines))

    def get_report_text(self):
        """Get report as string"""
        return "\n".join(self.report_lines)


# ============================================================
# STANDALONE TEST - GENERATE DEMO REPORT
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("   EXECUTIVE SUMMARY GENERATOR - TEST")
    print("=" * 60)

    generator = SummaryGenerator()

    # ── Mock Stats for Demo ───────────────────────────────────
    mock_cart_stats = {
        "session_id"    : "DEMO001",
        "customer"      : "Demo Customer",
        "items_added"   : 8,
        "items_removed" : 2,
        "unknown_scans" : 1,
        "scan_count"    : 8,
        "unique_items"  : 5,
        "total_items"   : 6,
        "subtotal"      : 18.46,
        "tax"           : 1.48,
        "total"         : 19.94,
        "runtime_secs"  : 245,
        "is_active"     : False,
        "is_checkout"   : True
    }

    mock_tracker_stats = {
        "tracker_type"    : "DeepSORT",
        "total_frames"    : 7350,
        "locked_frames"   : 6890,
        "active_tracks"   : 2,
        "is_locked"       : True,
        "locked_id"       : 1,
        "lost_events"     : 3,
        "recovered_events": 3,
        "lost_frame_count": 0,
        "runtime_seconds" : 245,
        "smooth_factor"   : 0.7
    }

    mock_scanner_stats = {
        "total_scans"       : 9,
        "successful_scans"  : 8,
        "failed_scans"      : 1,
        "last_barcode"      : "049000028911",
        "cooldown_remaining": 0.0,
        "is_active"         : True,
        "is_ready"          : True
    }

    mock_video_stats = {
        "source"          : "webcam",
        "is_open"         : True,
        "is_paused"       : False,
        "is_recording"    : False,
        "frame_count"     : 7350,
        "total_read"      : 7350,
        "dropped_frames"  : 12,
        "current_fps"     : 28.4,
        "target_fps"      : 30,
        "resolution"      : "1280x720",
        "runtime_secs"    : 245,
        "video_progress"  : "100%",
        "position_secs"   : 245.0,
        "loop_video"      : False,
        "flip_h"          : False,
        "enhance"         : False,
        "denoise"         : False
    }

    # ── Generate Summary ──────────────────────────────────────
    result = generator.generate(
        cart_stats    = mock_cart_stats,
        tracker_stats = mock_tracker_stats,
        scanner_stats = mock_scanner_stats,
        video_stats   = mock_video_stats,
        session_id    = "DEMO001"
    )

    # ── Print to terminal ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("   GENERATED REPORT PREVIEW")
    print("=" * 60)
    generator.print_report()

    print("\n" + "=" * 60)
    print(f"✅ Report saved to: {result['txt_path']}")
    print(f"✅ JSON saved to  : {result['json_path']}")
    print(f"   Total lines    : {result['lines']}")
    print("=" * 60)
