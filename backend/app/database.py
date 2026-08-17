import os, sqlite3, logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

DEFAULT_DB = os.path.join(DATA_DIR, "amh_lab.db")
DB_PATH = os.environ.get("AMH_DB_PATH", DEFAULT_DB)

logger = logging.getLogger("amh_db")

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'technician',
        is_active BOOLEAN NOT NULL DEFAULT 1,
        password_reset_required BOOLEAN NOT NULL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        token TEXT UNIQUE NOT NULL,
        expires_at DATETIME NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        section_id INTEGER NOT NULL REFERENCES sections(id),
        is_tracked BOOLEAN NOT NULL DEFAULT 0,
        parent_rollup_id INTEGER REFERENCES tests(id),
        is_active BOOLEAN NOT NULL DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        UNIQUE(name, section_id)
    );

    CREATE TABLE IF NOT EXISTS test_parameters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL REFERENCES tests(id),
        parameter_name TEXT NOT NULL,
        unit TEXT,
        ref_range TEXT,
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS daily_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date DATE NOT NULL,
        test_id INTEGER NOT NULL REFERENCES tests(id),
        done INTEGER NOT NULL DEFAULT 0,
        positive INTEGER,
        paper_register_tally INTEGER,
        entered_by_user_id INTEGER REFERENCES users(id),
        entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_by_user_id INTEGER REFERENCES users(id),
        updated_at DATETIME,
        UNIQUE(entry_date, test_id)
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        detail TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        date_of_birth DATE,
        sex TEXT,
        phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS test_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL REFERENCES clients(id),
        test_id INTEGER NOT NULL REFERENCES tests(id),
        sample_id TEXT,
        ordered_by_user_id INTEGER REFERENCES users(id),
        ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending'
    );

    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL REFERENCES test_orders(id),
        parameter_id INTEGER REFERENCES test_parameters(id),
        result_value TEXT,
        is_positive BOOLEAN,
        entered_by_user_id INTEGER REFERENCES users(id),
        entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        verified_by_user_id INTEGER REFERENCES users(id),
        verified_at DATETIME
    );
"""

def get_connection():
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    logger.debug(f"Connected to database at {DB_PATH}")
    return conn

def get_db():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
        logger.debug("Closed database connection")

def init_db():
    logger.info("Initializing database schema...")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL)
    
    # Safe Migrations for existing database columns
    migrations = [
        ("tests", "parent_rollup_id", "INTEGER REFERENCES tests(id)"),
        ("test_orders", "sample_id", "TEXT"),
        ("daily_entries", "paper_register_tally", "INTEGER"),
        ("test_results", "parameter_id", "INTEGER REFERENCES test_parameters(id)"),
        ("users", "password_reset_required", "BOOLEAN NOT NULL DEFAULT 0")
    ]
    for table, col, col_def in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            logger.info(f"Migration: Added column {col} to table {table}")
        except sqlite3.OperationalError:
            pass # Column already exists

    conn.commit()
    conn.close()
    logger.info("Database schema initialized and migrated successfully")

if __name__ == "__main__":
    init_db()
    print(f"Database schema created successfully at {DB_PATH}!")
