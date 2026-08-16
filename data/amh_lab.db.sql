BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        detail TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
CREATE TABLE IF NOT EXISTS daily_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date DATE NOT NULL,
        test_id INTEGER NOT NULL REFERENCES tests(id),
        done INTEGER NOT NULL DEFAULT 0,
        positive INTEGER,
        entered_by_user_id INTEGER REFERENCES users(id),
        entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_by_user_id INTEGER REFERENCES users(id),
        updated_at DATETIME, paper_register_tally INTEGER,
        UNIQUE(entry_date, test_id)
    );
CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        date_of_birth DATE,
        sex TEXT,
        phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        sort_order INTEGER DEFAULT 0
    );
CREATE TABLE IF NOT EXISTS test_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL REFERENCES patients(id),
        test_id INTEGER NOT NULL REFERENCES tests(id),
        ordered_by_user_id INTEGER REFERENCES users(id),
        ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending'
    , sample_id TEXT);
CREATE TABLE IF NOT EXISTS test_parameters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL REFERENCES tests(id),
        parameter_name TEXT NOT NULL,
        unit TEXT,
        ref_range TEXT,
        sort_order INTEGER DEFAULT 0
    );
CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL REFERENCES test_orders(id),
        result_value TEXT,
        is_positive BOOLEAN,
        entered_by_user_id INTEGER REFERENCES users(id),
        entered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        verified_by_user_id INTEGER REFERENCES users(id),
        verified_at DATETIME
    , parameter_id INTEGER REFERENCES test_parameters(id));
CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        section_id INTEGER NOT NULL REFERENCES sections(id),
        is_tracked BOOLEAN NOT NULL DEFAULT 0,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        sort_order INTEGER DEFAULT 0, parent_rollup_id INTEGER REFERENCES tests(id),
        UNIQUE(name, section_id)
    );
CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        token TEXT UNIQUE NOT NULL,
        expires_at DATETIME NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'technician',
        is_active BOOLEAN NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
COMMIT;
