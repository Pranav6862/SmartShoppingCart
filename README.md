# 🛒 Smart Shopping Cart AI

An intelligent, AI-powered shopping cart prototype designed to track customers, scan products, and manage live shopping carts seamlessly. It features a modern web dashboard built with Flask and WebSocket integration for real-time video streaming and inventory tracking.

## ✨ Key Features

- **🛍️ Live Shopping Cart**: Maintains an active cart session, calculates subtotal, tax, and total, and provides a full checkout summary.
- **📷 Real-Time Barcode Scanning**: Uses `pyzbar` and advanced OpenCV image filtering (like Otsu Thresholding) to read barcodes, intelligently ignoring glare and preventing false positives.
- **🚶‍♂️ Customer Tracking**: Leverages **YOLOv8** for person detection and **DeepSORT** to uniquely identify and track a single customer throughout their session.
- **💻 Interactive Web Dashboard**: A responsive Flask-based web interface to monitor the camera feed, manage the cart, and view real-time AI tracking data over WebSockets (Socket.IO).
- **📦 Inventory Database**: Powered by SQLite3, allowing for easy product lookups and pricing synchronization.

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask, Flask-SocketIO
- **Computer Vision**: OpenCV (`cv2`)
- **AI / Tracking**: Ultralytics (YOLOv8), `deep-sort-realtime`
- **Barcode Decoding**: `pyzbar`
- **Database**: SQLite3
- **Frontend**: HTML5, Vanilla CSS, JavaScript

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Pranav6862/SmartShoppingCart.git
cd SmartShoppingCart
```

### 2. Set up the Virtual Environment
Create and activate the virtual environment:
```bash
python3 -m venv smartcart_env
source smartcart_env/bin/activate  # On macOS/Linux
# OR: .\smartcart_env\Scripts\activate # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize the Database
This will create `database/products.db` and populate it with sample products (like KitKats, Oreos, and beverages).
```bash
python database/db_setup.py
```

### 5. Run the Application
Start the Flask development server:
```bash
python web/app.py
```
Open your browser and navigate to: **`http://localhost:5001`**

## ⚙️ Configuration

You can customize the application's behavior using the following environment variables (or by editing `config.py`):

- `SMARTCART_WEBCAM_INDEX`: Selects the default webcam (default: `0`)
- `SMARTCART_BARCODE_COOLDOWN`: Delay in seconds between scanning the same barcode (default: `3.0`)
- `SMARTCART_TAX_RATE`: Default tax applied at checkout (default: `0.08`)
- `SMARTCART_CURRENCY_SYMBOL`: Display currency (default: `$`)

---
*Developed as an advanced prototype for AI-driven retail technology.*
