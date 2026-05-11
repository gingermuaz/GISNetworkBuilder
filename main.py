import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import tkintermapview
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import os
from geopy.distance import geodesic
from tkinter.simpledialog import askfloat, askstring

# Import our custom modules
import file_handler
import ui_popups
import network_engine
import ui_datatable
import web_export


class GISNetworkBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GIS Network Builder Pro - Ultimate Edition")
        self.geometry("1200x800")

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

        self.setup_ui()

    # ==========================================
    # UI SETUP
    # ==========================================
    def setup_ui(self):
        left_panel = tk.Frame(self, width=250)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)

        notebook = ttk.Notebook(left_panel)
        notebook.pack(fill="both", expand=True)

        tab_draw = tk.Frame(notebook)
        tab_tools = tk.Frame(notebook)
        tab_layers = tk.Frame(notebook)

        notebook.add(tab_draw, text="Draw")
        notebook.add(tab_tools, text="Tools")
        notebook.add(tab_layers, text="Layers/Data")

        self._setup_draw_tab(tab_draw)
        self._setup_tools_tab(tab_tools)
        self._setup_layers_tab(tab_layers)

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_cache.db")
        self.map_widget = tkintermapview.TkinterMapView(self, corner_radius=0, database_path=db_path)
        self.map_widget.pack(side="right", fill="both", expand=True)
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        self.map_widget.set_position(52.4862, -1.8904)
        self.map_widget.set_zoom(15)
        self.map_widget.add_left_click_map_command(self.map_click)

    def _setup_draw_tab(self, parent):
        tk.Button(parent, text="Draw Point", command=lambda: self.set_mode("Point"), width=20).pack(pady=5)
        tk.Button(parent, text="Draw Line", command=lambda: self.set_mode("Line"), width=20).pack(pady=(15, 5))
        tk.Button(parent, text="Finish Line", command=self.finish_line, width=20, bg="lightblue").pack(pady=5)
        tk.Button(parent, text="Draw Polygon", command=lambda: self.set_mode("Polygon"), width=20).pack(pady=(15, 5))
        tk.Button(parent, text="Finish Polygon", command=self.finish_polygon, width=20, bg="#d4edda").pack(pady=5)

        tk.Frame(parent, height=2, bg="gray").pack(fill="x", padx=20, pady=10)
        tk.Button(parent, text="↩️ Undo (Ctrl+Z)", command=self.undo_action, width=20, bg="#f0f0f0").pack(pady=5)
        self.lbl_status = tk.Label(parent, text="Mode: None", fg="blue", font=("Arial", 10, "bold"))
        self.lbl_status.pack(pady=20)

    def _setup_tools_tab(self, parent):
        tk.Label(parent, text="Network Routing", font=("Arial", 10, "bold")).pack(pady=10)
        tk.Button(parent, text="Set Start Point", command=lambda: self.set_mode("SetStart"), width=20).pack(pady=5)
        tk.Button(parent, text="Set End Point", command=lambda: self.set_mode("SetEnd"), width=20).pack(pady=5)
        tk.Button(parent, text="Calculate Shortest Path", command=self.calculate_route, width=20, bg="plum").pack(
            pady=10)
        tk.Button(parent, text="Calculate Service Area", command=lambda: self.set_mode("SetIsochrone"), width=20,
                  bg="thistle").pack(pady=5)
        tk.Button(parent, text="Clear Route", command=self.clear_route, width=20).pack(pady=5)
        self.lbl_route = tk.Label(parent, text="Start: Not Set\nEnd: Not Set", fg="purple")
        self.lbl_route.pack(pady=10)

        tk.Frame(parent, height=2, bg="gray").pack(fill="x", padx=20, pady=10)
        tk.Label(parent, text="Spatial Analysis", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(parent, text="Select by Polygon", command=lambda: self.set_mode("Geofence"), width=20,
                  bg="#fffacd").pack(pady=5)
        tk.Button(parent, text="Clear Selection", command=self.render_map, width=20).pack(pady=5)

    def _setup_layers_tab(self, parent):
        tk.Label(parent, text="Visibility", font=("Arial", 10, "bold")).pack(pady=10)
        self.show_points = tk.BooleanVar(value=True)
        self.show_lines = tk.BooleanVar(value=True)
        self.show_polygons = tk.BooleanVar(value=True)

        tk.Checkbutton(parent, text="Show Points", variable=self.show_points, command=self.render_map).pack(anchor="w",
                                                                                                            padx=20)
        tk.Checkbutton(parent, text="Show Lines", variable=self.show_lines, command=self.render_map).pack(anchor="w",
                                                                                                          padx=20)
        tk.Checkbutton(parent, text="Show Polygons", variable=self.show_polygons, command=self.render_map).pack(
            anchor="w", padx=20)

        tk.Frame(parent, height=20).pack()
        tk.Label(parent, text="Data Visualization", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(parent, text="🎨 Generate Choropleth", command=self.generate_choropleth, width=20, bg="#ffefd5").pack(
            pady=5)
        tk.Button(parent, text="📊 Attribute Table", command=self.open_attribute_table, width=20, bg="#e6e6fa").pack(
            pady=5)

        # This is the button that was throwing the error!
        tk.Button(parent, text="🌐 Export to Web Map", command=self.export_to_web, width=20, bg="#e0ffff").pack(pady=5)

        tk.Frame(parent, height=20).pack()
        tk.Label(parent, text="File I/O", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(parent, text="📂 Load File", command=self.load_file, width=20, bg="#ffe5b4").pack(pady=5)
        tk.Button(parent, text="💾 Save Network", command=self.save_network, width=20, bg="lightgreen").pack(pady=5)
        tk.Button(parent, text="🗑️ Clear Map", command=self.clear_map, width=20, bg="#ffcccc").pack(pady=5)

    def set_mode(self, mode_name):
        self.current_mode = mode_name
        self.current_drawing_coords = []
        self.lbl_status.config(text=f"Mode: {mode_name.upper()}")

    # ==========================================
    # DATA VISUALIZATION (CHOROPLETH)
    # ==========================================
    def generate_choropleth(self):
        if not self.polygons:
            messagebox.showinfo("Info", "Draw or load some polygons first!")
            return

        attr_name = askstring("Choropleth Map", "Enter the numeric attribute to color map (e.g., Area_sqm):",
                              initialvalue="Area_sqm")
        if not attr_name: return

        valid_polys = []
        for p in self.polygons:
            try:
                val = float(p['attributes'].get(attr_name, 0))
                valid_polys.append((p, val))
            except ValueError:
                pass

        if not valid_polys:
            messagebox.showerror("Error", f"Could not find valid numeric data for attribute '{attr_name}'.")
            return

        min_val = min(v for p, v in valid_polys)
        max_val = max(v for p, v in valid_polys)

        for p, val in valid_polys:
            ratio = 0.5 if max_val == min_val else (val - min_val) / (max_val - min_val)
            r = int(224 - (216 * ratio))
            g = int(243 - (195 * ratio))
            b = int(255 - (148 * ratio))
            p['custom_color'] = f"#{r:02x}{g:02x}{b:02x}"

        self.render_map()
        messagebox.showinfo("Success", f"Choropleth applied based on {attr_name}!")

    # ==========================================
    # UNDO & DELETE LOGIC
    # ==========================================
    def undo_action(self, event=None):
        if not self.history: return
        action, shape_type, item = self.history.pop()

        if action == 'add':
            if shape_type == 'point':
                self.nodes.remove(item)
            elif shape_type == 'line':
                self.edges.remove(item)
            elif shape_type == 'polygon':
                self.polygons.remove(item)
        elif action == 'delete':
            if shape_type == 'point':
                self.nodes.append(item)
            elif shape_type == 'line':
                self.edges.append(item)
            elif shape_type == 'polygon':
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

    def open_attribute_table(self):
        if not self.nodes and not self.edges and not self.polygons: return
        ui_datatable.AttributeTableWindow(self, self.nodes, self.edges, self.polygons, self.pan_to_feature)

    def pan_to_feature(self, geom):
        if geom.geom_type == 'Point':
            self.map_widget.set_position(geom.y, geom.x)
        else:
            self.map_widget.set_position(geom.centroid.y, geom.centroid.x)
        self.map_widget.set_zoom(17)

        # ==========================================

    # CORE LOGIC (Rendering & Drawing)
    # ==========================================
    def render_map(self):
        self.map_widget.delete_all_marker()
        self.map_widget.delete_all_path()
        self.map_widget.delete_all_polygon()

        if self.show_polygons.get():
            for p in self.polygons:
                coords = [(y, x) for x, y in p['geometry'].exterior.coords]
                fill_col = p.get('custom_color', "#5288ae")
                self.map_widget.set_polygon(coords, fill_color=fill_col, outline_color="navy", border_width=2,
                                            command=self.on_polygon_click)

        if self.show_lines.get():
            for e in self.edges:
                coords = [(y, x) for x, y in e['geometry'].coords]
                try:
                    speed = float(e['attributes'].get('Speed', 50))
                except ValueError:
                    speed = 50
                color = "green" if speed < 30 else "orange" if speed <= 60 else "red"
                self.map_widget.set_path(coords, color=color, width=3, command=self.on_path_click)

        if self.show_points.get():
            for n in self.nodes:
                self.map_widget.set_marker(n['geometry'].y, n['geometry'].x, text=n['attributes'].get('Name', 'Point'),
                                           command=self.on_marker_click)

    def finish_line(self):
        if len(self.current_drawing_coords) > 1:
            coords = self.current_drawing_coords
            line = LineString([(lon, lat) for lat, lon in coords])
            length_m = sum(geodesic(coords[i], coords[i + 1]).meters for i in range(len(coords) - 1))
            new_edge = {'EdgeID': len(self.edges) + 1, 'geometry': line,
                        'attributes': {'Name': f"Line_{len(self.edges) + 1}", 'Speed': "50", 'Weight': "1.0",
                                       'Length_m': round(length_m, 2)}}
            self.edges.append(new_edge)
            self.history.append(('add', 'line', new_edge))
            self.set_mode("None");
            self.render_map()

    def finish_polygon(self):
        if len(self.current_drawing_coords) > 2:
            poly = Polygon([(lon, lat) for lat, lon in self.current_drawing_coords])
            minx, miny, maxx, maxy = poly.bounds
            approx_area = (geodesic((miny, minx), (miny, maxx)).meters * geodesic((miny, minx),
                                                                                  (maxy, minx)).meters) * 0.7
            new_poly = {'PolygonID': len(self.polygons) + 1, 'geometry': poly,
                        'attributes': {'Name': f"Poly_{len(self.polygons) + 1}", 'Zone': "General",
                                       'Area_sqm': round(approx_area, 2)}}
            self.polygons.append(new_poly)
            self.history.append(('add', 'polygon', new_poly))
            self.set_mode("None");
            self.render_map()

    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    def map_click(self, coords):
        lat, lon = coords
        if self.current_mode == "Point":
            new_node = {'NodeID': len(self.nodes) + 1, 'geometry': Point(lon, lat),
                        'attributes': {'Name': f"P{len(self.nodes) + 1}"}}
            self.nodes.append(new_node)
            self.history.append(('add', 'point', new_node))
            self.set_mode("None");
            self.render_map()

        elif self.current_mode in ["Line", "Polygon"]:
            self.current_drawing_coords.append((lat, lon))
            self.map_widget.set_marker(lat, lon, marker_color_circle="blue", marker_color_outside="lightblue")
            if len(self.current_drawing_coords) > 1:
                self.map_widget.set_path(self.current_drawing_coords, color="blue", width=2)

        elif self.current_mode in ["SetStart", "SetEnd"]:
            if self.current_mode == "SetStart":
                self.route_start_coord = (lon, lat)
            else:
                self.route_end_coord = (lon, lat)
            self.update_route_label();
            self.set_mode("None")

        elif self.current_mode == "SetIsochrone":
            self.calculate_isochrone_area((lon, lat))
            self.set_mode("None")

    def on_marker_click(self, marker):
        lat, lon = marker.position
        if self.current_mode == "SetStart":
            self.route_start_coord = (lon, lat);
            self.update_route_label();
            self.set_mode("None");
            return
        elif self.current_mode == "SetEnd":
            self.route_end_coord = (lon, lat);
            self.update_route_label();
            self.set_mode("None");
            return
        elif self.current_mode == "SetIsochrone":
            self.calculate_isochrone_area((lon, lat));
            self.set_mode("None");
            return

        if self.current_mode in ["Line", "Polygon"]:
            self.current_drawing_coords.append((lat, lon))
            if len(self.current_drawing_coords) > 1:
                self.map_widget.set_path(self.current_drawing_coords, color="blue", width=2)
            return

        target = next((n for n in self.nodes if n['geometry'].x == lon and n['geometry'].y == lat), None)
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

        if self.current_mode == "Geofence":
            self.run_geofence(target)
            return

        if self.current_mode != "None": return
        ui_popups.DynamicEditorPopup(self, target, "Polygon", self.render_map, self.delete_item_callback)

    # ==========================================
    # SPATIAL ANALYSIS & ROUTING
    # ==========================================
    def run_geofence(self, target_poly):
        poly_geom = target_poly['geometry']
        selected_nodes = [n for n in self.nodes if poly_geom.contains(n['geometry'])]
        selected_edges = [e for e in self.edges if poly_geom.intersects(e['geometry'])]

        for n in selected_nodes: self.map_widget.set_marker(n['geometry'].y, n['geometry'].x,
                                                            marker_color_circle="yellow", marker_color_outside="orange")
        for e in selected_edges: self.map_widget.set_path([(y, x) for x, y in e['geometry'].coords], color="yellow",
                                                          width=4)

        name = target_poly['attributes'].get('Name', 'this zone')
        messagebox.showinfo("Geofence Results",
                            f"Found {len(selected_nodes)} points and {len(selected_edges)} lines interacting with '{name}'.")
        self.set_mode("None")

    def update_route_label(self):
        s_text = f"{self.route_start_coord[0]:.3f}, {self.route_start_coord[1]:.3f}" if self.route_start_coord else "Not Set"
        e_text = f"{self.route_end_coord[0]:.3f}, {self.route_end_coord[1]:.3f}" if self.route_end_coord else "Not Set"
        self.lbl_route.config(text=f"Start: {s_text}\nEnd: {e_text}")

    def clear_route(self):
        self.route_start_coord, self.route_end_coord = None, None
        if self.route_path_visual: self.route_path_visual.delete()
        for p in self.isochrone_paths_visual: p.delete()
        if self.isochrone_poly_visual: self.isochrone_poly_visual.delete()
        self.isochrone_paths_visual.clear()
        self.isochrone_poly_visual = None
        self.update_route_label()

    def calculate_route(self):
        if not self.route_start_coord or not self.route_end_coord: return
        try:
            route_coords, segment_count = network_engine.calculate_shortest_path(self.edges, self.route_start_coord,
                                                                                 self.route_end_coord)
            if self.route_path_visual: self.route_path_visual.delete()
            self.route_path_visual = self.map_widget.set_path(route_coords, color="magenta", width=5)
            messagebox.showinfo("Route Found!", f"Shortest path calculated across {segment_count} segments.")
        except ValueError as err:
            messagebox.showerror("Routing Error", str(err))

    def calculate_isochrone_area(self, start_coord):
        max_cost = askfloat("Service Area", "Enter maximum travel budget/cost (e.g., 10):", minvalue=0.1)
        if not max_cost: return
        try:
            for p in self.isochrone_paths_visual: p.delete()
            if self.isochrone_poly_visual: self.isochrone_poly_visual.delete()
            self.isochrone_paths_visual.clear()
            reachable_paths, hull_coords = network_engine.calculate_isochrone(self.edges, start_coord, max_cost)
            for path_coords in reachable_paths:
                visual = self.map_widget.set_path([(lat, lon) for lon, lat in path_coords], color="cyan", width=4)
                self.isochrone_paths_visual.append(visual)
            if hull_coords:
                self.isochrone_poly_visual = self.map_widget.set_polygon(hull_coords, fill_color="cyan",
                                                                         outline_color="teal", border_width=2)
            messagebox.showinfo("Success",
                                f"Service area calculated!\nFound {len(reachable_paths)} reachable road segments within a budget of {max_cost}.")
        except ValueError as err:
            messagebox.showerror("Error", str(err))

    # ==========================================
    # FILE I/O
    # ==========================================
    def export_to_web(self):
        if not self.nodes and not self.edges and not self.polygons: return
        try:
            filepath = web_export.generate_html_map(self.nodes, self.edges, self.polygons)
            messagebox.showinfo("Export Successful",
                                f"Web map generated and opened in your browser!\n\nSaved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def save_network(self):
        os.makedirs("shapefiles", exist_ok=True)
        try:
            if self.nodes: gpd.GeoDataFrame([{'geometry': n['geometry'], **n['attributes']} for n in self.nodes],
                                            crs="EPSG:4326").to_file("shapefiles/NetworkPoints.shp")
            if self.edges: gpd.GeoDataFrame([{'geometry': e['geometry'], **e['attributes']} for e in self.edges],
                                            crs="EPSG:4326").to_file("shapefiles/NetworkLines.shp")
            if self.polygons: gpd.GeoDataFrame([{'geometry': p['geometry'], **p['attributes']} for p in self.polygons],
                                               crs="EPSG:4326").to_file("shapefiles/NetworkPolygons.shp")
            messagebox.showinfo("Success", "Shapefiles exported!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save files: {e}")

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("All Supported", "*.shp *.kml *.geojson")])
        if not filepath: return
        try:
            points, lines, polys = file_handler.load_spatial_file(filepath)
            for p in points: self.nodes.append(
                {'NodeID': len(self.nodes) + 1, 'geometry': p['geometry'], 'attributes': {'Name': p['name']}})
            for l in lines: self.edges.append({'EdgeID': len(self.edges) + 1, 'geometry': l['geometry'],
                                               'attributes': {'Name': f"Line_{len(self.edges) + 1}", 'Speed': "50"}})
            for p in polys: self.polygons.append(
                {'PolygonID': len(self.polygons) + 1, 'geometry': p['geometry'], 'attributes': {'Name': p['name']}})
            self.render_map()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_map(self):
        if messagebox.askyesno("Confirm", "Clear everything?"):
            self.nodes.clear();
            self.edges.clear();
            self.polygons.clear()
            self.history.clear()
            self.clear_route();
            self.render_map()


if __name__ == "__main__":
    app = GISNetworkBuilder()
    app.mainloop()