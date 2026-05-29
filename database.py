"""
Database configuration and initialization for SQLite
"""
import sqlite3
import os

# Database file path
DATABASE_PATH = os.path.join('data', 'companies.db')


def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_db():
    """Initialize the database with required tables"""
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
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
            school_name TEXT NOT NULL,
            address TEXT,
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
