# 🌍 GIS Network Builder

GIS Network Builder is a modular, high-performance desktop GIS workstation built with Python. It is specifically designed for councils, local authorities, and civil engineers to digitise urban assets, model road networks, and perform advanced spatial analysis.

## 🚀 Features
🛠️ Advanced Digitising & UI
1) Modern Enterprise UI: Fully overhauled with CustomTkinter, featuring native Dark Mode and rounded, high-end design elements.
2) Automated Data Import: Instantly pull real-world street grids from OpenStreetMap with automatic road classification and speed limits.
3) Standardised Asset Management: Integrated dropdowns for rapid, error-free entry of standard council assets (Potholes, Streetlights, Manholes) and road directions.
4) Intelligent Snapping: Adjustable tolerance slider to ensure perfect connectivity between vertices.

🧠 Network & Spatial Analysis
1) Real-World Routing: Calculates the fastest path using travel time (seconds) rather than just physical distance.
2) Time-Based Isochrones: Visualise service coverage areas based on a precise travel time budget (e.g., 5-minute response zones).
3) Spatial Geofencing: Run "Select by Location" queries to identify all assets or roads interacting within a specific polygon boundary.

📊 Data Visualization & Export
1) Custom Map Layers: Dynamically switch between Google Maps, Satellite, Hybrid, OpenStreetMap, and Dark Mode base maps.
2) Interactive Web Export: Generate standalone HTML maps featuring interactive popups and Point Density Heatmaps.
3) Flexible Workspaces: Save entire sessions, including custom styles and attributes, to JSON Project Workspaces.
4) Industry Standard I/O: Export to Shapefile (.shp) for CAD/GIS or CSV for Microsoft Excel.

## 📖 Usage Guide
1. __Drawing and Editing
Draw shapes__: Select a mode (Point, Line, or Polygon) from the Draw tab. Left-click on the map to place points. For lines and polygons, click Finish to complete the shape.
Snapping: Adjust the Snapping Tolerance slider in the Layers/Data tab to help connect new lines exactly to existing points.
Edit Data: Click on any existing shape to open the Dynamic Editor. Here you can add custom fields, change values, or pick a custom colour.

2. __Network Analysis
Shortest Path__: In the Tools tab, use "Set Start" and "Set End" to choose your points on the map. Click Calculate Shortest Path to see the route.
Service Areas: Select Calculate Service Area, click a point on the map, and enter your "budget" (distance/cost) to visualise reachable areas.

3. __Spatial Analysis & Visualisation
Geofencing__: Click Select by Polygon in the Tools tab, then click on an existing polygon on the map. The app will highlight all points and lines inside that zone.
Choropleth: In the Layers/Data tab, click Generate Choropleth and enter a numeric attribute name (like Area_sqm) to colour-code your polygons by value.

4. __Search and Navigation
Search__: Type any address or landmark into the search bar above the map and press Enter to instantly fly to that location.
Attribute Table: Open the Attribute Table to see all data at once. Double-click a row to zoom the map directly to that feature.

## 🏗️ Project Architecture

The project follows a modular structure that separates the user interface from spatial processing, file handling, and export logic.

```text
GISNetworkBuilder/
│
├── main.py              # Core application and UI coordinator
├── network_engine.py    # Graph theory and spatial analysis logic using NetworkX
├── web_export.py        # HTML/Folium map generation and heatmap export
├── ui_datatable.py      # Attribute table and data management UI
├── ui_popups.py         # Dialogues, popups, and supporting UI components
├── file_handler.py      # Spatial file I/O for SHP, KML, GeoJSON, and CSV
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```
## 🛠️ Installation
1. Clone the repo: `https://github.com/gingermuaz/GISNetworkBuilder.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python main.py`
