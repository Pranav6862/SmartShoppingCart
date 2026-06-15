# ============================================================
# SmartShoppingCart/database/db_manager.py
# All database query functions used by the system
# ============================================================

import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

from config import DATABASE_PATH, TAX_RATE

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles all database operations"""

    def __init__(self):
        self.db_path    = DATABASE_PATH
        self.session_id = None
        self._ensure_database()

    def _ensure_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("Database operation failed")
            raise
        finally:
            conn.close()

    # =========================================================
    # PRODUCT FUNCTIONS
    # =========================================================

    def get_product_by_barcode(self, barcode):
        """
        Fetch product details using barcode
        Returns: dict with product info or None
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products
                WHERE barcode = ?
            ''', (barcode,))
            row = cursor.fetchone()

        if row:
            return {
                "id"          : row["id"],
                "barcode"     : row["barcode"],
                "name"        : row["name"],
                "brand"       : row["brand"],
                "category"    : row["category"],
                "price"       : row["price"],
                "unit"        : row["unit"],
                "stock"       : row["stock"],
                "description" : row["description"]
            }
        return None

    def get_all_products(self):
        """Get all products from database"""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products ORDER BY category, name')
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def search_product(self, keyword):
        """Search product by name or brand"""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products
                WHERE name  LIKE ?
                OR brand    LIKE ?
                OR category LIKE ?
            ''', (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # =========================================================
    # SESSION FUNCTIONS
    # =========================================================

    def start_session(self, customer_name="Customer"):
        """Start a new cart session"""
        self.session_id = str(uuid.uuid4())[:8].upper()

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO cart_sessions
                (session_id, customer_name, started_at, status)
                VALUES (?, ?, ?, ?)
            ''', (
                self.session_id,
                customer_name,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "active"
            ))

        logger.info("Session started: %s", self.session_id)
        return self.session_id

    def end_session(self, total_amount, tax_amount):
        """End current cart session"""
        if not self.session_id:
            return False

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE cart_sessions SET
                    ended_at     = ?,
                    total_amount = ?,
                    tax_amount   = ?,
                    status       = ?
                WHERE session_id = ?
            ''', (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total_amount,
                tax_amount,
                "completed",
                self.session_id
            ))

        logger.info("Session completed: %s", self.session_id)
        return True

    def get_session_details(self, session_id=None):
        """Get session details"""
        sid    = session_id or self.session_id
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM cart_sessions
                WHERE session_id = ?
            ''', (sid,))
            row = cursor.fetchone()
        return dict(row) if row else None

    # =========================================================
    # CART ITEM FUNCTIONS
    # =========================================================

    def add_cart_item(self, barcode, product_name, unit_price, quantity=1):
        """Add or update item in cart"""
        if not self.session_id:
            print("❌ No active session!")
            return False

        conn   = self.get_connection()
        cursor = conn.cursor()

        # Check if item already exists in session
        cursor.execute('''
            SELECT id, quantity FROM cart_items
            WHERE session_id = ? AND barcode = ?
        ''', (self.session_id, barcode))

        existing = cursor.fetchone()

        if existing:
            # Update quantity
            new_qty         = existing["quantity"] + quantity
            new_total_price = unit_price * new_qty

            cursor.execute('''
                UPDATE cart_items SET
                    quantity    = ?,
                    total_price = ?
                WHERE id = ?
            ''', (new_qty, new_total_price, existing["id"]))

        else:
            # Insert new item
            cursor.execute('''
                INSERT INTO cart_items
                (session_id, barcode, product_name, 
                 quantity, unit_price, total_price, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id,
                barcode,
                product_name,
                quantity,
                unit_price,
                unit_price * quantity,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        conn.commit()
        conn.close()
        return True

    def remove_cart_item(self, barcode, quantity=1):
        """Remove or reduce item quantity from cart"""
        if not self.session_id:
            return False

        conn   = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, quantity, unit_price FROM cart_items
            WHERE session_id = ? AND barcode = ?
        ''', (self.session_id, barcode))

        existing = cursor.fetchone()

        if not existing:
            conn.close()
            return False

        if existing["quantity"] <= quantity:
            # Remove item completely
            cursor.execute('''
                DELETE FROM cart_items
                WHERE id = ?
            ''', (existing["id"],))
        else:
            # Reduce quantity
            new_qty         = existing["quantity"] - quantity
            new_total_price = existing["unit_price"] * new_qty

            cursor.execute('''
                UPDATE cart_items SET
                    quantity    = ?,
                    total_price = ?
                WHERE id = ?
            ''', (new_qty, new_total_price, existing["id"]))

        conn.commit()
        conn.close()
        return True

    def get_cart_items(self):
        """Get all items in current cart"""
        if not self.session_id:
            return []

        conn   = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM cart_items
            WHERE session_id = ?
            ORDER BY added_at ASC
        ''', (self.session_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_cart(self):
        """Remove all items from current cart"""
        if not self.session_id:
            return False

        conn   = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM cart_items
            WHERE session_id = ?
        ''', (self.session_id,))

        conn.commit()
        conn.close()
        print("🗑️  Cart cleared")
        return True

    def get_cart_total(self):
        """Calculate cart totals"""
        items      = self.get_cart_items()
        subtotal   = sum(item["total_price"] for item in items)
        tax        = round(subtotal * TAX_RATE, 2)
        total      = round(subtotal + tax, 2)
        item_count = sum(item["quantity"] for item in items)

        return {
            "subtotal"   : round(subtotal, 2),
            "tax"        : tax,
            "total"      : total,
            "item_count" : item_count,
            "unique_items": len(items)
        }

    # =========================================================
    # SCAN HISTORY FUNCTIONS
    # =========================================================

    def log_scan(self, barcode, result="success"):
        """Log every barcode scan"""
        conn   = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO scan_history
            (session_id, barcode, scan_result, scanned_at)
            VALUES (?, ?, ?, ?)
        ''', (
            self.session_id,
            barcode,
            result,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

    def get_scan_history(self):
        """Get all scans for current session"""
        conn   = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM scan_history
            WHERE session_id = ?
            ORDER BY scanned_at DESC
        ''', (self.session_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# =========================================================
# QUICK TEST
# =========================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   TESTING DATABASE MANAGER")
    print("=" * 55)

    db = DatabaseManager()

    # Test session
    sid = db.start_session("Test Customer")
    print(f"\n✅ Session ID: {sid}")

    # Test product lookup
    print("\n🔍 Testing product lookup...")
    test_barcodes = [
        "049000028911",   # Coca Cola
        "028400090179",   # Doritos
        "999999999999"    # Unknown product
    ]

    for bc in test_barcodes:
        product = db.get_product_by_barcode(bc)
        if product:
            print(f"   ✅ Found: {product['name']} - ${product['price']}")
        else:
            print(f"   ❌ Not found: {bc}")

    # Test add to cart
    print("\n🛒 Testing cart operations...")
    db.add_cart_item("049000028911", "Coca Cola 330ml", 1.50)
    db.add_cart_item("028400090179", "Doritos Nacho Cheese", 3.99)
    db.add_cart_item("049000028911", "Coca Cola 330ml", 1.50)

    items = db.get_cart_items()
    print(f"   Items in cart: {len(items)}")
    for item in items:
        print(f"   • {item['product_name']} x{item['quantity']} = ${item['total_price']}")

    # Test totals
    totals = db.get_cart_total()
    print(f"\n💰 Cart Totals:")
    print(f"   Subtotal : ${totals['subtotal']}")
    print(f"   Tax      : ${totals['tax']}")
    print(f"   Total    : ${totals['total']}")

    # Test remove
    db.remove_cart_item("049000028911")
    print(f"\n   After removing 1 Coca Cola:")
    items = db.get_cart_items()
    for item in items:
        print(f"   • {item['product_name']} x{item['quantity']}")

    print("\n" + "=" * 55)
    print("✅ DATABASE MANAGER TEST COMPLETE")
    print("=" * 55)
