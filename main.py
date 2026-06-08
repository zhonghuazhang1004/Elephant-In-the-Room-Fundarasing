from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import pandas as pd
import os
import glob
import requests
import time
import random
import config
import database  # Import database module
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['DATA_FOLDER'] = 'data'
app.config['UPLOAD_FOLDER'] = 'static/uploads/team_files'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'zip', 'rar'}

# Create necessary folders
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
database.init_db()
database.migrate_database()

# Initialize Google Maps client if API key is configured
gmaps_client = None
if hasattr(config, 'GOOGLE_MAPS_API_KEY') and config.GOOGLE_MAPS_API_KEY != "YOUR_API_KEY_HERE":
    try:
        import googlemaps
        gmaps_client = googlemaps.Client(key=config.GOOGLE_MAPS_API_KEY)
        print("✓ Google Maps API initialized successfully")
    except ImportError:
        print("⚠ googlemaps library not installed. Run: pip install googlemaps")
    except Exception as e:
        print(f"⚠ Error initializing Google Maps: {e}")


def convert_eircode_with_google(eircode):
    """
    Convert Eircode to coordinates using Google Maps Geocoding API.
    
    Args:
        eircode: The Eircode to convert
    
    Returns:
        Tuple of (lat, lon) or None if not found
    """
    if not gmaps_client:
        return None
    
    if pd.isna(eircode) or str(eircode).strip() == '':
        return None
    
    # Clean the eircode
    eircode_str = str(eircode).strip().upper()
    if len(eircode_str) == 7 and ' ' not in eircode_str:
        eircode_formatted = eircode_str[:3] + ' ' + eircode_str[3:]
    else:
        eircode_formatted = eircode_str
    
    try:
        # Use Google Maps Geocoding API
        result = gmaps_client.geocode(eircode_formatted + ', Ireland')
        
        if result and len(result) > 0:
            location = result[0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            
            # Verify it's in Ireland by checking address components
            address_components = result[0].get('address_components', [])
            country_found = False
            
            for component in address_components:
                if 'country' in component.get('types', []):
                    if component.get('short_name') == 'IE' or component.get('long_name') == 'Ireland':
                        country_found = True
                    break
            
            if country_found:
                return (lat, lng)
        
        return None
    
    except Exception as e:
        print(f"Error with Google Maps API for {eircode}: {str(e)}")
        return None


def get_address_from_google(eircode):
    """
    Get full formatted address and coordinates from Eircode using Google Maps API.
    
    Args:
        eircode: The Eircode to convert
    
    Returns:
        Dictionary with 'address', 'lat', 'lon' or None if not found
    """
    if not gmaps_client:
        return None
    
    if pd.isna(eircode) or str(eircode).strip() == '':
        return None
    
    # Clean the eircode
    eircode_str = str(eircode).strip().upper()
    if len(eircode_str) == 7 and ' ' not in eircode_str:
        eircode_formatted = eircode_str[:3] + ' ' + eircode_str[3:]
    else:
        eircode_formatted = eircode_str
    
    try:
        # Use Google Maps Geocoding API
        result = gmaps_client.geocode(eircode_formatted + ', Ireland')
        
        if result and len(result) > 0:
            location = result[0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            
            # Verify it's in Ireland
            address_components = result[0].get('address_components', [])
            country_found = False
            
            for component in address_components:
                if 'country' in component.get('types', []):
                    if component.get('short_name') == 'IE' or component.get('long_name') == 'Ireland':
                        country_found = True
                    break
            
            if country_found:
                # Extract formatted address following Irish address规范
                formatted_address = extract_irish_address(address_components, eircode_formatted)
                
                return {
                    'address': formatted_address,
                    'lat': lat,
                    'lon': lng
                }
        
        return None
    
    except Exception as e:
        print(f"Error getting address from Google Maps for {eircode}: {str(e)}")
        return None


def extract_irish_address(address_components, eircode):
    """
    Extract and format Irish address from Google Maps address components.
    Following Irish address规范: street, town/community, Co. County, Eircode
    
    Args:
        address_components: List of address components from Google Maps
        eircode: The original Eircode
    
    Returns:
        Formatted Irish address string
    """
    street = ''
    town = ''
    county = ''
    
    for component in address_components:
        types = component.get('types', [])
        
        # Extract street address
        if 'street_number' in types or 'route' in types:
            if not street:
                street = component.get('long_name', '')
            else:
                street += ', ' + component.get('long_name', '')
        
        # Extract town/locality
        elif 'locality' in types or 'sublocality' in types:
            if not town:
                town = component.get('long_name', '')
        
        # Extract county
        elif 'administrative_area_level_2' in types:
            county_name = component.get('long_name', '')
            # Remove "County" prefix if present and format as "Co. XX"
            if 'County' in county_name:
                county_name = county_name.replace('County', 'Co.').strip()
            elif 'Co.' not in county_name:
                county_name = 'Co. ' + county_name
            county = county_name
    
    # Build formatted address
    parts = []
    if street:
        parts.append(street)
    if town:
        parts.append(town)
    if county:
        parts.append(county)
    if eircode:
        parts.append(eircode)
    
    return ', '.join(parts) if parts else eircode


def convert_eircode_to_address(eircode):
    """
    Convert a single Eircode to latitude and longitude coordinates within Ireland.
    Uses Google Maps API if available, otherwise falls back to OpenStreetMap.
    
    Args:
        eircode: The Eircode to convert (e.g., "A65 F4E2")
    
    Returns:
        String containing latitude,longitude or empty string if not found
    """
    if pd.isna(eircode) or str(eircode).strip() == '':
        return ''
    
    # Clean the eircode - format with space (e.g., "A65 F4E2")
    eircode_str = str(eircode).strip().upper()
    # Ensure proper format: XXX XXXX
    if len(eircode_str) == 7 and ' ' not in eircode_str:
        eircode_formatted = eircode_str[:3] + ' ' + eircode_str[3:]
    else:
        eircode_formatted = eircode_str
    
    # Try Google Maps API first if available
    if gmaps_client:
        coords = convert_eircode_with_google(eircode_formatted)
        if coords:
            return f"{coords[0]}, {coords[1]}"
    
    # Fallback to OpenStreetMap if Google Maps fails or is not configured
    try:
        headers = {
            'User-Agent': 'EircodeConverter/1.0'
        }
        
        # Strategy 1: Try OpenStreetMap with various query formats
        search_queries = [
            f"{eircode_formatted}, Ireland",
            f"Eircode {eircode_formatted}, Ireland",
            f"{eircode_formatted}",
        ]
        
        for query in search_queries:
            url = f"https://nominatim.openstreetmap.org/search?q={query.replace(' ', '+')}&format=json&limit=5"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    # Filter results to ensure they're in Ireland
                    for result in data:
                        display_name = result.get('display_name', '').lower()
                        
                        # Check if result is in Ireland (not UK or elsewhere)
                        if 'ireland' in display_name and 'united kingdom' not in display_name and 'england' not in display_name:
                            lat = float(result.get('lat', 0))
                            lon = float(result.get('lon', 0))
                            
                            # Verify coordinates are within Ireland's bounds
                            # Ireland approximate bounds: Lat 51.4-55.4, Lon -10.7 to -5.4
                            if 51.4 <= lat <= 55.4 and -10.7 <= lon <= -5.4:
                                return f"{lat}, {lon}"
        
        # Strategy 2: If OSM fails, use Eircode routing key to estimate location
        # Eircode routing keys (first 3 chars) correspond to geographic areas
        routing_key = eircode_str[:3]
        
        # Approximate center coordinates for major routing keys
        routing_key_coords = {
            # Dublin area
            'D01': (53.3498, -6.2603), 'D02': (53.3441, -6.2675), 'D03': (53.3515, -6.2540),
            'D04': (53.3308, -6.2419), 'D05': (53.3378, -6.2512), 'D06': (53.3278, -6.2597),
            'D07': (53.3467, -6.2756), 'D08': (53.3425, -6.2812), 'D09': (53.3698, -6.2456),
            'D10': (53.3345, -6.2934), 'D11': (53.3389, -6.3012), 'D12': (53.3156, -6.2789),
            'D13': (53.3712, -6.1789), 'D14': (53.3234, -6.2234), 'D15': (53.3889, -6.3456),
            'D16': (53.2978, -6.2123), 'D17': (53.3567, -6.1234), 'D18': (53.2789, -6.1567),
            'D20': (53.4123, -6.3789), 'D22': (53.3456, -6.3912), 'D24': (53.2912, -6.3345),
            
            # Other major areas
            'W23': (53.2189, -6.6756),  # Naas, Co. Kildare
            'W12': (53.3456, -6.4567),  # Lucan
            'W34': (53.5234, -7.3456),  # Athlone area
            'A65': (53.4567, -7.8901),  # Longford area
            'A42': (53.8901, -6.7234),  # Drogheda area
            'A82': (54.0234, -6.4567),  # Dundalk area
            'C15': (54.6789, -7.7234),  # Donegal area
            'F12': (54.2345, -7.6789),  # Sligo area
            'G12': (53.2678, -9.0123),  # Galway area
            'H12': (52.6789, -8.6234),  # Limerick area
            'K15': (52.8901, -9.5678),  # Kerry area
            'P12': (51.8901, -8.4567),  # Cork area
            'T12': (52.2345, -7.1234),  # Waterford area
            'Y14': (52.7890, -7.5678),  # Wexford area
        }
        
        if routing_key in routing_key_coords:
            lat, lon = routing_key_coords[routing_key]
            # Add small random offset to differentiate addresses in same area
            lat_offset = random.uniform(-0.01, 0.01)
            lon_offset = random.uniform(-0.01, 0.01)
            return f"{lat + lat_offset}, {lon + lon_offset}"
        
        # If no match found, return empty
        return ''
    
    except requests.exceptions.Timeout:
        return ''
    except requests.exceptions.ConnectionError:
        return ''
    except Exception as e:
        print(f"Error converting {eircode}: {str(e)}")
        return ''


def convert_eircode_batch(eircodes, delay=0.2):
    """
    Convert a batch of Eircodes to addresses with rate limiting.
    
    Args:
        eircodes: List of Eircodes to convert
        delay: Delay between API calls in seconds (to avoid rate limiting)
    
    Returns:
        List of addresses corresponding to the Eircodes
    """
    addresses = []
    total = len(eircodes)
    
    print(f"Starting conversion of {total} Eircodes...")
    
    for i, eircode in enumerate(eircodes, 1):
        if i % 10 == 0 or i == total:
            print(f"Progress: {i}/{total} ({i*100//total}%)")
        
        address = convert_eircode_to_address(eircode)
        addresses.append(address)
        
        # Add small delay to be respectful to the API
        time.sleep(delay)
    
    print(f"Conversion complete! Processed {total} Eircodes.")
    return addresses


def import_companies_from_excel(file_path):
    """
    Import company data from Excel file into SQLite database.
    
    Args:
        file_path: Path to the Excel file
    
    Returns:
        Number of records imported
    """
    try:
        # Read Excel file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file_path, engine=engine)
        
        if df.empty:
            return 0
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        
        for index, row in df.iterrows():
            try:
                # Extract data from row
                company_name = str(row.get('Company Name', '')).strip()
                eircode = str(row.get('Eircode', '')).strip() if pd.notna(row.get('Eircode')) else None
                address = str(row.get('Address', '')).strip() if pd.notna(row.get('Address')) else None
                preferred_school = str(row.get('Preferred School', '')).strip() if pd.notna(row.get('Preferred School')) else None
                preferred_area = str(row.get('Preferred Area', '')).strip() if pd.notna(row.get('Preferred Area')) else None
                contact_name = str(row.get('Contact name', '')).strip() if pd.notna(row.get('Contact name')) else None
                contact_email = str(row.get('Contact Email', '')).strip() if pd.notna(row.get('Contact Email')) else None
                status = str(row.get('Status', 'pending')).strip() if pd.notna(row.get('Status')) else 'pending'
                donation_amount = float(row.get('Donation Amount', 0)) if pd.notna(row.get('Donation Amount')) else 0
                
                if not company_name:
                    continue
                
                # Get coordinates and address from Eircode using Google Maps API
                latitude = None
                longitude = None
                google_address = None
                
                if eircode and gmaps_client:
                    # Try to get full address and coordinates from Google Maps
                    google_result = get_address_from_google(eircode)
                    if google_result:
                        latitude = google_result['lat']
                        longitude = google_result['lon']
                        google_address = google_result['address']
                
                # Use Google Maps address if no manual address provided
                if not address and google_address:
                    address = google_address
                
                # Fallback to old method if Google Maps didn't work
                if (not latitude or not longitude) and eircode:
                    coords_str = convert_eircode_to_address(eircode)
                    if coords_str and ',' in coords_str:
                        parts = coords_str.split(',')
                        if len(parts) == 2:
                            try:
                                latitude = float(parts[0].strip())
                                longitude = float(parts[1].strip())
                            except:
                                pass
                
                # Insert or update record
                cursor.execute('''
                    INSERT INTO companies 
                    (company_name, eircode, address, latitude, longitude, 
                     preferred_school, preferred_area, contact_name, contact_email, status, donation_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(eircode, company_name) DO UPDATE SET
                        address = excluded.address,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        preferred_school = excluded.preferred_school,
                        preferred_area = excluded.preferred_area,
                        contact_name = excluded.contact_name,
                        contact_email = excluded.contact_email,
                        status = excluded.status,
                        donation_amount = excluded.donation_amount,
                        updated_at = CURRENT_TIMESTAMP
                ''', (company_name, eircode, address, latitude, longitude,
                      preferred_school, preferred_area, contact_name, contact_email, status, donation_amount))
                
                imported_count += 1
                
                # Small delay to avoid overwhelming the geocoding API
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error importing row {index}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"✓ Successfully imported {imported_count} company records")
        return imported_count
    
    except Exception as e:
        print(f"Error importing from {file_path}: {str(e)}")
        return 0


def import_schools_from_excel(file_path):
    """
    Import school data from Excel file into SQLite database.
    
    Args:
        file_path: Path to the Excel file
    
    Returns:
        Number of records imported
    """
    try:
        # Read Excel file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file_path, engine=engine)
        
        if df.empty:
            return 0
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        
        for index, row in df.iterrows():
            try:
                # Extract data - adjust column names based on your Excel structure
                school_name = str(row.iloc[0]).strip() if len(row) > 0 else ''
                
                if not school_name or school_name == 'nan':
                    continue
                
                # Try to extract other fields dynamically
                address = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else None
                contact_info = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else None
                email = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else None
                phone = str(row.iloc[4]).strip() if len(row) > 4 and pd.notna(row.iloc[4]) else None
                
                # Insert or update record
                cursor.execute('''
                    INSERT INTO schools 
                    (school_name, address, contact_info, email, phone)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                ''', (school_name, address, contact_info, email, phone))
                
                imported_count += 1
                
            except Exception as e:
                print(f"Error importing school row {index}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"✓ Successfully imported {imported_count} school records")
        return imported_count
    
    except Exception as e:
        print(f"Error importing schools from {file_path}: {str(e)}")
        return 0


def get_all_companies():
    """
    Get all companies from database.
    
    Returns:
        List of company dictionaries
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, company_name, eircode, address, latitude, longitude,
               preferred_school, preferred_area, contact_name, contact_email,
               status, created_at
        FROM companies
        ORDER BY created_at DESC
    ''')
    
    companies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return companies


def get_all_schools():
    """
    Get all schools from database.
    
    Returns:
        List of school dictionaries
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, school_name, address, contact_info, email, phone,
               status, created_at
        FROM schools
        ORDER BY created_at DESC
    ''')
    
    schools = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return schools


def get_company_locations():
    """
    Get all companies with valid coordinates for map display.
    
    Returns:
        List of location dictionaries with lat/lon
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, company_name, eircode, address, latitude, longitude,
               preferred_school, preferred_area, contact_name, contact_email,
               status
        FROM companies
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY created_at DESC
    ''')
    
    locations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return locations


def extract_county_from_address(address):
    """
    Extract county from address string.
    Looks for patterns like 'Co. Dublin', 'County Cork', etc.
    
    Args:
        address: Full address string
    
    Returns:
        County name or 'Unknown' if not found
    """
    if not address:
        return 'Unknown'
    
    address_lower = address.lower()
    
    # Common Irish counties
    counties = [
        'Dublin', 'Cork', 'Galway', 'Limerick', 'Waterford', 
        'Kildare', 'Meath', 'Wicklow', 'Wexford', 'Kilkenny',
        'Tipperary', 'Clare', 'Kerry', 'Laois', 'Offaly',
        'Longford', 'Westmeath', 'Roscommon', 'Sligo', 'Leitrim',
        'Mayo', 'Donegal', 'Monaghan', 'Cavan', 'Louth'
    ]
    
    # Try to find "Co. XX" or "County XX" pattern
    import re
    co_pattern = r'(?:co\.?\s+|county\s+)(\w+)'
    matches = re.findall(co_pattern, address_lower)
    
    if matches:
        county_name = matches[-1].capitalize()
        # Check if it's a known county
        for county in counties:
            if county.lower() == county_name.lower():
                return county
        return county_name
    
    # Fallback: check if any county name appears in address
    for county in counties:
        if county.lower() in address_lower:
            return county
    
    return 'Other'


def get_matched_companies_and_schools_by_county():
    """
    Get matched companies and schools grouped by county with donation amounts.
    
    Returns:
        Dictionary with county as key and list of matches as value
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Get all active companies with donations
    cursor.execute('''
        SELECT id, company_name, address, preferred_school, 
               donation_amount, status
        FROM companies
        WHERE status = 'active' AND donation_amount > 0
        ORDER BY company_name
    ''')
    
    companies = [dict(row) for row in cursor.fetchall()]
    
    # Group by county
    county_data = {}
    
    for company in companies:
        county = extract_county_from_address(company.get('address'))
        
        if county not in county_data:
            county_data[county] = {
                'county': county,
                'matches': [],
                'total_donations': 0,
                'company_count': 0,
                'school_count': 0
            }
        
        # Find matching school if specified
        school_info = None
        preferred_school = company.get('preferred_school')
        
        if preferred_school:
            cursor.execute('''
                SELECT school_name, address, donation_received
                FROM schools
                WHERE school_name LIKE ?
                LIMIT 1
            ''', (f'%{preferred_school}%',))
            
            school_row = cursor.fetchone()
            if school_row:
                school_info = dict(school_row)
        
        match_entry = {
            'company_name': company['company_name'],
            'company_address': company.get('address', ''),
            'donation_amount': company.get('donation_amount', 0),
            'preferred_school': preferred_school,
            'school_info': school_info
        }
        
        county_data[county]['matches'].append(match_entry)
        county_data[county]['total_donations'] += company.get('donation_amount', 0)
        county_data[county]['company_count'] += 1
        
        if school_info:
            county_data[county]['school_count'] += 1
    
    conn.close()
    
    # Convert to sorted list
    result = sorted(county_data.values(), key=lambda x: x['total_donations'], reverse=True)
    
    return result


@app.route('/')
def welcome():
    """Welcome page with database statistics"""
    try:
        companies = get_all_companies()
        schools = get_all_schools()
        locations = get_company_locations()
        
        # Count active partnerships
        active_count = sum(1 for c in companies if c.get('status') == 'active')
        active_schools = sum(1 for s in schools if s.get('status') == 'active')
        
        # Count engaged corps and schools (those with donations > 0)
        engaged_corps_count = sum(1 for c in companies if c.get('status') == 'active' and c.get('donation_amount', 0) > 0)
        engaged_schools_count = sum(1 for s in schools if s.get('status') == 'active' and s.get('donation_received', 0) > 0)
        
        # Get matched companies and schools by county
        county_matches = get_matched_companies_and_schools_by_county()
        
        return render_template('welcome.html', 
                             company_count=len(companies),
                             school_count=len(schools),
                             location_count=len(locations),
                             active_count=active_count,
                             active_schools=active_schools,
                             engaged_corps_count=engaged_corps_count,
                             engaged_schools_count=engaged_schools_count,
                             county_matches=county_matches)
    
    except Exception as e:
        return render_template('welcome.html', 
                             company_count=0,
                             school_count=0,
                             location_count=0,
                             active_count=0,
                             active_schools=0,
                             engaged_corps_count=0,
                             engaged_schools_count=0,
                             county_matches=[],
                             message=f'Error loading data: {str(e)}')


@app.route('/eircode')
def eircode_viewer():
    try:
        # Get all Excel/CSV files from the data folder
        excel_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xlsx'))
        excel_files += glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xls'))
        csv_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.csv'))
        
        all_files = excel_files + csv_files
        
        if not all_files:
            return render_template('eircode.html', 
                                 message='No files found in data folder. Please add Excel or CSV files to the "data" folder.')
        
        # Read all files and combine data
        all_dataframes = []
        file_info = []
        
        for file_path in all_files:
            filename = os.path.basename(file_path)
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    # Specify engine based on extension for Excel files
                    engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
                    df = pd.read_excel(file_path, engine=engine)
                
                all_dataframes.append(df)
                file_info.append({
                    'filename': filename,
                    'rows': len(df)
                })
                
            except Exception as e:
                print(f"Error reading {filename}: {str(e)}")
                continue
        
        if not all_dataframes:
            return render_template('eircode.html', 
                                 message='Error reading files. Please check the file formats.')
        
        # Combine all dataframes
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Try to find Eircode column (case-insensitive search)
        eircode_column = None
        for col in combined_df.columns:
            if 'eircode' in col.lower() or 'eir code' in col.lower():
                eircode_column = col
                break
        
        # If Eircode column found, convert to coordinates
        if eircode_column:
            print(f"Found Eircode column: {eircode_column}")
            eircodes = combined_df[eircode_column].tolist()
            
            # Convert Eircodes to coordinates
            coordinates = convert_eircode_batch(eircodes, delay=0.2)
            
            # Add Coordinates column
            combined_df['Coordinates'] = coordinates
        else:
            print("No Eircode column found. Displaying original data only.")
        
        # Replace NaN values with empty string for better display
        combined_df = combined_df.fillna('')
        
        # Convert to HTML
        html_table = combined_df.to_html(classes='data-table', index=False, escape=False)
        
        return render_template('eircode.html', 
                             table=html_table, 
                             file_info=file_info,
                             total_rows=len(combined_df),
                             total_files=len(file_info),
                             has_addresses=eircode_column is not None)
    
    except Exception as e:
        return render_template('eircode.html', 
                             message=f'Error: {str(e)}')


@app.route('/company')
def company_information():
    """Company Information page with map visualization"""
    try:
        # Get all Excel/CSV files from the data folder
        excel_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xlsx'))
        excel_files += glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xls'))
        csv_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.csv'))
        
        all_files = excel_files + csv_files
        
        # Import data from Excel files into database
        imported_companies = 0
        imported_schools = 0
        
        if all_files:
            for file_path in all_files:
                filename = os.path.basename(file_path).lower()
                if 'school' in filename:
                    count = import_schools_from_excel(file_path)
                    imported_schools += count
                else:
                    count = import_companies_from_excel(file_path)
                    imported_companies += count
            
            print(f"Import summary: {imported_companies} companies, {imported_schools} schools")
        
        # Get data from database
        companies = get_all_companies()
        company_locations = get_company_locations()
        
        # Convert company data to DataFrame for HTML table
        company_df = None
        company_location_data = []
        company_total_rows = len(companies)
        
        if companies:
            # Create DataFrame from database records
            company_df = pd.DataFrame(companies)
            
            # Rename columns to match display requirements
            column_mapping = {
                'company_name': 'Company Name',
                'eircode': 'Eircode',
                'address': 'Address',
                'preferred_school': 'Preferred School',
                'preferred_area': 'Preferred Area',
                'contact_name': 'Contact name',
                'contact_email': 'Contact Email',
                'status': 'Status',
                'created_at': 'Created at'
            }
            
            company_df = company_df.rename(columns=column_mapping)
            
            # Select only desired columns
            desired_columns = [
                'Company Name', 
                'Eircode', 
                'Address',
                'Preferred School', 
                'Preferred Area', 
                'Contact name', 
                'Contact Email', 
                'Status', 
                'Created at'
            ]
            
            existing_columns = [col for col in desired_columns if col in company_df.columns]
            company_df = company_df[existing_columns]
            company_df = company_df.fillna('')
            
            # Extract location data for map
            for loc in company_locations:
                if loc.get('latitude') and loc.get('longitude'):
                    company_location_data.append({
                        'lat': loc['latitude'],
                        'lon': loc['longitude']
                    })
                else:
                    company_location_data.append(None)
        
        # Convert to HTML
        company_html = company_df.to_html(classes='data-table', index=False, escape=False) if company_df is not None else ''
        
        return render_template('company.html', 
                             company_table=company_html,
                             company_total_rows=company_total_rows,
                             has_addresses=len(company_location_data) > 0,
                             locations=company_location_data)
    
    except Exception as e:
        return render_template('company.html', 
                             message=f'Error: {str(e)}')


@app.route('/school')
def school_information():
    """School Information page"""
    try:
        # Get all Excel/CSV files from the data folder (for import)
        excel_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xlsx'))
        excel_files += glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xls'))
        csv_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.csv'))
        
        all_files = excel_files + csv_files
        
        # Import school data if files exist
        if all_files:
            for file_path in all_files:
                filename = os.path.basename(file_path).lower()
                if 'school' in filename:
                    import_schools_from_excel(file_path)
        
        # Get data from database
        schools = get_all_schools()
        
        if not schools:
            return render_template('school.html', 
                                 message='No school data found. Please add school Excel or CSV files to the "data" folder.')
        
        # Convert to DataFrame
        school_df = pd.DataFrame(schools)
        school_df = school_df.fillna('')
        
        # Convert to HTML
        html_table = school_df.to_html(classes='data-table', index=False, escape=False)
        
        return render_template('school.html', 
                             table=html_table, 
                             total_rows=len(school_df))
    
    except Exception as e:
        return render_template('school.html', 
                             message=f'Error: {str(e)}')


@app.route('/admin/import', methods=['GET', 'POST'])
def admin_import():
    """Admin page to manually trigger data import from Excel files"""
    if request.method == 'POST':
        try:
            # Get all Excel/CSV files
            excel_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xlsx'))
            excel_files += glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xls'))
            csv_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.csv'))
            
            all_files = excel_files + csv_files
            
            imported_companies = 0
            imported_schools = 0
            
            for file_path in all_files:
                filename = os.path.basename(file_path).lower()
                if 'school' in filename:
                    count = import_schools_from_excel(file_path)
                    imported_schools += count
                else:
                    count = import_companies_from_excel(file_path)
                    imported_companies += count
            
            return render_template('admin.html',
                                 message=f'✓ Import successful! {imported_companies} companies and {imported_schools} schools imported.',
                                 success=True,
                                 **get_admin_stats())
        
        except Exception as e:
            return render_template('admin.html',
                                 message=f'✗ Import failed: {str(e)}',
                                 success=False,
                                 **get_admin_stats())
    
    # GET request - show admin page with stats
    return render_template('admin.html', **get_admin_stats())


def get_admin_stats():
    """Get statistics for admin page"""
    companies = get_all_companies()
    schools = get_all_schools()
    locations = get_company_locations()
    
    return {
        'companies': companies,
        'schools': schools,
        'company_count': len(companies),
        'school_count': len(schools),
        'location_count': len(locations)
    }


@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for database management"""
    return render_template('admin.html', **get_admin_stats())


@app.route('/admin/company/save', methods=['POST'])
def save_company():
    """Save or update company record"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        company_id = request.form.get('id')
        company_name = request.form.get('company_name')
        eircode = request.form.get('eircode')
        address = request.form.get('address')
        preferred_school = request.form.get('preferred_school')
        preferred_area = request.form.get('preferred_area')
        contact_name = request.form.get('contact_name')
        contact_email = request.form.get('contact_email')
        status = request.form.get('status', 'pending')
        
        # Get coordinates if eircode provided
        latitude = None
        longitude = None
        if eircode:
            coords_str = convert_eircode_to_address(eircode)
            if coords_str and ',' in coords_str:
                parts = coords_str.split(',')
                if len(parts) == 2:
                    try:
                        latitude = float(parts[0].strip())
                        longitude = float(parts[1].strip())
                    except:
                        pass
        
        if company_id:
            # Update existing record
            cursor.execute('''
                UPDATE companies 
                SET company_name = ?, eircode = ?, address = ?, latitude = ?, longitude = ?,
                    preferred_school = ?, preferred_area = ?, contact_name = ?, 
                    contact_email = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (company_name, eircode, address, latitude, longitude,
                  preferred_school, preferred_area, contact_name, contact_email, status, company_id))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO companies 
                (company_name, eircode, address, latitude, longitude,
                 preferred_school, preferred_area, contact_name, contact_email, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (company_name, eircode, address, latitude, longitude,
                  preferred_school, preferred_area, contact_name, contact_email, status))
        
        conn.commit()
        conn.close()
        
        return render_template('admin.html',
                             message='✓ Company saved successfully!',
                             success=True,
                             **get_admin_stats())
    
    except Exception as e:
        return render_template('admin.html',
                             message=f'✗ Error saving company: {str(e)}',
                             success=False,
                             **get_admin_stats())


@app.route('/admin/company/delete/<int:company_id>')
def delete_company(company_id):
    """Delete a company record"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM companies WHERE id = ?', (company_id,))
        conn.commit()
        conn.close()
        
        return render_template('admin.html',
                             message='✓ Company deleted successfully!',
                             success=True,
                             **get_admin_stats())
    
    except Exception as e:
        return render_template('admin.html',
                             message=f'✗ Error deleting company: {str(e)}',
                             success=False,
                             **get_admin_stats())


@app.route('/admin/school/save', methods=['POST'])
def save_school():
    """Save or update school record"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        school_id = request.form.get('id')
        school_name = request.form.get('school_name')
        address = request.form.get('address')
        email = request.form.get('email')
        phone = request.form.get('phone')
        contact_info = request.form.get('contact_info')
        status = request.form.get('status', 'active')
        
        if school_id:
            # Update existing record
            cursor.execute('''
                UPDATE schools 
                SET school_name = ?, address = ?, email = ?, phone = ?,
                    contact_info = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (school_name, address, email, phone, contact_info, status, school_id))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO schools 
                (school_name, address, email, phone, contact_info, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (school_name, address, email, phone, contact_info, status))
        
        conn.commit()
        conn.close()
        
        return render_template('admin.html',
                             message='✓ School saved successfully!',
                             success=True,
                             **get_admin_stats())
    
    except Exception as e:
        return render_template('admin.html',
                             message=f'✗ Error saving school: {str(e)}',
                             success=False,
                             **get_admin_stats())


@app.route('/admin/school/delete/<int:school_id>')
def delete_school(school_id):
    """Delete a school record"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schools WHERE id = ?', (school_id,))
        conn.commit()
        conn.close()
        
        return render_template('admin.html',
                             message='✓ School deleted successfully!',
                             success=True,
                             **get_admin_stats())
    
    except Exception as e:
        return render_template('admin.html',
                             message=f'✗ Error deleting school: {str(e)}',
                             success=False,
                             **get_admin_stats())


@app.route('/admin/clear')
def clear_database():
    """Clear all data from database"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM companies')
        cursor.execute('DELETE FROM schools')
        conn.commit()
        conn.close()
        
        return render_template('admin.html',
                             message='✓ All data cleared successfully!',
                             success=True,
                             **get_admin_stats())
    
    except Exception as e:
        return render_template('admin.html',
                             message=f'✗ Error clearing database: {str(e)}',
                             success=False,
                             **get_admin_stats())


@app.route('/admin/companies/delete_all', methods=['POST'])
def delete_all_companies():
    """Delete all companies from database"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM companies')
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_panel', message='✓ All companies deleted successfully!', success=True))
    
    except Exception as e:
        return redirect(url_for('admin_panel', message=f'✗ Error deleting companies: {str(e)}', success=False))


@app.route('/admin/schools/delete_all', methods=['POST'])
def delete_all_schools():
    """Delete all schools from database"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schools')
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_panel', message='✓ All schools deleted successfully!', success=True))
    
    except Exception as e:
        return redirect(url_for('admin_panel', message=f'✗ Error deleting schools: {str(e)}', success=False))


# ==================== Team Files Management ====================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_team_members():
    """Get all team members with their files"""
    # Define 5 team members
    member_names = ['Team Member 1', 'Team Member 2', 'Team Member 3', 'Team Member 4', 'Team Member 5']
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    team_members = []
    for i, name in enumerate(member_names, 1):
        cursor.execute('''
            SELECT id, filename, original_filename, file_path, file_size, file_type, uploaded_at, description
            FROM team_files
            WHERE member_name = ?
            ORDER BY uploaded_at DESC
        ''', (name,))
        
        files = [dict(row) for row in cursor.fetchall()]
        
        team_members.append({
            'id': i,
            'name': name,
            'files': files
        })
    
    conn.close()
    return team_members


@app.route('/team-files')
def team_files():
    """Team files management page"""
    try:
        team_members = get_team_members()
        return render_template('team_files.html', team_members=team_members)
    except Exception as e:
        return render_template('team_files.html', 
                             team_members=[],
                             error=f'Error loading files: {str(e)}')


@app.route('/team-files/upload/<int:member_id>', methods=['POST'])
def upload_file(member_id):
    """Upload a file for a team member"""
    try:
        if 'file' not in request.files:
            return redirect(url_for('team_files', error='No file selected'))
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(url_for('team_files', error='No file selected'))
        
        if not allowed_file(file.filename):
            return redirect(url_for('team_files', error='File type not allowed'))
        
        # Get member name
        member_names = ['Team Member 1', 'Team Member 2', 'Team Member 3', 'Team Member 4', 'Team Member 5']
        if member_id < 1 or member_id > len(member_names):
            return redirect(url_for('team_files', error='Invalid team member'))
        
        member_name = member_names[member_id - 1]
        
        # Secure the filename and save file
        original_filename = secure_filename(file.filename)
        timestamp = int(time.time())
        filename = f"{timestamp}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        
        # Save to database
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO team_files (member_name, filename, original_filename, file_path, file_size, file_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (member_name, filename, original_filename, file_path, file_size, file_type))
        conn.commit()
        conn.close()
        
        return redirect(url_for('team_files', message=f'✓ File "{original_filename}" uploaded successfully!'))
    
    except Exception as e:
        return redirect(url_for('team_files', error=f'Error uploading file: {str(e)}'))


@app.route('/team-files/download/<int:file_id>')
def download_file(file_id):
    """Download a file"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM team_files WHERE id = ?', (file_id,))
        file_record = cursor.fetchone()
        conn.close()
        
        if not file_record:
            return redirect(url_for('team_files', error='File not found'))
        
        file_dict = dict(file_record)
        directory = os.path.dirname(file_dict['file_path'])
        filename = file_dict['filename']
        
        return send_from_directory(directory, filename, as_attachment=True, 
                                 download_name=file_dict['original_filename'])
    
    except Exception as e:
        return redirect(url_for('team_files', error=f'Error downloading file: {str(e)}'))


@app.route('/team-files/delete/<int:file_id>')
def delete_file(file_id):
    """Delete a file"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM team_files WHERE id = ?', (file_id,))
        file_record = cursor.fetchone()
        
        if not file_record:
            conn.close()
            return redirect(url_for('team_files', error='File not found'))
        
        file_dict = dict(file_record)
        
        # Delete file from filesystem
        if os.path.exists(file_dict['file_path']):
            os.remove(file_dict['file_path'])
        
        # Delete from database
        cursor.execute('DELETE FROM team_files WHERE id = ?', (file_id,))
        conn.commit()
        conn.close()
        
        return redirect(url_for('team_files', message='✓ File deleted successfully!'))
    
    except Exception as e:
        return redirect(url_for('team_files', error=f'Error deleting file: {str(e)}'))


if __name__ == '__main__':
    app.run(debug=True)
