"""
WSGI configuration file for PythonAnywhere deployment
This file is used by PythonAnywhere to serve the Flask application
"""
import os
import sys

# Add the project directory to the Python path
project_home = u'/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables for the application
os.environ['DATABASE_PATH'] = '/home/zhonghuazhang/Elephant-In-the-Room-Fundarasing/data/companies.db'
os.environ['GOOGLE_MAPS_API_KEY'] = 'AIzaSyAC5xqPdp_6Ey87-ram1gZWM5L658yo-I4'  # Your API key

# Import the Flask app from main.py
from main import app as application