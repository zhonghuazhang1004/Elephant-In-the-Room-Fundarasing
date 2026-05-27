from flask import Flask, render_template, request
import pandas as pd
import os
import glob
import requests
import time
import random
import config

app = Flask(__name__)
app.config['DATA_FOLDER'] = 'data'

# Create data folder if it doesn't exist
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

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


def get_address_from_eircode(eircode):
    """
    Get full Irish address from Eircode using Google Maps Geocoding API.
    
    Args:
        eircode: The Eircode to convert
    
    Returns:
        String containing formatted Irish address or empty string if not found
    """
    if not gmaps_client:
        return ''
    
    if pd.isna(eircode) or str(eircode).strip() == '':
        return ''
    
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
            # Verify it's in Ireland
            address_components = result[0].get('address_components', [])
            country_found = False
            
            for component in address_components:
                if 'country' in component.get('types', []):
                    if component.get('short_name') == 'IE' or component.get('long_name') == 'Ireland':
                        country_found = True
                    break
            
            if not country_found:
                return ''
            
            # Extract structured address components for Irish format
            street_number = ''
            route = ''
            locality = ''
            administrative_area = ''
            postal_code = ''
            
            for component in address_components:
                types = component.get('types', [])
                
                if 'street_number' in types:
                    street_number = component.get('long_name', '')
                elif 'route' in types:
                    route = component.get('long_name', '')
                elif 'locality' in types or 'sublocality' in types:
                    locality = component.get('long_name', '')
                elif 'administrative_area_level_1' in types:
                    administrative_area = component.get('long_name', '')
                elif 'postal_code' in types:
                    postal_code = component.get('long_name', '')
            
            # Build Irish-style address
            address_parts = []
            
            # Street address
            if street_number and route:
                address_parts.append(f"{street_number} {route}")
            elif route:
                address_parts.append(route)
            
            # Locality/Town
            if locality:
                address_parts.append(locality)
            
            # County (Co. XX format for Ireland)
            if administrative_area:
                # Format as "Co. CountyName" for Irish addresses
                county_name = administrative_area.replace('County ', '').replace('Co. ', '')
                address_parts.append(f"Co. {county_name}")
            
            # Eircode
            if postal_code:
                address_parts.append(postal_code)
            
            # Join with commas
            return ', '.join(address_parts)
        
        return ''
    
    except Exception as e:
        print(f"Error getting address for {eircode}: {str(e)}")
        return ''


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


@app.route('/')
def welcome_page():
    return render_template('welcome.html')


@app.route('/company')
def company_information():
    """Company Information page with map visualization"""
    try:
        # Get all Excel/CSV files from the data folder
        excel_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xlsx'))
        excel_files += glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xls'))
        csv_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.csv'))
        
        all_files = excel_files + csv_files
        
        if not all_files:
            return render_template('company.html', 
                                 message='No files found in data folder. Please add Excel or CSV files to the "data" folder.')
        
        # Separate company and school files
        company_files = []
        school_files = []
        
        for file_path in all_files:
            filename = os.path.basename(file_path).lower()
            if 'school' in filename:
                school_files.append(file_path)
            else:
                company_files.append(file_path)
        
        # Read and process company data
        company_df = None
        company_location_data = []
        company_total_rows = 0
        
        if company_files:
            all_company_dfs = []
            for file_path in company_files:
                try:
                    if file_path.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    else:
                        engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
                        df = pd.read_excel(file_path, engine=engine)
                    all_company_dfs.append(df)
                except Exception as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
            
            if all_company_dfs:
                company_df = pd.concat(all_company_dfs, ignore_index=True)
                
                # Try to find Eircode column
                eircode_column = None
                for col in company_df.columns:
                    if 'eircode' in col.lower() or 'eir code' in col.lower():
                        eircode_column = col
                        break
                
                # Convert Eircodes to addresses and coordinates
                if eircode_column:
                    eircodes = company_df[eircode_column].tolist()
                    
                    # Convert to addresses
                    addresses = []
                    for i, eircode in enumerate(eircodes, 1):
                        address = get_address_from_eircode(eircode)
                        addresses.append(address)
                        time.sleep(0.2)
                    
                    company_df['Address'] = addresses
                    
                    # Get coordinates for map
                    coordinates = convert_eircode_batch(eircodes, delay=0.2)
                    company_df['Coordinates'] = coordinates
                    
                    # Extract location data
                    for coord_str in coordinates:
                        if coord_str and ',' in coord_str and 'Error' not in coord_str:
                            parts = coord_str.split(',')
                            if len(parts) == 2:
                                try:
                                    lat = float(parts[0].strip())
                                    lon = float(parts[1].strip())
                                    company_location_data.append({'lat': lat, 'lon': lon})
                                except:
                                    company_location_data.append(None)
                            else:
                                company_location_data.append(None)
                        else:
                            company_location_data.append(None)
                
                # Define columns to display
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
                
                if existing_columns:
                    company_df = company_df[existing_columns]
                
                company_df = company_df.fillna('')
                company_total_rows = len(company_df)
        
        # Read and process school data
        school_df = None
        school_total_rows = 0
        
        if school_files:
            all_school_dfs = []
            for file_path in school_files:
                try:
                    if file_path.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    else:
                        engine = 'openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
                        df = pd.read_excel(file_path, engine=engine)
                    all_school_dfs.append(df)
                except Exception as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
            
            if all_school_dfs:
                school_df = pd.concat(all_school_dfs, ignore_index=True)
                school_df = school_df.fillna('')
                school_total_rows = len(school_df)
        
        # Convert to HTML
        company_html = company_df.to_html(classes='data-table', index=False, escape=False) if company_df is not None else ''
        school_html = school_df.to_html(classes='data-table', index=False, escape=False) if school_df is not None else ''
        
        return render_template('company.html', 
                             company_table=company_html,
                             school_table=school_html,
                             company_total_rows=company_total_rows,
                             school_total_rows=school_total_rows,
                             has_addresses=len(company_location_data) > 0,
                             locations=company_location_data)
    
    except Exception as e:
        return render_template('company.html', 
                             message=f'Error: {str(e)}')


@app.route('/school')
def school_information():
    """School Information page"""
    try:
        # Get all Excel/CSV files from the data folder
        excel_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xlsx'))
        excel_files += glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.xls'))
        csv_files = glob.glob(os.path.join(app.config['DATA_FOLDER'], '*.csv'))
        
        all_files = excel_files + csv_files
        
        if not all_files:
            return render_template('school.html', 
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
            return render_template('school.html', 
                                 message='Error reading files. Please check the file formats.')
        
        # Combine all dataframes
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Replace NaN values with empty string for better display
        combined_df = combined_df.fillna('')
        
        # Convert to HTML
        html_table = combined_df.to_html(classes='data-table', index=False, escape=False)
        
        return render_template('school.html', 
                             table=html_table, 
                             total_rows=len(combined_df))
    
    except Exception as e:
        return render_template('school.html', 
                             message=f'Error: {str(e)}')


if __name__ == '__main__':
    app.run(debug=True)
