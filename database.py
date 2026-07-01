"""
Database configuration and initialization for SQLite
Supports both local development and PythonAnywhere deployment via environment variables
"""
import sqlite3
import os

# Database file path - Support environment variable for PythonAnywhere deployment
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join('data', 'companies.db'))


def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def migrate_database():
    """Migrate database to add new columns if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if donation_amount column exists in companies table
        cursor.execute("PRAGMA table_info(companies)")
        company_columns = [row[1] for row in cursor.fetchall()]
        
        if 'donation_amount' not in company_columns:
            print("Adding donation_amount column to companies table...")
            cursor.execute('ALTER TABLE companies ADD COLUMN donation_amount REAL DEFAULT 0')
            print("✓ Added donation_amount column")
        
        # Check if donation_received column exists in schools table
        cursor.execute("PRAGMA table_info(schools)")
        school_columns = [row[1] for row in cursor.fetchall()]
        
        if 'donation_received' not in school_columns:
            print("Adding donation_received column to schools table...")
            cursor.execute('ALTER TABLE schools ADD COLUMN donation_received REAL DEFAULT 0')
            print("✓ Added donation_received column")
        
        conn.commit()
        print("✓ Database migration completed successfully")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables"""
    # Ensure data directory exists
    data_dir = os.path.dirname(DATABASE_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create companies table - matching Excel columns exactly
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            county TEXT,
            description TEXT,
            address TEXT,
            eircode TEXT,
            website TEXT,
            phone_number TEXT,
            linkedin TEXT,
            additional_links TEXT,
            notes TEXT,
            socials TEXT,
            latitude REAL,
            longitude REAL,
            preferred_school TEXT,
            preferred_area TEXT,
            contact_name TEXT,
            contact_email TEXT,
            status TEXT DEFAULT 'pending',
            donation_amount REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(eircode, company_name)
        )
    ''')
    
    # Create schools table - matching Excel columns exactly
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            internal_id TEXT,
            roll_number TEXT UNIQUE,
            school_name TEXT NOT NULL,
            county TEXT,
            address TEXT,
            eircode TEXT,
            school_type TEXT,
            email TEXT,
            phone TEXT,
            contact_name TEXT,
            contact_info TEXT,
            latitude REAL,
            longitude REAL,
            deis TEXT,
            school_level TEXT,
            enrolment INTEGER,
            status TEXT DEFAULT 'active',
            donation_received REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migrate existing tables that may be missing new columns
    for col, definition in [
        ('county', 'TEXT'),
        ('description', 'TEXT'),
        ('website', 'TEXT'),
        ('phone_number', 'TEXT'),
        ('linkedin', 'TEXT'),
        ('additional_links', 'TEXT'),
        ('notes', 'TEXT'),
        ('socials', 'TEXT'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE companies ADD COLUMN {col} {definition}')
        except Exception:
            pass  # column already exists
    
    for col, definition in [
        ('internal_id', 'TEXT'),
        ('roll_number', 'TEXT'),
        ('county', 'TEXT'),
        ('email', 'TEXT'),
        ('phone', 'TEXT'),
        ('contact_name', 'TEXT'),
        ('contact_info', 'TEXT'),
        ('deis', 'TEXT'),
        ('school_level', 'TEXT'),
        ('enrolment', 'INTEGER'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE schools ADD COLUMN {col} {definition}')
        except Exception:
            pass  # column already exists
    
    # Create team_files table for document management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    ''')
    
    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company_eircode ON companies(eircode)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_school_name ON schools(school_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_team_member ON team_files(member_name)')
    # roll_number was added via ALTER TABLE on existing databases (see above), so it
    # lacks the UNIQUE constraint declared in the CREATE TABLE statement above. A unique
    # index is required for the school import's ON CONFLICT(roll_number) upsert to work.
    # Must NOT be a partial (WHERE-qualified) index: SQLite requires ON CONFLICT's target
    # to repeat a partial index's WHERE clause verbatim, which main.py's INSERT doesn't do.
    # A plain unique index works fine since SQLite allows unlimited NULLs in it, and the
    # import code only ever passes a non-empty roll_number or None (never '').
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_school_roll_number ON schools(roll_number)')
    
    conn.commit()
    conn.close()
    
    print("✓ Database initialized successfully")


if __name__ == '__main__':
    init_db()
    migrate_database()
    print(f"Database created at: {DATABASE_PATH}")
