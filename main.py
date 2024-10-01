import sys
import folium
import os
import requests
from PyQt6.QtCore import QUrl, QThread, QTimer
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer
from functools import partial
import shutil
import tempfile


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
    def __init__(self, cache_dir, online, *args, **kwargs):
        self.cache_dir = cache_dir
        self.online = online
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
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    with open(tile_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    if is_online():
                        # Only try to download tiles if online
                        tile_url = f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                        try:
                            response = requests.get(tile_url, stream=True)
                            if response.status_code == 200:
                                os.makedirs(os.path.dirname(tile_path), exist_ok=True)
                                with open(tile_path, 'wb') as tile_file:
                                    for chunk in response.iter_content(1024):
                                        tile_file.write(chunk)
                                self.send_response(200)
                                self.send_header('Content-Type', 'image/png')
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

    def run(self):
        handler = partial(TileServerHandler, self.cache_dir, self.online)
        self.httpd = HTTPServer(('localhost', self.port), handler)
        print(f"Starting tile server on port {self.port}")
        self.httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()
        print("Tile server stopped")

    def set_online_status(self, online):
        """Update the online status for the tile server."""
        self.online = online

class MapWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize the layout
        self.layout = QVBoxLayout(self)

        # Initialize the WebEngineView
        self.view = QWebEngineView(self)
        self.layout.addWidget(self.view)

        # Directory to store cached tiles
        self.cache_dir = per_resource_path('map_tiles')
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

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


    def closeEvent(self, event):
        # Stop the tile server when closing the application
        self.tile_server_thread.stop()
        self.tile_server_thread.wait()
        event.accept()

    def load_map(self):
        start_coords = (37.32500, -6.02884)  # Coordinates as an example

        # Create a folium map with the OpenStreetMap tiles (low-res)
        folium_map = folium.Map(
            location=start_coords,
            zoom_start=15,
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
        folium.Marker(start_coords, popup='Starting Point').add_to(folium_map)

        leaflet_css = resource_path('web_resources/css/leaflet.css')
        leaflet_js = resource_path('web_resources/js/leaflet.js')

        folium_map.get_root().header.add_child(folium.Element(f"""
            <link rel="stylesheet" href="file:///{leaflet_css}" />
        """))
        folium_map.get_root().html.add_child(folium.Element(f"""
            <script src="file:///{leaflet_js}"></script>
        """))


        # Save map data to an HTML file
        map_path = resource_path('map.html')
        # Get the system temp directory and save the map there
        temp_dir = tempfile.gettempdir()
        map_path = os.path.join(temp_dir, 'map.html')
        folium_map.save(map_path)


        # Enable local file access
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # Load the map into the QWebEngineView
        self.view.setUrl(QUrl.fromLocalFile(map_path))
        self.view.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self):
        # JavaScript code to ensure mapObject is globally accessible
        js_code = """
        if (typeof window.mapObject === 'undefined') {
            for (let key in window) {
                if (key.startsWith("map_") && window[key] instanceof L.Map) {
                    window.mapObject = window[key];  // Store globally accessible mapObject
                    break;
                }
            }
        }
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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the main window layout
        self.layout = QVBoxLayout(self)

        # Initialize and add the map widget to the window
        self.map_widget = MapWidget()

        self.layout.addWidget(self.map_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create the main window and show it
    window = MainWindow()
    window.setWindowTitle('QGroundControl-like Map App')
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())
