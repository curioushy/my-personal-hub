# Singapore HDB Resale Hunter

Exploratory project by Curious_HY. A single-page web app to help with HDB resale flat hunting in Singapore. Search any address to see resale transaction history, nearby schools (primary through university), MRT stations, bus stops, hawker centres, coffee shops, supermarkets — all on an interactive map with distance lines.

## Files

| File | Size | Description |
|---|---|---|
| `hdb-hunter.html` | ~372 KB | Main app — open this in a browser. Contains all CSS, JS, and embedded static data (179 primary schools, 158 secondary/JC, 14 polytechnics/universities/ITE, 186 MRT stations, 129 hawker centres, 606 coffee shops, 526 supermarkets, 67 shopping malls, 589 bus service names), and UI logic. |
| `hdb-resale.csv` | ~22 MB | Full HDB resale transaction dataset (227K records, Jan 2017 – present). Downloaded from data.gov.sg. **Primary data source** — parsed in-browser via PapaParse. |
| `hdb-resale-data.js` | ~3.6 MB | Compact fallback (58K records, Jan 2024+). Used only if CSV is absent. Pre-processed into indexed JS arrays for fast loading. |
| `bus-stops-data.js` | ~621 KB | 4,976 Singapore bus stops with coordinates and bus service numbers per stop. Sourced from LTA DataMall + busrouter.sg. Loaded as a separate script. |
| `README.md` | This file | App documentation. |

## How to Use

1. Open `hdb-hunter.html` in any modern browser (Chrome, Firefox, Edge, Safari).
2. Type an address or postal code in the "Property Address" search bar.
3. Select from autocomplete results.
4. Use the tab bar to switch between views:
   - **Transactions** — Block profile (unit types, lease, price ranges) + resale comparables with sorting, filtering, PSF trend sparkline, and CSV export. Three scopes: This Block / Same Street / Same Town.
   - **Schools** — Primary schools (P1 zones), secondary schools, JCs, polytechnics, ITE, and universities with distance.
   - **Transport** — MRT stations (2km) + bus stops (500m) with bus service numbers and route popups. All pins shown on map.
   - **F&B** — Hawker centres (2km) + coffee shops/eating houses (1km).
   - **Others** — Shopping malls (5km) + supermarkets (2km).
   - **PropertyGuru** — Opens PropertyGuru search pre-filled with the address.
5. Click any item in the sidebar — or any pin on the map — to see a popup with name and distance. Sidebar clicks also draw a dotted distance line.

## Features
- **Distance summary card** — at-a-glance nearest MRT, hawker, school, mall shown below the address.
- **Shortlist/bookmarks** — star addresses to save them. Click "saved" count to view and jump to any bookmarked address.
- **Search history** — focus the empty search box to see last 10 searches. Click to re-load instantly.
- **Map layer toggles** — bottom-left of map. Tick to show all MRT/bus/school/hawker/mall pins at once. Auto-toggles by tab. All pins are clickable with popups showing name, distance, and (for bus stops) service numbers.
- **Dark mode** — moon icon in the tab bar. Preference saved between sessions.
- **Print** — Print button generates a printable summary (hides UI chrome, expands sidebar).
- **CSV export** — export filtered/sorted transaction comps as a CSV file.

## Data Sources

| Dataset | Source | Records | Update Frequency |
|---|---|---|---|
| HDB Resale Transactions | [data.gov.sg](https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view) (HDB) | 227K+ | Monthly |
| MRT Station Exits | [data.gov.sg](https://data.gov.sg/datasets/d_b39d3a0871985372d7e1637193335da5/view) (LTA) | 186 stations | As needed |
| Hawker Centres | [data.gov.sg](https://data.gov.sg/datasets/d_4a086da0a5553be1d89383cd90d07ecd/view) (NEA) | 129 centres | As needed |
| Bus Stops | [LTA DataMall](https://datamall.lta.gov.sg/) via community mirror | 4,976 stops | As needed |
| Supermarkets | [data.gov.sg](https://data.gov.sg/datasets/d_cac2c32f01960a3ad7202a99c27268a0/view) (SFA) | 526 outlets | As needed |
| Primary Schools | [data.gov.sg](https://data.gov.sg) (MOE) + OneMap geocoding | 179 schools | Annually |
| Secondary Schools & JCs | [data.gov.sg](https://data.gov.sg/datasets/d_688b934f82c1059ed0a6993d2a829089/view) (MOE) + OneMap geocoding | 158 schools | Annually |
| Polytechnics, ITE & Universities | Curated list + OneMap geocoding | 14 institutions | As needed |
| Coffee Shops / Eating Houses | [data.gov.sg](https://data.gov.sg/datasets/d_1f0313499a17075d13aae6ed3e825bc6/view) (SFA) | 606 establishments | As needed |
| Shopping Malls | Curated list (67 major malls) + OneMap geocoding | 67 malls | As needed |
| Bus Services (route names) | [busrouter.sg](https://busrouter.sg/) | 589 services | As needed |
| Map Tiles | [OneMap](https://www.onemap.gov.sg/) (SLA) | — | Live |
| Address Search | [OneMap Search API](https://www.onemap.gov.sg/) (no auth required) | — | Live |

## Refreshing Data

### HDB Resale Transactions (recommended: monthly)
Click **Refresh DB** in the app tab bar, or manually:
1. Go to https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view
2. Click "Download CSV"
3. Save as `hdb-resale.csv` in this folder (overwrite the old one)
4. Reload the app

### Other Datasets
MRT stations, hawker centres, and supermarkets are embedded in the HTML as static JS arrays. Schools are also embedded. Bus stops are in `bus-stops-data.js`. These change infrequently and don't need regular updates. To refresh, re-download the GeoJSON from data.gov.sg and re-process.

## Architecture

Single HTML file, no build tools, no backend server. All data is either embedded or loaded from local files in the same folder. The app works from `file://` protocol — just double-click the HTML.

### APIs Used at Runtime
- **OneMap Search** (no auth): Address autocomplete and geocoding.
- **OneMap Auth** (auto-login): Token for authenticated features (currently unused since Themes API was deprecated; credentials are embedded for future use).
- **OneMap Geocode** (no auth): Geocoding comp blocks when clicked (click-to-map feature).

### Key Technical Details
- **Postal sector → HDB town mapping**: A static lookup table maps the first 2 digits of Singapore postal codes to HDB planning area towns. Used when the address text doesn't contain a recognizable town name (e.g., "Eunos Road 5" → sector 40 → GEYLANG).
- **Street name normalization**: OneMap returns full names ("EUNOS ROAD 5") while HDB dataset uses abbreviations ("EUNOS RD 5"). The normalizer converts ROAD→RD, STREET→ST, AVENUE→AVE, etc.
- **Haversine distance**: All "within X km" calculations use straight-line haversine distance.
- **PapaParse**: Parses the 22MB CSV in-browser in ~2-3 seconds.
- **Leaflet.js**: Map rendering with OneMap tile layer.

## Data.gov.sg API Key
The app includes a data.gov.sg API key for the Refresh DB feature. Rate limits: 4 calls/10s without key, 20/10s with production key. Key is passed via `x-api-key` header.

## OneMap Credentials
Auto-login is configured with embedded credentials. The OneMap token expires every 3 days and is refreshed on each page load. Currently only used for geocoding comp blocks on click.
