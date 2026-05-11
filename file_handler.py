import geopandas as gpd
import fiona

# --- Enable KML Support ---
# By default, Geopandas might block KML reading. These lines force it to allow KMLs.
try:
    fiona.drvsupport.supported_drivers['KML'] = 'rw'
    fiona.drvsupport.supported_drivers['libkml'] = 'rw'
except Exception:
    pass


def load_spatial_file(filepath):
    """
    Reads a SHP, GeoJSON, or KML file.
    Returns three lists: points, lines, and polygons.
    """
    try:
        # Load the file into a GeoDataFrame
        gdf = gpd.read_file(filepath)

        # Reproject to standard GPS coordinates (Latitude/Longitude) if it isn't already
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        points = []
        lines = []
        polygons = []  # NEW: Array to hold polygons

        # Loop through every shape in the file and sort it
        for idx, row in gdf.iterrows():
            geom = row.geometry

            # Try to grab a 'Name' or 'id' attribute if the file has one
            name = row.get('Name', row.get('name', row.get('id', f"Imported_{idx}")))

            if geom is None:
                continue

            if geom.geom_type == 'Point':
                points.append({'name': str(name), 'geometry': geom})

            elif geom.geom_type in ['LineString', 'MultiLineString']:
                # Sometimes network lines are grouped. Break them apart.
                if geom.geom_type == 'MultiLineString':
                    for line in geom.geoms:
                        lines.append({'geometry': line})
                else:
                    lines.append({'geometry': geom})

            elif geom.geom_type in ['Polygon', 'MultiPolygon']:
                # Extract polygons and handle MultiPolygons
                if geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        polygons.append({'name': str(name), 'geometry': poly})
                else:
                    polygons.append({'name': str(name), 'geometry': geom})

        return points, lines, polygons

    except Exception as e:
        raise Exception(f"Failed to read file: {str(e)}")