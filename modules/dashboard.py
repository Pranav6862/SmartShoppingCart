# ============================================================
# SmartShoppingCart/modules/dashboard.py
# Live Digital Dashboard
# - Real time item list
# - Live price and total updates
# - + / - buttons for each item
# - Notification display
# - Checkout button
# - OpenCV side panel dashboard
# - Session info display
# ============================================================

import cv2
import sys
import os
import time
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    DASHBOARD_TITLE,
    DASHBOARD_WIDTH,
    DASHBOARD_HEIGHT,
    DASHBOARD_BG_COLOR,
    CURRENCY_SYMBOL,
    TAX_RATE,
    CV_GREEN, CV_RED, CV_BLUE,
    CV_WHITE, CV_YELLOW,
    CV_ORANGE, CV_CYAN,
    CV_BLACK
)


# ============================================================
# COLOR PALETTE (BGR Format for OpenCV)
# ============================================================
class Colors:
    BG_DARK       = (20,  20,  35)     # Main background
    BG_PANEL      = (30,  30,  50)     # Panel background
    BG_ITEM       = (40,  40,  65)     # Item row background
    BG_ITEM_ALT   = (35,  35,  55)     # Alternate item row
    BG_HEADER     = (15,  15,  30)     # Header background
    BG_FOOTER     = (15,  15,  30)     # Footer background
    BG_BTN_ADD    = (0,   140, 0)      # + button green
    BG_BTN_REM    = (0,   0,   180)    # - button blue
    BG_BTN_DEL    = (0,   0,   160)    # delete button red
    BG_BTN_CHECK  = (0,   160, 0)      # checkout button
    BG_BTN_CLEAR  = (0,   0,   160)    # clear cart button
    ACCENT        = (90,  69,  233)    # Purple accent
    TEXT_PRIMARY  = (255, 255, 255)    # White text
    TEXT_SECONDARY= (180, 180, 180)    # Gray text
    TEXT_SUCCESS  = (0,   230, 118)    # Green text
    TEXT_WARNING  = (255, 193, 7)      # Yellow text
    TEXT_ERROR    = (100, 100, 255)    # Red text
    TEXT_PRICE    = (0,   230, 118)    # Price text green
    TEXT_TOTAL    = (255, 215, 0)      # Total text gold
    DIVIDER       = (60,  60,  90)     # Divider line
    HIGHLIGHT     = (60,  60,  100)    # Highlighted row


# ============================================================
# BUTTON CLASS
# ============================================================
class Button:
    """Represents a clickable button on the dashboard"""

    def __init__(self, x, y, w, h,
                 label, action, color,
                 text_color=None, data=None):
        self.x          = x
        self.y          = y
        self.w          = w
        self.h          = h
        self.label      = label
        self.action     = action
        self.color      = color
        self.text_color = text_color or Colors.TEXT_PRIMARY
        self.data       = data          # Extra data (barcode etc)
        self.hovered    = False
        self.pressed    = False
        self.visible    = True

    @property
    def rect(self):
        return (self.x, self.y,
                self.x + self.w,
                self.y + self.h)

    def contains(self, px, py):
        """Check if point is inside button"""
        return (self.x <= px <= self.x + self.w and
                self.y <= py <= self.y + self.h)

    def draw(self, canvas):
        """Draw button on canvas"""
        if not self.visible:
            return

        # ── Button Color (darker if hovered) ─────────────────
        color = self.color
        if self.hovered:
            color = tuple(min(255, c + 40) for c in color)
        if self.pressed:
            color = tuple(max(0, c - 40) for c in color)

        # ── Draw Button Background ────────────────────────────
        cv2.rectangle(canvas,
                      (self.x, self.y),
                      (self.x + self.w, self.y + self.h),
                      color, -1)

        # ── Draw Border ───────────────────────────────────────
        border_color = tuple(min(255, c + 60) for c in color)
        cv2.rectangle(canvas,
                      (self.x, self.y),
                      (self.x + self.w, self.y + self.h),
                      border_color, 1)

        # ── Draw Label ────────────────────────────────────────
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness  = 1

        text_size, _ = cv2.getTextSize(
            self.label, font, font_scale, thickness
        )
        tx = self.x + (self.w - text_size[0]) // 2
        ty = self.y + (self.h + text_size[1]) // 2

        cv2.putText(canvas, self.label,
                    (tx, ty), font,
                    font_scale,
                    self.text_color,
                    thickness)


# ============================================================
# MAIN DASHBOARD CLASS
# ============================================================

class Dashboard:
    """
    Live Digital Dashboard
    ──────────────────────
    Renders a full shopping cart dashboard
    as an OpenCV image panel
    Shows items, prices, totals
    Interactive + / - buttons
    Notifications and checkout
    """

    def __init__(self, width=DASHBOARD_WIDTH,
                 height=DASHBOARD_HEIGHT):
        # ── Dimensions ────────────────────────────────────────
        self.width        = width
        self.height       = height

        # ── Layout Zones ──────────────────────────────────────
        self.header_h     = 100          # Header height
        self.footer_h     = 180          # Footer height
        self.item_h       = 70           # Each item row height
        self.btn_w        = 28           # Button width
        self.btn_h        = 24           # Button height
        self.padding      = 10           # General padding

        # ── Canvas ────────────────────────────────────────────
        self.canvas       = None
        self._make_canvas()

        # ── Buttons List ──────────────────────────────────────
        self.buttons      = []

        # ── Scroll ────────────────────────────────────────────
        self.scroll_y     = 0
        self.max_visible  = (
            (self.height - self.header_h - self.footer_h)
            // self.item_h
        )

        # ── Interaction State ─────────────────────────────────
        self.mouse_pos    = (0, 0)
        self.last_click   = None
        self.click_callback = None       # External click handler

        # ── Animation ─────────────────────────────────────────
        self.pulse_phase  = 0.0
        self.frame_count  = 0

        # ── Session Info ──────────────────────────────────────
        self.session_id   = "------"
        self.customer_name= "Customer"
        self.start_time   = datetime.now()

        # ── Highlight ─────────────────────────────────────────
        self.highlighted_item = None
        self.highlight_time   = 0

        print(f"✅ Dashboard initialized")
        print(f"   Size : {width} x {height}")
        print(f"   Max visible items: {self.max_visible}")

    # =========================================================
    # CANVAS SETUP
    # =========================================================

    def _make_canvas(self):
        """Create blank dashboard canvas"""
        self.canvas = np.zeros(
            (self.height, self.width, 3),
            dtype=np.uint8
        )
        self.canvas[:] = Colors.BG_DARK

    def _clear_canvas(self):
        """Clear canvas for fresh draw"""
        self.canvas[:] = Colors.BG_DARK
        self.buttons   = []

    # =========================================================
    # MAIN RENDER FUNCTION
    # =========================================================

    def render(self, cart, scanner=None,
               tracker=None, extra_info=None):
        """
        Main render function - draws complete dashboard

        Args:
            cart       : SmartCart instance
            scanner    : BarcodeScanner instance (optional)
            tracker    : CustomerTracker instance (optional)
            extra_info : dict with extra data to show

        Returns:
            dashboard canvas (numpy array)
        """
        self._clear_canvas()
        self.frame_count  += 1
        self.pulse_phase   = (time.time() * 2) % (2 * np.pi)

        # ── Get Cart Data ─────────────────────────────────────
        items      = cart.get_items()
        totals     = cart.get_totals()
        notifs     = cart.get_active_notifications()
        last_action= cart.get_last_action()

        # ── Draw Sections ─────────────────────────────────────
        self._draw_header(cart, totals)
        self._draw_item_list(items, totals)
        self._draw_footer(totals, cart)
        self._draw_notifications(notifs)

        if scanner:
            self._draw_scanner_status(scanner)

        if tracker:
            self._draw_tracker_status(tracker)

        if last_action:
            self._draw_last_action(last_action)

        # ── Draw Decorative Elements ──────────────────────────
        self._draw_borders()

        return self.canvas.copy()

    # =========================================================
    # HEADER SECTION
    # =========================================================

    def _draw_header(self, cart, totals):
        """Draw dashboard header"""
        # ── Background ────────────────────────────────────────
        cv2.rectangle(self.canvas,
                      (0, 0),
                      (self.width, self.header_h),
                      Colors.BG_HEADER, -1)

        # ── Accent Line ───────────────────────────────────────
        cv2.rectangle(self.canvas,
                      (0, self.header_h - 2),
                      (self.width, self.header_h),
                      Colors.ACCENT, -1)

        # ── Cart Icon + Title ─────────────────────────────────
        cv2.putText(self.canvas,
                    "SMART SHOPPING CART",
                    (self.padding + 5, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, Colors.TEXT_PRIMARY, 2)

        # ── Session Info ──────────────────────────────────────
        cv2.putText(self.canvas,
                    f"Session: {cart.session_id}",
                    (self.padding + 5, 52),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, Colors.TEXT_SECONDARY, 1)

        cv2.putText(self.canvas,
                    f"Customer: {cart.customer_name}",
                    (self.padding + 5, 68),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, Colors.TEXT_SECONDARY, 1)

        # ── Live Time ─────────────────────────────────────────
        time_str = datetime.now().strftime("%H:%M:%S")
        cv2.putText(self.canvas,
                    time_str,
                    (self.width - 85, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, Colors.TEXT_WARNING, 2)

        date_str = datetime.now().strftime("%Y-%m-%d")
        cv2.putText(self.canvas,
                    date_str,
                    (self.width - 95, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, Colors.TEXT_SECONDARY, 1)

        # ── Item Count Badge ──────────────────────────────────
        count_text = f"{totals['item_count']} items"
        cv2.rectangle(self.canvas,
                      (self.padding + 5, 74),
                      (self.padding + 80, 94),
                      Colors.ACCENT, -1)

        cv2.putText(self.canvas,
                    count_text,
                    (self.padding + 10, 89),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, Colors.TEXT_PRIMARY, 1)

        # ── Column Headers ────────────────────────────────────
        y_col = self.header_h + 16
        cv2.rectangle(self.canvas,
                      (0, self.header_h),
                      (self.width, y_col + 6),
                      (25, 25, 45), -1)

        cols = [
            (8,   "PRODUCT"),
            (225, "QTY"),
            (268, "PRICE"),
            (330, "TOTAL"),
            (395, "+/-")
        ]

        for cx, label in cols:
            cv2.putText(self.canvas,
                        label,
                        (cx, y_col),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.38,
                        Colors.TEXT_SECONDARY,
                        1)

        # Divider under column headers
        cv2.line(self.canvas,
                 (0, self.header_h + 22),
                 (self.width, self.header_h + 22),
                 Colors.DIVIDER, 1)

    # =========================================================
    # ITEM LIST SECTION
    # =========================================================

    def _draw_item_list(self, items, totals):
        """Draw scrollable item list"""
        list_top  = self.header_h + 24
        list_bot  = self.height - self.footer_h
        list_h    = list_bot - list_top

        # ── Background ────────────────────────────────────────
        cv2.rectangle(self.canvas,
                      (0, list_top),
                      (self.width, list_bot),
                      Colors.BG_PANEL, -1)

        if not items:
            # ── Empty Cart Message ─────────────────────────────
            self._draw_empty_cart(list_top, list_bot)
            return

        # ── Draw Items ────────────────────────────────────────
        visible_items = items[
            self.scroll_y:
            self.scroll_y + self.max_visible
        ]

        for i, item in enumerate(visible_items):
            y_start = list_top + (i * self.item_h)
            y_end   = y_start + self.item_h

            if y_end > list_bot:
                break

            self._draw_item_row(item, i, y_start)

        # ── Draw Scroll Indicator ─────────────────────────────
        if len(items) > self.max_visible:
            self._draw_scroll_indicator(
                list_top, list_bot, len(items)
            )

    def _draw_item_row(self, item, index, y):
        """Draw a single item row"""
        is_even      = index % 2 == 0
        is_highlight = (item["barcode"] == self.highlighted_item and
                        time.time() - self.highlight_time < 1.5)

        # ── Row Background ────────────────────────────────────
        if is_highlight:
            bg = Colors.HIGHLIGHT
        elif is_even:
            bg = Colors.BG_ITEM
        else:
            bg = Colors.BG_ITEM_ALT

        cv2.rectangle(self.canvas,
                      (0, y),
                      (self.width, y + self.item_h),
                      bg, -1)

        # ── Product Name ──────────────────────────────────────
        name = item["name"]
        if len(name) > 18:
            name = name[:17] + "."

        cv2.putText(self.canvas, name,
                    (8, y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, Colors.TEXT_PRIMARY, 1)

        # ── Brand / Category ──────────────────────────────────
        sub = f"{item.get('brand','')}"
        if len(sub) > 16:
            sub = sub[:15]

        cv2.putText(self.canvas, sub,
                    (8, y + 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.33, Colors.TEXT_SECONDARY, 1)

        # ── Added Time ────────────────────────────────────────
        cv2.putText(self.canvas,
                    item.get("added_at", ""),
                    (8, y + 52),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3, Colors.TEXT_SECONDARY, 1)

        # ── Quantity Display ──────────────────────────────────
        qty_text = str(item["quantity"])
        cv2.putText(self.canvas, qty_text,
                    (232, y + 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, Colors.TEXT_WARNING, 2)

        # ── Unit Price ────────────────────────────────────────
        price_text = f"${item['price']:.2f}"
        cv2.putText(self.canvas, price_text,
                    (265, y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, Colors.TEXT_SECONDARY, 1)

        # ── Unit label ────────────────────────────────────────
        cv2.putText(self.canvas,
                    item.get("unit","")[:8],
                    (265, y + 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3, Colors.TEXT_SECONDARY, 1)

        # ── Total Price ───────────────────────────────────────
        total_text = f"${item['total_price']:.2f}"
        cv2.putText(self.canvas, total_text,
                    (328, y + 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48, Colors.TEXT_PRICE, 1)

        # ── + / - / X Buttons ─────────────────────────────────
        btn_y    = y + (self.item_h - self.btn_h) // 2
        barcode  = item["barcode"]

        # + Button
        btn_plus = Button(
            x      = 392,
            y      = btn_y,
            w      = self.btn_w,
            h      = self.btn_h,
            label  = "+",
            action = "INCREMENT",
            color  = Colors.BG_BTN_ADD,
            data   = barcode
        )
        btn_plus.draw(self.canvas)
        self.buttons.append(btn_plus)

        # - Button
        btn_minus = Button(
            x      = 424,
            y      = btn_y,
            w      = self.btn_w,
            h      = self.btn_h,
            label  = "-",
            action = "DECREMENT",
            color  = Colors.BG_BTN_REM,
            data   = barcode
        )
        btn_minus.draw(self.canvas)
        self.buttons.append(btn_minus)

        # X Button (remove all)
        btn_del = Button(
            x      = 456,
            y      = btn_y,
            w      = self.btn_w,
            h      = self.btn_h,
            label  = "X",
            action = "REMOVE",
            color  = Colors.BG_BTN_DEL,
            data   = barcode
        )
        btn_del.draw(self.canvas)
        self.buttons.append(btn_del)

        # ── Row Divider ───────────────────────────────────────
        cv2.line(self.canvas,
                 (0, y + self.item_h - 1),
                 (self.width - 1, y + self.item_h - 1),
                 Colors.DIVIDER, 1)

    def _draw_empty_cart(self, top, bot):
        """Draw empty cart message"""
        cy = (top + bot) // 2

        # Cart icon lines
        cv2.putText(self.canvas,
                    "[   ]",
                    (self.width // 2 - 30, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, Colors.DIVIDER, 2)

        cv2.putText(self.canvas,
                    "Cart is Empty",
                    (self.width // 2 - 70, cy + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, Colors.TEXT_SECONDARY, 1)

        cv2.putText(self.canvas,
                    "Scan a barcode to add items",
                    (self.width // 2 - 100, cy + 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, Colors.TEXT_SECONDARY, 1)

    def _draw_scroll_indicator(self, top, bot, total):
        """Draw scroll position indicator"""
        track_h   = bot - top
        thumb_h   = max(
            30,
            int(track_h * self.max_visible / total)
        )
        thumb_y   = top + int(
            track_h * self.scroll_y / total
        )

        # Track
        cv2.rectangle(self.canvas,
                      (self.width - 6, top),
                      (self.width - 2, bot),
                      Colors.DIVIDER, -1)

        # Thumb
        cv2.rectangle(self.canvas,
                      (self.width - 6, thumb_y),
                      (self.width - 2, thumb_y + thumb_h),
                      Colors.ACCENT, -1)

    # =========================================================
    # FOOTER SECTION
    # =========================================================

    def _draw_footer(self, totals, cart):
        """Draw footer with totals and buttons"""
        footer_y = self.height - self.footer_h

        # ── Background ────────────────────────────────────────
        cv2.rectangle(self.canvas,
                      (0, footer_y),
                      (self.width, self.height),
                      Colors.BG_FOOTER, -1)

        # ── Top Accent Line ───────────────────────────────────
        cv2.rectangle(self.canvas,
                      (0, footer_y),
                      (self.width, footer_y + 2),
                      Colors.ACCENT, -1)

        # ── Totals Section ────────────────────────────────────
        ty = footer_y + 22

        # Subtotal
        self._draw_total_row(
            ty, "Subtotal:",
            f"{CURRENCY_SYMBOL}{totals['subtotal']:.2f}",
            Colors.TEXT_SECONDARY
        )

        # Tax
        tax_label = f"Tax ({totals['tax_rate']}):"
        self._draw_total_row(
            ty + 22, tax_label,
            f"{CURRENCY_SYMBOL}{totals['tax']:.2f}",
            Colors.TEXT_SECONDARY
        )

        # Divider
        cv2.line(self.canvas,
                 (self.padding, ty + 42),
                 (self.width - self.padding, ty + 42),
                 Colors.DIVIDER, 1)

        # Grand Total (larger + animated pulse)
        pulse     = abs(np.sin(self.pulse_phase))
        intensity = int(200 + 55 * pulse)
        total_color = (0, intensity, intensity)

        cv2.putText(self.canvas,
                    "TOTAL:",
                    (self.padding, ty + 64),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65, Colors.TEXT_PRIMARY, 2)

        cv2.putText(self.canvas,
                    f"{CURRENCY_SYMBOL}{totals['total']:.2f}",
                    (self.width - 120, ty + 64),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, total_color, 2)

        # ── Action Buttons ────────────────────────────────────
        btn_y = footer_y + 100

        # Checkout Button
        btn_checkout = Button(
            x      = self.padding,
            y      = btn_y,
            w      = 200,
            h      = 38,
            label  = "CHECKOUT",
            action = "CHECKOUT",
            color  = Colors.BG_BTN_CHECK,
            data   = None
        )
        btn_checkout.draw(self.canvas)
        self.buttons.append(btn_checkout)

        # Clear Cart Button
        btn_clear = Button(
            x      = self.padding + 215,
            y      = btn_y,
            w      = 130,
            h      = 38,
            label  = "CLEAR CART",
            action = "CLEAR",
            color  = Colors.BG_BTN_CLEAR,
            data   = None
        )
        btn_clear.draw(self.canvas)
        self.buttons.append(btn_clear)

        # ── Items Summary ─────────────────────────────────────
        summary = (
            f"Products: {totals['unique_items']}  |  "
            f"Items: {totals['item_count']}"
        )
        cv2.putText(self.canvas, summary,
                    (self.padding, btn_y + 56),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, Colors.TEXT_SECONDARY, 1)

        # ── Scroll Help ───────────────────────────────────────
        cv2.putText(self.canvas,
                    "W/S = Scroll Up/Down",
                    (self.padding, btn_y + 72),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, Colors.TEXT_SECONDARY, 1)

    def _draw_total_row(self, y, label, value, color):
        """Draw a single total row"""
        cv2.putText(self.canvas, label,
                    (self.padding, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48, color, 1)

        cv2.putText(self.canvas, value,
                    (self.width - 90, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48, color, 1)

    # =========================================================
    # NOTIFICATION SECTION
    # =========================================================

    def _draw_notifications(self, notifications):
        """Draw active notifications"""
        if not notifications:
            return

        # Show most recent notification
        latest  = notifications[-1]
        msg     = latest["message"]
        ntype   = latest["type"]
        age     = time.time() - latest["timestamp"]
        alpha   = max(0.0, 1.0 - age / 3.0)

        # ── Color by Type ─────────────────────────────────────
        if ntype == "success":
            color = Colors.TEXT_SUCCESS
            bg    = (0, 60, 20)
        elif ntype == "warning":
            color = Colors.TEXT_WARNING
            bg    = (0, 40, 80)
        elif ntype == "error":
            color = Colors.TEXT_ERROR
            bg    = (0, 0, 80)
        else:
            color = Colors.TEXT_PRIMARY
            bg    = (40, 40, 60)

        # ── Notification Banner ───────────────────────────────
        notif_y = self.header_h + 2

        # Fade effect
        overlay = self.canvas.copy()
        cv2.rectangle(overlay,
                      (0, notif_y),
                      (self.width, notif_y + 26),
                      bg, -1)
        cv2.addWeighted(overlay, alpha,
                        self.canvas, 1 - alpha,
                        0, self.canvas)

        cv2.putText(self.canvas,
                    msg[:55],
                    (8, notif_y + 18),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, color, 1)

    # =========================================================
    # STATUS OVERLAYS
    # =========================================================

    def _draw_scanner_status(self, scanner):
        """Draw scanner status in header"""
        stats   = scanner.get_stats()
        ready   = stats["is_ready"]

        status  = "READY" if ready else f"WAIT {stats['cooldown_remaining']}s"
        color   = Colors.TEXT_SUCCESS if ready else Colors.TEXT_WARNING

        cv2.putText(self.canvas,
                    f"Scanner: {status}",
                    (self.width - 140, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, color, 1)

        cv2.putText(self.canvas,
                    f"Scans: {stats['total_scans']}",
                    (self.width - 140, 85),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, Colors.TEXT_SECONDARY, 1)

    def _draw_tracker_status(self, tracker):
        """Draw tracker status in header"""
        stats   = tracker.get_stats()
        locked  = stats["is_locked"]

        status  = f"ID:{stats['locked_id']}" if locked else "NONE"
        color   = Colors.TEXT_SUCCESS if locked else Colors.TEXT_ERROR

        cv2.putText(self.canvas,
                    f"Customer: {status}",
                    (self.width - 145, 95),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, color, 1)

    def _draw_last_action(self, action):
        """Draw last action taken"""
        cv2.putText(self.canvas,
                    f"Last: {action}",
                    (self.padding, self.height - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, Colors.TEXT_SECONDARY, 1)

    # =========================================================
    # DECORATIVE ELEMENTS
    # =========================================================

    def _draw_borders(self):
        """Draw outer border"""
        pulse  = abs(np.sin(self.pulse_phase))
        b_val  = int(100 + 50 * pulse)
        border = (b_val, 50, 150)

        cv2.rectangle(self.canvas,
                      (0, 0),
                      (self.width - 1, self.height - 1),
                      border, 2)

    # =========================================================
    # INTERACTION HANDLING
    # =========================================================

    def handle_click(self, x, y, cart):
        """
        Handle mouse click on dashboard

        Args:
            x, y : click coordinates
            cart : SmartCart instance

        Returns:
            dict with action result or None
        """
        self.mouse_pos = (x, y)

        for btn in self.buttons:
            if btn.contains(x, y):
                result = self._execute_button(btn, cart)
                if result:
                    return result

        return None

    def _execute_button(self, btn, cart):
        """Execute button action"""
        action  = btn.action
        barcode = btn.data

        if action == "INCREMENT" and barcode:
            self.highlight_item(barcode)
            return cart.increment_item(barcode)

        elif action == "DECREMENT" and barcode:
            self.highlight_item(barcode)
            return cart.decrement_item(barcode)

        elif action == "REMOVE" and barcode:
            return cart.remove_item(barcode, remove_all=True)

        elif action == "CHECKOUT":
            return cart.checkout()

        elif action == "CLEAR":
            return cart.clear_cart()

        return None

    def handle_scroll(self, direction, cart):
        """
        Handle scroll up / down

        Args:
            direction : 1 = down, -1 = up
            cart      : SmartCart instance
        """
        total     = cart.get_unique_item_count()
        max_scroll = max(0, total - self.max_visible)

        self.scroll_y = max(
            0,
            min(max_scroll, self.scroll_y + direction)
        )

    def handle_key(self, key, cart):
        """
        Handle keyboard input

        Args:
            key  : OpenCV key code
            cart : SmartCart instance

        Returns:
            action string or None
        """
        if key == ord('w') or key == ord('W'):
            self.handle_scroll(-1, cart)
        elif key == ord('s') or key == ord('S'):
            self.handle_scroll(1, cart)
        elif key == ord('c') or key == ord('C'):
            cart.clear_cart()
            return "CLEAR"
        elif key == 13:  # Enter key
            return "CHECKOUT"
        return None

    def highlight_item(self, barcode):
        """Highlight a specific item row briefly"""
        self.highlighted_item = barcode
        self.highlight_time   = time.time()

    def set_click_callback(self, callback):
        """Set external callback for button clicks"""
        self.click_callback = callback

    # =========================================================
    # SETUP MOUSE CALLBACK
    # =========================================================

    def setup_mouse(self, window_name, cart):
        """
        Setup OpenCV mouse callback

        Args:
            window_name : OpenCV window name
            cart        : SmartCart instance
        """
        def mouse_cb(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                result = self.handle_click(x, y, cart)
                if result and self.click_callback:
                    self.click_callback(result)

            elif event == cv2.EVENT_MOUSEMOVE:
                self.mouse_pos = (x, y)
                for btn in self.buttons:
                    btn.hovered = btn.contains(x, y)

        cv2.setMouseCallback(window_name, mouse_cb)
        print(f"✅ Dashboard mouse callback set")

    # =========================================================
    # DISPLAY
    # =========================================================

    def show(self, window_name=DASHBOARD_TITLE):
        """Show dashboard in OpenCV window"""
        cv2.imshow(window_name, self.canvas)

    def get_canvas(self):
        """Get current canvas"""
        return self.canvas.copy()

    def resize(self, w, h):
        """Resize dashboard"""
        self.width    = w
        self.height   = h
        self._make_canvas()
        self.max_visible = (
            (h - self.header_h - self.footer_h)
            // self.item_h
        )


# =========================================================
# QUICK TEST
# =========================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   DASHBOARD - MODULE TEST")
    print("=" * 55)

    # Import SmartCart for test
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    from modules.smart_cart import SmartCart
    from modules.barcode_scanner import BarcodeScanner

    # Create instances
    cart    = SmartCart("Test Customer")
    scanner = BarcodeScanner()
    dash    = Dashboard(width=500, height=700)

    # Add some items
    cart.add_item_by_barcode("049000028911")
    cart.add_item_by_barcode("028400090179")
    cart.add_item_by_barcode("038000596148")
    cart.add_item_by_barcode("049000028911")
    cart.add_item_by_barcode("070847811169")

    print("\n🧪 Test 1: Render dashboard")
    frame = dash.render(cart, scanner=scanner)
    print(f"   Canvas shape : {frame.shape}")
    print(f"   Buttons count: {len(dash.buttons)}")

    print("\n🧪 Test 2: Show dashboard window")
    window = "Dashboard Test"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 500, 700)

    dash.setup_mouse(window, cart)

    print("\n   Dashboard running...")
    print("   Press Q to quit")
    print("   Click + / - buttons to change quantities")
    print("   Press W/S to scroll")
    print("   Press CHECKOUT to checkout")

    while True:
        frame = dash.render(cart, scanner=scanner)
        cv2.imshow(window, frame)

        key = cv2.waitKey(30) & 0xFF

        if key == ord('q') or key == ord('Q'):
            break

        action = dash.handle_key(key, cart)
        if action == "CHECKOUT":
            print("   Checkout triggered!")
            break

    cv2.destroyAllWindows()

    print("\n🧪 Test 3: Final cart state")
    totals = cart.get_totals()
    print(f"   Items   : {totals['item_count']}")
    print(f"   Subtotal: ${totals['subtotal']}")
    print(f"   Tax     : ${totals['tax']}")
    print(f"   Total   : ${totals['total']}")

    print("\n" + "=" * 55)
    print("✅ DASHBOARD TEST COMPLETE")
    print("=" * 55)
