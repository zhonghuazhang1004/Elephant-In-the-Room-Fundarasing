# 🚀 Quick Start - SQLite Database Edition

## One-Click Start
```bash
python main.py
```
Visit: http://127.0.0.1:5000

---

## 📋 Common Commands

### Check Database Status
```bash
python test_migration.py
```

### Manage Database (Command-line Tool)
```bash
python db_utils.py
```

### Re-import Excel Data
Visit homepage → Click "Re-import Data" button

---

## 📁 File Locations

- **Database**: `data/companies.db`
- **Excel Source Files**: `data/*.xlsx`, `data/*.csv`
- **Configuration**: `config.py`

---

## 🔑 Key Improvements

✅ **Auto Import** - Automatically imports from Excel to database when visiting pages  
✅ **Smart Deduplication** - Same Eircode + company name won't be inserted twice  
✅ **Persistent Storage** - Data saved in database, independent of Excel files  
✅ **Fast Queries** - Database indexes accelerate data retrieval  
✅ **Easy Backup** - Just copy the .db file  

---

## 💡 Tips

1. **First Use**: Ensure Excel files exist in `data/` folder
2. **Update Data**: Click "Re-import" after replacing Excel files
3. **Google Maps**: Configure API Key for more accurate addresses
4. **Database Tools**: Recommended to install [DB Browser for SQLite](https://sqlitebrowser.org/)

---

**Questions?** Check `MIGRATION_GUIDE.md` for detailed documentation
