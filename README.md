# Elephant in the Room - Company & School Information System

A Flask-based web application for managing and visualizing company and school information with interactive maps.

## 🚀 Recent Updates: SQLite Database Integration

The system has been migrated from Excel-only storage to **SQLite database** for better data management, performance, and scalability.

### Key Features:
- ✅ **SQLite Database**: Automatic data persistence in `data/companies.db`
- ✅ **Excel Import**: Automatically imports data from Excel/CSV files on page load
- ✅ **Duplicate Handling**: Smart upsert logic prevents duplicate entries
- ✅ **Geocoding**: Automatic conversion of Eircodes to coordinates using Google Maps API
- ✅ **Interactive Maps**: Leaflet.js integration for visualizing company locations
- ✅ **Data Management**: Manual re-import functionality via admin interface

## 📋 Prerequisites

- Python 3.7+
- pip (Python package manager)

## 🛠️ Installation

1. **Clone the repository** (if applicable)
   ```bash
   cd "Elephant in the Room"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Google Maps API** (Optional but recommended)
   - Edit `config.py` and add your Google Maps API key
   - This enables accurate Eircode to address conversion

## 📁 Project Structure

```
Elephant in the Room/
├── data/
│   ├── companies.db          # SQLite database (auto-created)
│   ├── company.xlsx          # Company data source
│   └── school.xlsx           # School data source
├── templates/
│   ├── welcome.html          # Homepage with stats
│   ├── company.html          # Company info + map
│   └── school.html           # School information
├── static/
│   └── images/               # Static assets
├── main.py                   # Main Flask application
├── database.py               # Database initialization & helpers
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🗄️ Database Schema

### Companies Table
```sql
CREATE TABLE companies (
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
);
```

### Schools Table
```sql
CREATE TABLE schools (
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
);
```

## 🚦 Running the Application

1. **Start the Flask server**
   ```bash
   python main.py
   ```

2. **Access the application**
   - Homepage: http://127.0.0.1:5000/
   - Company Info: http://127.0.0.1:5000/company
   - School Info: http://127.0.0.1:5000/school

## 📊 How It Works

### Data Flow:
1. **Place Excel files** in the `data/` folder
2. **Visit any page** - the app automatically imports data into SQLite
3. **Eircode Conversion** - Backend converts Eircodes to addresses & coordinates
4. **Map Visualization** - Companies with valid coordinates appear on the map
5. **Database Persistence** - Data remains even if Excel files are removed

### Manual Re-import:
- Visit the homepage to see database statistics
- Click "Re-import Data from Excel Files" to refresh the database
- Useful when you update Excel files and want to sync changes

## 🔧 Configuration

### Google Maps API Setup (Recommended)

1. Get an API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Geocoding API**
3. Edit `config.py`:
   ```python
   GOOGLE_MAPS_API_KEY = "your_actual_api_key_here"
   ```

### Without Google Maps API:
- The system falls back to OpenStreetMap Nominatim
- Less accurate for Irish Eircodes
- May use routing key estimation as last resort

## 📝 Adding New Data

### Method 1: Excel Files (Recommended)
1. Place new `.xlsx` or `.csv` files in `data/` folder
2. Name company files without "school" in the name
3. Name school files with "school" in the name
4. Visit the website - automatic import occurs

### Method 2: Direct Database Access
You can also directly manipulate the SQLite database:
```python
import database

conn = database.get_db_connection()
cursor = conn.cursor()

# Insert a company
cursor.execute('''
    INSERT INTO companies (company_name, eircode, address)
    VALUES (?, ?, ?)
''', ('Company Name', 'A65 F4E2', 'Address'))

conn.commit()
conn.close()
```

## 🎨 Features

### Company Information Page (`/company`)
- Tabbed interface (Company Data / School Information)
- Interactive map showing company locations
- Searchable and sortable data table
- Real-time coordinate visualization

### School Information Page (`/school`)
- Complete school directory
- Contact information display
- Clean tabular format

### Homepage (`/`)
- Database statistics overview
- Quick navigation
- Manual re-import trigger

## 🔍 Troubleshooting

### Database not created?
- Ensure `data/` directory exists
- Check file permissions
- Run `python database.py` manually to initialize

### Eircodes not converting?
- Verify Google Maps API key is configured
- Check API quota and billing status
- Review console logs for error messages

### Map not displaying?
- Clear browser cache (Ctrl+Shift+R / Cmd+Shift+R)
- Check browser console for JavaScript errors
- Ensure companies have valid coordinates

## 📈 Future Enhancements

Potential improvements:
- [ ] User authentication system
- [ ] Advanced search and filtering
- [ ] Export data to Excel/CSV
- [ ] Bulk edit functionality
- [ ] API endpoints for external integrations
- [ ] Real-time collaboration features

## 📄 License

This project is for internal use.

## 👥 Support

For issues or questions, please contact the development team.

---

**Last Updated**: 2026-05-28  
**Version**: 2.0 (SQLite Migration)
