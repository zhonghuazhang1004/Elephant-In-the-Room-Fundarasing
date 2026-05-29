# Team Files Management Guide

## Overview
The Team Files page allows your 5 team members to upload, manage, and share documents (PDF, DOC, XLS, etc.) through a web interface.

## Access
- **URL**: http://127.0.0.1:5000/team-files
- **Navigation**: Access via the Admin Panel sidebar (left side)

## Navigation Structure

### Admin Panel Sidebar
The Admin Panel now features a **left sidebar** with quick navigation to all admin functions:

- 📊 **Dashboard** - Overview and statistics
- 🏢 **Companies** - Manage company data
- 🎓 **Schools** - Manage school data  
- 📁 **Team Files** - Document management (this page)
- ⚠️ **Clear Data** - Clear all database records

The sidebar is available on both the Admin Dashboard and Team Files pages for easy navigation.

## Features

### For Each Team Member:
1. **Upload Files**: Click "Choose file" and select documents to upload
2. **View Files**: See all uploaded files with size and date information
3. **Download Files**: Click "Download" to retrieve any file
4. **Delete Files**: Click "Delete" to remove files (with confirmation)

### Supported File Types:
- Documents: PDF, DOC, DOCX
- Spreadsheets: XLS, XLSX
- Presentations: PPT, PPTX
- Images: JPG, JPEG, PNG, GIF
- Archives: ZIP, RAR
- Text: TXT

### File Size Limit:
- Maximum file size: 16 MB per file

## How It Works

### Upload Process:
1. Navigate to Team Files via the Admin sidebar
2. Select a team member card (Team Member 1-5)
3. Click "Choose file to upload"
4. Select your document
5. Click "Upload File"
6. File is saved and appears in the list

### Storage:
- Files are stored in: `static/uploads/team_files/`
- Database tracks: filename, uploader, size, type, upload date
- Original filenames are preserved for downloads

### Security:
- Filenames are sanitized to prevent security issues
- Only allowed file types can be uploaded
- File paths are secured against directory traversal

## Team Members
Currently configured for 5 team members:
- Team Member 1
- Team Member 2
- Team Member 3
- Team Member 4
- Team Member 5

You can customize these names in the `get_team_members()` function in `main.py`.

## Technical Details

### Database Table: `team_files`
```sql
CREATE TABLE team_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_name TEXT NOT NULL,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

### Routes:
- `GET /team-files` - Display team files page
- `POST /team-files/upload/<member_id>` - Upload a file
- `GET /team-files/download/<file_id>` - Download a file
- `GET /team-files/delete/<file_id>` - Delete a file

## UI Layout

### Sidebar Navigation
- **Position**: Left side of Admin Panel and Team Files pages
- **Style**: White card with green accent (#36943b)
- **Active State**: Highlighted with gradient background
- **Icons**: Emoji icons for visual clarity
- **Sticky**: Remains visible while scrolling

### Main Content
- **Layout**: Responsive grid for team member cards
- **Cards**: White cards with shadow and hover effects
- **File List**: Compact display with download/delete actions

## Customization

### To Change Team Member Names:
Edit the `get_team_members()` function in `main.py`:
```python
member_names = ['Your Name 1', 'Your Name 2', 'Your Name 3', 'Your Name 4', 'Your Name 5']
```

### To Add More Team Members:
1. Add names to the `member_names` list
2. Update the validation in `upload_file()` route
3. Adjust the grid layout in CSS if needed

### To Change File Size Limit:
Edit `main.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Change 16 to desired MB
```

### To Allow Additional File Types:
Edit `main.py`:
```python
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', ... , 'your_extension'}
```

## Troubleshooting

### Files Not Uploading:
- Check file size is under 16MB
- Verify file type is in allowed list
- Ensure `static/uploads/team_files/` directory exists and is writable

### Can't See Uploaded Files:
- Refresh the page
- Check database connection
- Verify files exist in `static/uploads/team_files/`

### Download Issues:
- Check file still exists on disk
- Verify file path in database matches actual location

### Sidebar Not Showing:
- Ensure you're on Admin Panel or Team Files page
- Check browser console for JavaScript errors
- Verify CSS is loading correctly