"""Polite map tile loading for tkintermapview.

OpenStreetMap's volunteer-run tile servers block apps that send a library's default
User-Agent. tkintermapview always sends "TkinterMapView", which is why the OpenStreetMap
base map showed "403 Access blocked". The tile usage policy
(https://operations.osmfoundation.org/policies/tiles/) also asks apps to:
  * cache tiles (following the server's cache headers, or at least 7 days),
  * revalidate expired tiles with If-None-Match / If-Modified-Since rather than re-download,
  * only fetch the tiles being viewed plus a modest look-ahead (no bulk prefetching),
  * show "(c) OpenStreetMap contributors" on the map.

This module does all four:
  * install() routes tkintermapview's downloads through TileFetcher, which sends a
    User-Agent that identifies this app and keeps a disk cache of OpenStreetMap tiles,
  * PoliteMapView limits the library's background prefetch (up to 8 rings of tiles,
    roughly 289 tiles every time the map moves) to one ring around the visible area for
    OpenStreetMap, and shows the attribution whenever an OpenStreetMap base map is active.
"""
import email.utils
import hashlib
import io
import json
import math
import os
import re
import threading
import time
import tkinter as tk
from urllib.parse import urlparse

import requests
import tkintermapview
from tkintermapview import map_widget as _tmv_map_widget

APP_NAME = "GISNetworkBuilder"
APP_VERSION = "1.0"
APP_URL = "https://github.com/gingermuaz/GISNetworkBuilder"
# Stable app name + a way to get in touch; bump the version with each release
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (+{APP_URL})"

OSM_ATTRIBUTION = "© OpenStreetMap contributors"
DEFAULT_MAX_AGE_SEC = 7 * 24 * 3600  # used when the server sends no cache headers
TIMEOUT_SEC = 15


def is_osm_host(host):
    host = (host or "").lower()
    return host == "tile.openstreetmap.org" or host.endswith(".tile.openstreetmap.org")


def default_cache_dir():
    """Per-user cache folder, e.g. %LOCALAPPDATA%\\GISNetworkBuilder\\tiles on Windows."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, APP_NAME, "tiles")


def _max_age(headers):
    """Seconds a tile may be reused for, from Cache-Control / Expires (default 7 days)."""
    m = re.search(r"max-age=(\d+)", headers.get("Cache-Control", ""))
    if m:
        return int(m.group(1))
    expires = headers.get("Expires")
    if expires:
        try:
            return max(0.0, email.utils.parsedate_to_datetime(expires).timestamp() - time.time())
        except (TypeError, ValueError):
            pass
    return DEFAULT_MAX_AGE_SEC


class _Response:
    """The small part of requests.Response that tkintermapview uses (it reads .raw)."""

    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code
        self.raw = io.BytesIO(content)


class TileFetcher:
    """Stands in for the `requests` module inside tkintermapview's map widget."""

    exceptions = requests.exceptions  # the widget catches requests.exceptions.ConnectionError

    def __init__(self, cache_dir=None, user_agent=USER_AGENT):
        self.cache_dir = cache_dir or default_cache_dir()
        self.user_agent = user_agent
        self._local = threading.local()  # one HTTP session per thread (the widget uses two threads)

    def _session(self):
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers["User-Agent"] = self.user_agent
            self._local.session = session
        return session

    def get(self, url, stream=False, headers=None, **kwargs):
        # tkintermapview passes headers={"User-Agent": "TkinterMapView"}; that is deliberately ignored
        if is_osm_host(urlparse(url).hostname):
            return self._get_cached(url)
        r = self._session().get(url, timeout=TIMEOUT_SEC)
        return _Response(r.content, r.status_code)

    # --- disk cache (OpenStreetMap tiles only) -------------------------------------------------

    def _paths(self, url):
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()
        folder = os.path.join(self.cache_dir, key[:2])
        return os.path.join(folder, key + ".tile"), os.path.join(folder, key + ".json")

    def _write(self, path, blob):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
            with open(tmp, "wb") as f:
                f.write(blob)
            os.replace(tmp, path)  # atomic, so two threads can't leave half a file behind
        except OSError:
            pass  # a cache that can't be written must never stop the map working

    def _get_cached(self, url):
        data_path, meta_path = self._paths(url)
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            with open(data_path, "rb") as f:
                data = f.read()
        except (OSError, ValueError):
            meta, data = {}, None

        if data is not None and time.time() < meta.get("expires", 0):
            return _Response(data)  # still fresh: no request at all

        headers = {}
        if data is not None:  # expired: ask the server whether the tile changed
            if meta.get("etag"):
                headers["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                headers["If-Modified-Since"] = meta["last_modified"]
        try:
            r = self._session().get(url, headers=headers, timeout=TIMEOUT_SEC)
        except requests.exceptions.RequestException:
            if data is not None:
                return _Response(data)  # offline: an old tile beats a blank one
            raise

        if r.status_code == 304 and data is not None:
            meta["expires"] = time.time() + _max_age(r.headers)
            self._write(meta_path, json.dumps(meta).encode("utf-8"))
            return _Response(data)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image/"):
            meta = {"url": url, "expires": time.time() + _max_age(r.headers),
                    "etag": r.headers.get("ETag"), "last_modified": r.headers.get("Last-Modified")}
            self._write(data_path, r.content)
            self._write(meta_path, json.dumps(meta).encode("utf-8"))
            return _Response(r.content)
        # Anything else (e.g. a 403 "blocked" tile) is never cached
        return _Response(data) if data is not None else _Response(r.content, r.status_code)


_fetcher = None


def install(cache_dir=None):
    """Route all of tkintermapview's tile downloads through TileFetcher. Call once at start-up."""
    global _fetcher
    if _fetcher is None:
        _fetcher = TileFetcher(cache_dir)
        _tmv_map_widget.requests = _fetcher  # the widget calls requests.get(...) for every tile
    return _fetcher


class PoliteMapView(tkintermapview.TkinterMapView):
    """TkinterMapView that prefetches less for OpenStreetMap and shows its attribution."""

    LOOKAHEAD_TILES = 1  # tiles fetched beyond the visible area ("modest look-ahead")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attribution = tk.Label(self, text=OSM_ATTRIBUTION, font=("Arial", 8),
                                     bg="#ffffff", fg="#333333", padx=4, pady=1)
        self._update_attribution()

    def _osm_active(self):
        return is_osm_host(urlparse(self.tile_server).hostname)

    def _update_attribution(self):
        label = getattr(self, "_attribution", None)
        if label is None:
            return
        if self._osm_active():
            label.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")
            label.lift()
        else:
            label.place_forget()

    def set_tile_server(self, tile_server, tile_size=256, max_zoom=19):
        super().set_tile_server(tile_server, tile_size=tile_size, max_zoom=max_zoom)
        self._update_attribution()

    def _in_lookahead(self, zoom, x, y):
        """Is tile (x, y) at this zoom on screen or within LOOKAHEAD_TILES of it?"""
        if zoom != round(self.zoom):
            return False
        n = self.LOOKAHEAD_TILES
        x0, y0 = self.upper_left_tile_pos
        x1, y1 = self.lower_right_tile_pos
        return (math.floor(x0) - n <= x <= math.floor(x1) + n and
                math.floor(y0) - n <= y <= math.floor(y1) + n)

    def request_image(self, zoom, x, y, db_cursor=None):
        # The library's prefetch thread works outwards up to 8 rings from the centre. For
        # OpenStreetMap, skip anything beyond the look-ahead (skipped tiles aren't cached, so
        # they still load normally if the user pans to them).
        if (threading.current_thread() is getattr(self, "pre_cache_thread", None)
                and self._osm_active() and not self._in_lookahead(zoom, x, y)):
            return self.empty_tile_image
        return super().request_image(zoom, x, y, db_cursor=db_cursor)
