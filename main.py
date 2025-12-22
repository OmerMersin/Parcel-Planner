import sys
import folium
import os
import requests
from PyQt6.QtCore import QUrl, QThread, QTimer, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebChannel import QWebChannel
import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from functools import partial
import shutil
import tempfile
import configparser
import email.utils

def is_online():
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        pass
    return False

def resource_path(relative_path):
    """ Get absolute path to resource, works for PyInstaller executables """
    try:
        # PyInstaller creates a temp folder and stores resources in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # If not running in a PyInstaller bundle, use the current directory
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def per_resource_path(relative_path):
    """ Get absolute path to resource, works for development and for PyInstaller """
    try:
        # When running as an executable, use the folder where the .exe is located
        base_path = os.path.dirname(sys.executable)
    except AttributeError:
        # When running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class TileServerHandler(SimpleHTTPRequestHandler):
    session = requests.Session()

    def __init__(self, cache_dir, *args, **kwargs):
        self.cache_dir = cache_dir
        self.no_tile_image = resource_path("no_tile_found.png")
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.startswith('/tiles/'):
            path_parts = self.path.strip('/').split('/')
            if len(path_parts) == 4:
                _, z, x, y_png = path_parts
                y = y_png.replace('.png', '')
                tile_path = os.path.join(self.cache_dir, f'{z}_{x}_{y}.png')

                if os.path.exists(tile_path):
                    etag = f"\"{os.path.getmtime(tile_path)}-{os.path.getsize(tile_path)}\""
                    if self.headers.get("If-None-Match") == etag:
                        self.send_response(304)
                        self.send_header("ETag", etag)
                        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                        self.end_headers()
                        return

                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                    self.send_header("ETag", etag)
                    self.send_header("Last-Modified", email.utils.formatdate(os.path.getmtime(tile_path), usegmt=True))
                    self.end_headers()
                    with open(tile_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    online = getattr(self.server, "online", False)
                    if online:
                        # Only try to download tiles if online
                        tile_url = f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                        try:
                            response = TileServerHandler.session.get(tile_url, stream=True, timeout=(3, 20))
                            if response.status_code == 200:
                                os.makedirs(os.path.dirname(tile_path), exist_ok=True)
                                with open(tile_path, 'wb') as tile_file:
                                    for chunk in response.iter_content(1024):
                                        tile_file.write(chunk)
                                self.send_response(200)
                                self.send_header('Content-Type', 'image/png')
                                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                                etag = f"\"{os.path.getmtime(tile_path)}-{os.path.getsize(tile_path)}\""
                                self.send_header("ETag", etag)
                                self.end_headers()
                                with open(tile_path, 'rb') as f:
                                    self.wfile.write(f.read())
                            else:
                                print(f"Tile not available online: {z}/{x}/{y}")
                                self.serve_no_tile_found_image()
                        except requests.exceptions.RequestException as e:
                            print(f"Error downloading tile {z}/{x}/{y}: {e}")
                            self.serve_no_tile_found_image()
                    else:
                        print(f"Offline, serving 'No Tile Found' image for {z}/{x}/{y}")
                        self.serve_no_tile_found_image()
            else:
                self.send_error(404)


    def serve_no_tile_found_image(self):
        """Serve the 'No Tile Found' image from a writable location."""
        try:
            # Copy the no_tile_found.png to a writable temporary directory
            temp_dir = tempfile.gettempdir()
            temp_image_path = os.path.join(temp_dir, 'no_tile_found.png')

            # If the image doesn't already exist in the temp dir, copy it
            if not os.path.exists(temp_image_path):
                shutil.copy(self.no_tile_image, temp_image_path)

            # Now serve the copied image from the temp directory
            if os.path.exists(temp_image_path):
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    with open(temp_image_path, 'rb') as f:
                        self.wfile.write(f.read())
                except ConnectionAbortedError as e:
                    print(f"Connection was aborted by the client: {e}")
            else:
                self.send_error(404, "No tile found image not available.")
        except PermissionError as e:
            print(f"Permission Error: {e}")
            self.send_error(403, "Permission denied while trying to read no_tile_found.png.")
        except Exception as e:
            print(f"Error serving no_tile_found.png: {e}")
            self.send_error(500, "Error serving no_tile_found.png.")


class TileServerThread(QThread):
    def __init__(self, cache_dir, online, port=8000):
        super().__init__()
        self.cache_dir = cache_dir
        self.online = online
        self.no_tile_image = resource_path("no_tile_found.png")
        self.port = port
        self.httpd = None

    def run(self):
        handler = partial(TileServerHandler, self.cache_dir)
        # Threaded server improves tile loading speed significantly (many tiles requested in parallel)
        self.httpd = ThreadingHTTPServer(('localhost', self.port), handler)
        self.httpd.online = self.online
        print(f"Starting tile server on port {self.port}")
        self.httpd.serve_forever()

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
        print("Tile server stopped")

    def set_online_status(self, online):
        """Update the online status for the tile server."""
        self.online = online
        if self.httpd is not None:
            self.httpd.online = online

class MapWidget(QWidget):
    mapReady = pyqtSignal()
    cornerMoved = pyqtSignal(str, float, float)

    def __init__(self):
        super().__init__()

        # Initialize the layout
        self.layout = QVBoxLayout(self)

        # Initialize the WebEngineView
        self.view = QWebEngineView(self)
        self.layout.addWidget(self.view)

        # Enable persistent on-disk WebEngine cache (speeds up tile reloading significantly)
        try:
            profile = self.view.page().profile()
            web_cache_root = os.path.join(tempfile.gettempdir(), "ParcelPlanner", "qtwebengine")
            os.makedirs(web_cache_root, exist_ok=True)
            profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
            profile.setCachePath(os.path.join(web_cache_root, "cache"))
            profile.setPersistentStoragePath(os.path.join(web_cache_root, "storage"))
            profile.setHttpCacheMaximumSize(256 * 1024 * 1024)  # 256MB
        except Exception as e:
            print(f"Failed to enable WebEngine cache: {e}")

        # WebChannel bridge (used for draggable corner markers)
        self._bridge = _MapBridge()
        self._bridge.cornerMoved.connect(self.cornerMoved)
        self._web_channel = QWebChannel(self.view.page())
        self._web_channel.registerObject("bridge", self._bridge)
        self.view.page().setWebChannel(self._web_channel)

        # Directory to store cached tiles
        # Directory to store cached tiles (must be writable even in packaged builds)
        preferred_cache_dir = per_resource_path('map_tiles')
        try:
            os.makedirs(preferred_cache_dir, exist_ok=True)
            self.cache_dir = preferred_cache_dir
        except Exception:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "ParcelPlanner", "map_tiles")
            os.makedirs(self.cache_dir, exist_ok=True)

        self.no_tile_image = resource_path("no_tile_found.png")

        # Check if online
        self.online = is_online()

        # Start the tile server
        self.tile_server_port = 8000
        self.tile_server_thread = TileServerThread(self.cache_dir, self.online, port=self.tile_server_port)
        self.tile_server_thread.start()

        # Regularly check if the app is online
        self.timer = QTimer(self)
        self.timer.setInterval(5000)  # Check every 5 seconds
        self.timer.timeout.connect(self.check_connection)
        self.timer.start()

        self.satellite_layer = None
        # Config file handling
        self.config_file = per_resource_path("config.ini")
        self.map_coords, self.map_zoom = self.load_coordinates_from_config()

        # Create and load the map
        self.load_map()

    def check_connection(self):
        """Periodically check if the app is online and update the tile server."""
        is_now_online = is_online()
        if is_now_online != self.online:
            print(f"Connection status changed. Online: {is_now_online}")
            self.online = is_now_online
            self.tile_server_thread.set_online_status(self.online)
            if self.online:
                # Reload satellite tiles to fetch new tiles
                self.reload_satellite_tiles()

    def load_coordinates_from_config(self):
        config = configparser.ConfigParser()

        # Check if the config file exists
        if os.path.exists(self.config_file):
            print(f"Config file found at: {self.config_file}")
            config.read(self.config_file)
            
            # Debug: Print config sections
            print(f"Config sections: {config.sections()}")
            
            if 'Map' in config:
                # Attempt to get latitude, longitude, and zoom from the config file
                try:
                    lat = float(config.get("Map", "latitude"))
                    lon = float(config.get("Map", "longitude"))
                    zoom = int(config.get("Map", "zoom"))
                    print(f"Loaded from config: lat={lat}, lon={lon}, zoom={zoom}")
                    return (lat, lon), zoom
                except Exception as e:
                    print(f"Error reading config values: {e}")
                    # Return default values if there's an error
                    return (37.32500, -6.02884), 15
            else:
                print("No 'Map' section in the config file.")
                return (37.32500, -6.02884), 15
        else:
            print("Config file does not exist.")
            # Return default values if the file does not exist
            return (37.32500, -6.02884), 15

            
    def closeEvent(self, event):
        """Override the closeEvent to save map coordinates and close."""
        # Stop the tile server when closing the application
        self.tile_server_thread.stop()
        self.tile_server_thread.wait()
        event.accept()  # Accept the event to proceed with closing the window

    def load_map(self):
        # Reuse the generated HTML when possible (avoids slow folium regeneration on every run)
        temp_dir = tempfile.gettempdir()
        map_path = os.path.join(temp_dir, 'parcel_planner_map.html')
        if os.path.exists(map_path):
            self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            self.view.setUrl(QUrl.fromLocalFile(map_path))
            self.view.loadFinished.connect(self.on_load_finished)
            return

        # Create a folium map with the OpenStreetMap tiles (low-res)
        folium_map = folium.Map(
            location=self.map_coords,
            zoom_start=self.map_zoom,
            tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            control_scale=False,
            prefer_canvas=False,
            no_touch=False,
            disable_3d=False,
        )

        # Add the high-resolution satellite tile layer from the local tile server
        self.satellite_layer = folium.TileLayer(
            tiles=f'http://localhost:{self.tile_server_port}/tiles/{{z}}/{{x}}/{{y}}.png',
            attr='&copy; <a href="https://www.esri.com/en-us/home">Esri</a>',
            name='Esri Satellite',
            max_zoom=20,
            extra_options={'async': True}
        )
        self.satellite_layer.add_to(folium_map)

        # Add a marker to the map
        # folium.Marker(start_coords, popup='Starting Point').add_to(folium_map)

        leaflet_css = resource_path('web_resources/css/leaflet.css')
        leaflet_js = resource_path('web_resources/js/leaflet.js')

        folium_map.get_root().header.add_child(folium.Element(f"""
            <link rel="stylesheet" href="file:///{leaflet_css}" />
        """))
        folium_map.get_root().html.add_child(folium.Element(f"""
            <script src="file:///{leaflet_js}"></script>
        """))
        # Enable Qt WebChannel in the generated map so JS can call back into Python.
        folium_map.get_root().header.add_child(folium.Element("""
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        """))


        # Save map data to an HTML file (temp, writable)
        folium_map.save(map_path)


        # Enable local file access
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # Load the map into the QWebEngineView
        self.view.setUrl(QUrl.fromLocalFile(map_path))
        self.view.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self):
        # JavaScript code to ensure mapObject is globally accessible + set up bridge + corner markers
        js_code = """
        if (typeof window.mapObject === 'undefined') {
            for (let key in window) {
                if (key.startsWith("map_") && window[key] instanceof L.Map) {
                    window.mapObject = window[key];  // Store globally accessible mapObject
                    break;
                }
            }
        }

        // Initialize WebChannel bridge (if available)
        if (typeof window.bridge === 'undefined' && typeof QWebChannel !== 'undefined' && typeof qt !== 'undefined') {
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.bridge = channel.objects.bridge;
            });
        }

        // Draggable corner markers (A, B, C, D)
        if (typeof window.cornerMarkers === 'undefined') {
            window.cornerMarkers = {};
        }

        window.setCornerMarkers = function(corners) {
            if (!window.mapObject || !corners) return;

            const keys = Object.keys(corners);
            for (let idx = 0; idx < keys.length; idx++) {
                const name = keys[idx];
                const lat = corners[name][0];
                const lng = corners[name][1];

                if (!window.cornerMarkers[name]) {
                    const marker = L.marker([lat, lng], { draggable: true }).addTo(window.mapObject);
                    marker.bindTooltip(name, { permanent: true, direction: 'top', opacity: 0.9 });
                    marker.on('dragend', function(e) {
                        const pos = e.target.getLatLng();
                        if (window.bridge && window.bridge.updateCorner) {
                            window.bridge.updateCorner(name, pos.lat, pos.lng);
                        }
                    });
                    window.cornerMarkers[name] = marker;
                } else {
                    window.cornerMarkers[name].setLatLng([lat, lng]);
                }
            }

            // Fit bounds if we have at least 2 markers
            if (keys.length >= 2) {
                const latlngs = keys.map(k => window.cornerMarkers[k].getLatLng());
                const bounds = L.latLngBounds(latlngs);
                window.mapObject.fitBounds(bounds, { padding: [20, 20] });
            }
        };

        // One-shot click-to-set corner marker (used by Planner right panel)
        window.enableCornerPick = function(cornerName) {
            if (!window.mapObject || !cornerName) return;

            // Remove any previous pending handler by overwriting the target.
            window._cornerPickTarget = cornerName;

            window.mapObject.once('click', function(e) {
                const name = window._cornerPickTarget;
                const lat = e.latlng.lat;
                const lng = e.latlng.lng;

                // Ensure marker exists and move it
                if (!window.cornerMarkers) window.cornerMarkers = {};
                if (!window.cornerMarkers[name]) {
                    const marker = L.marker([lat, lng], { draggable: true }).addTo(window.mapObject);
                    marker.bindTooltip(name, { permanent: true, direction: 'top', opacity: 0.9 });
                    marker.on('dragend', function(ev) {
                        const pos = ev.target.getLatLng();
                        if (window.bridge && window.bridge.updateCorner) {
                            window.bridge.updateCorner(name, pos.lat, pos.lng);
                        }
                    });
                    window.cornerMarkers[name] = marker;
                } else {
                    window.cornerMarkers[name].setLatLng([lat, lng]);
                }

                if (window.bridge && window.bridge.updateCorner) {
                    window.bridge.updateCorner(name, lat, lng);
                }
            });
        };

        if (window._pendingCornerMarkers) {
            window.setCornerMarkers(window._pendingCornerMarkers);
            window._pendingCornerMarkers = null;
        }

        if (window._pendingCornerPick) {
            window.enableCornerPick(window._pendingCornerPick);
            window._pendingCornerPick = null;
        }
        """
        def _after_init(_result=None):
            try:
                self.update_map_center(self.map_coords[0], self.map_coords[1], self.map_zoom)
            except Exception:
                pass
            self.mapReady.emit()

        self.view.page().runJavaScript(js_code, _after_init)

    def set_corner_markers(self, corners):
        """
        corners: dict like {"A": (lat, lon), "B": (lat, lon), ...}
        """
        if not corners:
            return
        # Convert tuples to JS-friendly arrays
        corners_js = {k: [v[0], v[1]] for k, v in corners.items()}
        import json
        corners_json = json.dumps(corners_js)
        js_code = f"""
        (function() {{
            var corners = {corners_json};
            if (typeof window.setCornerMarkers === 'function') {{
                window.setCornerMarkers(corners);
            }} else {{
                window._pendingCornerMarkers = corners;
            }}
        }})();
        """
        self.view.page().runJavaScript(js_code)

    def enable_corner_pick(self, corner_name):
        """
        Arms the map so the next click places the given corner marker and reports back via the bridge.
        """
        if not corner_name:
            return
        import json
        corner_json = json.dumps(str(corner_name))
        js_code = f"""
        (function() {{
            var name = {corner_json};
            if (typeof window.enableCornerPick === 'function') {{
                window.enableCornerPick(name);
            }} else {{
                window._pendingCornerPick = name;
            }}
        }})();
        """
        self.view.page().runJavaScript(js_code)

    def reload_satellite_tiles(self):
        # JavaScript code to remove the existing satellite layer and add a new one
        js_code = """
        if (typeof window.satelliteLayer !== 'undefined') {
            window.mapObject.removeLayer(window.satelliteLayer);
        }
        window.satelliteLayer = L.tileLayer('http://localhost:{port}/tiles/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.esri.com/en-us/home">Esri</a>',
            maxZoom: 20,
            async: true
        }).addTo(window.mapObject);
        """.replace("{port}", str(self.tile_server_port))

        # Run the JavaScript to update the map
        self.view.page().runJavaScript(js_code)


    def update_map_center(self, lat, lon, zoom):
        # JavaScript code to update map center and zoom
        js_code = f"""
        window.mapObject.setView([{lat}, {lon}], {zoom});
        """
        self.view.page().runJavaScript(js_code)

    def generate_parcels(self, parcel_coordinates, center_lat, center_lon, zoom_level):
        """
        Generates parcel rectangles on the map and updates the map's center and zoom level.
        :param parcel_coordinates: List of coordinates representing the parcel corners
        :param center_lat: Latitude of the map center
        :param center_lon: Longitude of the map center
        :param zoom_level: Zoom level of the map
        """
        # Batch the parcel marker additions in one JavaScript call for performance
        js_code = "var parcels = [];\n"

        for i, parcel_info in enumerate(parcel_coordinates):
            coordinates = parcel_info['coordinates']  # Coordinates of each parcel
            color = parcel_info['color']  # Color for the parcel polygon
            js_code += f"""
            var parcelCoords{i} = {coordinates};
            var parcel{i} = L.polygon(parcelCoords{i}, {{
                color: '{color}',
                weight: 1,
                fillOpacity: 0.30
            }}).addTo(window.mapObject);
            parcels.push(parcel{i});
            """

        # Add JavaScript to update the map center and zoom level
        js_code += f"""
        window.mapObject.setView([{center_lat}, {center_lon}], {zoom_level});
        """

        # Run the generated JavaScript in one batch
        self.view.page().runJavaScript(js_code)

    def save_map_coordinates(self):
        js_code = """
        (function() {
            var center = window.mapObject.getCenter();
            var zoom = window.mapObject.getZoom();
            return [center.lat, center.lng, zoom];
        })();
        """

        def save_coords_in_config(coords):
            # Check if we have a valid result
            if isinstance(coords, list) and len(coords) == 3:
                lat, lon, zoom = coords
                print(f"Saving coordinates: lat={lat}, lon={lon}, zoom={zoom}")
                self.save_coordinates_to_config(lat, lon, zoom)
            else:
                print("Failed to retrieve valid coordinates.")

        self.view.page().runJavaScript(js_code, save_coords_in_config)


    def save_coordinates_to_config(self, lat, lon, zoom):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)

        config['Map'] = {
            'latitude': str(lat),
            'longitude': str(lon),
            'zoom': str(zoom)
        }
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)


class _MapBridge(QObject):
    cornerMoved = pyqtSignal(str, float, float)

    @pyqtSlot(str, float, float)
    def updateCorner(self, name, lat, lon):
        self.cornerMoved.emit(name, lat, lon)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the main window layout
        self.layout = QVBoxLayout(self)

        # Initialize and add the map widget to the window
        self.map_widget = MapWidget()

        self.layout.addWidget(self.map_widget)

    def closeEvent(self, event):
        """Override the closeEvent to save map coordinates and close."""
        self.map_widget.save_map_coordinates()  # Save coordinates before closing
        print("Close event triggered!")
        event.accept()  # Accept the event to proceed with closing the window


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create the main window and show it
    window = MainWindow()
    window.setWindowTitle('QGroundControl-like Map App')
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())
