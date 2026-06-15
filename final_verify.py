# ============================================================
# SmartShoppingCart/final_verify.py
# Final complete system verification - FIXED VERSION
# ============================================================

import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

print("=" * 60)
print("   SMART SHOPPING CART - FINAL VERIFICATION")
print("=" * 60)

# ── Check All Files ───────────────────────────────────────────
print("\n📁 Checking all project files...")

required_files = [
    "main.py",
    "config.py",
    "requirements.txt",
    "verify_setup.py",
    "summary_generator.py",
    "final_verify.py",
    "modules/__init__.py",
    "modules/barcode_scanner.py",
    "modules/person_detector.py",
    "modules/customer_tracker.py",
    "modules/smart_cart.py",
    "modules/dashboard.py",
    "modules/video_handler.py",
    "database/__init__.py",
    "database/db_setup.py",
    "database/db_manager.py",
    "database/products.db"
]

all_files_ok = True
for f in required_files:
    exists = os.path.exists(f)
    status = "✅" if exists else "❌"
    print(f"   {status} {f}")
    if not exists:
        all_files_ok = False

# ── Check Module Imports ──────────────────────────────────────
print("\n📦 Checking module imports...")
modules_ok = True

# ── config ────────────────────────────────────────────────────
try:
    from config import DATABASE_PATH, TAX_RATE
    print("   ✅ config.py")
except Exception as e:
    print(f"   ❌ config.py: {e}")
    modules_ok = False

# ── database ──────────────────────────────────────────────────
try:
    from database.db_manager import DatabaseManager
    print("   ✅ database.db_manager")
except Exception as e:
    print(f"   ❌ database.db_manager: {e}")
    modules_ok = False

# ── video_handler (import first - has VideoSource) ────────────
try:
    from modules.video_handler import VideoHandler, VideoSource
    print("   ✅ modules.video_handler")
except Exception as e:
    print(f"   ❌ modules.video_handler: {e}")
    modules_ok = False

# ── barcode_scanner ───────────────────────────────────────────
try:
    from modules.barcode_scanner import BarcodeScanner
    print("   ✅ modules.barcode_scanner")
except Exception as e:
    print(f"   ❌ modules.barcode_scanner: {e}")
    modules_ok = False

# ── person_detector ───────────────────────────────────────────
try:
    from modules.person_detector import PersonDetector
    print("   ✅ modules.person_detector")
except Exception as e:
    print(f"   ❌ modules.person_detector: {e}")
    modules_ok = False

# ── customer_tracker ──────────────────────────────────────────
try:
    from modules.customer_tracker import CustomerTracker
    print("   ✅ modules.customer_tracker")
except Exception as e:
    print(f"   ❌ modules.customer_tracker: {e}")
    modules_ok = False

# ── smart_cart ────────────────────────────────────────────────
try:
    from modules.smart_cart import SmartCart
    print("   ✅ modules.smart_cart")
except Exception as e:
    print(f"   ❌ modules.smart_cart: {e}")
    modules_ok = False

# ── dashboard ─────────────────────────────────────────────────
try:
    from modules.dashboard import Dashboard
    print("   ✅ modules.dashboard")
except Exception as e:
    print(f"   ❌ modules.dashboard: {e}")
    modules_ok = False

# ── summary_generator ─────────────────────────────────────────
try:
    from summary_generator import SummaryGenerator
    print("   ✅ summary_generator")
except Exception as e:
    print(f"   ❌ summary_generator: {e}")
    modules_ok = False

# ── Test Core Functions ───────────────────────────────────────
print("\n🧪 Testing core functions...")
core_ok = True

# Test DatabaseManager
try:
    db = DatabaseManager()
    print("   ✅ DatabaseManager created")
except Exception as e:
    print(f"   ❌ DatabaseManager: {e}")
    core_ok = False

# Test SmartCart
try:
    cart = SmartCart("Verification Test")
    print("   ✅ SmartCart created")
except Exception as e:
    print(f"   ❌ SmartCart: {e}")
    core_ok = False
    cart = None

# Test Add Item
if cart:
    try:
        result = cart.add_item_by_barcode("049000028911")
        print(f"   ✅ Add item  : {result['message']}")
    except Exception as e:
        print(f"   ❌ Add item  : {e}")
        core_ok = False

    try:
        result = cart.add_item_by_barcode("028400090179")
        print(f"   ✅ Add item  : {result['message']}")
    except Exception as e:
        print(f"   ❌ Add item  : {e}")
        core_ok = False

    try:
        totals = cart.get_totals()
        print(f"   ✅ Totals    : ${totals['total']:.2f}")
    except Exception as e:
        print(f"   ❌ Totals    : {e}")
        core_ok = False

    try:
        cart.increment_item("049000028911")
        print("   ✅ Increment item")
    except Exception as e:
        print(f"   ❌ Increment : {e}")
        core_ok = False

    try:
        cart.decrement_item("049000028911")
        print("   ✅ Decrement item")
    except Exception as e:
        print(f"   ❌ Decrement : {e}")
        core_ok = False

# Test BarcodeScanner
try:
    scanner = BarcodeScanner(cooldown=2.0)
    r1 = scanner.simulate_scan("049000028911")
    print(f"   ✅ Scanner scan  : {r1['barcode']}")

    r2 = scanner.simulate_scan("049000028911")
    print(f"   ✅ Cooldown block: {r2 is None}")
except Exception as e:
    print(f"   ❌ BarcodeScanner: {e}")
    core_ok = False

# Test PersonDetector
try:
    import numpy as np
    detector   = PersonDetector()
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    persons    = detector.detect_persons(test_frame)
    print(f"   ✅ PersonDetector: {len(persons)} detected")
except Exception as e:
    print(f"   ❌ PersonDetector: {e}")
    core_ok = False

# Test CustomerTracker
try:
    tracker = CustomerTracker()
    print(f"   ✅ CustomerTracker: {tracker.tracker_type}")
except Exception as e:
    print(f"   ❌ CustomerTracker: {e}")
    core_ok = False

# Test Dashboard
try:
    dash  = Dashboard(width=500, height=700)
    if cart:
        frame = dash.render(cart)
        print(f"   ✅ Dashboard render: {frame.shape}")
    else:
        print("   ⚠️  Dashboard skipped (no cart)")
except Exception as e:
    print(f"   ❌ Dashboard: {e}")
    core_ok = False

# Test VideoHandler
try:
    vh = VideoHandler(source=VideoSource.WEBCAM)
    print(f"   ✅ VideoHandler: {vh.source}")
except Exception as e:
    print(f"   ❌ VideoHandler: {e}")
    core_ok = False

# Test SummaryGenerator
try:
    gen    = SummaryGenerator()
    result = gen.generate(
        cart_stats = {
            "session_id"   : "VERIFY001",
            "customer"     : "Test",
            "items_added"  : 2,
            "items_removed": 0,
            "unknown_scans": 0,
            "scan_count"   : 2,
            "unique_items" : 2,
            "total_items"  : 2,
            "subtotal"     : 5.49,
            "tax"          : 0.44,
            "total"        : 5.93,
            "runtime_secs" : 10
        }
    )
    print(f"   ✅ SummaryGenerator: {result['lines']} lines")
except Exception as e:
    print(f"   ❌ SummaryGenerator: {e}")
    core_ok = False

# ── Check Output Files ────────────────────────────────────────
print("\n📂 Checking output files...")

output_files = list(os.listdir("output")) if os.path.exists("output") else []
if output_files:
    for f in output_files:
        print(f"   ✅ output/{f}")
else:
    print("   ⚠️  No output files yet")

# ── Final Result ──────────────────────────────────────────────
print("\n" + "=" * 60)

if all_files_ok and modules_ok and core_ok:
    print("✅ ALL CHECKS PASSED!")
    print("✅ SYSTEM FULLY READY!")
    print("")
    print("   ╔══════════════════════════════════════╗")
    print("   ║   Run the system with:               ║")
    print("   ║                                      ║")
    print("   ║   python3 main.py                    ║")
    print("   ║                                      ║")
    print("   ║   With options:                      ║")
    print("   ║   python3 main.py --customer Pranav  ║")
    print("   ║                                      ║")
    print("   ║   Press 1-9 : Simulate barcode scan  ║")
    print("   ║   Press L   : Lock customer          ║")
    print("   ║   Press H   : Show help              ║")
    print("   ║   Press Q   : Quit                   ║")
    print("   ╚══════════════════════════════════════╝")
else:
    print("❌ Some checks failed - Fix above errors")
    print("")
    if not all_files_ok:
        print("   → Some files are missing")
    if not modules_ok:
        print("   → Some imports failed")
    if not core_ok:
        print("   → Some core functions failed")

print("=" * 60)
