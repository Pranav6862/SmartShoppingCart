# ============================================================
# SmartShoppingCart/database/db_setup.py
# Creates and populates the product database
# ============================================================

import sqlite3
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH

def create_database():
    """Create all tables in the database"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("📦 Creating database tables...")

    # ── Products Table ────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode       TEXT    UNIQUE NOT NULL,
            name          TEXT    NOT NULL,
            brand         TEXT,
            category      TEXT,
            price         REAL    NOT NULL,
            unit          TEXT    DEFAULT "1 piece",
            stock         INTEGER DEFAULT 100,
            image_path    TEXT    DEFAULT "",
            description   TEXT    DEFAULT "",
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ products table created")

    # ── Cart Sessions Table ───────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT    UNIQUE NOT NULL,
            customer_name TEXT    DEFAULT "Customer",
            started_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at      TIMESTAMP,
            total_amount  REAL    DEFAULT 0.0,
            tax_amount    REAL    DEFAULT 0.0,
            status        TEXT    DEFAULT "active"
        )
    ''')
    print("   ✅ cart_sessions table created")

    # ── Cart Items Table ──────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT    NOT NULL,
            barcode       TEXT    NOT NULL,
            product_name  TEXT    NOT NULL,
            quantity      INTEGER DEFAULT 1,
            unit_price    REAL    NOT NULL,
            total_price   REAL    NOT NULL,
            added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES cart_sessions(session_id)
        )
    ''')
    print("   ✅ cart_items table created")

    # ── Scan History Table ────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT,
            barcode       TEXT    NOT NULL,
            scan_result   TEXT    DEFAULT "success",
            scanned_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ scan_history table created")

    conn.commit()
    conn.close()
    print("\n✅ All tables created successfully!")


def populate_sample_products():
    """Insert sample products with real barcodes"""

    # ── Sample Product Data ───────────────────────────────────
    sample_products = [

        # ── Beverages ─────────────────────────────────────────
        ("049000028911", "Coca Cola 330ml",        "Coca Cola",  "Beverages",    1.50, "1 can"    ),
        ("049000006582", "Pepsi 330ml",             "Pepsi",      "Beverages",    1.50, "1 can"    ),
        ("012000001086", "Mountain Dew 330ml",      "Mountain Dew","Beverages",   1.50, "1 can"    ),
        ("078000053401", "Red Bull Energy Drink",   "Red Bull",   "Beverages",    2.99, "1 can"    ),
        ("070847811169", "Tropicana Orange Juice",  "Tropicana",  "Beverages",    3.49, "1 bottle" ),
        ("041130306129", "Minute Maid Lemonade",    "Minute Maid","Beverages",    2.99, "1 bottle" ),

        # ── Snacks ────────────────────────────────────────────
        ("8901058904741", "Kitkat",                 "Nestle",     "Snacks",       25.00, "1 piece" ),
        ("0010200000182", "Kitkat Variant",         "Nestle",     "Snacks",       25.00, "1 piece" ),
        ("8901058024401", "Kitkat Mini",                 "Nestle",     "Snacks",      10.00, "1 piece" ),
        ("7622202818400", "5 Star",                 "Cadbury",    "Snacks",       10.00, "1 piece" ),
        ("7622202852541", "Oreo",                   "Oreo",       "Snacks",       30.00, "1 pack"  ),
        ("7622202225512", "Oreo Mini",              "Oreo",       "Snacks",       10.00, "1 pack"  ),
        ("028400090179", "Doritos Nacho Cheese",    "Doritos",    "Snacks",       3.99, "1 pack"   ),
        ("028400315142", "Lays Classic Chips",      "Lays",       "Snacks",       3.49, "1 pack"   ),
        ("030100301023", "Pringles Original",        "Pringles",   "Snacks",       2.49, "1 can"    ),
        ("041570037607", "Oreo Cookies",             "Oreo",       "Snacks",       4.29, "1 pack"   ),
        ("044000031756", "Chips Ahoy Cookies",       "Chips Ahoy", "Snacks",       4.49, "1 pack"   ),
        ("016000275287", "Cheez-It Crackers",        "Cheez-It",   "Snacks",       4.99, "1 box"    ),

        # ── Dairy ─────────────────────────────────────────────
        ("070470003030", "Great Value Whole Milk",  "Great Value","Dairy",        3.78, "1 gallon" ),
        ("021000011988", "Philadelphia Cream Cheese","Philadelphia","Dairy",       3.99, "1 pack"   ),
        ("077567331328", "Kraft American Cheese",    "Kraft",      "Dairy",        4.49, "1 pack"   ),
        ("041270001311", "Greek Yogurt Plain",       "Chobani",    "Dairy",        1.29, "1 cup"    ),

        # ── Bread & Bakery ─────────────────────────────────────
        ("072250901947", "Wonder Bread White",       "Wonder",     "Bakery",       3.49, "1 loaf"   ),
        ("073410007670", "Thomas English Muffins",   "Thomas",     "Bakery",       4.29, "1 pack"   ),

        # ── Breakfast ─────────────────────────────────────────
        ("038000596148", "Kelloggs Corn Flakes",     "Kelloggs",   "Breakfast",    3.99, "1 box"    ),
        ("016000124691", "Cheerios Original",         "General Mills","Breakfast",  4.49, "1 box"    ),
        ("043000200414", "Quaker Oats",               "Quaker",     "Breakfast",    4.99, "1 box"    ),
        ("038000845543", "Kelloggs Frosted Flakes",   "Kelloggs",   "Breakfast",    3.99, "1 box"    ),

        # ── Household ─────────────────────────────────────────
        ("037000753209", "Tide Detergent",            "Tide",       "Household",    11.97,"1 bottle" ),
        ("044600302059", "Bounty Paper Towels",        "Bounty",     "Household",    5.99, "1 roll"   ),
        ("030772008010", "Colgate Toothpaste",         "Colgate",    "Personal Care",2.99, "1 tube"   ),
        ("037000849048", "Head & Shoulders Shampoo",   "Head&Shoulders","Personal Care",6.99,"1 bottle"),

        # ── Frozen Foods ──────────────────────────────────────
        ("013800152015", "DiGiorno Frozen Pizza",      "DiGiorno",   "Frozen",       7.99, "1 pizza"  ),
        ("021130123872", "Birds Eye Frozen Vegetables","Birds Eye",  "Frozen",       2.49, "1 bag"    ),

        # ── Canned Goods ──────────────────────────────────────
        ("064144291450", "Campbell Tomato Soup",       "Campbell",   "Canned Goods", 1.49, "1 can"    ),
        ("041196000052", "Heinz Baked Beans",           "Heinz",      "Canned Goods", 1.99, "1 can"    ),
    ]

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("\n📦 Inserting sample products...")

    inserted = 0
    skipped  = 0

    for product in sample_products:
        try:
            cursor.execute('''
                INSERT INTO products 
                (barcode, name, brand, category, price, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', product)
            inserted += 1
            print(f"   ✅ Added: {product[1]} - ${product[4]}")
        except sqlite3.IntegrityError:
            skipped += 1
            print(f"   ⚠️  Skipped (exists): {product[1]}")

    conn.commit()
    conn.close()

    print(f"\n📊 Summary:")
    print(f"   Total Products : {len(sample_products)}")
    print(f"   Inserted       : {inserted}")
    print(f"   Skipped        : {skipped}")
    print(f"\n✅ Products database ready!")


def verify_database():
    """Verify database was created correctly"""

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("\n🔍 Verifying database...")

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n   Tables found: {[t[0] for t in tables]}")

    # Count products
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    print(f"   Total products: {count}")

    # Show categories
    cursor.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
    categories = cursor.fetchall()
    print(f"\n   Products by category:")
    for cat in categories:
        print(f"      {cat[0]:<20} : {cat[1]} items")

    conn.close()
    print("\n✅ Database verification complete!")


if __name__ == "__main__":
    print("=" * 55)
    print("   SMART CART - DATABASE SETUP")
    print("=" * 55)

    # Create database directory if missing
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    create_database()
    populate_sample_products()
    verify_database()

    print("\n" + "=" * 55)
    print("✅ DATABASE SETUP COMPLETE - Ready for STEP 3")
    print("=" * 55)
