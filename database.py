import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/tekmetric.db")

# --------------------------------------------------
# Defines Users Table
#--------------------------------------------------


def create_users_table():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    """Return a connection to the local database."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    # WAL mode allows the dashboard to keep reading while a background
    # sync is writing, instead of hitting "database is locked" errors.
    connection.execute("PRAGMA journal_mode=WAL")

    return connection


def initialize_database():
    """Create all required database tables."""

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------
    # Employees
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            role_id INTEGER,
            role_name TEXT,
            updated_date TEXT,
            synced_at TEXT
        )
    """)

    # --------------------------------------------------
    # Repair Orders
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repair_orders (
            id INTEGER PRIMARY KEY,
            repair_order_number INTEGER,
            shop_id INTEGER,

            status_id INTEGER,
            status_code TEXT,
            status_name TEXT,

            label_code TEXT,
            label_name TEXT,

            appointment_start_time TEXT,

            customer_id INTEGER,
            vehicle_id INTEGER,

            technician_id INTEGER,
            service_writer_id INTEGER,

            miles_in INTEGER,
            miles_out INTEGER,

            completed_date TEXT,
            posted_date TEXT,
            created_date TEXT,
            updated_date TEXT,

            labor_sales INTEGER,
            parts_sales INTEGER,
            sublet_sales INTEGER,
            discount_total INTEGER,
            fee_total INTEGER,
            taxes INTEGER,
            total_sales INTEGER,

            synced_at TEXT
        )
    """)

    # --------------------------------------------------
    # Jobs
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,

            repair_order_id INTEGER,
            vehicle_id INTEGER,
            customer_id INTEGER,

            name TEXT,

            authorized INTEGER,
            authorized_date TEXT,
            selected INTEGER,

            technician_id INTEGER,

            note TEXT,
            job_category_name TEXT,

            parts_total INTEGER,
            labor_total INTEGER,
            discount_total INTEGER,
            fee_total INTEGER,
            subtotal INTEGER,

            archived INTEGER,

            created_date TEXT,
            updated_date TEXT,
            completed_date TEXT,

            labor_hours REAL,

            synced_at TEXT
        )
    """)

    # --------------------------------------------------
    # Labor Lines
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS labor_lines (
            id INTEGER PRIMARY KEY,

            job_id INTEGER,

            name TEXT,
            rate INTEGER,
            hours REAL,
            complete INTEGER,
            technician_id INTEGER,

            synced_at TEXT
        )
    """)

    # --------------------------------------------------
    # Parts
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY,

            job_id INTEGER,

            quantity REAL,
            brand TEXT,
            name TEXT,
            part_number TEXT,
            description TEXT,

            cost INTEGER,
            retail INTEGER,

            synced_at TEXT
        )
    """)

    connection.commit()
    connection.close()

    print("✓ Database initialized")