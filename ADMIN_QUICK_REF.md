# Admin Panel - Quick Reference

## 🌐 Access
- **URL**: http://127.0.0.1:5000/admin
- **Or**: Homepage → "⚙️ Admin Panel" button

---

## ✨ Features

### View Data
- ✅ See all companies in a table
- ✅ See all schools in a table
- ✅ Real-time statistics

### Add Records
- ✅ Click "➕ Add Company" or "➕ Add School"
- ✅ Fill the form modal
- ✅ Auto-converts Eircode to coordinates
- ✅ Instant map updates

### Edit Records
- ✅ Click yellow "Edit" button
- ✅ Modify any field
- ✅ Save changes

### Delete Records
- ✅ Click red "Delete" button
- ✅ Confirm deletion
- ✅ Permanently removed

### Bulk Operations
- ✅ Re-import from Excel files
- ✅ Clear all data (with confirmation)

---

## 🎯 Common Tasks

### Add a Company
1. Click "➕ Add Company"
2. Enter company name (required)
3. Enter Eircode (auto-converts to GPS)
4. Fill other details
5. Click "Save"

### Update Contact Info
1. Find the record in table
2. Click "Edit"
3. Change email/phone
4. Click "Save"

### Import Excel Data
1. Put Excel file in `data/` folder
2. Click "🔄 Re-import from Excel"
3. Wait for completion

### Remove Old Records
1. Find the record
2. Click "Delete"
3. Confirm

---

## 💡 Pro Tips

- **Eircode Auto-Convert**: Just enter the Eircode, system handles coordinates
- **No Code Needed**: Everything is point-and-click
- **Instant Updates**: Changes appear immediately
- **Backup First**: Copy `data/companies.db` before bulk changes
- **Status Field**: Use "Inactive" instead of deleting

---

## ⚠️ Warnings

- Deletions are **permanent** (cannot undo)
- No authentication (anyone with access can edit)
- Clear All Data removes **everything**

---

**Full Guide**: See `ADMIN_GUIDE.md` for detailed documentation
