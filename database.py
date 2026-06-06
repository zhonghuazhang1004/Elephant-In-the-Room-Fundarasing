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


def init_db():
    """Initialize the database with required tables"""
    # Ensure data directory exists
    data_dir = os.path.dirname(DATABASE_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create companies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            eircode TEXT,
            address TEXT,
            latitude REAL,
            longitude REAL,
            preferred_school TEXT,
            preferred_area TEXT,
            contact_name TEXT,
            contact_email TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(eircode, company_name)
        )
    ''')
    
    # Create schools table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE,
            school_name TEXT NOT NULL,
            eircode TEXT,
            address TEXT,
            county TEXT,
            latitude REAL,
            longitude REAL,
            contact_info TEXT,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migrate existing tables that may be missing new columns
    for col, definition in [
        ('roll_number', 'TEXT'),
        ('eircode', 'TEXT'),
        ('county', 'TEXT'),
        ('latitude', 'REAL'),
        ('longitude', 'REAL'),
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
    
    conn.commit()
    conn.close()
    
    print("✓ Database initialized successfully")


if __name__ == '__main__':
    init_db()
    print(f"Database created at: {DATABASE_PATH}")
