import os
import sys

print("=" * 50)
print("   SMART SHOPPING CART - SETUP VERIFICATION")
print("=" * 50)

# ── Check Folders ─────────────────────────────────────────
folders = [
    "modules",
    "database",
    "assets",
    "logs",
    "output",
    "assets/yolo_weights"
]

print("\n📁 Checking Folders:")
for folder in folders:
    if os.path.exists(folder):
        print(f"   ✅ {folder}")
    else:
        print(f"   ❌ {folder} - MISSING! Run: mkdir {folder}")

# ── Check Files ───────────────────────────────────────────
files = [
    "requirements.txt",
    "config.py",
    "modules/__init__.py",
    "database/__init__.py",
    "verify_setup.py"
]

print("\n📄 Checking Files:")
for file in files:
    if os.path.exists(file):
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ {file} - MISSING!")

# ── Check Libraries ───────────────────────────────────────
print("\n📦 Checking Library Installations:")

libraries = {
    "cv2"               : "opencv-python",
    "pyzbar"            : "pyzbar",
    "ultralytics"       : "ultralytics",
    "deep_sort_realtime": "deep-sort-realtime",
    "numpy"             : "numpy",
    "PIL"               : "Pillow",
    "streamlit"         : "streamlit",
    "pandas"            : "pandas",
    "sqlalchemy"        : "SQLAlchemy",
    "matplotlib"        : "matplotlib"
}

all_good = True
for lib, package in libraries.items():
    try:
        __import__(lib)
        print(f"   ✅ {package}")
    except ImportError:
        print(f"   ❌ {package} - Run: pip install {package}")
        all_good = False

# ── Final Result ──────────────────────────────────────────
print("\n" + "=" * 50)
if all_good:
    print("✅ ALL CHECKS PASSED! Ready for STEP 2")
else:
    print("❌ Fix issues above before going to STEP 2")
print("=" * 50)
