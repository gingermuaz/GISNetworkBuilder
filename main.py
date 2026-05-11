import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import tkintermapview
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon
from shapely import wkt
import json
import os
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from tkinter.simpledialog import askfloat, askstring

import file_handler
import ui_popups
import network_engine
import ui_datatable
import web_export

# Set the modern theme and dark mode!
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class GISNetworkBuilder(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GIS Network Builder Pro - Enterprise Edition")
        self.geometry("1250x800")

        self.nodes, self.edges, self.polygons = [], [], []
        self.current_mode = "None"
        self.current_drawing_coords = []
        self.history = []
        self.bind_all("<Control-z>", self.undo_action)

        self.route_start_coord = None
        self.route_end_coord = None
        self.route_path_visual = None
        self.isochrone_paths_visual = []
        self.isochrone_poly_visual = None

        self.geocoder = Nominatim(user_agent="gis_network_builder")
        self.snapping_tolerance = tk.DoubleVar(value=0.0005)

        self.setup_ui()

    def setup_ui(self):
        left_panel = ctk.CTkFrame(self, width=300, corner_radius=0)
        left_panel.pack(side="left", fill="y")

        self.tabview = ctk.CTkTabview(left_panel, width=280)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tab_draw = self.tabview.add("Draw")
        tab_tools = self.tabview.add("Tools")
        tab_layers = self.tabview.add("Layers")

        self._setup_draw_tab(tab_draw)
        self._setup_tools_tab(tab_tools)
        self._setup_layers_tab(tab_layers)

        map_container = ctk.CTkFrame(self, corner_radius=0)
        map_container.pack(side="right", fill="both", expand=True)

        search_frame = ctk.CTkFrame(map_container, height=50, corner_radius=0, fg_color="transparent")
        search_frame.pack(side="top", fill="x", padx=10, pady=10)

        ctk.CTkLabel(search_frame, text="🔍 Search:", font=("Arial", 14, "bold")).pack(side="left", padx=(0, 10))
        self.search_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="e.g., Moseley, Birmingham")
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda e: self.search_location())
        ctk.CTkButton(search_frame, text="Fly To", width=100, command=self.search_location).pack(side="left", padx=5)

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_cache.db")
        self.map_widget = tkintermapview.TkinterMapView(map_container, corner_radius=10, database_path=db_path)
        self.map_widget.pack(side="bottom", fill="both", expand=True, padx=10, pady=(0, 10))

        # Default to Google Maps on startup
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        self.map_widget.set_position(52.4862, -1.8904);
        self.map_widget.set_zoom(15)
        self.map_widget.add_left_click_map_command(self.map_click)

    def _setup_draw_tab(self, parent):
        ctk.CTkButton(parent, text="📍 Draw Point", command=lambda: self.set_mode("Point")).pack(pady=5, fill="x",
                                                                                                padx=20)
        ctk.CTkButton(parent, text="📏 Draw Line", command=lambda: self.set_mode("Line")).pack(pady=(15, 5), fill="x",
                                                                                              padx=20)
        ctk.CTkButton(parent, text="✓ Finish Line", command=self.finish_line, fg_color="#2ecc71",
                      hover_color="#27ae60").pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(parent, text="⬡ Draw Polygon", command=lambda: self.set_mode("Polygon")).pack(pady=(15, 5),
                                                                                                    fill="x", padx=20)
        ctk.CTkButton(parent, text="✓ Finish Polygon", command=self.finish_polygon, fg_color="#2ecc71",
                      hover_color="#27ae60").pack(pady=5, fill="x", padx=20)

        ctk.CTkFrame(parent, height=2).pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(parent, text="↩️ Undo (Ctrl+Z)", command=self.undo_action, fg_color="#95a5a6",
                      hover_color="#7f8c8d").pack(pady=5, fill="x", padx=20)
        self.lbl_status = ctk.CTkLabel(parent, text="Mode: NONE", text_color="#3498db", font=("Arial", 14, "bold"))
        self.lbl_status.pack(pady=20)

    def _setup_tools_tab(self, parent):
        ctk.CTkLabel(parent, text="Network Routing", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkButton(parent, text="🟢 Set Start Point", command=lambda: self.set_mode("SetStart"), fg_color="#27ae60",
                      hover_color="#1e8449").pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(parent, text="🔴 Set End Point", command=lambda: self.set_mode("SetEnd"), fg_color="#c0392b",
                      hover_color="#922b21").pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(parent, text="⚡ Calculate Route", command=self.calculate_route, fg_color="#8e44ad",
                      hover_color="#732d91").pack(pady=10, fill="x", padx=20)
        ctk.CTkButton(parent, text="⏳ Calculate Isochrone", command=lambda: self.set_mode("SetIsochrone")).pack(pady=5,
                                                                                                                fill="x",
                                                                                                                padx=20)
        ctk.CTkButton(parent, text="✖ Clear Route", command=self.clear_route, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90")).pack(pady=5, fill="x", padx=20)

        self.lbl_route = ctk.CTkLabel(parent, text="Start: Not Set\nEnd: Not Set", text_color="#9b59b6")
        self.lbl_route.pack(pady=5)

        ctk.CTkFrame(parent, height=2).pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(parent, text="Spatial Analysis", font=("Arial", 14, "bold")).pack(pady=5)
        ctk.CTkButton(parent, text="🎯 Geofence Selection", command=lambda: self.set_mode("Geofence"),
                      fg_color="#f39c12", hover_color="#d68910").pack(pady=5, fill="x", padx=20)
        ctk.CTkButton(parent, text="Clear Selection", command=self.render_map, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90")).pack(pady=5, fill="x", padx=20)

    def _setup_layers_tab(self, parent):
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        # --- NEW: Base Map Style Dropdown ---
        ctk.CTkLabel(scroll_frame, text="Base Map Style", font=("Arial", 14, "bold")).pack(pady=5)
        self.map_style_var = ctk.StringVar(value="Google Maps")
        self.map_style_dropdown = ctk.CTkOptionMenu(
            scroll_frame,
            variable=self.map_style_var,
            values=["Google Maps", "Google Satellite", "Google Hybrid", "OpenStreetMap", "Dark Mode"],
            command=self.change_map_style
        )
        self.map_style_dropdown.pack(pady=5, fill="x", padx=20)

        ctk.CTkFrame(scroll_frame, height=2).pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(scroll_frame, text="Visibility", font=("Arial", 14, "bold")).pack(pady=5)
        self.show_points, self.show_lines, self.show_polygons = tk.BooleanVar(value=True), tk.BooleanVar(
            value=True), tk.BooleanVar(value=True)
        ctk.CTkSwitch(scroll_frame, text="Show Assets (Points)", variable=self.show_points,
                      command=self.render_map).pack(anchor="w", padx=20, pady=5)
        ctk.CTkSwitch(scroll_frame, text="Show Roads (Lines)", variable=self.show_lines, command=self.render_map).pack(
            anchor="w", padx=20, pady=5)
        ctk.CTkSwitch(scroll_frame, text="Show Zones (Polys)", variable=self.show_polygons,
                      command=self.render_map).pack(anchor="w", padx=20, pady=5)

        ctk.CTkFrame(scroll_frame, height=2).pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(scroll_frame, text="Snapping Tolerance:", font=("Arial", 12)).pack()
        ctk.CTkSlider(scroll_frame, from_=0.0, to=0.002, variable=self.snapping_tolerance).pack(fill="x", padx=20,
                                                                                                pady=5)

        ctk.CTkLabel(scroll_frame, text="Data Tools", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkButton(scroll_frame, text="🎨 Generate Choropleth", command=self.generate_choropleth,
                      fg_color="#16a085").pack(pady=2, fill="x", padx=20)
        ctk.CTkButton(scroll_frame, text="📊 Attribute Table", command=self.open_attribute_table).pack(pady=2, fill="x",
                                                                                                      padx=20)
        ctk.CTkButton(scroll_frame, text="🌐 Web Map Export", command=self.export_to_web).pack(pady=2, fill="x", padx=20)
        ctk.CTkButton(scroll_frame, text="📄 Export to CSV", command=self.export_to_csv).pack(pady=2, fill="x", padx=20)

        ctk.CTkLabel(scroll_frame, text="File I/O", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkButton(scroll_frame, text="🌍 Import OSM Data", command=self.import_osm_data, fg_color="#d35400").pack(
            pady=5, fill="x", padx=20)
        ctk.CTkButton(scroll_frame, text="💾 Save Project (JSON)", command=self.save_workspace).pack(pady=2, fill="x",
                                                                                                    padx=20)
        ctk.CTkButton(scroll_frame, text="📂 Load Project (JSON)", command=self.load_workspace).pack(pady=2, fill="x",
                                                                                                    padx=20)
        ctk.CTkButton(scroll_frame, text="📂 Load GIS File", command=self.load_file, fg_color="transparent",
                      border_width=1).pack(pady=2, fill="x", padx=20)
        ctk.CTkButton(scroll_frame, text="💾 Save SHP", command=self.save_network, fg_color="transparent",
                      border_width=1).pack(pady=2, fill="x", padx=20)
        ctk.CTkButton(scroll_frame, text="🗑️ Clear Map", command=self.clear_map, fg_color="#c0392b",
                      hover_color="#922b21").pack(pady=(15, 5), fill="x", padx=20)

    # ==========================================
    # MAP STYLE LOGIC
    # ==========================================
    def change_map_style(self, style_name):
        """Changes the background tile server of the map widget dynamically."""
        if style_name == "Google Maps":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga",
                                            max_zoom=22)
        elif style_name == "Google Satellite":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga",
                                            max_zoom=22)
        elif style_name == "Google Hybrid":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga",
                                            max_zoom=22)
        elif style_name == "OpenStreetMap":
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=19)
        elif style_name == "Dark Mode":
            # CartoDB Dark Matter tile server
            self.map_widget.set_tile_server("https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", max_zoom=19)

    # ==========================================
    # LOGIC: QoL FEATURES & IMPORTS
    # ==========================================
    def import_osm_data(self):
        prompt_msg = (
            "Enter a small local neighborhood (e.g., 'Moseley, Birmingham'):\n\n"
            "⚠️ WARNING: Stick to local neighborhoods! Searching for massive "
            "cities like 'London' will try to download millions of roads and crash your computer."
        )
        place_name = askstring("OSM Import", prompt_msg)
        if not place_name: return

        try:
            import osmnx as ox
            self.lbl_status.configure(text="Downloading OSM Data...")
            self.update()

            G = ox.graph_from_address(place_name, dist=1500, network_type='drive')

            node_map = {}
            for osmid, data in G.nodes(data=True):
                lat, lon = data['y'], data['x']
                new_node = {
                    'NodeID': len(self.nodes) + 1,
                    'geometry': Point(lon, lat),
                    'attributes': {'Name': f"Node_{osmid}", 'Asset': 'Intersection'}
                }
                self.nodes.append(new_node)
                node_map[osmid] = new_node

            for u, v, key, data in G.edges(keys=True, data=True):
                if 'geometry' in data:
                    line_geom = data['geometry']
                else:
                    line_geom = LineString([node_map[u]['geometry'], node_map[v]['geometry']])

                name = data.get('name', 'Unnamed Road')
                if isinstance(name, list): name = name[0]
                highway = data.get('highway', 'Unclassified')
                if isinstance(highway, list): highway = highway[0]
                maxspeed = data.get('maxspeed', '30')
                if isinstance(maxspeed, list): maxspeed = maxspeed[0]

                clean_speed = str(maxspeed).replace(" mph", "").replace(" km/h", "")

                new_edge = {
                    'EdgeID': len(self.edges) + 1,
                    'geometry': line_geom,
                    'attributes': {
                        'Name': name,
                        'Class': highway,
                        'Speed': clean_speed,
                        'Length_m': round(float(data.get('length', 0.0)), 2)
                    }
                }
                self.edges.append(new_edge)

            if self.nodes:
                self.map_widget.set_position(self.nodes[-1]['geometry'].y, self.nodes[-1]['geometry'].x)
                self.map_widget.set_zoom(14)

            self.lbl_status.configure(text="Mode: NONE")
            self.render_map()
            messagebox.showinfo("Success",
                                f"Imported {len(node_map)} intersections and {len(G.edges)} roads within 1.5km of {place_name}!")

        except ImportError:
            messagebox.showerror("Missing Library", "OSMnx is not installed.\nPlease run: pip install osmnx")
            self.lbl_status.configure(text="Mode: NONE")
        except Exception as e:
            self.lbl_status.configure(text="Mode: NONE")
            messagebox.showerror("OSM Import Error", f"Could not fetch data for '{place_name}'.\n\nError: {e}")

    def get_snapped_coord(self, lat, lon):
        tol = self.snapping_tolerance.get()
        for n in self.nodes:
            if abs(n['geometry'].y - lat) < tol and abs(n['geometry'].x - lon) < tol:
                return n['geometry'].y, n['geometry'].x
        return lat, lon

    # ==========================================
    # WORKSPACE SAVE / LOAD (JSON)
    # ==========================================
    def save_workspace(self):
        if not self.nodes and not self.edges and not self.polygons:
            messagebox.showinfo("Info", "Map is empty! Nothing to save.")
            return

        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Project", "*.json")])
        if not filepath: return

        try:
            workspace_data = {"nodes": [], "edges": [], "polygons": []}

            for n in self.nodes:
                data = {"NodeID": n.get("NodeID"), "geometry": n["geometry"].wkt, "attributes": n["attributes"]}
                if "custom_color" in n: data["custom_color"] = n["custom_color"]
                workspace_data["nodes"].append(data)

            for e in self.edges:
                data = {"EdgeID": e.get("EdgeID"), "geometry": e["geometry"].wkt, "attributes": e["attributes"]}
                if "custom_color" in e: data["custom_color"] = e["custom_color"]
                workspace_data["edges"].append(data)

            for p in self.polygons:
                data = {"PolygonID": p.get("PolygonID"), "geometry": p["geometry"].wkt, "attributes": p["attributes"]}
                if "custom_color" in p: data["custom_color"] = p["custom_color"]
                workspace_data["polygons"].append(data)

            with open(filepath, "w") as f:
                json.dump(workspace_data, f, indent=4)

            messagebox.showinfo("Success", "Project Workspace saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save workspace: {e}")

    def load_workspace(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Project", "*.json")])
        if not filepath: return

        try:
            with open(filepath, "r") as f:
                workspace_data = json.load(f)

            self.nodes.clear()
            self.edges.clear()
            self.polygons.clear()
            self.history.clear()
            self.clear_route()

            for n_data in workspace_data.get("nodes", []):
                node = {
                    "NodeID": n_data.get("NodeID", len(self.nodes) + 1),
                    "geometry": wkt.loads(n_data["geometry"]),
                    "attributes": n_data.get("attributes", {})
                }
                if "custom_color" in n_data: node["custom_color"] = n_data["custom_color"]
                self.nodes.append(node)

            for e_data in workspace_data.get("edges", []):
                edge = {
                    "EdgeID": e_data.get("EdgeID", len(self.edges) + 1),
                    "geometry": wkt.loads(e_data["geometry"]),
                    "attributes": e_data.get("attributes", {})
                }
                if "custom_color" in e_data: edge["custom_color"] = e_data["custom_color"]
                self.edges.append(edge)

            for p_data in workspace_data.get("polygons", []):
                poly = {
                    "PolygonID": p_data.get("PolygonID", len(self.polygons) + 1),
                    "geometry": wkt.loads(p_data["geometry"]),
                    "attributes": p_data.get("attributes", {})
                }
                if "custom_color" in p_data: poly["custom_color"] = p_data["custom_color"]
                self.polygons.append(poly)

            if self.nodes:
                self.map_widget.set_position(self.nodes[0]['geometry'].y, self.nodes[0]['geometry'].x)
            elif self.edges:
                first_coord = self.edges[0]['geometry'].coords[0]
                self.map_widget.set_position(first_coord[1], first_coord[0])

            self.render_map()
            messagebox.showinfo("Success",
                                f"Project Loaded!\nFound {len(self.nodes)} points, {len(self.edges)} roads, and {len(self.polygons)} polygons.")

        except Exception as e:
            messagebox.showerror("Error", f"Could not load workspace: {e}")

    # ==========================================
    # CORE LOGIC & EVENT HANDLERS
    # ==========================================
    def set_mode(self, mode_name):
        self.current_mode = mode_name;
        self.current_drawing_coords = []
        self.lbl_status.configure(text=f"Mode: {mode_name.upper()}")

    def search_location(self):
        address = self.search_entry.get()
        if not address: return
        try:
            loc = self.geocoder.geocode(address)
            if loc:
                self.map_widget.set_position(loc.latitude, loc.longitude);
                self.map_widget.set_zoom(17)
                self.map_widget.set_marker(loc.latitude, loc.longitude, text=address)
            else:
                messagebox.showwarning("Not Found", "Address not found.")
        except:
            messagebox.showerror("Error", "Geocoding failed.")

    def render_map(self):
        self.map_widget.delete_all_marker();
        self.map_widget.delete_all_path();
        self.map_widget.delete_all_polygon()
        if self.show_polygons.get():
            for p in self.polygons:
                self.map_widget.set_polygon([(y, x) for x, y in p['geometry'].exterior.coords],
                                            fill_color=p.get('custom_color', "#5288ae"), outline_color="navy",
                                            border_width=2, command=self.on_polygon_click)
        if self.show_lines.get():
            for e in self.edges:
                speed = float(e['attributes'].get('Speed', 30)) if str(e['attributes'].get('Speed', 30)).replace('.',
                                                                                                                 '',
                                                                                                                 1).isdigit() else 30
                color = e.get('custom_color', ("#2ecc71" if speed < 30 else "#f39c12" if speed <= 60 else "#c0392b"))
                self.map_widget.set_path([(y, x) for x, y in e['geometry'].coords], color=color, width=3,
                                         command=self.on_path_click)
        if self.show_points.get():
            for n in self.nodes:
                label_text = n['attributes'].get('Asset', n['attributes'].get('Name', 'Point'))
                self.map_widget.set_marker(n['geometry'].y, n['geometry'].x, text=label_text,
                                           command=self.on_marker_click)

        # Draw Start and End Markers in Green and Red
        if self.route_start_coord:
            self.map_widget.set_marker(self.route_start_coord[1], self.route_start_coord[0], text="Start",
                                       marker_color_circle="white", marker_color_outside="#27ae60")
        if self.route_end_coord:
            self.map_widget.set_marker(self.route_end_coord[1], self.route_end_coord[0], text="End",
                                       marker_color_circle="white", marker_color_outside="#c0392b")

    def map_click(self, coords):
        lat, lon = self.get_snapped_coord(coords[0], coords[1])
        if self.current_mode == "Point":
            new_node = {'geometry': Point(lon, lat),
                        'attributes': {'Name': f"P{len(self.nodes) + 1}", 'Asset': 'Streetlight'}}
            self.nodes.append(new_node);
            self.history.append(('add', 'point', new_node));
            self.set_mode("None");
            self.render_map()
        elif self.current_mode in ["Line", "Polygon"]:
            self.current_drawing_coords.append((lat, lon))
            self.map_widget.set_marker(lat, lon, marker_color_circle="#3498db")
            if len(self.current_drawing_coords) > 1: self.map_widget.set_path(self.current_drawing_coords,
                                                                              color="#3498db", width=2)
        elif self.current_mode in ["SetStart", "SetEnd", "SetIsochrone"]:
            if self.current_mode == "SetStart":
                self.route_start_coord = (lon, lat)
            elif self.current_mode == "SetEnd":
                self.route_end_coord = (lon, lat)
            else:
                self.calculate_isochrone_area((lon, lat))
            self.update_route_label()
            self.set_mode("None")
            self.render_map()

    def on_marker_click(self, marker):
        lat, lon = marker.position
        if self.current_mode in ["SetStart", "SetEnd", "SetIsochrone"]: self.map_click((lat, lon)); return
        if self.current_mode in ["Line", "Polygon"]:
            self.current_drawing_coords.append((lat, lon))
            if len(self.current_drawing_coords) > 1: self.map_widget.set_path(self.current_drawing_coords,
                                                                              color="#3498db", width=2)
            return
        target = next(
            (n for n in self.nodes if abs(n['geometry'].x - lon) < 0.0001 and abs(n['geometry'].y - lat) < 0.0001),
            None)
        if target: ui_popups.DynamicEditorPopup(self, target, "Point", self.render_map, self.delete_item_callback)

    def on_path_click(self, path):
        if self.current_mode != "None": return
        first_lon = path.position_list[0][1]
        target = next((e for e in self.edges if abs(e['geometry'].coords[0][0] - first_lon) < 0.0001), None)
        if target: ui_popups.DynamicEditorPopup(self, target, "Line", self.render_map, self.delete_item_callback)

    def on_polygon_click(self, polygon):
        first_lon = polygon.position_list[0][1]
        target = next((p for p in self.polygons if abs(p['geometry'].exterior.coords[0][0] - first_lon) < 0.0001), None)
        if not target: return
        if self.current_mode == "Geofence": self.run_geofence(target); return
        ui_popups.DynamicEditorPopup(self, target, "Polygon", self.render_map, self.delete_item_callback)

    def finish_line(self):
        if len(self.current_drawing_coords) > 1:
            line = LineString([(lon, lat) for lat, lon in self.current_drawing_coords])
            length_m = sum(geodesic(self.current_drawing_coords[i], self.current_drawing_coords[i + 1]).meters for i in
                           range(len(self.current_drawing_coords) - 1))
            new_edge = {'geometry': line,
                        'attributes': {'Name': f"Road_{len(self.edges) + 1}", 'Class': 'Unclassified', 'Speed': "30",
                                       'Length_m': round(length_m, 2)}}
            self.edges.append(new_edge);
            self.history.append(('add', 'line', new_edge));
            self.set_mode("None");
            self.render_map()

    def finish_polygon(self):
        if len(self.current_drawing_coords) > 2:
            poly = Polygon([(lon, lat) for lat, lon in self.current_drawing_coords])
            new_poly = {'geometry': poly, 'attributes': {'Name': f"Poly_{len(self.polygons) + 1}", 'Zone': "General"}}
            self.polygons.append(new_poly);
            self.history.append(('add', 'polygon', new_poly));
            self.set_mode("None");
            self.render_map()

    def undo_action(self, event=None):
        if not self.history: return
        action, type, item = self.history.pop()
        if action == 'add':
            if type == 'point':
                self.nodes.remove(item)
            elif type == 'line':
                self.edges.remove(item)
            else:
                self.polygons.remove(item)
        else:
            if type == 'point':
                self.nodes.append(item)
            elif type == 'line':
                self.edges.append(item)
            else:
                self.polygons.append(item)
        self.render_map()

    def delete_item_callback(self, item, item_type):
        if item_type == "Point":
            self.nodes.remove(item)
        elif item_type == "Line":
            self.edges.remove(item)
        elif item_type == "Polygon":
            self.polygons.remove(item)
        self.history.append(('delete', item_type.lower(), item))
        self.render_map()

    # ==========================================
    # ROUTING & SPATIAL ANALYSIS
    # ==========================================
    def update_route_label(self):
        s_text = f"{self.route_start_coord[0]:.3f}, {self.route_start_coord[1]:.3f}" if self.route_start_coord else "Not Set"
        e_text = f"{self.route_end_coord[0]:.3f}, {self.route_end_coord[1]:.3f}" if self.route_end_coord else "Not Set"
        self.lbl_route.configure(text=f"Start: {s_text}\nEnd: {e_text}")

    def clear_route(self):
        self.route_start_coord, self.route_end_coord = None, None
        if self.route_path_visual: self.route_path_visual.delete()
        for p in self.isochrone_paths_visual: p.delete()
        if self.isochrone_poly_visual: self.isochrone_poly_visual.delete()
        self.isochrone_paths_visual.clear()
        self.isochrone_poly_visual = None
        self.update_route_label()
        self.render_map()

    def calculate_route(self):
        if not self.route_start_coord or not self.route_end_coord: return
        try:
            route_coords, segment_count, total_time_sec = network_engine.calculate_shortest_path(self.edges,
                                                                                                 self.route_start_coord,
                                                                                                 self.route_end_coord)
            if self.route_path_visual: self.route_path_visual.delete()
            self.route_path_visual = self.map_widget.set_path(route_coords, color="#9b59b6", width=5)

            mins = int(total_time_sec // 60)
            secs = int(total_time_sec % 60)
            messagebox.showinfo("Route Found!",
                                f"Fastest path calculated across {segment_count} road segments.\n\nEstimated Travel Time: {mins} min {secs} sec.")
        except ValueError as err:
            messagebox.showerror("Routing Error", str(err))

    def calculate_isochrone_area(self, start_coord):
        max_time_sec = askfloat("Service Area", "Enter maximum travel time budget (in SECONDS):", minvalue=1)
        if not max_time_sec: return
        try:
            for p in self.isochrone_paths_visual: p.delete()
            if self.isochrone_poly_visual: self.isochrone_poly_visual.delete()
            self.isochrone_paths_visual.clear()

            reachable_paths, hull_coords = network_engine.calculate_isochrone(self.edges, start_coord, max_time_sec)

            for path_coords in reachable_paths:
                visual = self.map_widget.set_path([(lat, lon) for lon, lat in path_coords], color="#00ffff", width=4)
                self.isochrone_paths_visual.append(visual)
            if hull_coords:
                self.isochrone_poly_visual = self.map_widget.set_polygon(hull_coords, fill_color="#00ffff",
                                                                         outline_color="#008080", border_width=2)

            mins = int(max_time_sec // 60)
            messagebox.showinfo("Success",
                                f"Service area calculated!\nFound {len(reachable_paths)} road segments reachable within {mins} minutes.")
        except ValueError as err:
            messagebox.showerror("Error", str(err))

    def run_geofence(self, target_poly):
        selected_nodes = [n for n in self.nodes if target_poly['geometry'].contains(n['geometry'])]
        selected_edges = [e for e in self.edges if target_poly['geometry'].intersects(e['geometry'])]
        for n in selected_nodes: self.map_widget.set_marker(n['geometry'].y, n['geometry'].x,
                                                            marker_color_circle="#f1c40f")
        for e in selected_edges: self.map_widget.set_path([(y, x) for x, y in e['geometry'].coords], color="#f1c40f",
                                                          width=4)
        messagebox.showinfo("Geofence", f"Found {len(selected_nodes)} points and {len(selected_edges)} lines.");
        self.set_mode("None")

    def generate_choropleth(self):
        attr = askstring("Choropleth", "Attribute:", initialvalue="Area_sqm")
        if not attr: return
        vals = []
        for p in self.polygons:
            try:
                vals.append(float(p['attributes'].get(attr, 0)))
            except:
                pass
        if not vals: return
        mn, mx = min(vals), max(vals)
        for p in self.polygons:
            try:
                v = float(p['attributes'].get(attr, 0))
                ratio = (v - mn) / (mx - mn) if mx != mn else 0.5
                p[
                    'custom_color'] = f"#{int(224 - 216 * ratio):02x}{int(243 - 195 * ratio):02x}{int(255 - 148 * ratio):02x}"
            except:
                pass
        self.render_map()

    # ==========================================
    # DATA EXPORT & FILE I/O
    # ==========================================
    def export_to_csv(self):
        all_data = []
        for n in self.nodes: all_data.append({'Type': 'Point', **n['attributes']})
        for e in self.edges: all_data.append({'Type': 'Line', **e['attributes']})
        for p in self.polygons: all_data.append({'Type': 'Polygon', **p['attributes']})

        if not all_data: return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filepath:
            pd.DataFrame(all_data).to_csv(filepath, index=False)
            messagebox.showinfo("Success", "Attributes exported to CSV!")

    def open_attribute_table(self):
        ui_datatable.AttributeTableWindow(self, self.nodes, self.edges, self.polygons, self.pan_to_feature)

    def export_to_web(self):
        try:
            webbrowser.open(
                f"file://{os.path.abspath(web_export.generate_html_map(self.nodes, self.edges, self.polygons))}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_network(self):
        os.makedirs("shapefiles", exist_ok=True)
        try:
            if self.nodes: gpd.GeoDataFrame([{'geometry': n['geometry'], **n['attributes']} for n in self.nodes],
                                            crs="EPSG:4326").to_file("shapefiles/Points.shp")
            if self.edges: gpd.GeoDataFrame([{'geometry': e['geometry'], **e['attributes']} for e in self.edges],
                                            crs="EPSG:4326").to_file("shapefiles/Lines.shp")
            if self.polygons: gpd.GeoDataFrame([{'geometry': p['geometry'], **p['attributes']} for p in self.polygons],
                                               crs="EPSG:4326").to_file("shapefiles/Polygons.shp")
            messagebox.showinfo("Success", "Exported!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_file(self):
        fp = filedialog.askopenfilename(filetypes=[("All Supported", "*.shp *.kml *.geojson")])
        if not fp: return
        try:
            pts, lns, polys = file_handler.load_spatial_file(fp)
            for p in pts: self.nodes.append({'geometry': p['geometry'], 'attributes': {'Name': p['name']}})
            for l in lns: self.edges.append(
                {'geometry': l['geometry'], 'attributes': {'Name': f"Line_{len(self.edges) + 1}", 'Speed': "30"}})
            for p in polys: self.polygons.append({'geometry': p['geometry'], 'attributes': {'Name': p['name']}})
            self.render_map()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_map(self):
        if messagebox.askyesno("Confirm", "Wipe all?"):
            self.nodes, self.edges, self.polygons, self.history = [], [], [], []
            self.clear_route();
            self.render_map()


if __name__ == "__main__":
    app = GISNetworkBuilder()
    app.mainloop()