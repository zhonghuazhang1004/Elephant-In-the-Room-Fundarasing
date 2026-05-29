"""
Database utility script for viewing and managing data
Run this script to inspect the database contents
"""
import database
import sqlite3


def view_companies():
    """Display all companies in the database"""
    print("\n" + "="*80)
    print("COMPANIES DATABASE")
    print("="*80)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM companies')
    count = cursor.fetchone()[0]
    print(f"\nTotal Companies: {count}\n")
    
    if count > 0:
        cursor.execute('''
            SELECT id, company_name, eircode, address, 
                   latitude, longitude, status, created_at
            FROM companies
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        
        companies = cursor.fetchall()
        print(f"{'ID':<5} {'Company Name':<30} {'Eircode':<12} {'Status':<10} {'Created':<20}")
        print("-" * 80)
        
        for company in companies:
            print(f"{company[0]:<5} {company[1]:<30} {company[2]:<12} {company[6]:<10} {company[7]:<20}")
        
        if count > 20:
            print(f"\n... and {count - 20} more records")
    
    conn.close()


def view_schools():
    """Display all schools in the database"""
    print("\n" + "="*80)
    print("SCHOOLS DATABASE")
    print("="*80)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM schools')
    count = cursor.fetchone()[0]
    print(f"\nTotal Schools: {count}\n")
    
    if count > 0:
        cursor.execute('''
            SELECT id, school_name, address, email, phone, created_at
            FROM schools
            ORDER BY created_at DESC
            LIMIT 20
        ''')
        
        schools = cursor.fetchall()
        print(f"{'ID':<5} {'School Name':<40} {'Email':<30} {'Phone':<15}")
        print("-" * 80)
        
        for school in schools:
            print(f"{school[0]:<5} {school[1]:<40} {school[3]:<30} {school[4]:<15}")
        
        if count > 20:
            print(f"\n... and {count - 20} more records")
    
    conn.close()


def view_locations():
    """Display companies with valid coordinates"""
    print("\n" + "="*80)
    print("COMPANIES WITH LOCATIONS (For Map Display)")
    print("="*80)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM companies
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ''')
    count = cursor.fetchone()[0]
    print(f"\nCompanies with Coordinates: {count}\n")
    
    if count > 0:
        cursor.execute('''
            SELECT company_name, eircode, latitude, longitude, address
            FROM companies
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY created_at DESC
        ''')
        
        locations = cursor.fetchall()
        print(f"{'Company Name':<30} {'Eircode':<12} {'Latitude':<12} {'Longitude':<12}")
        print("-" * 80)
        
        for loc in locations:
            print(f"{loc[0]:<30} {loc[1]:<12} {loc[2]:<12} {loc[3]:<12}")
    
    conn.close()


def clear_database():
    """Clear all data from the database (with confirmation)"""
    confirm = input("\n⚠️  WARNING: This will delete ALL data. Type 'YES' to confirm: ")
    
    if confirm == 'YES':
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM companies')
        cursor.execute('DELETE FROM schools')
        
        conn.commit()
        conn.close()
        
        print("✓ Database cleared successfully")
    else:
        print("Operation cancelled")


def main():
    """Main menu"""
    while True:
        print("\n" + "="*80)
        print("DATABASE MANAGEMENT TOOL")
        print("="*80)
        print("1. View Companies")
        print("2. View Schools")
        print("3. View Locations (Map Data)")
        print("4. View All Statistics")
        print("5. Clear Database (Delete All Data)")
        print("6. Exit")
        print("="*80)
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            view_companies()
        elif choice == '2':
            view_schools()
        elif choice == '3':
            view_locations()
        elif choice == '4':
            view_companies()
            view_schools()
            view_locations()
        elif choice == '5':
            clear_database()
        elif choice == '6':
            print("\nGoodbye! 👋\n")
            break
        else:
            print("\n❌ Invalid choice. Please try again.")


if __name__ == '__main__':
    main()
