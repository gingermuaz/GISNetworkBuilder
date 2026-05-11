# 🌍 GIS Network Builder Pro

GIS Network Builder Pro is a modular desktop GIS workstation built with Python. It bridges the gap between desktop spatial engineering and web-based data visualisation, allowing users to digitise, analyse, and export complex geographic networks with ease.

## 🚀 Features
🛠️ Advanced Digitising Tools
1) Dynamic Drawing: Digitise Points, Lines, and Polygons with custom data attributes.
2) Intelligent Snapping: Use the Snapping Tolerance slider to "magnetise" vertices to existing nodes for perfectly connected networks.
3) Undo/Redo Support: Built-in history stack allows you to reverse accidental edits with Ctrl+Z.
4) Custom Styling: Use the integrated color picker to style individual shapes on the fly.

🧠 Network & Spatial Analysis
1) Shortest Path (Dijkstra): Calculate the most efficient route between any two points in your network.
2) Service Areas (Isochrones): Visualize reachability by calculating coverage zones based on a travel "budget" or distance.
3) Geofencing: Run "Select by Location" queries to find all points and lines interacting with a specific polygon.

📊 Data Visualization & Export
1) Attribute Table: A spreadsheet-style view to manage all spatial data, featuring Double-Click to Pan functionality.
2) Choropleth Mapping: Automatically color-code polygons based on numeric values (like Area).
3) Web Map Export: Compile your entire network into an interactive Leaflet.js HTML map featuring Point Density Heatmaps.
4) Flexible I/O: Save and load standard Shapefiles (.shp) or export data attributes to CSV for use in Excel.

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

## 🛠️ Installation
1. Clone the repo: `https://github.com/gingermuaz/GISNetworkBuilder.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python main.py`
