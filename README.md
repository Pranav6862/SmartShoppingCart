# SmartCart

AI-based smart shopping cart prototype with a professional web dashboard for video input, customer tracking, barcode scanning, cart management, and checkout.

## What It Does

- Starts a shopping session from a webcam or uploaded video.
- Detects people in the video feed and lets an operator lock onto a customer.
- Scans barcodes from the camera feed, with quick-scan controls for testing.
- Looks up products from SQLite and maintains a live cart with tax and checkout receipt.
- Streams the processed camera feed to a Flask dashboard with real-time cart/status updates.

## Project Layout

- `web/app.py` - Flask and Socket.IO web application.
- `web/templates/index.html` - main dashboard.
- `web/static/` - frontend styles and behavior.
- `modules/` - computer vision, scanning, tracking, cart, and video modules.
- `database/` - SQLite setup and database access.
- `config.py` - environment-aware application settings.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database/db_setup.py
```

## Run

```bash
python web/app.py
```

Open `http://localhost:5001`.

## Useful Environment Variables

- `SMARTCART_SECRET_KEY` - Flask secret key.
- `SMARTCART_WEBCAM_INDEX` - webcam index, default `0`.
- `SMARTCART_TAX_RATE` - tax rate, default `0.08`.
- `SMARTCART_CURRENCY_SYMBOL` - display currency, default `$`.
- `SMARTCART_BARCODE_COOLDOWN` - seconds between accepted scans, default `2.0`.
- `SMARTCART_YOLO_MODEL` - YOLO model path/name, default `yolov8n.pt`.

## Notes

The app can run without optional AI/barcode dependencies, but detection/scanning quality depends on `ultralytics`, `deep-sort-realtime`, and `pyzbar` being installed and supported on the host system.
