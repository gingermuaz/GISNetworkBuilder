import folium
from folium.plugins import HeatMap  # NEW: Import the HeatMap plugin
import os
import webbrowser

def generate_html_map(nodes, edges, polygons, output_filename="Network_WebMap.html"):
    if nodes:
        center_lat, center_lon = sum(n['geometry'].y for n in nodes) / len(nodes), sum(n['geometry'].x for n in nodes) / len(nodes)
    elif edges:
        center_lat, center_lon = edges[0]['geometry'].coords[0][1], edges[0]['geometry'].coords[0][0]
    else:
        center_lat, center_lon = 52.4862, -1.8904

    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles="CartoDB positron")

    # --- 1. Draw standard shapes (Polygons, Lines, Points) ---
    for p in polygons:
        coords = [(y, x) for x, y in p['geometry'].exterior.coords]
        popup_html = "<br>".join([f"<b>{k}:</b> {v}" for k, v in p['attributes'].items()])
        folium.Polygon(locations=coords, color="navy", fill=True, fill_color="#5288ae", fill_opacity=0.4, popup=folium.Popup(popup_html, max_width=300)).add_to(m)

    for e in edges:
        coords = [(y, x) for x, y in e['geometry'].coords]
        try: speed = float(e['attributes'].get('Speed', 50))
        except ValueError: speed = 50
        color = "green" if speed < 30 else "orange" if speed <= 60 else "red"
        popup_html = "<br>".join([f"<b>{k}:</b> {v}" for k, v in e['attributes'].items()])
        folium.PolyLine(locations=coords, color=color, weight=4, popup=folium.Popup(popup_html, max_width=300)).add_to(m)

    for n in nodes:
        popup_html = "<br>".join([f"<b>{k}:</b> {v}" for k, v in n['attributes'].items()])
        folium.CircleMarker(location=[n['geometry'].y, n['geometry'].x], radius=6, color="blue", fill=True, fill_color="white", fill_opacity=1, popup=folium.Popup(popup_html, max_width=300)).add_to(m)

    # --- 2. NEW: Generate the Density Heatmap Layer ---
    if nodes:
        heat_data = [[n['geometry'].y, n['geometry'].x] for n in nodes]
        HeatMap(heat_data, name="Point Density Heatmap", radius=20, blur=15, gradient={0.4: 'blue', 0.65: 'yellow', 1: 'red'}).add_to(m)

    # --- 3. Add a UI Layer Toggle to the Webpage ---
    folium.LayerControl().add_to(m)

    filepath = os.path.abspath(output_filename)
    m.save(filepath)
    webbrowser.open(f"file://{filepath}")
    return filepath