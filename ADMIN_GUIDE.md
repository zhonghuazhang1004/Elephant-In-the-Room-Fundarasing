# Admin Panel User Guide

## 🎯 Overview

The Admin Panel provides a complete web-based interface for managing your database without writing any code. You can view, add, edit, and delete records directly from your browser.

---

## 🚀 Accessing the Admin Panel

### Method 1: From Homepage
1. Visit http://127.0.0.1:5000/
2. Click the **"⚙️ Admin Panel"** button (green button)

### Method 2: Direct URL
Visit: http://127.0.0.1:5000/admin

---

## 📊 Dashboard Features

### 1. Statistics Overview
At the top of the page, you'll see three cards showing:
- **Total Companies**: Number of company records
- **Total Schools**: Number of school records
- **Mapped Locations**: Companies with valid GPS coordinates

### 2. Quick Actions
Four action buttons for common tasks:

#### 🔄 Re-import from Excel
- Reads all Excel/CSV files from `data/` folder
- Updates database with latest data
- Prevents duplicates automatically
- **Use when**: You've updated Excel files and want to sync changes

#### ➕ Add Company
- Opens a form to add a new company
- Automatically converts Eircode to coordinates
- **Fields**:
  - Company Name (required)
  - Eircode
  - Address
  - Preferred School
  - Preferred Area
  - Contact Name
  - Contact Email
  - Status (Pending/Active/Inactive)

#### ➕ Add School
- Opens a form to add a new school
- **Fields**:
  - School Name (required)
  - Address
  - Email
  - Phone
  - Contact Info
  - Status (Active/Inactive)

#### ⚠️ Clear All Data
- **WARNING**: Deletes ALL records from both tables
- Requires double confirmation
- **Use with caution!**

---

## 📝 Managing Records

### Viewing Data

The admin panel has two tabs:

#### Companies Tab
Shows a table with:
- ID, Company Name, Eircode, Address
- Contact Name, Contact Email, Status
- Action buttons (Edit/Delete)

#### Schools Tab
Shows a table with:
- ID, School Name, Address
- Email, Phone, Status
- Action buttons (Edit/Delete)

### Editing a Record

1. Find the record in the table
2. Click the **"Edit"** button (yellow)
3. A modal window opens with pre-filled data
4. Make your changes
5. Click **"Save"**
6. The page refreshes with updated data

### Deleting a Record

1. Find the record in the table
2. Click the **"Delete"** button (red)
3. Confirm the deletion in the popup
4. The record is permanently removed

---

## 💡 Use Cases

### Scenario 1: Adding a New Company Manually
**Problem**: You have company details but no Excel file yet.

**Solution**:
1. Go to Admin Panel
2. Click "➕ Add Company"
3. Fill in the form
4. Enter the Eircode (system will auto-convert to coordinates)
5. Click "Save"
6. Done! The company appears on the map immediately.

### Scenario 2: Updating Contact Information
**Problem**: A company changed their email address.

**Solution**:
1. Go to Admin Panel → Companies tab
2. Find the company
3. Click "Edit"
4. Update the email field
5. Click "Save"

### Scenario 3: Removing Inactive Companies
**Problem**: Some companies are no longer relevant.

**Solution**:
1. Go to Admin Panel → Companies tab
2. Find inactive companies
3. Click "Delete" for each one
4. Confirm deletion

### Scenario 4: Bulk Import from Excel
**Problem**: You received a new Excel file with 50 companies.

**Solution**:
1. Place the Excel file in `data/` folder
2. Go to Admin Panel
3. Click "🔄 Re-import from Excel"
4. Wait for import to complete
5. All 50 companies are now in the database!

---

## 🔧 Advanced Tips

### Automatic Geocoding
When you enter an Eircode:
- The system automatically converts it to latitude/longitude
- Uses Google Maps API (if configured) or OpenStreetMap
- The company appears on the map instantly
- No manual coordinate entry needed!

### Status Management
Use the Status field to organize records:
- **Companies**: Pending / Active / Inactive
- **Schools**: Active / Inactive
- Filter by status in your queries

### Data Validation
The system enforces:
- Required fields (Company Name, School Name)
- Valid email format
- Unique constraints prevent duplicates
- Timestamps track creation/modification dates

---

## ⚠️ Important Notes

### Backup Your Data
Before making bulk changes:
```bash
cp data/companies.db data/companies_backup_$(date +%Y%m%d).db
```

### Cannot Undo Deletions
- Deleted records are permanently removed
- Always double-check before deleting
- Consider changing status to "Inactive" instead of deleting

### Excel Import Behavior
- Import is **additive** (adds new records)
- Existing records are **updated** if Eircode + Company Name match
- Original Excel files are NOT modified
- Keep Excel files as backup sources

---

## 🎨 UI Features

### Responsive Design
- Works on desktop, tablet, and mobile
- Tables scroll horizontally on small screens
- Modal forms adapt to screen size

### Visual Feedback
- Success messages (green): Operations completed
- Error messages (red): Something went wrong
- Hover effects on buttons and rows
- Color-coded action buttons

### Keyboard Shortcuts
- **ESC**: Close modal windows
- **Tab**: Navigate form fields
- **Enter**: Submit forms

---

## 📞 Troubleshooting

### Problem: Changes don't appear
**Solution**: Refresh the page (F5 or Ctrl+R)

### Problem: Can't save a record
**Solution**: 
- Check that required fields are filled
- Verify email format is correct
- Look for error message at the top

### Problem: Eircode not converting to coordinates
**Solution**:
- Verify Eircode format (e.g., "A65 F4E2")
- Check if Google Maps API is configured in `config.py`
- System will use fallback method if API unavailable

### Problem: Import not working
**Solution**:
- Ensure Excel files are in `data/` folder
- Check file format (.xlsx, .xls, or .csv)
- Verify column names match expected format
- Check Flask console for error messages

---

## 🔐 Security Note

Currently, the admin panel has **no authentication**. Anyone who can access your server can modify data.

**For production use**, consider adding:
- Username/password login
- Role-based access control
- HTTPS encryption
- IP whitelisting

---

## 📈 Future Enhancements

Potential improvements:
- [ ] Search and filter functionality
- [ ] Export data to Excel/CSV
- [ ] Bulk edit operations
- [ ] Data validation rules
- [ ] Audit log (track changes)
- [ ] User authentication
- [ ] API endpoints for external tools

---

**Last Updated**: 2026-05-28  
**Version**: 2.1 - Admin Panel Edition 🎉
