from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import pandas as pd
import os
import glob
import math
import requests
import time
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

_nominatim_last_call = 0.0


def _nominatim_request(params):
    """Single Nominatim request with 1 RPS rate limiting. params is a dict."""
    global _nominatim_last_call
    elapsed = time.time() - _nominatim_last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    base_params = {'format': 'jsonv2', 'limit': 5, 'countrycodes': 'ie'}
    base_params.update(params)
    response = requests.get(
        'https://nominatim.openstreetmap.org/search',
        params=base_params,
        headers={'User-Agent': 'ElephantFundraising/1.0'},
        timeout=10,
    )
    _nominatim_last_call = time.time()
    if response.status_code == 200:
        return response.json()
    return []


def _ireland_coords(results):
    """Extract first valid Irish (lat, lon) from a Nominatim result list."""
    for r in results:
        try:
            lat, lon = float(r['lat']), float(r['lon'])
            if 51.4 <= lat <= 55.4 and -10.7 <= lon <= -5.4:
                return lat, lon
        except (KeyError, ValueError):
            continue
    return None, None


def geocode_location(eircode=None, address=None):
    """
    Resolve coordinates for a manually entered record.
    Tries in order:
      1. Nominatim free-text address search (if address given)
      2. Nominatim postalcode search (if eircode given)
    Returns (lat, lon) floats or raises ValueError if nothing found.
    """
    if address and str(address).strip():
        try:
            results = _nominatim_request({'q': str(address).strip()})
            lat, lon = _ireland_coords(results)
            if lat is not None:
                return lat, lon
        except Exception as e:
            print(f"Nominatim address error for {address}: {e}")

    eircode_str = str(eircode).strip().upper() if eircode else ''
    if eircode_str:
        if len(eircode_str) == 7 and ' ' not in eircode_str:
            eircode_formatted = eircode_str[:3] + ' ' + eircode_str[3:]
        else:
            eircode_formatted = eircode_str
        try:
            results = _nominatim_request({'postalcode': eircode_formatted})
            lat, lon = _ireland_coords(results)
            if lat is not None:
                return lat, lon
        except Exception as e:
            print(f"Nominatim postalcode error for {eircode}: {e}")

    raise ValueError(f"Could not find coordinates for address='{address}', eircode='{eircode}'")


def convert_eircode_to_address(eircode):
    """Convert an Eircode to 'lat, lon' string for batch import. Returns '' if not found."""
    if pd.isna(eircode) or str(eircode).strip() == '':
        return ''
    try:
        lat, lon = geocode_location(eircode=eircode)
        return f"{lat}, {lon}"
    except ValueError:
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
        
        # Get company and school locations for map
        company_locations = []
        for loc in locations:
            if loc.get('latitude') and loc.get('longitude'):
                company_locations.append({
                    'name': loc.get('company_name', ''),
                    'lat': float(loc.get('latitude')),
                    'lon': float(loc.get('longitude')),
                    'eircode': loc.get('eircode', '')
                })
        
        school_locations = []
        for school in schools:
            if school.get('latitude') and school.get('longitude'):
                school_locations.append({
                    'name': school.get('school_name', ''),
                    'lat': float(school.get('latitude')),
                    'lon': float(school.get('longitude')),
                    'address': school.get('address', '')
                })
        
        print(f"DEBUG: Company locations count: {len(company_locations)}")
        print(f"DEBUG: School locations count: {len(school_locations)}")
        print(f"DEBUG: Total locations from DB: {len(locations)}")
        print(f"DEBUG: Sample company location: {company_locations[0] if company_locations else 'None'}")
        
        return render_template('welcome.html', 
                             company_count=len(companies),
                             school_count=len(schools),
                             location_count=len(locations),
                             active_count=active_count,
                             active_schools=active_schools,
                             engaged_corps_count=engaged_corps_count,
                             engaged_schools_count=engaged_schools_count,
                             county_matches=county_matches,
                             company_locations=company_locations,
                             school_locations=school_locations)
    
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
                             company_locations=[],
                             school_locations=[],
                             message=f'Error loading data: {str(e)}')


@app.route('/reference')
def reference():
    """Reference page with team member files"""
    try:
        # Get all team files
        team_files_list = get_all_team_files()
        
        return render_template('reference.html', 
                             team_files=team_files_list)
    
    except Exception as e:
        return render_template('reference.html', 
                             team_files=[],
                             message=f'Error loading files: {str(e)}')


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
    """Company Information page with map visualization - merged with schools"""
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
        schools = get_all_schools()
        company_locations = get_company_locations()
        
        # Convert company data to DataFrame for HTML table
        company_df = None
        company_location_data = []
        school_location_data = []
        company_total_rows = len(companies)
        school_total_rows = len(schools)
        
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
            
            # Extract location data for map (companies)
            for loc in company_locations:
                if loc.get('latitude') and loc.get('longitude'):
                    company_location_data.append({
                        'lat': loc['latitude'],
                        'lon': loc['longitude'],
                        'name': loc.get('company_name', ''),
                        'type': 'company'
                    })
                else:
                    company_location_data.append(None)
        
        # Extract school location data
        if schools:
            for school in schools:
                if school.get('latitude') and school.get('longitude'):
                    school_location_data.append({
                        'lat': school['latitude'],
                        'lon': school['longitude'],
                        'name': school.get('school_name', ''),
                        'type': 'school'
                    })
        
        # Convert to HTML
        company_html = company_df.to_html(classes='data-table', index=False, escape=False) if company_df is not None else ''
        
        # Also prepare school table
        school_df = None
        school_html = ''
        if schools:
            school_df = pd.DataFrame(schools)
            school_df = school_df.fillna('')
            school_html = school_df.to_html(classes='data-table', index=False, escape=False)
        
        return render_template('company.html', 
                             company_table=company_html,
                             school_table=school_html,
                             company_total_rows=company_total_rows,
                             school_total_rows=school_total_rows,
                             has_addresses=len(company_location_data) > 0,
                             company_locations=company_location_data,
                             school_locations=school_location_data)
    
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
    
    # Get all team files
    team_files_list = get_all_team_files()
    
    return {
        'companies': companies,
        'schools': schools,
        'company_count': len(companies),
        'school_count': len(schools),
        'location_count': len(locations),
        'team_files': team_files_list
    }


@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for database management"""
    return render_template('admin.html', **get_admin_stats())


@app.route('/admin/files')
def admin_files():
    """Admin Team Files management page"""
    return render_template('admin_files.html', **get_admin_stats())


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
        
        try:
            latitude, longitude = geocode_location(eircode=eircode, address=address)
        except ValueError as e:
            return render_template('admin.html',
                                   message=f'✗ Location not found: {e}. Please check the address or Eircode.',
                                   success=False,
                                   **get_admin_stats())

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
        eircode = request.form.get('eircode') or None
        address = request.form.get('address')
        email = request.form.get('email')
        phone = request.form.get('phone')
        contact_info = request.form.get('contact_info')
        status = request.form.get('status', 'active')

        try:
            latitude, longitude = geocode_location(eircode=eircode, address=address)
        except ValueError as e:
            return render_template('admin.html',
                                   message=f'✗ Location not found: {e}. Please check the address or Eircode.',
                                   success=False,
                                   **get_admin_stats())

        if school_id:
            cursor.execute('''
                UPDATE schools
                SET school_name = ?, eircode = ?, address = ?, email = ?, phone = ?,
                    contact_info = ?, latitude = ?, longitude = ?,
                    status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (school_name, eircode, address, email, phone,
                  contact_info, latitude, longitude, status, school_id))
        else:
            cursor.execute('''
                INSERT INTO schools
                (school_name, eircode, address, email, phone, contact_info,
                 latitude, longitude, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (school_name, eircode, address, email, phone,
                  contact_info, latitude, longitude, status))
        
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
    # Define 7 team members
    member_names = ['Barrett,Leanne', 'Adams,Conor', 'Harevice,Anzelina', 'Mcmorrow,Maeve', "O'Donoghue,Fergus", 'Podynihlazov,Oleksandr', 'Zhonghua,Zhang']
    
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


def get_all_team_files():
    """Get all team files from database"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, member_name, filename, original_filename, file_path, file_size, file_type, uploaded_at
            FROM team_files
            ORDER BY uploaded_at DESC
        ''')
        
        files = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return files
    except Exception as e:
        print(f"Error getting team files: {e}")
        return []


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


@app.route('/team-files/upload', methods=['POST'])
def upload_file():
    """Upload a file for a team member (from admin panel)"""
    try:
        if 'file' not in request.files:
            return redirect(url_for('admin_dashboard', error='No file selected'))
        
        file = request.files['file']
        member_name = request.form.get('member_name')
        
        if file.filename == '':
            return redirect(url_for('admin_dashboard', error='No file selected'))
        
        if not member_name:
            return redirect(url_for('admin_dashboard', error='Please select a team member'))
        
        if not allowed_file(file.filename):
            return redirect(url_for('admin_dashboard', error='File type not allowed'))
        
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
        
        return redirect(url_for('admin_dashboard', message=f'✓ File "{original_filename}" uploaded successfully!'))
    
    except Exception as e:
        return redirect(url_for('admin_dashboard', error=f'Error uploading file: {str(e)}'))


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


@app.route('/team-files/delete/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    """Delete a file"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM team_files WHERE id = ?', (file_id,))
        file_record = cursor.fetchone()
        
        if not file_record:
            conn.close()
            return redirect(url_for('admin_dashboard', error='File not found'))
        
        file_dict = dict(file_record)
        
        # Delete file from filesystem
        if os.path.exists(file_dict['file_path']):
            os.remove(file_dict['file_path'])
        
        # Delete from database
        cursor.execute('DELETE FROM team_files WHERE id = ?', (file_id,))
        conn.commit()
        conn.close()
        
        return redirect(url_for('admin_dashboard', message='✓ File deleted successfully!'))
    
    except Exception as e:
        return redirect(url_for('admin_dashboard', error=f'Error deleting file: {str(e)}'))


@app.route('/debug-data')
def debug_data():
    """Debug route to check database data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all companies with coordinates
        cursor.execute('SELECT company_name, eircode, latitude, longitude FROM companies WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
        companies_with_coords = cursor.fetchall()
        
        # Get all schools with coordinates
        cursor.execute('SELECT school_name, address, latitude, longitude FROM schools WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
        schools_with_coords = cursor.fetchall()
        
        # Get all companies (total)
        cursor.execute('SELECT COUNT(*) as count FROM companies')
        total_companies = cursor.fetchone()['count']
        
        # Get all schools (total)
        cursor.execute('SELECT COUNT(*) as count FROM schools')
        total_schools = cursor.fetchone()['count']
        
        conn.close()
        
        return f"""
        <h1>Database Debug Info</h1>
        <h2>Companies</h2>
        <p>Total: {total_companies}</p>
        <p>With coordinates: {len(companies_with_coords)}</p>
        <ul>
            {''.join(f'<li>{c["company_name"]} - Lat: {c["latitude"]}, Lon: {c["longitude"]}</li>' for c in companies_with_coords)}
        </ul>
        
        <h2>Schools</h2>
        <p>Total: {total_schools}</p>
        <p>With coordinates: {len(schools_with_coords)}</p>
        <ul>
            {''.join(f'<li>{s["school_name"]} - Lat: {s["latitude"]}, Lon: {s["longitude"]}</li>' for s in schools_with_coords)}
        </ul>
        """
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>"


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
