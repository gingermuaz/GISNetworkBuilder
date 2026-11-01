import math
from collections import Counter, defaultdict

import networkx as nx
from geopy.distance import geodesic
from shapely.geometry import LineString, MultiPoint, Point
from shapely.strtree import STRtree

# How close (in degrees, about 1 mm) a line end or shared vertex must be to another line to join them
NODE_TOL_DEG = 1e-8

# Values used by a line's "Direction" attribute (also offered in the editor dropdown in ui_popups.py)
TWO_WAY = "Two-Way"
ONE_WAY_A_TO_B = "One-Way (A to B)"  # A = the first point drawn, B = the last
ONE_WAY_B_TO_A = "One-Way (B to A)"

NO_ROADS_MSG = ("There are no roads in this project to route along.\n\n"
                "Routing only uses roads you have drawn or imported - not the roads shown on the "
                "background map. Draw some with Draw > Draw Line, or load real streets with "
                "Layers > Import OSM Data.")


def direction_of(attributes):
    """Return 'both', 'forward' (A to B) or 'backward' (B to A) from a line's Direction attribute."""
    d = str(attributes.get('Direction', TWO_WAY)).strip().lower()
    if not d.startswith('one'):
        return 'both'
    return 'backward' if ('b to a' in d or '-1' in d) else 'forward'


def line_length_m(coords):
    """Geodesic length in metres of a list of (lon, lat) coordinates."""
    # geopy expects (lat, lon) but shapely stores (lon, lat), so swap each pair
    return sum(geodesic((coords[i][1], coords[i][0]), (coords[i + 1][1], coords[i + 1][0])).meters
               for i in range(len(coords) - 1))


# --- Snapping ------------------------------------------------------------------------------

def _metres_per_degree(lat):
    """(metres per degree of longitude, metres per degree of latitude) around a given latitude."""
    return 111_320.0 * math.cos(math.radians(lat)), 110_574.0


def snap_coordinate(lon, lat, tol_m, vertices, lines):
    """Snap a clicked (lon, lat) onto existing geometry within tol_m metres.

    The nearest existing vertex (an asset point, a line vertex or a polygon corner) wins. If none is
    in range, the click snaps onto the nearest position along a line, so a new road can join an
    existing road part-way along it (routing then treats that spot as a junction).
    Returns the snapped (lon, lat), or None when nothing is within range.
    """
    if not tol_m or tol_m <= 0:
        return None
    kx, ky = _metres_per_degree(lat)
    dlon, dlat = tol_m / kx, tol_m / ky

    best, best_d = None, tol_m
    for c in vertices:
        x, y = c[0], c[1]
        if abs(x - lon) > dlon or abs(y - lat) > dlat:
            continue
        d = math.hypot((x - lon) * kx, (y - lat) * ky)
        if d <= best_d:
            best, best_d = (x, y), d
    if best is not None:
        return best

    for line in lines:
        minx, miny, maxx, maxy = line.bounds
        if lon < minx - dlon or lon > maxx + dlon or lat < miny - dlat or lat > maxy + dlat:
            continue
        cs = list(line.coords)
        for (x1, y1, *_), (x2, y2, *_) in zip(cs, cs[1:]):
            # Work in local metres relative to the click, then map the answer back to degrees
            ax, ay = (x1 - lon) * kx, (y1 - lat) * ky
            dx, dy = (x2 - x1) * kx, (y2 - y1) * ky
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / seg2))
            d = math.hypot(ax + t * dx, ay + t * dy)
            if d <= best_d:
                best, best_d = (x1 + t * (x2 - x1), y1 + t * (y2 - y1)), d
    return best


# --- Graph building ------------------------------------------------------------------------

def _approx_length_m(coords):
    """Quick flat-earth length in metres - plenty for comparing pieces of the same street."""
    kx, ky = _metres_per_degree(coords[0][1])
    return sum(math.hypot((b[0] - a[0]) * kx, (b[1] - a[1]) * ky) for a, b in zip(coords, coords[1:]))


def _point_on_segment(a, b, c, tol=NODE_TOL_DEG):
    """Position (0-1) of point c along segment a-b if c lies strictly inside it, otherwise None."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    seg2 = dx * dx + dy * dy
    if seg2 == 0:
        return None
    t = ((c[0] - a[0]) * dx + (c[1] - a[1]) * dy) / seg2
    if t <= 0 or t >= 1:
        return None
    if math.hypot(c[0] - (a[0] + t * dx), c[1] - (a[1] + t * dy)) > tol:
        return None
    return t


def _split_coords(coords, cuts):
    """Split a line's (lon, lat) coords at the cut points that lie on it. Returns a list of pieces."""
    pieces, current = [], [coords[0]]
    last = len(coords) - 1
    for i in range(last):
        a, b = coords[i], coords[i + 1]
        on_segment = []
        for c in cuts:
            t = _point_on_segment(a, b, c)
            if t is not None:
                on_segment.append((t, c))
        for _, c in sorted(on_segment):  # a junction part-way along this segment
            if c != current[-1]:
                current.append(c)
            if len(current) > 1:
                pieces.append(current)
            current = [c]
        if b != current[-1]:
            current.append(b)
        if i + 1 < last and b in cuts and len(current) > 1:  # a junction at one of the line's own vertices
            pieces.append(current)
            current = [b]
    if len(current) > 1:
        pieces.append(current)
    return pieces


def _split_at_junctions(lines_coords):
    """For each line, return its pieces after splitting it wherever another line ends on it
    (a T-junction) or where it shares a vertex with another line.

    Lines that merely cross without a shared vertex are left alone, because that could be a
    bridge or an underpass. Snap a vertex onto the other road to make a real crossroads.
    """
    vertex_use = Counter()
    for coords in lines_coords:
        vertex_use.update(set(coords))
    junctions = {c for coords in lines_coords for c in (coords[0], coords[-1])}
    junctions.update(c for c, n in vertex_use.items() if n > 1)
    junctions = list(junctions)

    tree = STRtree([LineString(c) for c in lines_coords])
    pt_idx, line_idx = tree.query([Point(j) for j in junctions], predicate='dwithin', distance=NODE_TOL_DEG)
    cuts = defaultdict(set)
    for p, li in zip(pt_idx, line_idx):
        j, coords = junctions[p], lines_coords[li]
        if j != coords[0] and j != coords[-1]:
            cuts[li].add(j)
    return [_split_coords(c, cuts[i]) if i in cuts else [c] for i, c in enumerate(lines_coords)]


def _add_edge(G, coords, travel_time_sec):
    u, v = coords[0], coords[-1]
    if u == v:
        return  # a closed loop with no junction on it can't be part of a route
    # If two roads join the same pair of junctions, keep the faster one
    if G.has_edge(u, v) and G[u][v]['weight'] <= travel_time_sec:
        return
    G.add_edge(u, v, weight=travel_time_sec, path_coords=coords)


def build_graph(edges):
    """Build a directed, travel-time weighted graph from the UI edges.

    Junctions are line ends, T-junctions (a line ending part-way along another line) and vertices
    shared by two lines. One-way roads (Direction attribute) only get an edge in their direction
    of travel. The user's own lines are never modified - the splitting happens on copies.
    """
    G = nx.DiGraph()
    lines, line_attrs = [], []
    for e in edges:
        coords = []
        for c in e['geometry'].coords:
            c = (c[0], c[1])  # ignore any Z (height) values
            if not coords or c != coords[-1]:
                coords.append(c)
        if len(coords) >= 2:
            lines.append(coords)
            line_attrs.append(e['attributes'])
    if not lines:
        return G

    for coords, attrs, pieces in zip(lines, line_attrs, _split_at_junctions(lines)):
        # 1. Physical length of the street in metres (the Length_m attribute if set, else measured)
        try:
            length_attr = float(attrs.get('Length_m') or 0)
        except (TypeError, ValueError):
            length_attr = 0  # blank or non-numeric value typed into the editor
        if not length_attr > 0:  # also catches NaN
            length_attr = 0

        if len(pieces) == 1 and length_attr:
            piece_lengths = [length_attr]
        elif length_attr:
            # Share the recorded Length_m out between the pieces in proportion to their size
            shares = [_approx_length_m(p) for p in pieces]
            total = sum(shares)
            piece_lengths = ([length_attr * s / total for s in shares] if total > 0
                             else [length_attr / len(pieces)] * len(pieces))
        else:
            piece_lengths = [line_length_m(p) for p in pieces]

        # 2. Speed limit (default 30 mph for council streets), converted to metres per second
        try:
            speed_mph = float(attrs.get('Speed', 30))
        except (TypeError, ValueError):
            speed_mph = 30
        if math.isnan(speed_mph):
            speed_mph = 30
        if speed_mph <= 0:
            speed_mph = 1  # prevent division by zero
        speed_mps = speed_mph * 0.44704

        # 3. Travel time in seconds (time = distance / speed) is the routing weight
        direction = direction_of(attrs)
        for piece, length_m in zip(pieces, piece_lengths):
            travel_time_sec = length_m / speed_mps
            if direction in ('both', 'forward'):
                _add_edge(G, piece, travel_time_sec)
            if direction in ('both', 'backward'):
                _add_edge(G, piece[::-1], travel_time_sec)
    return G


def get_closest_node(G, target_coord):
    """Finds the closest mathematical node to a user's map click."""
    # A flat-earth distance picks the same nearest junction as a geodesic one at street scale,
    # and is ~100x faster on large OSM imports
    lon0, lat0 = target_coord[0], target_coord[1]
    kx, ky = _metres_per_degree(lat0)
    return min(G.nodes, key=lambda n: ((n[0] - lon0) * kx) ** 2 + ((n[1] - lat0) * ky) ** 2)


def calculate_shortest_path(edges, start_coord, end_coord):
    G = build_graph(edges)
    if len(G.nodes) == 0: raise ValueError(NO_ROADS_MSG)

    try:
        graph_start = get_closest_node(G, start_coord)
        graph_end = get_closest_node(G, end_coord)
        if graph_start == graph_end:
            raise ValueError("Start and end snap to the same junction - pick points further apart.")

        # Calculate the path and the total time it takes (one Dijkstra run gives both)
        total_time_sec, path = nx.single_source_dijkstra(G, graph_start, graph_end, weight='weight')

        route_coords = []
        for u, v in zip(path[:-1], path[1:]):
            seg = G.edges[u, v]['path_coords']
            if seg[0] != u:  # safety net: draw every piece in the direction of travel
                seg = seg[::-1]
            seg_latlon = [(lat, lon) for lon, lat in seg]
            if route_coords and route_coords[-1] == seg_latlon[0]:
                seg_latlon = seg_latlon[1:]  # don't repeat the shared junction vertex
            route_coords.extend(seg_latlon)

        return route_coords, len(path) - 1, total_time_sec
    except nx.NetworkXNoPath:
        raise ValueError("No path exists between these points.\n\n"
                         "Check that the roads are joined and that one-way streets allow this journey.")


def calculate_isochrone(edges, start_coord, max_time_sec):
    """
    Finds all roads that can be fully driven within a TIME limit and generates a boundary.
    """
    G = build_graph(edges)
    if len(G.nodes) == 0: raise ValueError(NO_ROADS_MSG)

    graph_start = get_closest_node(G, start_coord)

    # Ask NetworkX for the travel time to EVERY junction within our time budget
    reachable_nodes = nx.single_source_dijkstra_path_length(G, graph_start, cutoff=max_time_sec, weight='weight')

    reachable_paths, seen = [], set()
    for u, v, data in G.edges(data=True):
        if u in reachable_nodes and reachable_nodes[u] + data['weight'] <= max_time_sec:
            key = frozenset((u, v))
            if key not in seen:  # draw two-way roads once, not once per direction
                seen.add(key)
                reachable_paths.append(data['path_coords'])

    hull_coords = []
    if len(reachable_nodes) >= 3:
        # Graph nodes are already (lon, lat), so use them as-is for the hull
        points = MultiPoint(list(reachable_nodes.keys()))
        hull = points.convex_hull
        if hull.geom_type == 'Polygon':
            hull_coords = [(lat, lon) for lon, lat in hull.exterior.coords]  # tkintermapview wants (lat, lon)

    return reachable_paths, hull_coords
