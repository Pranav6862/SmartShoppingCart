# ============================================================
# SmartShoppingCart/modules/smart_cart.py
# Smart Cart Logic - Add/Remove items, pricing, tax
# - Add items by barcode scan
# - Remove items with - button
# - Quantity management
# - Real time price calculation
# - Tax computation
# - Cart state management
# - Database integration
# - Cart history and session
# ============================================================

import logging
import time
from datetime import datetime
from collections import OrderedDict

from config import (
    TAX_RATE,
    CURRENCY_SYMBOL,
    MAX_CART_ITEMS,
)

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


# ============================================================
# CART ITEM CLASS
# ============================================================

class CartItem:
    """Represents a single item in the cart"""

    def __init__(self, barcode, name, price,
                 brand="", category="", unit="1 piece"):
        self.barcode      = barcode
        self.name         = name
        self.price        = price
        self.brand        = brand
        self.category     = category
        self.unit         = unit
        self.quantity     = 1
        self.added_at     = datetime.now()
        self.updated_at   = datetime.now()

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return round(self.price * self.quantity, 2)

    def increment(self):
        """Add one more of this item"""
        self.quantity   += 1
        self.updated_at  = datetime.now()

    def decrement(self):
        """Remove one of this item"""
        if self.quantity > 1:
            self.quantity  -= 1
            self.updated_at = datetime.now()
            return True
        return False

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "barcode"     : self.barcode,
            "name"        : self.name,
            "brand"       : self.brand,
            "category"    : self.category,
            "price"       : self.price,
            "quantity"    : self.quantity,
            "total_price" : self.total_price,
            "unit"        : self.unit,
            "added_at"    : self.added_at.strftime("%H:%M:%S"),
            "updated_at"  : self.updated_at.strftime("%H:%M:%S")
        }

    def __repr__(self):
        return (
            f"CartItem({self.name} x{self.quantity}"
            f" @ {CURRENCY_SYMBOL}{self.price}"
            f" = {CURRENCY_SYMBOL}{self.total_price})"
        )


# ============================================================
# SMART CART CLASS
# ============================================================

class SmartCart:
    """
    Smart Cart Module
    ─────────────────
    Manages all cart operations
    Add / Remove / Update items
    Real time price and tax calculation
    Full database integration
    Cart history and receipts
    """

    def __init__(self, customer_name="Customer"):
        # ── Database ──────────────────────────────────────────
        self.db              = DatabaseManager()
        self.session_id      = self.db.start_session(customer_name)

        # ── Cart Items ────────────────────────────────────────
        # OrderedDict keeps insertion order
        self.items           = OrderedDict()

        # ── Cart State ────────────────────────────────────────
        self.customer_name   = customer_name
        self.is_active       = True
        self.is_checkout     = False

        # ── Notification System ───────────────────────────────
        self.last_action     = None       # Last action taken
        self.last_action_time = 0         # When last action happened
        self.notifications   = []         # Notification queue
        self.notification_duration = 3.0  # Seconds to show notification

        # ── Cart History ──────────────────────────────────────
        self.action_history  = []         # All actions taken
        self.scan_count      = 0          # Total scans this session

        # ── Statistics ────────────────────────────────────────
        self.session_start   = datetime.now()
        self.items_added     = 0
        self.items_removed   = 0
        self.unknown_scans   = 0

        logger.info("SmartCart session %s started for %s", self.session_id, customer_name)

    # =========================================================
    # ADD ITEM
    # =========================================================

    def add_item_by_barcode(self, barcode):
        """
        Add item to cart using barcode
        Looks up product in database

        Args:
            barcode: scanned barcode string

        Returns:
            dict with result info
        """
        if not self.is_active:
            return self._result(False, "Cart is not active")

        if barcode not in self.items and len(self.items) >= MAX_CART_ITEMS:
            return self._result(False, f"Cart full ({MAX_CART_ITEMS} items max)")

        # ── Lookup Product ────────────────────────────────────
        product = self.db.get_product_by_barcode(barcode)

        if not product:
            self.unknown_scans += 1
            self.db.log_scan(barcode, "not_found")
            self._add_notification(
                f"Unknown barcode: {barcode}",
                "error"
            )
            return self._result(
                False,
                f"Product not found: {barcode}",
                barcode=barcode
            )

        # ── Add To Cart ───────────────────────────────────────
        result = self.add_item(
            barcode  = product["barcode"],
            name     = product["name"],
            price    = product["price"],
            brand    = product.get("brand", ""),
            category = product.get("category", ""),
            unit     = product.get("unit", "1 piece")
        )

        # ── Log Scan ──────────────────────────────────────────
        self.db.log_scan(barcode, "success")
        self.scan_count += 1

        return result

    def add_item(self, barcode, name, price,
                 brand="", category="", unit="1 piece"):
        """
        Add item directly to cart

        Args:
            barcode  : product barcode
            name     : product name
            price    : unit price
            brand    : brand name
            category : product category
            unit     : unit description

        Returns:
            dict with result info
        """
        if barcode in self.items:
            # ── Item exists - increment quantity ───────────────
            self.items[barcode].increment()
            qty    = self.items[barcode].quantity
            action = f"Updated: {name} (x{qty})"
            msg    = f"{name} quantity updated to {qty}"
        else:
            # ── New item - add to cart ─────────────────────────
            self.items[barcode] = CartItem(
                barcode  = barcode,
                name     = name,
                price    = price,
                brand    = brand,
                category = category,
                unit     = unit
            )
            action = f"Added: {name}"
            msg    = f"{name} added to cart"

        # ── Update Database ───────────────────────────────────
        self.db.add_cart_item(barcode, name, price)

        # ── Track Action ──────────────────────────────────────
        self.items_added += 1
        self._log_action("ADD", barcode, name, price)
        self._add_notification(msg, "success")
        self._set_last_action(action)

        logger.info("%s. Cart subtotal: %s%.2f", msg, CURRENCY_SYMBOL, self.get_subtotal())

        return self._result(
            True, msg,
            product = self.items[barcode].to_dict(),
            totals  = self.get_totals()
        )

    # =========================================================
    # REMOVE ITEM
    # =========================================================

    def remove_item(self, barcode, remove_all=False):
        """
        Remove one or all of an item from cart

        Args:
            barcode    : product barcode
            remove_all : if True removes all qty

        Returns:
            dict with result info
        """
        if barcode not in self.items:
            return self._result(False, "Item not in cart")

        item = self.items[barcode]
        name = item.name

        if remove_all or item.quantity <= 1:
            # ── Remove item completely ────────────────────────
            del self.items[barcode]
            self.db.remove_cart_item(barcode, 999)
            msg    = f"{name} removed from cart"
            action = f"Removed: {name}"
        else:
            # ── Decrement quantity ────────────────────────────
            item.decrement()
            qty = item.quantity
            self.db.remove_cart_item(barcode, 1)
            msg    = f"{name} quantity reduced to {qty}"
            action = f"Reduced: {name} (x{qty})"

        self.items_removed += 1
        self._log_action("REMOVE", barcode, name, 0)
        self._add_notification(msg, "warning")
        self._set_last_action(action)

        logger.info(msg)

        return self._result(
            True, msg,
            totals = self.get_totals()
        )

    def remove_item_by_index(self, index):
        """Remove item by its position in cart"""
        keys = list(self.items.keys())
        if 0 <= index < len(keys):
            return self.remove_item(keys[index])
        return self._result(False, "Invalid item index")

    def clear_cart(self):
        """Remove all items from cart"""
        count = len(self.items)
        self.items.clear()
        self.db.clear_cart()
        msg = f"Cart cleared ({count} items removed)"
        self._add_notification(msg, "warning")
        self._set_last_action("Cart Cleared")
        logger.info(msg)
        return self._result(True, msg)

    # =========================================================
    # QUANTITY MANAGEMENT (+ / - SYSTEM)
    # =========================================================

    def increment_item(self, barcode):
        """
        Increment item quantity ( + button )

        Args:
            barcode: product barcode

        Returns:
            dict with result
        """
        if barcode not in self.items:
            return self._result(False, "Item not in cart")

        item = self.items[barcode]
        item.increment()

        self.db.add_cart_item(barcode, item.name, item.price)
        msg = f"{item.name} x{item.quantity}"
        self._add_notification(msg, "success")
        self._set_last_action(msg)
        self._log_action("INCREMENT", barcode, item.name, item.price)

        logger.info(msg)
        return self._result(
            True, msg,
            product = item.to_dict(),
            totals  = self.get_totals()
        )

    def decrement_item(self, barcode):
        """
        Decrement item quantity ( - button )
        Removes item if quantity reaches 0

        Args:
            barcode: product barcode

        Returns:
            dict with result
        """
        if barcode not in self.items:
            return self._result(False, "Item not in cart")

        item = self.items[barcode]
        name = item.name

        if item.quantity <= 1:
            # Remove item completely
            return self.remove_item(barcode)
        else:
            item.decrement()
            self.db.remove_cart_item(barcode, 1)
            msg = f"{name} x{item.quantity}"
            self._add_notification(msg, "warning")
            self._set_last_action(msg)
            self._log_action(
                "DECREMENT", barcode, name, item.price
            )
            logger.info(msg)
            return self._result(
                True, msg,
                product = item.to_dict(),
                totals  = self.get_totals()
            )

    def set_item_quantity(self, barcode, quantity):
        """
        Set exact quantity for an item

        Args:
            barcode  : product barcode
            quantity : desired quantity (0 = remove)
        """
        if barcode not in self.items:
            return self._result(False, "Item not in cart")

        if quantity <= 0:
            return self.remove_item(barcode, remove_all=True)

        item          = self.items[barcode]
        old_qty       = item.quantity
        item.quantity = quantity
        item.updated_at = datetime.now()

        msg = f"{item.name} quantity set to {quantity}"
        self._log_action("SET_QTY", barcode, item.name, item.price)
        logger.info(msg)

        return self._result(
            True, msg,
            product = item.to_dict(),
            totals  = self.get_totals()
        )

    # =========================================================
    # PRICE CALCULATIONS
    # =========================================================

    def get_subtotal(self):
        """Calculate subtotal (before tax)"""
        return round(
            sum(item.total_price for item in self.items.values()),
            2
        )

    def get_tax(self):
        """Calculate tax amount"""
        return round(self.get_subtotal() * TAX_RATE, 2)

    def get_total(self):
        """Calculate grand total (with tax)"""
        return round(self.get_subtotal() + self.get_tax(), 2)

    def get_item_count(self):
        """Get total number of items (with quantities)"""
        return sum(item.quantity for item in self.items.values())

    def get_unique_item_count(self):
        """Get number of unique products"""
        return len(self.items)

    def get_totals(self):
        """Get all totals in one dict"""
        subtotal    = self.get_subtotal()
        tax         = self.get_tax()
        total       = self.get_total()
        item_count  = self.get_item_count()
        unique      = self.get_unique_item_count()

        return {
            "subtotal"     : subtotal,
            "tax"          : tax,
            "total"        : total,
            "item_count"   : item_count,
            "unique_items" : unique,
            "currency"     : CURRENCY_SYMBOL,
            "tax_rate"     : f"{int(TAX_RATE * 100)}%"
        }

    def get_savings(self):
        """Calculate total savings (future: discount system)"""
        return 0.00

    # =========================================================
    # CART DATA
    # =========================================================

    def get_items(self):
        """Get all cart items as list of dicts"""
        return [item.to_dict() for item in self.items.values()]

    def get_item(self, barcode):
        """Get specific item by barcode"""
        if barcode in self.items:
            return self.items[barcode].to_dict()
        return None

    def get_items_by_category(self):
        """Get items grouped by category"""
        categories = {}
        for item in self.items.values():
            cat = item.category or "Other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item.to_dict())
        return categories

    def has_item(self, barcode):
        """Check if item is in cart"""
        return barcode in self.items

    def is_empty(self):
        """Check if cart is empty"""
        return len(self.items) == 0

    # =========================================================
    # CHECKOUT
    # =========================================================

    def checkout(self):
        """
        Process checkout
        Saves session to database
        Generates receipt

        Returns:
            dict with receipt data
        """
        if self.is_empty():
            return self._result(False, "Cart is empty")

        if self.is_checkout:
            return self._result(False, "Already checked out")

        totals           = self.get_totals()
        self.is_checkout = True
        self.is_active   = False

        # ── Save to Database ──────────────────────────────────
        self.db.end_session(
            total_amount = totals["total"],
            tax_amount   = totals["tax"]
        )

        # ── Generate Receipt ──────────────────────────────────
        receipt = self._generate_receipt(totals)

        logger.info("Checkout complete for session %s", self.session_id)

        self._add_notification(
            f"Checkout complete. Total: {CURRENCY_SYMBOL}{totals['total']}",
            "success"
        )

        return self._result(
            True,
            "Checkout successful",
            receipt = receipt,
            totals  = totals
        )

    def _generate_receipt(self, totals):
        """Generate receipt text"""
        now   = datetime.now()
        lines = []

        lines.append("=" * 40)
        lines.append("      SMART SHOPPING CART")
        lines.append(f"  Session : {self.session_id}")
        lines.append(f"  Customer: {self.customer_name}")
        lines.append(f"  Date    : {now.strftime('%Y-%m-%d')}")
        lines.append(f"  Time    : {now.strftime('%H:%M:%S')}")
        lines.append("=" * 40)
        lines.append(f"{'ITEM':<22}{'QTY':>4}{'PRICE':>8}{'TOTAL':>8}")
        lines.append("-" * 40)

        for item in self.items.values():
            name  = item.name[:20]
            lines.append(
                f"{name:<22}"
                f"{item.quantity:>4}"
                f"{CURRENCY_SYMBOL}{item.price:>7.2f}"
                f"{CURRENCY_SYMBOL}{item.total_price:>7.2f}"
            )

        lines.append("-" * 40)
        lines.append(
            f"{'Subtotal':<30}"
            f"{CURRENCY_SYMBOL}{totals['subtotal']:>7.2f}"
        )
        lines.append(
            f"{'Tax (' + totals['tax_rate'] + ')':<30}"
            f"{CURRENCY_SYMBOL}{totals['tax']:>7.2f}"
        )
        lines.append("=" * 40)
        lines.append(
            f"{'TOTAL':<30}"
            f"{CURRENCY_SYMBOL}{totals['total']:>7.2f}"
        )
        lines.append("=" * 40)
        lines.append(f"  Items: {totals['item_count']}")
        lines.append(f"  Unique Products: {totals['unique_items']}")
        lines.append("=" * 40)
        lines.append("    Thank you for shopping!")
        lines.append("=" * 40)

        receipt_text = "\n".join(lines)

        return {
            "text"       : receipt_text,
            "lines"      : lines,
            "session_id" : self.session_id,
            "customer"   : self.customer_name,
            "items"      : self.get_items(),
            "totals"     : totals,
            "timestamp"  : now.strftime("%Y-%m-%d %H:%M:%S")
        }

    # =========================================================
    # NOTIFICATION SYSTEM
    # =========================================================

    def _add_notification(self, message, ntype="info"):
        """
        Add notification to queue

        Args:
            message : notification text
            ntype   : info / success / warning / error
        """
        notification = {
            "message"   : message,
            "type"      : ntype,
            "timestamp" : time.time(),
            "shown"     : False
        }
        self.notifications.append(notification)

        # Keep only last 5
        if len(self.notifications) > 5:
            self.notifications.pop(0)

    def get_active_notifications(self):
        """Get notifications that should still be displayed"""
        current_time = time.time()
        active = []

        for n in self.notifications:
            age = current_time - n["timestamp"]
            if age < self.notification_duration:
                active.append(n)

        return active

    def _set_last_action(self, action):
        """Set the last action taken"""
        self.last_action      = action
        self.last_action_time = time.time()

    def get_last_action(self):
        """Get last action if still recent"""
        if not self.last_action:
            return None

        age = time.time() - self.last_action_time
        if age < self.notification_duration:
            return self.last_action
        return None

    # =========================================================
    # ACTION HISTORY
    # =========================================================

    def _log_action(self, action_type, barcode, name, price):
        """Log cart action to history"""
        self.action_history.append({
            "type"      : action_type,
            "barcode"   : barcode,
            "name"      : name,
            "price"     : price,
            "timestamp" : datetime.now().strftime("%H:%M:%S"),
            "cart_total": self.get_total()
        })

    def get_action_history(self):
        """Get full action history"""
        return self.action_history

    def undo_last_action(self):
        """Undo the last cart action"""
        if not self.action_history:
            return self._result(False, "Nothing to undo")

        last = self.action_history[-1]
        action_type = last["type"]
        barcode     = last["barcode"]

        if action_type in ["ADD", "INCREMENT"]:
            result = self.decrement_item(barcode)
        elif action_type in ["REMOVE", "DECREMENT"]:
            result = self.add_item_by_barcode(barcode)
        else:
            return self._result(False, "Cannot undo this action")

        self.action_history.pop()
        self.action_history.pop()  # Remove the undo action too
        logger.info("Undid %s for %s", action_type, last["name"])
        return result

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_stats(self):
        """Get cart session statistics"""
        runtime = (datetime.now() - self.session_start).seconds

        return {
            "session_id"    : self.session_id,
            "customer"      : self.customer_name,
            "items_added"   : self.items_added,
            "items_removed" : self.items_removed,
            "unknown_scans" : self.unknown_scans,
            "scan_count"    : self.scan_count,
            "unique_items"  : self.get_unique_item_count(),
            "total_items"   : self.get_item_count(),
            "subtotal"      : self.get_subtotal(),
            "tax"           : self.get_tax(),
            "total"         : self.get_total(),
            "runtime_secs"  : runtime,
            "is_active"     : self.is_active,
            "is_checkout"   : self.is_checkout
        }

    # =========================================================
    # HELPER FUNCTIONS
    # =========================================================

    def _result(self, success, message,
                product=None, totals=None, receipt=None,
                barcode=None):
        """Build standard result dictionary"""
        return {
            "success" : success,
            "message" : message,
            "product" : product,
            "totals"  : totals or self.get_totals(),
            "receipt" : receipt,
            "barcode" : barcode,
            "time"    : datetime.now().strftime("%H:%M:%S")
        }

    def __len__(self):
        return self.get_item_count()

    def __contains__(self, barcode):
        return barcode in self.items

    def __repr__(self):
        return (
            f"SmartCart("
            f"{self.get_unique_item_count()} items, "
            f"Total: {CURRENCY_SYMBOL}{self.get_total()}"
            f")"
        )


# =========================================================
# QUICK TEST
# =========================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   SMART CART - MODULE TEST")
    print("=" * 55)

    cart = SmartCart(customer_name="Test Customer")

    # Test 1: Add by barcode
    print("\n🧪 Test 1: Add items by barcode")
    r1 = cart.add_item_by_barcode("049000028911")  # Coca Cola
    print(f"   Result  : {r1['message']}")

    r2 = cart.add_item_by_barcode("028400090179")  # Doritos
    print(f"   Result  : {r2['message']}")

    r3 = cart.add_item_by_barcode("038000596148")  # Corn Flakes
    print(f"   Result  : {r3['message']}")

    # Test 2: Duplicate scan
    print("\n🧪 Test 2: Duplicate scan (should increment)")
    r4 = cart.add_item_by_barcode("049000028911")
    print(f"   Result  : {r4['message']}")

    # Test 3: Unknown barcode
    print("\n�� Test 3: Unknown barcode")
    r5 = cart.add_item_by_barcode("999999999999")
    print(f"   Result  : {r5['message']}")

    # Test 4: Show cart items
    print("\n🧪 Test 4: Cart contents")
    for item in cart.get_items():
        print(
            f"   • {item['name']:<25}"
            f" x{item['quantity']}"
            f" @ ${item['price']}"
            f" = ${item['total_price']}"
        )

    # Test 5: Totals
    print("\n🧪 Test 5: Cart totals")
    totals = cart.get_totals()
    print(f"   Subtotal     : ${totals['subtotal']}")
    print(f"   Tax (8%)     : ${totals['tax']}")
    print(f"   Total        : ${totals['total']}")
    print(f"   Items        : {totals['item_count']}")
    print(f"   Unique       : {totals['unique_items']}")

    # Test 6: Increment / Decrement
    print("\n🧪 Test 6: + / - system")
    cart.increment_item("028400090179")
    print(f"   After +1 Doritos: {cart.get_item('028400090179')['quantity']}")
    cart.decrement_item("028400090179")
    print(f"   After -1 Doritos: {cart.get_item('028400090179')['quantity']}")

    # Test 7: Remove item
    print("\n🧪 Test 7: Remove item")
    cart.remove_item("038000596148")
    print(f"   Items after remove: {cart.get_unique_item_count()}")

    # Test 8: Undo
    print("\n🧪 Test 8: Undo last action")
    cart.undo_last_action()
    print(f"   Items after undo: {cart.get_unique_item_count()}")

    # Test 9: Categories
    print("\n🧪 Test 9: Items by category")
    by_cat = cart.get_items_by_category()
    for cat, items in by_cat.items():
        print(f"   {cat}: {len(items)} item(s)")

    # Test 10: Stats
    print("\n🧪 Test 10: Cart statistics")
    stats = cart.get_stats()
    for key, val in stats.items():
        print(f"   {key:<18} : {val}")

    # Test 11: Checkout
    print("\n🧪 Test 11: Checkout")
    result = cart.checkout()
    print(f"   Checkout: {result['message']}")

    print("\n" + "=" * 55)
    print("✅ SMART CART TEST COMPLETE")
    print("=" * 55)
