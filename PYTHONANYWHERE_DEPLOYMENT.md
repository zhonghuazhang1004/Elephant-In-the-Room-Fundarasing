# PythonAnywhere Deployment Configuration Guide

## 📋 Overview
This guide provides the complete configuration needed to deploy the Elephant in the Room application on PythonAnywhere.

## ✅ Files Modified for PythonAnywhere Compatibility

### 1. **pythonanywhere_wsgi.py** (NEW)
- **Purpose**: WSGI entry point for PythonAnywhere
- **Location**: Project root directory
- **Key Features**:
  - Sets project path: `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing`
  - Configures environment variables for database and API key
  - Imports Flask app from main.py

### 2. **config.py** (UPDATED)
- **Changes**: Added environment variable support
- **Features**:
  - Reads `GOOGLE_MAPS_API_KEY` from environment or uses default
  - Reads `DATABASE_PATH` from environment or uses relative path
  - Supports both local development and production deployment

### 3. **database.py** (UPDATED)
- **Changes**: Added environment variable support for DATABASE_PATH
- **Features**:
  - Reads database path from `DATABASE_PATH` environment variable
  - Falls back to `data/companies.db` for local development
  - Automatically creates data directory if it doesn't exist

## 🔧 PythonAnywhere Web App Configuration

### Required Settings in PythonAnywhere Dashboard:

| Setting | Value |
|---------|-------|
| **Source code** | `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing` |
| **Working directory** | `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing` |
| **WSGI configuration file** | `/var/www/zhonghuazhang_pythonanywhere_com_wsgi.py` |
| **Python version** | 3.10 |
| **Virtualenv** | `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing/venv` |

### Static Files Mapping:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing/static/` |

## 🚀 Deployment Steps

### Step 1: Clone Repository on PythonAnywhere
```bash
cd ~
git clone https://github.com/zhonghuazhang1004/Elephant-In-the-Room-Fundarasing.git
cd Elephant-In-the-Room-Fundarasing
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Web App
1. Go to **Web** tab in PythonAnywhere dashboard
2. Click **"Add a new web app"**
3. Select **Manual configuration** → **Python 3.10**
4. Set paths as shown in the table above

### Step 4: Edit WSGI Configuration File
1. Click on the **WSGI configuration file** link
2. Replace all content with the content of `pythonanywhere_wsgi.py`
3. **IMPORTANT**: Update the Google Maps API key:
   ```python
   os.environ['GOOGLE_MAPS_API_KEY'] = 'YOUR_ACTUAL_API_KEY_HERE'
   ```
4. Save the file

### Step 5: Create Data Directory
```bash
mkdir -p ~/Elephant-In-the-Room-Fundarasing/data
mkdir -p ~/Elephant-In-the-Room-Fundarasing/static/uploads/team_files
chmod 755 ~/Elephant-In-the-Room-Fundarasing/data
chmod 755 ~/Elephant-In-the-Room-Fundarasing/static/uploads/team_files
```

### Step 6: Reload Web App
Click the green **"Reload"** button in the Web tab

### Step 7: Test Your Application
Visit: `https://zhonghuazhang.pythonanywhere.com`

## 🔐 Security Configuration

### Google Maps API Key Setup

1. **In WSGI File** (Recommended for PythonAnywhere):
   Edit `/var/www/zhonghuazhang_pythonanywhere_com_wsgi.py`:
   ```python
   os.environ['GOOGLE_MAPS_API_KEY'] = 'your_actual_api_key_here'
   ```

2. **API Restrictions** (Important!):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services → Credentials
   - Add HTTP referrer restrictions:
     - `*.pythonanywhere.com/*`
     - `zhonghuazhang.pythonanywhere.com/*`

### Database Security

- Database file is stored at: `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing/data/companies.db`
- Ensure proper permissions: `chmod 755 data/`
- Database is NOT committed to Git (excluded via .gitignore)

## 🔄 Updating Your Application

When you make changes to your code:

```bash
# On PythonAnywhere Bash console
cd ~/Elephant-In-the-Room-Fundarasing
git pull origin master

# Then click "Reload" button in Web tab
```

## 📊 Environment Variables Summary

| Variable | Purpose | Default Value |
|----------|---------|---------------|
| `DATABASE_PATH` | SQLite database location | `data/companies.db` |
| `GOOGLE_MAPS_API_KEY` | Google Maps Geocoding API | From config.py |
| `FLASK_DEBUG` | Enable debug mode | `False` |
| `FLASK_HOST` | Server host | `127.0.0.1` |
| `FLASK_PORT` | Server port | `5000` |

## ⚠️ Common Issues & Solutions

### Issue 1: "Directory does not exist" error
**Solution**: Ensure Source code and Working directory use the SAME username path:
- Both should be: `/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing`

### Issue 2: Database not created
**Solution**: 
```bash
mkdir -p ~/Elephant-In-the-Room-Fundarasing/data
chmod 755 ~/Elephant-In-the-Room-Fundarasing/data
```

### Issue 3: Google Maps API not working
**Solution**:
1. Check API key is set in WSGI file
2. Verify Geocoding API is enabled in Google Cloud Console
3. Ensure billing account is linked
4. Check API restrictions allow pythonanywhere.com

### Issue 4: File upload fails
**Solution**:
```bash
mkdir -p ~/Elephant-In-the-Room-Fundarasing/static/uploads/team_files
chmod 755 ~/Elephant-In-the-Room-Fundarasing/static/uploads/team_files
```

### Issue 5: Module not found errors
**Solution**:
```bash
source ~/Elephant-In-the-Room-Fundarasing/venv/bin/activate
pip install -r requirements.txt
```

## 📈 Monitoring & Logs

### View Application Logs
1. Go to **Web** tab
2. Scroll down to **"Error log"** and **"Server log"** links
3. Click to view real-time logs

### Check Resource Usage
- **CPU Time**: Limited on free tier (check Dashboard)
- **Bandwidth**: Monitor in Dashboard
- **Storage**: 512 MB limit on free tier

## 🎯 Final Checklist

Before going live, verify:

- [ ] Repository cloned to PythonAnywhere
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Web app configured with correct paths
- [ ] WSGI file edited with correct API key
- [ ] Static files mapping configured
- [ ] Data directory created with proper permissions
- [ ] Uploads directory created with proper permissions
- [ ] Web app reloaded
- [ ] Application accessible at `https://zhonghuazhang.pythonanywhere.com`
- [ ] Google Maps API working (test company page)
- [ ] File upload working (test team files page)

## 🆘 Support

If you encounter issues:
1. Check PythonAnywhere error logs
2. Verify all paths use correct username (`zhonghuazhang`)
3. Ensure virtual environment is activated when running commands
4. Test locally first before deploying

---

**Last Updated**: 2026-05-29  
**Compatible With**: PythonAnywhere Free & Paid Tiers  
**Python Version**: 3.10+
