import networkx as nx
from geopy.distance import geodesic
from shapely.geometry import MultiPoint


def build_graph(edges):
    """Helper function to build the mathematical graph from UI edges."""
    G = nx.Graph()
    for e in edges:
        coords = list(e['geometry'].coords)
        raw_weight = str(e['attributes'].get('Weight', 1.0))
        try:
            weight = float(raw_weight) if raw_weight.replace('.', '', 1).isdigit() else 1.0
        except ValueError:
            weight = 1.0
        G.add_edge(coords[0], coords[-1], weight=weight, path_coords=coords)
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

        path = nx.shortest_path(G, source=graph_start, target=graph_end, weight='weight')
        route_coords = []
        for u, v in zip(path[:-1], path[1:]):
            route_coords.extend([(lat, lon) for lon, lat in G.get_edge_data(u, v)['path_coords']])

        return route_coords, len(path) - 1
    except nx.NetworkXNoPath:
        raise ValueError("No path exists between these points.")


def calculate_isochrone(edges, start_coord, max_cost):
    """
    Finds all reachable paths within a certain 'cost' and generates a boundary shape.
    """
    G = build_graph(edges)
    if len(G.nodes) == 0: raise ValueError("No valid network edges.")

    graph_start = get_closest_node(G, start_coord)

    # 1. Ask NetworkX to find EVERY node within our budget limit
    reachable_nodes = nx.single_source_dijkstra_path_length(G, graph_start, cutoff=max_cost, weight='weight')

    # 2. Find all the edge paths that connect these reachable nodes
    reachable_paths = []
    for u, v, data in G.edges(data=True):
        if u in reachable_nodes and v in reachable_nodes:
            reachable_paths.append(data['path_coords'])

    # 3. Create a bounding shape (Convex Hull) around the reachable area
    hull_coords = []
    if len(reachable_nodes) >= 3:
        points = MultiPoint([(lon, lat) for lat, lon in reachable_nodes.keys()])
        hull = points.convex_hull
        if hull.geom_type == 'Polygon':
            hull_coords = [(lat, lon) for lon, lat in hull.exterior.coords]

    return reachable_paths, hull_coords