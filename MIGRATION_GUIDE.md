# SQLite Database Migration Guide

## ✅ Migration Complete!

Your project has been successfully migrated from Excel-only storage to a **SQLite database** system.

---

## 📊 Current Status

- ✅ Database file created: `data/companies.db`
- ✅ Database tables initialized
- ✅ Existing Excel data imported
- ✅ Flask application running normally

### Data Statistics:
- **Company Records**: 2 entries
- **School Records**: 2 entries  
- **Companies with Coordinates**: 2 entries (displayable on map)

---

## 🚀 How to Use

### 1. Start the Application
```bash
python main.py
```

The application will run at `http://127.0.0.1:5000`

### 2. Access Pages
- **Homepage**: http://127.0.0.1:5000/ - View database statistics and manual import
- **Company Info**: http://127.0.0.1:5000/company - View company data and map
- **School Info**: http://127.0.0.1:5000/school - View school data

### 3. Add New Data

#### Method A: Excel Files (Recommended)
1. Place new `.xlsx` or `.csv` files in the `data/` folder
2. Company files: Do NOT include "school" in the filename
3. School files: Include "school" in the filename
4. Refresh the webpage - data will be automatically imported to the database

#### Method B: Manual Re-import
1. Visit homepage http://127.0.0.1:5000/
2. Click "🔄 Re-import Data from Excel Files" button
3. The system will re-read all Excel files and update the database

### 4. View Database Contents

Run the database management tool:
```bash
python db_utils.py
```

Features include:
- View all company records
- View all school records
- View companies with coordinates (for map display)
- Clear database (use with caution)

---

## 🗄️ Database Advantages

### Improvements over Excel:

| Feature | Excel | SQLite |
|---------|-------|--------|
| **Query Speed** | Slow (reads entire file each time) | Fast (indexed queries) |
| **Data Consistency** | Error-prone | ✅ Transaction guaranteed |
| **Concurrent Access** | ❌ Not supported | ✅ Supported |
| **Data Persistence** | Depends on file existence | ✅ Independent storage |
| **Duplicate Handling** | Manual | ✅ Automatic (UNIQUE constraint) |
| **Scalability** | Limited | ✅ Handles millions of records |

---

## 📁 Important Files

### Core Files:
- `database.py` - Database initialization and connection functions
- `main.py` - Main Flask application (database integrated)
- `data/companies.db` - SQLite database file

### Utility Scripts:
- `db_utils.py` - Database management tool (command-line)
- `test_migration.py` - Migration verification test script

### Data Sources:
- `data/company.xlsx` - Company data source (kept as backup)
- `data/school.xlsx` - School data source (kept as backup)

---

## 🔧 Frequently Asked Questions

### Q1: How to backup the database?
```bash
# Simply copy the database file
cp data/companies.db data/companies_backup.db
```

### Q2: How to reset the database?
```bash
# Delete the database file, it will be recreated on restart
rm data/companies.db
python main.py
```

### Q3: How to view raw SQL queries?
```python
import database

conn = database.get_db_connection()
cursor = conn.cursor()

# Execute any SQL query
cursor.execute('SELECT * FROM companies WHERE status = "active"')
results = cursor.fetchall()

for row in results:
    print(dict(row))

conn.close()
```

### Q4: Excel updated but website hasn't changed?
- Click the "Re-import Data" button on the homepage
- Or restart the Flask application (will auto-import)

### Q5: How to add more fields?
Edit the table structure in `database.py`, then run:
```python
import database
database.init_db()  # Won't delete existing data
```

---

## 🎯 Next Steps

1. **Configure Google Maps API** (Optional but recommended)
   - Edit `config.py`
   - Add your API Key
   - Get more accurate address conversion

2. **Regular Database Backups**
   ```bash
   cp data/companies.db backups/companies_$(date +%Y%m%d).db
   ```

3. **Explore Database Tools**
   - [DB Browser for SQLite](https://sqlitebrowser.org/) - GUI interface
   - Open `data/companies.db` directly to view and edit

4. **Consider Adding Features**
   - User authentication system
   - Data export to Excel/CSV
   - Advanced search and filtering
   - API endpoints

---

## 📞 Need Help?

If you encounter issues, check:
1. Error messages in Flask console output
2. JavaScript errors in browser console
3. Run `python test_migration.py` to verify database status

---

**Migration Date**: 2026-05-28  
**Version**: 2.0 - SQLite Edition 🎉
