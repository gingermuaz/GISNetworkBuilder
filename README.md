# 🌍 GIS Network Builder

GIS Network Builder is a modular, high-performance desktop GIS workstation built with Python. It is specifically designed for councils, local authorities, and civil engineers to digitise urban assets, model road networks, and perform advanced spatial analysis.

## 🚀 Features

### 🛠️ Advanced Digitising & UI
1. **Modern Enterprise UI**: Built with CustomTkinter, featuring a native dark theme and rounded, high-end design elements.
2. **Automated Data Import**: Pull real-world drivable streets from OpenStreetMap around any address, with road names, classes, speed limits and one-way streets.
3. **Standardised Asset Management**: Dropdowns for rapid, error-free entry of standard council assets (Streetlights, Potholes, Drains, Manhole Covers, Bus Stops and more), road classes and road directions.
4. **Intelligent Snapping**: An adjustable tolerance (in metres) snaps new clicks to the nearest asset point, line vertex or polygon corner, or part-way along an existing road, so digitised networks connect properly.
5. **Undo**: Ctrl+Z undoes the last shape you added or deleted.

### 🧠 Network & Spatial Analysis
1. **Real-World Routing**: Calculates the fastest path using travel time (length ÷ speed limit) rather than just physical distance. Respects one-way streets and treats line ends, T-junctions and shared vertices as junctions.
2. **Time-Based Isochrones**: Visualise service coverage areas based on a travel-time budget (e.g., 5-minute response zones).
3. **Spatial Geofencing**: Run "Select by Location" queries to find all assets and roads inside or crossing a zone.
4. **Choropleth Mapping**: Colour-code zones by any numeric attribute.

### 📊 Data Visualisation & Export
1. **Custom Map Layers**: Switch between Google Maps, Google Satellite, Google Hybrid and OpenStreetMap base maps.
2. **Interactive Web Export**: Generate standalone HTML maps (OpenStreetMap background) with interactive popups and a Point Density Heatmap.
3. **Flexible Workspaces**: Save entire sessions, including custom colours and attributes, to JSON Project Workspaces.
4. **Industry Standard I/O**: Load Shapefile, KML and GeoJSON; export to Shapefile (.shp) for CAD/GIS or CSV for Microsoft Excel.

## 📖 Usage Guide

The left-hand panel has three tabs: **Draw**, **Tools** and **Layers**.

### 1. Drawing and Editing
- **Draw shapes**: On the Draw tab, choose 📍 Draw Point, 📏 Draw Line or ⬡ Draw Polygon, then left-click on the map. For lines and polygons, click ✓ Finish Line or ✓ Finish Polygon to complete the shape.
- **Snapping**: Set the Snapping Tolerance slider on the Layers tab (0–50 m; 0 turns snapping off). Clicks snap to the nearest existing point or vertex, or onto an existing road, so a new road started part-way along another one becomes a T-junction. Clicking an existing point marker while drawing uses its exact position.
- **Crossroads**: Roads that simply cross without a shared vertex are *not* joined, because they could be a bridge or an underpass. To make a crossroads, click on the other road while drawing so the new road gets a vertex on it.
- **One-way streets**: Click a road and set its Direction to "One-Way (A to B)" (A = the first point drawn) or "One-Way (B to A)". One-way roads show an arrowhead in the direction of travel, and routing and isochrones follow it.
- **Edit data**: Click any shape to open the Dynamic Editor. Here you can add custom fields, change values, pick a custom colour or delete the shape. A road's `Speed` (mph) and `Length_m` are used for routing.
- **Undo**: Click ↩️ Undo or press Ctrl+Z.

### 2. Getting a Road Network
Routing and isochrones only use the roads **in your project**. The roads on the background map are just a picture. To add roads, either:
- **Import real streets**: On the Layers tab, click 🌍 Import OSM Data and enter a place (e.g., "Moseley, Birmingham"). Drivable roads within about 1.5 km of it are downloaded. Stick to neighbourhoods rather than whole cities.
- **Draw your own**: Use 📏 Draw Line with snapping switched on so the roads join up.

### 3. Network Analysis
- **Fastest route**: On the Tools tab, click 🟢 Set Start Point and click the map, then 🔴 Set End Point and click again, then ⚡ Calculate Route. The route is drawn in purple with the estimated travel time. If the start or end point is more than 200 m from your road network, a note tells you the route uses the nearest junction instead.
- **Isochrones (service areas)**: Click ⏳ Calculate Isochrone, click a start point on the map and enter a travel-time budget in **seconds** (e.g., 300 for 5 minutes). Reachable roads are highlighted and outlined.
- **Clear**: ✖ Clear Route removes the route, the isochrone and the start/end markers.

### 4. Spatial Analysis & Visualisation
- **Geofencing**: On the Tools tab, click 🎯 Geofence Selection, then click on a zone. Points inside it and roads inside or crossing it are highlighted. Click Clear Selection to reset.
- **Choropleth**: On the Layers tab, click 🎨 Generate Choropleth and enter the name of a numeric attribute on your zones (add one in the editor first, e.g., `Population` or `Area_sqm`). Zones are shaded from light to dark blue by value.
- **Visibility**: The switches on the Layers tab show or hide points, roads and zones.

### 5. Search and Navigation
- **Search**: Type an address or landmark into the search bar above the map and press Enter (or click Fly To).
- **Attribute Table**: On the Layers tab, click 📊 Attribute Table to see all data at once. Double-click a row to zoom the map to that feature.

### 6. Saving and Exporting
- **💾 Save Project (JSON) / 📂 Load Project (JSON)**: Save or reload your whole workspace.
- **📂 Load GIS File**: Add shapes from a Shapefile, KML or GeoJSON. Data is reprojected to WGS84 automatically and height values are dropped. Only each feature's name is imported for now.
- **💾 Save SHP**: Writes `Points.shp`, `Lines.shp` and `Polygons.shp` to a `shapefiles` folder in the folder the app was started from.
- **📄 Export to CSV**: Exports every feature's attributes (no coordinates).
- **🌐 Web Map Export**: Creates `Network_WebMap.html` and opens it in your browser.

## 🗺️ Map Tiles & Data Licences
- **OpenStreetMap**: Tiles come from OpenStreetMap's volunteer-run servers, which have a [tile usage policy](https://operations.osmfoundation.org/policies/tiles/). The app follows it by identifying itself (the `GISNetworkBuilder/1.0` User-Agent set in `map_tiles.py`), caching tiles on disk (`%LOCALAPPDATA%\GISNetworkBuilder\tiles` on Windows), only fetching tiles around the area being viewed, and showing "© OpenStreetMap contributors" on the map. These servers aren't meant for heavy or commercial use.
- **Google**: The Google base maps are loaded straight from Google's tile servers without an API key, which Google Maps Platform's terms don't permit. For council or commercial use, switch to a licensed provider such as Ordnance Survey's OS Maps API.
- **Road data**: Imported roads are © OpenStreetMap contributors, available under the [Open Database Licence](https://www.openstreetmap.org/copyright).

## 🏗️ Project Architecture

- **GUI Framework**: CustomTkinter
- **Map Widget**: TkinterMapView
- **Spatial Logic**: Shapely & GeoPandas
- **Network Engine**: NetworkX (directed graph weighted by travel time)
- **API Integrations**: OpenStreetMap via OSMnx; Nominatim geocoding via Geopy
- **Web Export**: Folium

The project follows a modular structure that separates the user interface from spatial processing, file handling, and export logic.

```text
GISNetworkBuilder/
│
├── main.py              # Core application and UI coordinator
├── network_engine.py    # Snapping, graph building, routing and isochrones (NetworkX)
├── map_tiles.py         # Tile downloads that follow the OpenStreetMap tile usage policy
├── web_export.py        # HTML/Folium map generation and heatmap export
├── ui_datatable.py      # Attribute table window
├── ui_popups.py         # Dynamic Editor popup for points, lines and zones
├── file_handler.py      # Reading SHP, KML and GeoJSON files
├── requirements.txt     # Python dependencies (pinned, tested on Python 3.12)
└── README.md            # Project documentation
```

## 🛠️ Installation
Tested with Python 3.12 on Windows.

1. Clone the repo:
   ```bash
   git clone https://github.com/gingermuaz/GISNetworkBuilder.git
   cd GISNetworkBuilder
   ```
2. Create a virtual environment and install the dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python main.py
   ```

## ❓ Troubleshooting
- **"There are no roads in this project to route along"**: Import streets (Layers → 🌍 Import OSM Data) or draw some roads first. Routing doesn't use the background map.
- **"No path exists between these points"**: The roads aren't joined up (check snapping, and remember roads that cross without a shared vertex aren't connected), or a one-way street blocks the journey.
- **OpenStreetMap tiles show "403 Access blocked"**: Make sure you're running the latest `map_tiles.py`. If it continues, add a contact email to `USER_AGENT` in `map_tiles.py`, or switch to a tile provider that issues API keys.
