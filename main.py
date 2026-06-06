from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import pandas as pd
import os
import glob
import math
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

_nominatim_last_call = 0.0

ROUTING_KEY_COORDS = {
    'D01': (53.3498, -6.2603), 'D02': (53.3441, -6.2675), 'D03': (53.3515, -6.2540),
    'D04': (53.3308, -6.2419), 'D05': (53.3378, -6.2512), 'D06': (53.3278, -6.2597),
    'D07': (53.3467, -6.2756), 'D08': (53.3425, -6.2812), 'D09': (53.3698, -6.2456),
    'D10': (53.3345, -6.2934), 'D11': (53.3389, -6.3012), 'D12': (53.3156, -6.2789),
    'D13': (53.3712, -6.1789), 'D14': (53.3234, -6.2234), 'D15': (53.3889, -6.3456),
    'D16': (53.2978, -6.2123), 'D17': (53.3567, -6.1234), 'D18': (53.2789, -6.1567),
    'D20': (53.4123, -6.3789), 'D22': (53.3456, -6.3912), 'D24': (53.2912, -6.3345),
    'W23': (53.2189, -6.6756), 'W12': (53.3456, -6.4567), 'W34': (53.5234, -7.3456),
    'A65': (53.4567, -7.8901), 'A42': (53.8901, -6.7234), 'A82': (54.0234, -6.4567),
    'C15': (54.6789, -7.7234), 'F12': (54.2345, -7.6789), 'G12': (53.2678, -9.0123),
    'H12': (52.6789, -8.6234), 'K15': (52.8901, -9.5678), 'P12': (51.8901, -8.4567),
    'T12': (52.2345, -7.1234), 'Y14': (52.7890, -7.5678),
}


def _nominatim_search(query):
    """Single Nominatim request with 1 RPS rate limiting."""
    global _nominatim_last_call
    elapsed = time.time() - _nominatim_last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=5"
    response = requests.get(url, headers={'User-Agent': 'ElephantFundraising/1.0'}, timeout=10)
    _nominatim_last_call = time.time()
    if response.status_code == 200:
        return response.json()
    return []


def convert_eircode_to_address(eircode):
    """
    Convert an Eircode to latitude,longitude using Nominatim (OpenStreetMap).
    Falls back to routing-key centroid if Nominatim returns no result.

    Returns:
        String "lat, lon" or empty string if not found.
    """
    if pd.isna(eircode) or str(eircode).strip() == '':
        return ''

    eircode_str = str(eircode).strip().upper()
    if len(eircode_str) == 7 and ' ' not in eircode_str:
        eircode_formatted = eircode_str[:3] + ' ' + eircode_str[3:]
    else:
        eircode_formatted = eircode_str

    try:
        query = eircode_formatted.replace(' ', '+') + '+Ireland'
        results = _nominatim_search(query)
        for result in results:
            display_name = result.get('display_name', '').lower()
            if 'ireland' in display_name and 'united kingdom' not in display_name:
                lat = float(result.get('lat', 0))
                lon = float(result.get('lon', 0))
                # Ireland bounds: lat 51.4–55.4, lon -10.7 to -5.4
                if 51.4 <= lat <= 55.4 and -10.7 <= lon <= -5.4:
                    return f"{lat}, {lon}"
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        pass
    except Exception as e:
        print(f"Error converting {eircode}: {e}")

    # Fallback: routing-key centroid with small random offset
    routing_key = eircode_str[:3]
    if routing_key in ROUTING_KEY_COORDS:
        lat, lon = ROUTING_KEY_COORDS[routing_key]
        return f"{lat + random.uniform(-0.01, 0.01)}, {lon + random.uniform(-0.01, 0.01)}"

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
                
                if not company_name:
                    continue
                
                # Get coordinates from Eircode using Nominatim
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
                            except Exception:
                                pass
                
                # Insert or update record
                cursor.execute('''
                    INSERT INTO companies 
                    (company_name, eircode, address, latitude, longitude, 
                     preferred_school, preferred_area, contact_name, contact_email, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(eircode, company_name) DO UPDATE SET
                        address = excluded.address,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        preferred_school = excluded.preferred_school,
                        preferred_area = excluded.preferred_area,
                        contact_name = excluded.contact_name,
                        contact_email = excluded.contact_email,
                        status = excluded.status,
                        updated_at = CURRENT_TIMESTAMP
                ''', (company_name, eircode, address, latitude, longitude,
                      preferred_school, preferred_area, contact_name, contact_email, status))
                
                imported_count += 1

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


def _read_school_df(file_path):
    """Read school Excel sheets (Mainstream + Special) into one DataFrame."""
    frames = []
    if file_path.endswith('.csv'):
        frames.append(pd.read_csv(file_path))
    else:
        engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
        xl = pd.ExcelFile(file_path, engine=engine)
        for sheet in xl.sheet_names:
            if sheet.lower() in ('mainstream schools', 'special schools'):
                df = xl.parse(sheet, header=1)
                if not df.empty:
                    frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def import_schools_from_excel(file_path):
    """
    Import school data from Excel file into SQLite database.
    Uses School Latitude/Longitude from the file directly; falls back to
    Nominatim geocoding via convert_eircode_to_address() when missing.

    Returns:
        Number of records imported
    """
    try:
        df = _read_school_df(file_path)
        if df.empty:
            return 0

        conn = database.get_db_connection()
        cursor = conn.cursor()
        imported_count = 0

        for index, row in df.iterrows():
            try:
                school_name = str(row.get('Official Name', '')).strip()
                if not school_name or school_name == 'nan':
                    continue

                roll_number = str(row.get('Roll Number', '')).strip() or None
                eircode = str(row.get('Eircode', '')).strip() if pd.notna(row.get('Eircode')) else None
                county = str(row.get('County Description', '')).strip() if pd.notna(row.get('County Description')) else None
                email = str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else None
                phone = str(row.get('Phone No.', '')).strip() if pd.notna(row.get('Phone No.')) else None
                contact_info = str(row.get('Principal Name', '')).strip() if pd.notna(row.get('Principal Name')) else None
                deis = str(row.get('DEIS (Y/N)', '')).strip().upper() or None
                school_type = str(row.get('School Type', '')).strip() if pd.notna(row.get('School Type')) else None
                school_level = str(row.get('School Level', '')).strip() if pd.notna(row.get('School Level')) else None
                enrolment_raw = row.get('Enrolment per Return')
                enrolment = int(float(enrolment_raw)) if pd.notna(enrolment_raw) and float(enrolment_raw) < 5000 else None

                # Build address from up to 4 address lines
                addr_parts = [
                    str(row.get(f'Address (Line {i})', '')).strip()
                    for i in range(1, 5)
                    if pd.notna(row.get(f'Address (Line {i})')) and str(row.get(f'Address (Line {i})', '')).strip() not in ('', 'nan')
                ]
                if county and county not in addr_parts:
                    addr_parts.append(county)
                if eircode:
                    addr_parts.append(eircode)
                address = ', '.join(addr_parts) or None

                # Prefer coordinates already present in the file
                latitude = float(row['School Latitude']) if pd.notna(row.get('School Latitude')) else None
                longitude = float(row['School Longitude']) if pd.notna(row.get('School Longitude')) else None

                # Fallback: geocode via Nominatim when coordinates are absent
                if (latitude is None or longitude is None) and eircode:
                    coords_str = convert_eircode_to_address(eircode)
                    if coords_str and ',' in coords_str:
                        parts = coords_str.split(',')
                        try:
                            latitude = float(parts[0].strip())
                            longitude = float(parts[1].strip())
                        except Exception:
                            pass

                cursor.execute('''
                    INSERT INTO schools
                    (roll_number, school_name, eircode, address, county,
                     latitude, longitude, contact_info, email, phone,
                     deis, school_type, school_level, enrolment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(roll_number) DO UPDATE SET
                        school_name  = excluded.school_name,
                        eircode      = excluded.eircode,
                        address      = excluded.address,
                        county       = excluded.county,
                        latitude     = excluded.latitude,
                        longitude    = excluded.longitude,
                        contact_info = excluded.contact_info,
                        email        = excluded.email,
                        phone        = excluded.phone,
                        deis         = excluded.deis,
                        school_type  = excluded.school_type,
                        school_level = excluded.school_level,
                        enrolment    = excluded.enrolment,
                        updated_at   = CURRENT_TIMESTAMP
                ''', (roll_number, school_name, eircode, address, county,
                      latitude, longitude, contact_info, email, phone,
                      deis, school_type, school_level, enrolment))

                imported_count += 1

            except Exception as e:
                print(f"Error importing school row {index}: {e}")
                continue

        conn.commit()
        conn.close()
        print(f"✓ Successfully imported {imported_count} school records")
        return imported_count

    except Exception as e:
        print(f"Error importing schools from {file_path}: {e}")
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
    """Get all schools from database."""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, roll_number, school_name, eircode, address, county,
               latitude, longitude, contact_info, email, phone,
               deis, school_type, school_level, enrolment,
               status, created_at
        FROM schools
        ORDER BY school_name ASC
    ''')
    schools = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return schools


def get_school_locations():
    """Get all schools with valid coordinates for map display."""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, school_name, eircode, address, county,
               latitude, longitude, email, phone
        FROM schools
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY school_name ASC
    ''')
    locations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return locations


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


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_MAX_DISTANCE_KM = 25
_ENROLMENT_CAP = 600  # realistic 99th-percentile cap for normalization


def score_company_school(company: dict, school: dict) -> dict | None:
    """
    Score one (company, school) pair. Returns a score dict or None if
    coordinates are unavailable and there's no explicit preference match.

    Score components (weights):
      - Explicit preferred-school name match → 100 (override)
      - Distance 0-25km                      → 60%
      - Preferred-area / county match        → 20%
      - DEIS status                          → 10%
      - Enrolment (normalized to 600)        → 10%
    """
    pref = (company.get('preferred_school') or '').strip().lower()
    sname = (school.get('school_name') or '').strip().lower()

    # Explicit preferred-school override
    if pref and (pref == sname or pref in sname or sname in pref):
        clat, clon = company.get('latitude'), company.get('longitude')
        slat, slon = school.get('latitude'), school.get('longitude')
        dist_km = round(haversine(clat, clon, slat, slon), 2) if all(v is not None for v in (clat, clon, slat, slon)) else None
        return {
            'total_score': 100,
            'distance_km': dist_km,
            'distance_score': None,
            'area_score': None,
            'deis_score': None,
            'enrolment_score': None,
            'is_preferred_match': True,
            'outside_radius': (dist_km is not None and dist_km > _MAX_DISTANCE_KM),
        }

    clat, clon = company.get('latitude'), company.get('longitude')
    slat, slon = school.get('latitude'), school.get('longitude')
    if any(v is None for v in (clat, clon, slat, slon)):
        return None

    dist_km = haversine(clat, clon, slat, slon)
    distance_score = max(0.0, 100.0 * (1 - dist_km / _MAX_DISTANCE_KM))

    area = (company.get('preferred_area') or '').strip().lower()
    county = (school.get('county') or '').strip().lower()
    addr = (school.get('address') or '').strip().lower()
    area_score = 100 if area and (area in county or area in addr or county in area) else 0

    deis_score = 100 if (school.get('deis') or '').upper() == 'Y' else 0

    enrolment = school.get('enrolment') or 0
    enrolment_score = min(100, round(100 * enrolment / _ENROLMENT_CAP))

    total = (0.60 * distance_score + 0.20 * area_score +
             0.10 * deis_score + 0.10 * enrolment_score)

    return {
        'total_score': round(total, 1),
        'distance_km': round(dist_km, 2),
        'distance_score': round(distance_score, 1),
        'area_score': area_score,
        'deis_score': deis_score,
        'enrolment_score': enrolment_score,
        'is_preferred_match': False,
        'outside_radius': dist_km > _MAX_DISTANCE_KM,
    }


def get_matches_for_company(company_id: int, max_km: float = _MAX_DISTANCE_KM, top_n: int = 10) -> list:
    """
    Return a ranked list of (school_dict, score_dict) for one company.
    Rural fallback: if fewer than 5 schools are within max_km, extend the
    search to all schools sorted by distance, flagging them as outside radius.
    """
    companies = get_all_companies()
    company = next((c for c in companies if c['id'] == company_id), None)
    if company is None:
        return []

    schools = get_all_schools()

    scored = []
    for school in schools:
        result = score_company_school(company, school)
        if result is not None:
            scored.append((school, result))

    preferred_hits = [(s, r) for s, r in scored if r['is_preferred_match']]
    normal = [(s, r) for s, r in scored if not r['is_preferred_match']]

    within = [(s, r) for s, r in normal if not r['outside_radius']]
    within.sort(key=lambda x: x[1]['total_score'], reverse=True)

    if preferred_hits:
        return preferred_hits + within[:top_n - len(preferred_hits)]

    # Rural fallback: extend if fewer than 5 within radius
    if len(within) < 5:
        outside = [(s, r) for s, r in normal if r['outside_radius']]
        outside.sort(key=lambda x: x[1]['distance_km'])
        return (within + outside)[:top_n]

    return within[:top_n]


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
        
        return render_template('welcome.html', 
                             company_count=len(companies),
                             school_count=len(schools),
                             location_count=len(locations),
                             active_count=active_count,
                             active_schools=active_schools)
    
    except Exception as e:
        return render_template('welcome.html', 
                             company_count=0,
                             school_count=0,
                             location_count=0,
                             active_count=0,
                             active_schools=0,
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
        school_locations = get_school_locations()

        if not schools:
            return render_template('school.html',
                                   message='No school data found. Please add school Excel or CSV files to the "data" folder.')

        # Build table (drop internal cols like lat/lon/id)
        school_df = pd.DataFrame(schools)
        display_cols = ['roll_number', 'school_name', 'eircode', 'address', 'county',
                        'email', 'phone', 'contact_info', 'status']
        existing_cols = [c for c in display_cols if c in school_df.columns]
        school_df = school_df[existing_cols].fillna('')
        html_table = school_df.to_html(classes='data-table', index=False, escape=False)

        location_data = [
            {'lat': loc['latitude'], 'lon': loc['longitude'],
             'name': loc['school_name'], 'eircode': loc.get('eircode', '')}
            for loc in school_locations
            if loc.get('latitude') and loc.get('longitude')
        ]

        return render_template('school.html',
                               table=html_table,
                               total_rows=len(school_df),
                               locations=location_data,
                               has_locations=len(location_data) > 0)

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


@app.route('/match')
def match_overview():
    """Overview: all companies with their top 3 school matches."""
    companies = get_all_companies()
    overview = []
    for company in companies:
        matches = get_matches_for_company(company['id'], top_n=3)
        overview.append({'company': company, 'matches': matches})
    return render_template('match.html', overview=overview, view='overview')


@app.route('/match/company/<int:company_id>')
def match_detail(company_id):
    """Detail: top 10 matches for one company."""
    companies = get_all_companies()
    company = next((c for c in companies if c['id'] == company_id), None)
    if company is None:
        return render_template('match.html', error='Company not found', view='detail',
                               company=None, matches=[])
    matches = get_matches_for_company(company_id, top_n=10)
    return render_template('match.html', company=company, matches=matches, view='detail')


if __name__ == '__main__':
    app.run(debug=True)
