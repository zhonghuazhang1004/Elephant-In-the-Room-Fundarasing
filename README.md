# Company Information System

A Flask web application that displays company information with GPS coordinates on an interactive map.

## Features

- 📍 **GPS Coordinate Conversion**: Automatically converts Irish Eircodes to latitude/longitude coordinates
- 🗺️ **Interactive Map**: Visualizes all company locations on a beautiful Leaflet.js map
- 📊 **Multiple File Support**: Reads all Excel (.xlsx, .xls) and CSV files from the `data` folder
- 🎨 **Beautiful Display**: Shows data in a formatted table with highlighted coordinate column
- ⚡ **Batch Processing**: Processes all Eircodes with progress tracking
- 📈 **Statistics**: Shows record count and file information

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Your Data Files

Place your Excel or CSV files containing company data into the **`data`** folder:

```
Elepahnt in the Room/
│
├── data/                 ← Put your Excel/CSV files here
│   ├── companies.xlsx
│   ├── addresses.csv
│   └── ...
├── main.py
├── requirements.txt
└── ...
```

**Note:** Your file should have a column named "Eircode" or "Eir Code" (case-insensitive) for location mapping.

### 3. Run the Application

```bash
python main.py
```

The application will start on `http://127.0.0.1:5000`

### 4. View Company Information

Navigate to: `http://127.0.0.1:5000/company`

The page will automatically:
- Scan the `data` folder for all Excel and CSV files
- Detect the Eircode column
- Convert each Eircode to GPS coordinates via API
- Display all company data with location information
- Show an interactive map with all company locations marked

## How It Works

1. **Place files in the `data` folder** - Files should contain company data with Eircode column
2. **Visit the webpage** - Go to `/company` route
3. **Automatic conversion** - The system:
   - Detects the Eircode column automatically
   - Calls the geocoding API for each code
   - Converts Eircodes to latitude/longitude coordinates
   - Adds a "Coordinates" column to the data
4. **View results** - All company data is displayed with coordinates
5. **Interactive map** - Scroll down to see all locations plotted on a map
6. **Click markers** - Click on map markers to see detailed company information

## Output Format

### Table Data
The coordinates are stored in format: `latitude, longitude`

Example:
| Company Name | Eircode | Coordinates |
|--------------|---------|-------------|
| ABC Ltd | W23 DHR0 | 53.2189, -6.6756 |
| XYZ Corp | D02 AF30 | 53.3498, -6.2603 |

### Interactive Map
- All company locations are shown as markers on the map
- Click any marker to see the full company data
- Map automatically adjusts to show all locations
- Zoom and pan freely

## Use Cases

GPS coordinates can be used for:
- **Distance calculation** between company locations
- **Route planning** and optimization
- **Geographic analysis** and clustering
- **Integration with mapping services** (Google Maps, Mapbox, etc.)
- **Location-based services** and apps
- **Delivery logistics** and planning
- **Market analysis** based on location

## API Information

The application uses OpenStreetMap Nominatim API for geocoding with Google Maps as fallback.

**⚠️ Important Limitation:** OpenStreetMap has limited coverage for Irish Eircodes. Many Eircodes may not return coordinates because:
- Eircode is a relatively new postal code system (introduced in 2015)
- OpenStreetMap's database may not have complete Eircode coverage
- Some rural or new addresses may not be indexed

**For Production Use - Recommended Alternatives:**

1. **Official Eircode API** (Most Accurate)
   - Register at [eircode.ie](https://www.eircode.ie/)
   - Provides 100% accurate coordinates for all valid Eircodes
   - May require subscription or licensing

2. **Google Maps Geocoding API** (High Accuracy)
   - Sign up at [Google Cloud Platform](https://cloud.google.com/maps-platform)
   - Excellent coverage for Ireland
   - Free tier available (up to 40,000 requests/month)
   - Requires API key and billing setup

3. **Mapbox Geocoding API** (Good Alternative)
   - Sign up at [mapbox.com](https://www.mapbox.com/)
   - Good coverage and competitive pricing
   - Free tier available

**Rate Limiting:** The app includes a 0.2-second delay between API calls to avoid rate limiting with free services.

**Accuracy:** Coordinates are accurate to street level for most Irish Eircodes.

## File Structure

```
Elepahnt in the Room/
│
├── main.py                # Main Flask application with coordinate conversion
├── config.py              # Configuration file for API keys
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── data/                 # 📁 Place your Excel/CSV files here
│   └── (your files with Eircode column)
├── templates/
│   ├── welcome.html      # Welcome page with navigation
│   └── company.html      # Company information with coordinates and map
└── README.md             # This file
```

## Supported File Formats

- Excel (.xlsx, .xls)
- CSV (.csv)

## Example Data Format

Your Excel/CSV file should have a column like this:

| Company Name | Eircode | Other Data |
|--------------|---------|------------|
| ABC Ltd | W23 DHR0 | ... |
| XYZ Corp | D02 AF30 | ... |

The system will add a "Coordinates" column:

| Company Name | Eircode | Other Data | Coordinates |
|--------------|---------|------------|-------------|
| ABC Ltd | W23 DHR0 | ... | 53.2189, -6.6756 |
| XYZ Corp | D02 AF30 | ... | 53.3498, -6.2603 |

## Notes

- **Column Detection**: The system looks for columns containing "eircode" (case-insensitive)
- **Processing Time**: Conversion takes time (~0.2 seconds per Eircode). For 100 Eircodes, expect ~20 seconds
- **Progress Tracking**: Check the terminal/console for conversion progress
- **Empty Cells**: Empty Eircodes result in empty coordinate cells
- **Map Interaction**: Click markers to see details, scroll to zoom, drag to pan
- **Coordinate Format**: Latitude, Longitude (WGS84 standard)
- **Refresh**: Add/remove files from the `data` folder and refresh the page

## Troubleshooting

### No coordinates showing?
- Make sure your file has a column named "Eircode" or similar
- Check that Eircodes are in the correct format (e.g., W23 DHR0)
- Verify you have an internet connection for API calls

### Slow conversion?
- This is normal - each Eircode requires an API call
- The 0.2s delay prevents rate limiting
- For faster processing, you could reduce the delay (but risk being rate-limited)

### Map not loading?
- Ensure you have an internet connection (map tiles are loaded online)
- Check browser console for JavaScript errors
- Try refreshing the page

### ImportError: No module named 'flask' or 'requests'
- Install dependencies: `pip install -r requirements.txt`

## Export Options

To use coordinates in other applications:
- **Google Maps**: Copy coordinates and paste into search
- **Excel**: Copy the coordinates column
- **GIS Software**: Export as CSV and import
- **Custom Apps**: Use the lat/lon values directly

## License

This project is open source and available under the MIT License.


oracle cloud credentials
emmail address:mario.zhangzhonghua@gmail.com
pws:Fmr_Eitr_2026