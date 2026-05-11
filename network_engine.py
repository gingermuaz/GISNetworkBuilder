import networkx as nx
from geopy.distance import geodesic
from shapely.geometry import MultiPoint


def build_graph(edges):
    """Helper function to build the mathematical graph from UI edges."""
    G = nx.Graph()
    for e in edges:
        coords = list(e['geometry'].coords)

        # 1. Get the physical length of the street in meters
        length_m = float(e['attributes'].get('Length_m', 0))
        if length_m == 0:
            length_m = sum(geodesic(coords[i], coords[i + 1]).meters for i in range(len(coords) - 1))

        # 2. Get the speed limit (Default to 30mph for council streets)
        try:
            speed_mph = float(e['attributes'].get('Speed', 30))
        except ValueError:
            speed_mph = 30

        if speed_mph <= 0: speed_mph = 1  # Prevent division by zero

        # 3. Convert mph to meters per second
        speed_mps = speed_mph * 0.44704

        # 4. Calculate Travel Time in Seconds (Time = Distance / Speed)
        travel_time_sec = length_m / speed_mps

        # Use TRAVEL TIME as the mathematical weight instead of arbitrary numbers
        G.add_edge(coords[0], coords[-1], weight=travel_time_sec, path_coords=coords)

    return G


def get_closest_node(G, target_coord):
    """Finds the closest mathematical node to a user's map click."""
    return min(G.nodes, key=lambda n: geodesic((n[1], n[0]), (target_coord[1], target_coord[0])).meters)


def calculate_shortest_path(edges, start_coord, end_coord):
    G = build_graph(edges)
    if len(G.nodes) == 0: raise ValueError("No valid edges to route through.")

    try:
        graph_start = get_closest_node(G, start_coord)
        graph_end = get_closest_node(G, end_coord)

        # Calculate the path and the total time it takes
        path = nx.shortest_path(G, source=graph_start, target=graph_end, weight='weight')
        total_time_sec = nx.shortest_path_length(G, source=graph_start, target=graph_end, weight='weight')

        route_coords = []
        for u, v in zip(path[:-1], path[1:]):
            route_coords.extend([(lat, lon) for lon, lat in G.get_edge_data(u, v)['path_coords']])

        return route_coords, len(path) - 1, total_time_sec  # Return the time!
    except nx.NetworkXNoPath:
        raise ValueError("No path exists between these points.")


def calculate_isochrone(edges, start_coord, max_time_sec):
    """
    Finds all reachable paths within a certain TIME limit and generates a boundary.
    """
    G = build_graph(edges)
    if len(G.nodes) == 0: raise ValueError("No valid network edges.")

    graph_start = get_closest_node(G, start_coord)

    # Ask NetworkX to find EVERY node within our Time Budget
    reachable_nodes = nx.single_source_dijkstra_path_length(G, graph_start, cutoff=max_time_sec, weight='weight')

    reachable_paths = []
    for u, v, data in G.edges(data=True):
        if u in reachable_nodes and v in reachable_nodes:
            reachable_paths.append(data['path_coords'])

    hull_coords = []
    if len(reachable_nodes) >= 3:
        points = MultiPoint([(lon, lat) for lat, lon in reachable_nodes.keys()])
        hull = points.convex_hull
        if hull.geom_type == 'Polygon':
            hull_coords = [(lat, lon) for lon, lat in hull.exterior.coords]

    return reachable_paths, hull_coords