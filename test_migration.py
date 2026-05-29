"""
Quick test script to verify SQLite migration
Run this after starting the app to check if data was imported correctly
"""
import database
import os


def test_database():
    """Test database functionality"""
    print("\n🧪 Testing SQLite Database Migration\n")
    print("="*60)
    
    # Check if database file exists
    db_path = database.DATABASE_PATH
    if os.path.exists(db_path):
        print(f"✓ Database file exists: {db_path}")
    else:
        print(f"✗ Database file not found: {db_path}")
        return False
    
    # Test connection
    try:
        conn = database.get_db_connection()
        print("✓ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    # Check tables
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Check companies table
        cursor.execute('SELECT COUNT(*) FROM companies')
        company_count = cursor.fetchone()[0]
        print(f"✓ Companies table: {company_count} records")
        
        # Check schools table
        cursor.execute('SELECT COUNT(*) FROM schools')
        school_count = cursor.fetchone()[0]
        print(f"✓ Schools table: {school_count} records")
        
        # Check companies with coordinates
        cursor.execute('''
            SELECT COUNT(*) FROM companies 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ''')
        location_count = cursor.fetchone()[0]
        print(f"✓ Companies with coordinates: {location_count} records")
        
        conn.close()
        
        if company_count > 0:
            print("\n✅ Database migration successful!")
            print(f"\n📊 Summary:")
            print(f"   - Total Companies: {company_count}")
            print(f"   - Total Schools: {school_count}")
            print(f"   - Mapped Locations: {location_count}")
            return True
        else:
            print("\n⚠️  Database is empty. Visit /company or /school to import data.")
            return True
            
    except Exception as e:
        print(f"✗ Error querying database: {e}")
        return False


if __name__ == '__main__':
    success = test_database()
    exit(0 if success else 1)
