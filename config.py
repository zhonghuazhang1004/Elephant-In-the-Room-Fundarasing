"""
Configuration file for the application
Store sensitive information here and add to .gitignore
Supports both local development and PythonAnywhere deployment via environment variables
"""
import os

# Google Maps API Configuration
# Priority: Environment Variable > Local Config > Default
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', "AIzaSyAC5xqPdp_6Ey87-ram1gZWM5L658yo-I4")

# Database Configuration
# For PythonAnywhere deployment, use absolute path from environment variable
DATABASE_PATH = os.environ.get('DATABASE_PATH', "data/companies.db")

# Application Settings
DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
HOST = os.environ.get('FLASK_HOST', "127.0.0.1")
PORT = int(os.environ.get('FLASK_PORT', 5000))
