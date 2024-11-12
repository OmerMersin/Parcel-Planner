import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget, QSplitter, QLabel, QLineEdit, QFormLayout, QPushButton, QGridLayout, QSizePolicy, QRadioButton, QMessageBox, QToolBar, QFileDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QAction
import math
from parcel_main import app_state
from parcel_gen import ParcelGenerator
import os
import configparser
import time
from parcel_main import ColorButtonWidget
import logging
import json
from main import MapWidget
from PyQt6.QtCore import QTranslator, QLocale
# Carry only appstate between windows V
# Fix to create mission with original paths for spray on and off V
# RESTORE APP STATE DOESNT PROTECT THE PARAMS OF THE LAST BUTTON V
# S and F for markers V
# Restore is not fully successfull. restore on main screen and pass planner and play with fit function V

# Double quit on toolbar V
# save tiles but no reload 
# gap when passed to planner V

# Get the logger instance
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """ Get absolute path to resource, works for development and for PyInstaller """
    try:
        # When running as an executable, use the folder where the .exe is located
        base_path = os.path.dirname(sys.executable)
    except AttributeError:
        # When running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def temp_resource_path(relative_path):
    """ Get absolute path to resource, works for development and for PyInstaller. """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS when running in a bundle
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Define the paths to 'missions' and 'reports' directories
missions_dir = resource_path('missions')
reports_dir = resource_path('reports')

# Create the directories if they don't already exist
if not os.path.exists(missions_dir):
    os.makedirs(missions_dir)

if not os.path.exists(reports_dir):
    os.makedirs(reports_dir)

        
class PlannerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.debug("PlannerMainWindow initialized")
        self.translator = QTranslator()
        self.setWindowTitle("Parcel Planner")
        self.translator = QTranslator()
        self.colored_parcels = {}
        self.parcel_js_references = []
        self.parcel_marker_js_references = []
        self.parcel_coordinates = None
        self.current_color = None
        self.path_coordinates = []
        self.paths_by_color = {}
        self.path = None
        self.button_name = None
        self.button_params = {}
        self.parcel_points_by_color = {}

        # Replace the ParcelField with a QWebEngineView for the map
        logger.debug("map initialized")
        # self.map_view = QWebEngineView()
        # self.map_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # self.map_view.setUrl(QUrl("http://localhost:8000/map.html"))
        self.map_widget = MapWidget()


        self.file_opened = False
        self.prev_button = None
        self.acc_buffer = 2.0
    
        logger.debug("Setting up UI")
        self.create_toolbar()
        form_layout = QFormLayout()
        self.current_path = None
        self.current_start_marker = None
        self.current_end_marker = None

        self.clear_button = QPushButton(self.tr("Clear Parcels"))
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_parcels)

        self.back_button = QPushButton(self.tr("Previous Window"))
        self.back_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.back_button.clicked.connect(self.back)
        form_layout.addRow(self.back_button)

        self.top_left = QLabel(self.tr("Coordinate A"))
        self.top_left_lat = QLabel("lat:")
        self.top_left_lat_input = QLineEdit("37.32500")
        self.top_left_lon = QLabel("lon:")
        self.top_left_lon_input = QLineEdit("-6.02884")
        self.top_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hbox = QHBoxLayout()
        hbox.addWidget(self.top_left)
        hbox.addWidget(self.top_left_lat)
        hbox.addWidget(self.top_left_lat_input)
        hbox.addWidget(self.top_left_lon)
        hbox.addWidget(self.top_left_lon_input)
        form_layout.addRow(hbox)

        self.top_right = QLabel(self.tr("Coordinate B"))
        self.top_right_lat = QLabel("lat:")
        self.top_right_lat_input = QLineEdit("37.32490")
        self.top_right_lon = QLabel("lon:")
        self.top_right_lon_input = QLineEdit("-6.02861")
        self.top_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hbox = QHBoxLayout()
        hbox.addWidget(self.top_right)
        hbox.addWidget(self.top_right_lat)
        hbox.addWidget(self.top_right_lat_input)
        hbox.addWidget(self.top_right_lon)
        hbox.addWidget(self.top_right_lon_input)
        form_layout.addRow(hbox)

        self.bot_left = QLabel(self.tr("Coordinate C"))
        self.bot_left_lat = QLabel("lat:")
        self.bot_left_lat_input = QLineEdit("37.32466")
        self.bot_left_lon = QLabel("lon:")
        self.bot_left_lon_input = QLineEdit("-6.02899")
        self.bot_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hbox = QHBoxLayout()
        hbox.addWidget(self.bot_left)
        hbox.addWidget(self.bot_left_lat)
        hbox.addWidget(self.bot_left_lat_input)
        hbox.addWidget(self.bot_left_lon)
        hbox.addWidget(self.bot_left_lon_input)
        form_layout.addRow(hbox)


        self.bot_right = QLabel(self.tr("Coordinate D"))
        self.bot_right_lat = QLabel("lat:")
        self.bot_right_lat_input = QLineEdit("37.32427")
        self.bot_right_lon = QLabel("lon:")
        self.bot_right_lon_input = QLineEdit("-6.02829")
        self.bot_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hbox = QHBoxLayout()
        hbox.addWidget(self.bot_right)
        hbox.addWidget(self.bot_right_lat)
        hbox.addWidget(self.bot_right_lat_input)
        hbox.addWidget(self.bot_right_lon)
        hbox.addWidget(self.bot_right_lon_input)
        form_layout.addRow(hbox)

        self.spraying_width = QLabel(self.tr("Spraying Width"))
        self.spraying_width_input = QLineEdit("1.5")
        self.spraying_width.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.spraying_width_input.textChanged.connect(self.update_spray_width)
        form_layout.addRow(self.spraying_width, self.spraying_width_input)

        self.fit = QRadioButton()
        self.fit.setText(self.tr("Do you want parcels to fit the area?"))
        form_layout.addRow(self.fit)


        self.save_button = QPushButton(self.tr("Process"))
        self.save_button.clicked.connect(self.save)
        self.save_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form_layout.addWidget(self.save_button)
        

        self.generate_report = QPushButton(self.tr("Generate Report"))
        self.generate_report.clicked.connect(self.report)
        self.generate_report.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.button_names = {i: f"{i}" for i in range(1, 11)}  # Adjust range based on the number of buttons

        self.generate_mission = QPushButton(self.tr("Save the mission"))
        self.generate_mission.clicked.connect(lambda: self.create_mavlink_script(self.path))
        self.generate_mission.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


        
        self.total_length_label = QLabel(self.tr("Total Path Length: 0 meters"))
        self.total_length_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout.addRow(self.clear_button)
        form_layout.addRow(self.total_length_label)

        right_panel = QWidget()
        right_panel.setLayout(form_layout)

        # Create the color buttons
        self.color_buttons = []
        self.color_button_widgets = []
        self.color_layout = QGridLayout()

                # Mapping Qt.GlobalColor to color names as strings for use in stylesheets
        colors = [
            (Qt.GlobalColor.red, "#ff0000"), 
            (Qt.GlobalColor.blue, "#0000ff"),
            (Qt.GlobalColor.yellow, "#ffff00"), 
            (Qt.GlobalColor.cyan, "#00ffff"),
            (Qt.GlobalColor.magenta, "#ff00ff"), 
            (Qt.GlobalColor.gray, "#808080"),
            (Qt.GlobalColor.darkRed, "#8b0000"), 
            (Qt.GlobalColor.darkGreen, "#006400"),
            (Qt.GlobalColor.darkBlue, "#00008b"), 
            (Qt.GlobalColor.darkYellow, "#b8860b")
        ]

        self.params = {
            'application_dose': 300,
            'nozzle_rate': 0.8,
            'nozzle_number': 4,
            'altitude': 25
            }

        for i, (color, color_name) in enumerate(colors):
            button_name = self.button_names[i + 1]
            color_button_widget = ColorButtonWidget(i + 1, color_name, button_name=button_name)
            self.color_layout.addWidget(color_button_widget, i // 2, i % 2)
            self.color_buttons.append(color_button_widget)
            self.color_button_widgets.append(color_button_widget)  # Store the reference
            color_button_widget.button.clicked.connect(lambda _, b=color_button_widget, col=color_name: self.set_current_color(b, col))
            color_button_widget.button_named.connect(lambda button_name=i: self.set_button_names(button_name))
            self.button_params[color_button_widget.button_number] = self.params


        form_layout.addRow(self.color_layout)

        self.application_dose = QLabel(self.tr("Application Dose (liters/hectare)"))
        self.application_dose_input = QLineEdit("300")

        self.nozzle_rate = QLabel(self.tr("Nozzle flow rate (liters/minute)"))
        self.nozzle_rate_input = QLineEdit("0.8")

        self.nozzle_number = QLabel(self.tr("Number of Nozzles"))
        self.nozzle_number_input = QLineEdit("4")

        self.set_alt = QLabel(self.tr("Altitude (meters)"))
        self.set_alt_input = QLineEdit("25")

        self.set_acc = QLabel(self.tr("Acceleration Buffer (meters)"))
        self.set_acc_input = QLineEdit("2")

        self.application_dose_input.textChanged.connect(self.calculate_velocity)
        self.nozzle_rate_input.textChanged.connect(self.calculate_velocity)
        self.nozzle_number_input.textChanged.connect(self.calculate_velocity)
        self.set_acc_input.textChanged.connect(self.change_acc)


        form_layout.addRow(self.application_dose, self.application_dose_input)
        form_layout.addRow(self.nozzle_rate, self.nozzle_rate_input)
        form_layout.addRow(self.nozzle_number, self.nozzle_number_input)
        form_layout.addRow(self.set_alt, self.set_alt_input)
        form_layout.addRow(self.set_acc, self.set_acc_input)


        self.calculated_speed_label = QLabel(self.tr("Calculated Ground Speed: 0 km/h - 0 m/s"))
        form_layout.addRow(self.calculated_speed_label)


        form_layout.addRow(self.generate_mission)
        form_layout.addRow(self.generate_report)

        self.width_label = QLabel(self.tr("Parcel Width: {0} meters").format(3.0))
        self.height_label = QLabel(self.tr("Parcel Height: {0} meters").format(5.0))
        self.gap_x_layout = QLabel(self.tr("Gap X: {0} meters").format(0.3))
        self.gap_y_layout = QLabel(self.tr("Gap Y: {0} meters").format(1.0))

        self.div = QLabel("----------------------------")
        self.total_width = QLabel(self.tr("Total Width: {0} meters").format(19.5))
        self.total_height = QLabel(self.tr("Total Height: {0} meters").format(29.0))

        form_layout.addRow(self.width_label)
        form_layout.addRow(self.height_label)
        form_layout.addRow(self.gap_x_layout)
        form_layout.addRow(self.gap_y_layout)
        form_layout.addRow(self.div)
        form_layout.addRow(self.total_width)
        form_layout.addRow(self.total_height)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.map_widget)  # Add the map view to the splitter

        # Label for the stitched image (hidden by default)
        # splitter.addWidget(self.image_label)

        splitter.addWidget(right_panel)
        splitter.setSizes([800, 200])

        self.color_to_button_map = {widget.color_hex: widget.button_name for widget in self.color_button_widgets}
        
        self.config_file = resource_path("config.ini")
        self.load_coordinates_from_config()

        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.addWidget(splitter)
        self.setCentralWidget(container)
        # self.showMaximized()

    def change_acc(self):
        self.paths_by_color.clear()
        try:
            self.acc_buffer = float(self.set_acc_input.text())
            if self.acc_buffer == "" or self.acc_buffer <= 0:
                raise Exception
        except Exception:
            if self.set_acc_input.text() != "":
                logger.error(self.tr("Invalid input for Acceleration Buffer: {0}").format(self.set_acc_input.text()))
                self.show_warning(self.tr("Invalid Input"), self.tr("Please enter a valid acceleration buffer."))
                self.acc_buffer = 2.0
            return

    def update_spray_width(self):
        # Clear paths by color
        self.paths_by_color.clear()

        # Prepare JavaScript code to batch all operations
        js_code = ""

        # Remove the previous path if it exists
        if self.current_path is not None:
            js_code += f"{self.current_path}.remove();\n"
            self.current_path = None  # Reset the current path reference

        # Remove the previous start and end markers if they exist
        if self.current_start_marker is not None:
            js_code += f"{self.current_start_marker}.remove();\n"
            self.current_start_marker = None  # Reset the current start marker reference

        if self.current_end_marker is not None:
            js_code += f"{self.current_end_marker}.remove();\n"
            self.current_end_marker = None  # Reset the current end marker reference

        # Remove previous parcel markers
        if hasattr(self, 'parcel_marker_js_references') and self.parcel_marker_js_references:
            for marker_ref in self.parcel_marker_js_references:
                js_code += f"{marker_ref}.remove();\n"
            self.parcel_marker_js_references = []  # Clear the references after removal

        # Run the accumulated JavaScript code in a single call
        self.map_widget.view.page().runJavaScript(js_code)

        # Update the spraying width from the input
        # self.spraying_width = self.spraying_width_input.text()


    def calculate_velocity(self):
        """
        Calculate the ground speed (velocity) for spraying based on the application dose and nozzle rate inputs.
        """
        logger.debug("Calculating velocity")
            
        # Get application dose and nozzle rate from inputs
        try:
            application_dose = float(self.application_dose_input.text())
            if application_dose == "" or application_dose <= 0:
                raise Exception
        except Exception:
            if self.application_dose_input.text() != "":
                logger.error(self.tr("Invalid input for application dose: {0}").format(self.application_dose_input.text()))
                self.show_warning(self.tr("Invalid Input"), self.tr("Please enter a valid application dose."))
            return

        try:
            nozzle_rate = float(self.nozzle_rate_input.text())
            if nozzle_rate == "" or nozzle_rate <= 0:
                raise Exception
        except Exception:
            if self.nozzle_rate_input.text() != "":
                logger.error(self.tr("Invalid input for nozzle rate: {0}").format(self.nozzle_rate_input.text()))
                self.show_warning(self.tr("Invalid Input"), self.tr("Please enter a valid nozzle rate."))
            return
        
        try:
            nozzle_number = float(self.nozzle_number_input.text())
            if nozzle_number == "" or nozzle_number <= 0:
                raise Exception
        except Exception:
            if self.nozzle_number_input.text() != "":
                logger.error(self.tr("Invalid input for nozzle number: {0}").format(self.nozzle_number_input.text()))
                self.show_warning(self.tr("Invalid Input"), self.tr("Please enter a valid nozzle number."))
            return

        
        try:
            spraying_width = float(self.spraying_width_input.text())
            if spraying_width == "" or spraying_width <= 0:
                raise Exception
        except Exception:
            if self.spraying_width_input.text() != "":
                logger.error(self.tr("Invalid input for spraying width: {0}").format(self.spraying_width_input.text()))
                self.show_warning(self.tr("Invalid Input"), self.tr("Please enter a valid spraying width."))
            return


        # Check if parcels are available
        if not self.parcel_coordinates:
            self.show_warning(self.tr("No Parcels"), self.tr("Please save the area and generate parcels first."))
            return

        # Check if current color is selected
        if not self.current_color:
            self.show_warning(self.tr("No Color Selected"), self.tr("Please select a color to calculate velocity."))
            return


        # Filter parcels with the selected color
        parcels_to_spray = [parcel for parcel in self.parcel_coordinates if parcel['color'] == self.current_color]
        
        # If file is opened, calculate number of parcels based on current state
        if self.file_opened:
            number_of_parcels = len(self.parcel_coordinates)
            if number_of_parcels == 0:
                self.show_warning(self.tr("No Parcels"), self.tr("There are no parcels available for calculation."))
                return
        else:
            number_of_parcels = len(parcels_to_spray)
            if number_of_parcels == 0:
                self.show_warning(self.tr("No Parcels"), self.tr("There are no parcels with the selected color."))
                return


        # Assuming width and height are in meters
        parcel_area_m2 = self.width * self.height  # width and height should be in meters
        sup_aplicada_m2 = number_of_parcels * parcel_area_m2
        # print(f"Total application area (sup_aplicada_m2): {sup_aplicada_m2:.2f} m²")

        # Calculate total required solution (caldo necesario) in liters
        caldo_necesario = (application_dose * sup_aplicada_m2) / 10000  # Convert m² to hectares
        # print(f"Total required solution (caldo_necesario): {caldo_necesario:.2f} L")

        # Calculate solution needed per parcel
        caldo_per_plot = caldo_necesario / (number_of_parcels * self.width / float(self.spraying_width_input.text()))
        # print(f"Solution needed per parcel (caldo_per_plot): {caldo_per_plot:.2f} L")

        # Assume number of nozzles (boquillas)
        # print(f"Number of nozzles (boquillas): {nozzle_number}")

        # Total flow rate in L/min
        flow_rate_total_L_min = nozzle_rate * nozzle_number
        # print(f"Total flow rate (flow_rate_total_L_min): {flow_rate_total_L_min:.2f} L/min")

        # Convert total flow rate to L/s
        flow_rate_total_L_s = flow_rate_total_L_min / 60  # 60 seconds in a minute
        # print(f"Total flow rate (flow_rate_total_L_s): {flow_rate_total_L_s:.4f} L/s")

        # Length of each plot (longitud_plot) is the parcel height
        longitud_plot = self.height
        # print(f"Length of each plot (longitud_plot): {longitud_plot:.2f} m")

        # Time per plot in seconds
        time_per_plot_s = caldo_per_plot / flow_rate_total_L_s
        # print(f"Time per plot (time_per_plot_s): {time_per_plot_s:.2f} seconds")

        # Ground speed in m/s
        ground_speed_m_s = longitud_plot / time_per_plot_s
        # print(f"Ground speed (ground_speed_m_s): {ground_speed_m_s:.3f} m/s")

        # Ground speed in km/h
        ground_speed_km_h = ground_speed_m_s * 3.6
        # print(f"Ground speed (ground_speed_km_h): {ground_speed_km_h:.3f} km/h")

        # Update the label or store the calculated values as needed
        self.calculated_speed_label.setText(f"Calculated Ground Speed: {ground_speed_km_h:.2f} km/h - {ground_speed_m_s:.2f} m/s")

        app_state.application_dose = self.application_dose_input.text()
        app_state.nozzle_number = self.nozzle_number_input.text()
        app_state.nozzle_rate = self.nozzle_rate_input.text()
        app_state.altitude = self.set_alt_input.text()

        self.params = {
            'application_dose': str(self.application_dose_input.text()),
            'nozzle_rate': str(self.nozzle_rate_input.text()),
            'nozzle_number': str(self.nozzle_number_input.text()),
            'altitude': str(self.set_alt_input.text())
        }
        
        # Optionally, store the results in a dictionary or class attributes
        self.velocity_results = {
            "caldo_necesario_L": caldo_necesario,
            "caldo_per_plot_L": caldo_per_plot,
            "flow_rate_total_L_min": flow_rate_total_L_min,
            "flow_rate_total_L_s": flow_rate_total_L_s,
            "time_per_plot_s": time_per_plot_s,
            "ground_speed_m_s": ground_speed_m_s,
            "ground_speed_km_h": ground_speed_km_h,
        }


    def create_toolbar(self):
        """Create and add the menu bar to the main window."""
        # Create the menu bar
        menu_bar = self.menuBar()

        # Create the 'File' menu
        self.file_menu = menu_bar.addMenu(self.tr("File"))

        # Add 'Open' action with an icon to the 'File' menu
        self.open_action = QAction(QIcon("open.png"), self.tr("Open"), self)
        self.open_action.setStatusTip(self.tr("Open a file"))
        self.open_action.triggered.connect(self.open_file)  # Connect to a custom function
        self.file_menu.addAction(self.open_action)

        # Add a separator to the 'File' menu
        self.file_menu.addSeparator()

        # Add 'Save' action with an icon to the 'File' menu
        self.save_action = QAction(QIcon("save.png"), self.tr("Save"), self)
        self.save_action.setStatusTip(self.tr("Save your work"))
        self.save_action.triggered.connect(self.save_file)  # Connect to a custom function
        self.file_menu.addAction(self.save_action)

        # Create the 'Settings' menu
        self.settings_menu = menu_bar.addMenu(self.tr("Settings"))

        # Add Night Mode option to settings
        self.night_mode_action = QAction(self.tr("Night Mode"), self, checkable=True)
        self.night_mode_action.triggered.connect(self.toggle_night_mode)
        self.settings_menu.addAction(self.night_mode_action)

        # Create the 'Change Language' submenu under 'Settings'
        self.language_menu = self.settings_menu.addMenu(self.tr("Change Language"))

        # Add language options to the language menu
        self.lang_action_en = QAction("English", self, checkable=True)
        self.lang_action_en.triggered.connect(lambda: self.change_language('en'))
        self.language_menu.addAction(self.lang_action_en)

        self.lang_action_es = QAction("Español", self, checkable=True)
        self.lang_action_es.triggered.connect(lambda: self.change_language('es'))
        self.language_menu.addAction(self.lang_action_es)

        # Set the default checked language (e.g., English as default)
        self.lang_action_en.setChecked(True)

    def change_language(self, language):
        # Remove the old translator if any
        if self.translator is not None:
            QApplication.instance().removeTranslator(self.translator)
        # Load the appropriate language file
        if language == 'en':
            self.translator.load(temp_resource_path("translated_en.qm"))
            self.lang_action_en.setChecked(True)
            self.lang_action_es.setChecked(False)
        elif language == 'es':
            self.translator.load(temp_resource_path("translated_es.qm"))
            self.lang_action_es.setChecked(True)
            self.lang_action_en.setChecked(False)
        
        # Install the translator
        QApplication.instance().installTranslator(self.translator)
        
        # Retranslate the UI elements
        self.retranslateUi()
        app_state.language = language
        # Save settings
        self.save_settings_to_config(language, self.night_mode_action.isChecked())
        print("current language,", language)

    def toggle_night_mode(self):
        """Toggles between day and night mode stylesheets."""
        if self.night_mode_action.isChecked():
            # Apply night mode
            dark_stylesheet = """
            QMainWindow {
                background-color: #2E2E2E;
                color: white;
            }
            QLabel, QLineEdit, QPushButton, QToolBar, QMenuBar, QStatusBar, QMessageBox, QGraphicsView, QGraphicsRectItem, QGraphicsTextItem {
                background-color: #3A3A3A;
                color: white;
            }
            QLineEdit {
                background-color: #454545;
            }
            QPushButton {
                background-color: #3A3A3A;
                border: 1px solid #555555;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
            QMenuBar {
                background-color: #2E2E2E;
            }
            QMenuBar::item:selected {
                background-color: #4E4E4E;
            }
            QPushButton {
            background-color: #3a3a3a;
            color: #ffffff; /* Ensure button text is white */
            border: 1px solid #ffffff;
            }
            QRadioButton {
                color: #ffffff; /* Ensure radio button text is white */
            }
            """
            self.setStyleSheet(dark_stylesheet)
            app_state.night_mode = True
        else:
            # Apply day mode (reset stylesheet)
            self.setStyleSheet("")
            app_state.night_mode = False
                
    def retranslateUi(self):
        """Update all translatable UI elements."""
        # Update buttons
        # Update menu bar items
        self.file_menu.setTitle(self.tr("File"))
        self.save_action.setText(self.tr("Save"))
        self.open_action.setText(self.tr("Open"))
        self.settings_menu.setTitle(self.tr("Settings"))
        self.night_mode_action.setText(self.tr("Night Mode"))
        self.language_menu.setTitle(self.tr("Change Language"))
        self.lang_action_en.setText(self.tr("English"))
        self.lang_action_es.setText(self.tr("Español"))

        self.clear_button.setText(self.tr("Clear Parcels"))
        self.back_button.setText(self.tr("Previous Window"))
        self.save_button.setText(self.tr("Process"))
        self.generate_report.setText(self.tr("Generate Report"))
        self.generate_mission.setText(self.tr("Save the mission"))

        # Update labels for coordinates
        self.top_left.setText(self.tr("Coordinate A"))
        self.top_left_lat.setText(self.tr("lat:"))
        self.top_left_lon.setText(self.tr("lon:"))

        self.top_right.setText(self.tr("Coordinate B"))
        self.top_right_lat.setText(self.tr("lat:"))
        self.top_right_lon.setText(self.tr("lon:"))

        self.bot_left.setText(self.tr("Coordinate C"))
        self.bot_left_lat.setText(self.tr("lat:"))
        self.bot_left_lon.setText(self.tr("lon:"))

        self.bot_right.setText(self.tr("Coordinate D"))
        self.bot_right_lat.setText(self.tr("lat:"))
        self.bot_right_lon.setText(self.tr("lon:"))

        # Update spraying settings
        self.spraying_width.setText(self.tr("Spraying Width"))
        self.fit.setText(self.tr("Do you want parcels to fit the area?"))

        # Update velocity calculation labels
        self.application_dose.setText(self.tr("Application Dose (liters/hectare)"))
        self.nozzle_rate.setText(self.tr("Nozzle flow rate (liters/minute)"))
        self.nozzle_number.setText(self.tr("Number of Nozzles"))
        self.set_alt.setText(self.tr("Altitude (meters)"))
        self.set_acc.setText(self.tr("Acceleration Buffer (meters)"))

        # Update calculated values
        self.calculated_speed_label.setText(self.tr("Calculated Ground Speed: 0 km/h - 0 m/s"))
        self.total_length_label.setText(self.tr("Total Path Length: 0 meters"))
        
        try:
            self.width_label.setText(self.tr("Parcel Width: {0} meters").format(self.width))
            self.height_label.setText(self.tr("Parcel Height: {0} meters").format(self.height))
            self.gap_x_layout.setText(self.tr("Gap X: {0} meters").format(self.gap_x))
            self.gap_y_layout.setText(self.tr("Gap Y: {0} meters").format(self.gap_y))

            total_width = self.width * self.count_x + (self.count_x - 1) * self.gap_x
            total_height = self.height * self.count_y + (self.count_y - 1) * self.gap_y

            self.total_width.setText(self.tr("Total Width: {0} meters").format(total_width))
            self.total_height.setText(self.tr("Total Height: {0} meters").format(total_height))
        except:
            pass


    def open_file(self):
        logger.debug("Open file action triggered")

        # Create a file dialog for selecting the file to open
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open Planner State")
        file_dialog.setNameFilter("TXT Files (*.txt)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            logger.info(f"File selected: {file_path}")

            try:
                with open(file_path, 'r') as file:
                    loaded_data = json.load(file)
                    logger.info(f"Loaded data: {loaded_data}")
                    self.restore_app_state(loaded_data)
            except Exception as e:
                logger.error(f"Error opening or parsing file: {e}")
                self.show_warning(self.tr("Open Failed"), self.tr(f"Failed to open planner state: {e}"))

    def restore_app_state(self, data):
        logger.debug(f"Restoring planner state with data: {data}")

        try:
            # Restore the parameters from the loaded data
            self.button_names = {int(k): v for k, v in data['button_names'].items()}
            self.exact_width = data['width']
            self.exact_height = data['height']
            self.width = round(self.exact_width)
            self.height = round(self.exact_height)
            self.gap_x = data['gap_x']
            self.gap_y = data['gap_y']
            self.count_x = data['count_x']
            self.count_y = data['count_y']
            self.colored_parcels = data['colored_parcels']
            location = data['location']
            spraying_width = data['spraying_width']
            fit = data['fit']
            self.parcel_coordinates = data.get('parcel_coordinates', None)
            self.button_params = data["params"]
            self.acc_buffer = data["acc_buffer"]
            # self.paths_by_color = data.get('paths_by_color', {})

            app_state.location = location
            app_state.spraying_width = spraying_width
            app_state.fit = fit
            app_state.paths_by_color = self.paths_by_color

            # Ensure all parcels are included
            total_parcels = self.count_x * self.count_y  # Total number of parcels based on grid
            complete_parcel_dict = {}

            # Add colored parcels to the complete list
            for parcel_id in range(total_parcels):
                if str(parcel_id) in self.colored_parcels:
                    complete_parcel_dict[parcel_id] = self.colored_parcels[str(parcel_id)][0]  # Get the color
                else:
                    complete_parcel_dict[parcel_id] = "white"  # Set missing parcels to "white"

            self.color_codes_list = complete_parcel_dict

            # Update UI elements
            self.top_left_lat_input.setText(str(location[0][0]))
            self.top_left_lon_input.setText(str(location[0][1]))
            self.top_right_lat_input.setText(str(location[1][0]))
            self.top_right_lon_input.setText(str(location[1][1]))
            self.bot_left_lat_input.setText(str(location[2][0]))
            self.bot_left_lon_input.setText(str(location[2][1]))
            self.bot_right_lat_input.setText(str(location[3][0]))
            self.bot_right_lon_input.setText(str(location[3][1]))
            self.spraying_width_input.setText(str(spraying_width))
            self.fit.setChecked(fit)

            # Update the button names on the UI
            for i, (button_number, button_name) in enumerate(self.button_names.items()):
                self.color_button_widgets[i].text_background_label.setText(button_name)
                self.color_button_widgets[i].button_names = self.button_names
                self.color_button_widgets[i].button_name = button_name

            self.application_dose_input.blockSignals(True)
            self.nozzle_rate_input.blockSignals(True)
            self.nozzle_number_input.blockSignals(True)
            self.set_alt_input.blockSignals(True)
            self.set_acc_input.blockSignals(True)


            app_state.application_dose = self.application_dose_input.text()
            app_state.nozzle_rate = self.nozzle_rate_input.text()
            app_state.nozzle_number = self.nozzle_number_input.text()
            app_state.altitude = self.set_alt_input.text()
            app_state.acc_buffer = self.set_acc_input.text()

            # Re-enable signals after setting the text
            self.application_dose_input.blockSignals(False)
            self.nozzle_rate_input.blockSignals(False)
            self.nozzle_number_input.blockSignals(False)
            self.set_alt_input.blockSignals(False)
            self.set_acc_input.blockSignals(False)


            self.file_opened = True
            # Find the button with the greatest button number
            max_button_number = int(max(self.button_params.keys()))  # Get the largest button number
            logger.debug(f"Setting current color to button with greatest number: {max_button_number}")
            app_state.button_names = self.button_names
            app_state.width = self.width
            app_state.height = self.height
            app_state.gap_x = self.gap_x
            app_state.gap_y = self.gap_y
            app_state.count_x = self.count_x
            app_state.count_y = self.count_y
            app_state.colored_parcels = self.colored_parcels
            app_state.location = location
            app_state.spraying_width = spraying_width
            app_state.fit = fit
            app_state.file_opened = self.file_opened
            app_state.button_params = self.button_params
            app_state.acc_buffer = self.acc_buffer

         
            # Update internal variables
            self.initialize_params(app_state)
             # Set the color of the button with the greatest number
            self.set_current_color(self.color_button_widgets[max_button_number - 1], self.color_button_widgets[max_button_number - 1].color_name)

            # Redraw parcels and paths if parcel coordinates are available
            if self.parcel_coordinates:
                self.save()  # Redraw parcels on the map
                # Redraw paths for all colors
                for color, path in self.paths_by_color.items():
                    self.draw_path_on_map(path)
            else:
                self.clear_parcels()

            logger.info("Planner state restored successfully.")
            self.show_info("Restore Successful", "Planner state has been restored successfully.")
        except Exception as e:
            logger.error(f"Error restoring planner state: {e}")
            self.show_warning(self.tr("Restore Failed"), self.tr(f"Failed to restore planner state: {e}"))


    def save_file(self):
        logger.debug("Save file action triggered")
        try:

            # Collect the application state
            # if self.fit.isChecked():  # If 'fit' option is selected, use the fitted dimensions
            #     width_to_save = self.exact_width
            #     height_to_save = self.exact_height
            #     gap_x_to_save = self.gap_x  # These values are calculated in the `save` function
            #     gap_y_to_save = self.gap_y
            # else:  # Otherwise, use the original values
            width_to_save = self.width
            height_to_save = self.height
            gap_x_to_save = self.gap_x
            gap_y_to_save = self.gap_y

            app_state_data = {
                'button_names': self.button_names,
                'width': width_to_save,  # Save the correct width
                'height': height_to_save,  # Save the correct height
                'gap_x': gap_x_to_save,  # Save the correct gap_x
                'gap_y': gap_y_to_save,  # Save the correct gap_y
                'count_x': self.count_x,
                'count_y': self.count_y,
                'colored_parcels': self.colored_parcels,
                'location': [
                    [self.top_left_lat_input.text(), self.top_left_lon_input.text()],
                    [self.top_right_lat_input.text(), self.top_right_lon_input.text()],
                    [self.bot_left_lat_input.text(), self.bot_left_lon_input.text()],
                    [self.bot_right_lat_input.text(), self.bot_right_lon_input.text()]
                ],
                'spraying_width': self.spraying_width_input.text(),
                'fit': self.fit.isChecked(),
                'parcel_coordinates': self.parcel_coordinates,
                'paths_by_color': self.paths_by_color,
                'params': self.button_params,
                'acc_buffer': self.acc_buffer
            }

            # Create a save file dialog
            file_dialog = QFileDialog(self)
            file_dialog.setWindowTitle("Save Planner State")
            file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            file_dialog.setNameFilter("TXT Files (*.txt)")
            file_dialog.setDefaultSuffix("txt")

            # Generate a default filename
            default_file_name = f"planner_state_{time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            file_dialog.selectFile(default_file_name)

            if file_dialog.exec():
                save_path = file_dialog.selectedFiles()[0]
                logger.info(f"Saving planner state to: {save_path}")

                try:
                    with open(save_path, 'w') as save_file:
                        json.dump(app_state_data, save_file, indent=4)
                    logger.info("Planner state saved successfully.")
                    self.show_info("Save Successful", "Planner state has been saved successfully.")
                except Exception as e:
                    logger.error(f"Failed to save planner state: {e}")
                    self.show_warning(self.tr("Save Failed"), self.tr(f"Failed to save planner state: {e}"))
        except Exception as e:
                logger.error(f"Failed to save planner state: {e}")
                self.show_warning(self.tr("Save Failed"), self.tr(f"Failed to save planner state: {e}"))



    def initialize_with_parcels(self, colored_parcels):
        logger.debug(f"initializing with the parcels of:  {colored_parcels}")
        self.colored_parcels = colored_parcels
        self.color_codes_list = list(self.colored_parcels.values())

    def initialize_params(self, app_state, tr):
        logger.debug(f"initializing with the params of: {app_state}")
        print(app_state.count_x)
        self.translator = tr
        self.width = app_state.width
        self.height = app_state.height
        self.gap_x = app_state.gap_x
        self.gap_y = app_state.gap_y
        self.count_x = app_state.count_x
        self.count_y = app_state.count_y
        self.button_names = app_state.button_names
        self.colored_parcels = app_state.colored_parcels
        self.file_opened = app_state.file_opened
        self.paths_by_color = {}
        self.current_color = None
        self.parcel_coordinates = None
        self.button_params = {int(key): value for key, value in app_state.button_params.items()}
        self.acc_buffer = app_state.acc_buffer
        
        self.width_label.setText(self.tr("Parcel Width: {0} meters").format(self.width))
        self.height_label.setText(self.tr("Parcel Height: {0} meters").format(self.height))
        self.gap_x_layout.setText(self.tr("Gap X: {0} meters").format(self.gap_x))
        self.gap_y_layout.setText(self.tr("Gap Y: {0} meters").format(self.gap_y))

        total_width = self.width * self.count_x + (self.count_x - 1) * self.gap_x
        total_height = self.height * self.count_y + (self.count_y - 1) * self.gap_y

        self.total_width.setText(self.tr("Total Width: {0} meters").format(total_width))
        self.total_height.setText(self.tr("Total Height: {0} meters").format(total_height))

        # Then set the language and night mode
        app_state.language = app_state.language
        app_state.night_mode = app_state.night_mode
        self.change_language(app_state.language)
        self.night_mode_action.setChecked(app_state.night_mode)
        self.toggle_night_mode()


        self.application_dose_input.blockSignals(True)
        self.nozzle_rate_input.blockSignals(True)
        self.nozzle_number_input.blockSignals(True)
        self.set_alt_input.blockSignals(True)
        self.set_acc_input.blockSignals(True)

        for button_widget in self.color_button_widgets:
            self.load_button_params(button_widget)
        self.set_acc_input.setText(str(app_state.acc_buffer))
    
        # Re-enable signals after setting the text
        self.application_dose_input.blockSignals(False)
        self.nozzle_rate_input.blockSignals(False)
        self.nozzle_number_input.blockSignals(False)
        self.set_alt_input.blockSignals(False)
        self.set_acc_input.blockSignals(False)

            # Redraw parcels and paths if parcel coordinates are available
        if self.parcel_coordinates:
            self.save()  # Redraw parcels on the map
            # Redraw paths for all colors
            for color, path in self.paths_by_color.items():
                self.draw_path_on_map(path)
        else:
            self.clear_parcels()
        
        app_state.save_state(
                self.button_names,
                self.width,
                self.height,
                self.gap_x,
                self.gap_y,
                self.count_x,
                self.count_y,
                self.colored_parcels
            )
        used_color = []
        for i in self.colored_parcels.values():
            if i[0] != "white":
                used_color.append(i[0])

        # Clear the existing layout first (remove old buttons)
        for i in reversed(range(self.color_layout.count())):
            widget = self.color_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        visible_buttons = []
        for i, (button_number, button_name) in enumerate(self.button_names.items()):
            
            button_color = self.color_button_widgets[i].color_name
            if button_color in used_color:
                self.color_button_widgets[i].text_background_label.setText(button_name)
                self.color_button_widgets[i].button_names = self.button_names
                self.color_button_widgets[i].button_name = button_name
                visible_buttons.append(self.color_button_widgets[i])

        for i, button_widget in enumerate(visible_buttons):
            self.color_layout.addWidget(button_widget, i // 2, i % 2)

        self.color_layout.update()

        app_state.location = app_state.location
        app_state.spraying_width = app_state.spraying_width
        app_state.fit = app_state.fit

        self.top_left_lat_input.setText(str(app_state.location[0][0]))
        self.top_left_lon_input.setText(str(app_state.location[0][1]))
        self.top_right_lat_input.setText(str(app_state.location[1][0]))
        self.top_right_lon_input.setText(str(app_state.location[1][1]))
        self.bot_left_lat_input.setText(str(app_state.location[2][0]))
        self.bot_left_lon_input.setText(str(app_state.location[2][1]))
        self.bot_right_lat_input.setText(str(app_state.location[3][0]))
        self.bot_right_lon_input.setText(str(app_state.location[3][1]))
        self.spraying_width_input.setText(str(app_state.spraying_width))
        self.fit.setChecked(app_state.fit)

        self.generate_mission.setText(self.tr("Save Mission"))
        self.generate_mission.setStyleSheet(f"background-color: None; color: black;")
        self.load_coordinates_from_config()
        self.clear_parcels()

        if app_state.file_opened:
            self.save()

        print(2, self.count_x)

    def load_button_params(self, button_widget):
        """
        Load the saved params for the button and update the text fields.
        If no saved params are found, use default params and save them.
        """
        button_number = button_widget.button_number

        # Default parameters
        default_params = {
            "application_dose": "300",  # Default value for application dose
            "nozzle_rate": "0.8",       # Default value for nozzle rate
            "nozzle_number": "4",       # Default value for number of nozzles
            "altitude": "25"            # Default value for altitude
        }

        # Check if parameters are saved for this button, if not, set defaults
        if button_number in self.button_params:
            params = self.button_params[button_number]
        else:
            logger.warning(f"No saved params found for button {button_number}. Using default params.")
            # Assign default params if not present
            self.button_params[button_number] = default_params
            params = default_params

        # Update the input fields with the parameters (either saved or default)
        self.application_dose_input.setText(str(params.get("application_dose", "")))
        self.nozzle_rate_input.setText(str(params.get("nozzle_rate", "")))
        self.nozzle_number_input.setText(str(params.get("nozzle_number", "")))
        self.set_alt_input.setText(str(params.get("altitude", "")))


    def report(self):
        """
        Generate a report containing all the generated paths, parcel structure including colors, and additional layout details.
        This method writes the data into a text file.
        """
        logger.debug("generating report")
        if not self.parcel_coordinates:
            self.show_warning(self.tr("No Parcels"), self.tr("There are no parcels to generate a report."))
            return

        # Determine whether to use fitted dimensions or default ones
        if self.fit.isChecked():  # If 'fit' is selected, use fitted dimensions
            width_to_report = self.exact_width
            height_to_report = self.exact_height
            gap_x_to_report = self.gap_x
            gap_y_to_report = self.gap_y
        else:  # Otherwise, use default dimensions
            width_to_report = self.width
            height_to_report = self.height
            gap_x_to_report = self.gap_x
            gap_y_to_report = self.gap_y

        # Create a map of color to button name
        self.color_to_button_map = {widget.color_hex: widget.button_name for widget in self.color_button_widgets}
        update_time = time.strftime('%Y-%m-%d %H:%M:%S')

        report_lines = []
        report_lines.append("Parcel Layout Report\n")
        report_lines.append(f"\nUpdated on {update_time}\n")
        report_lines.append("="*50 + "\n")
        
        # Add general information
        report_lines.append("General Layout Information:\n")
        report_lines.append(f"Liquid Names: {self.button_names}\n")
        report_lines.append(f"Parcel Width: {width_to_report:.2f} meters\n")  # Use fitted or default width
        report_lines.append(f"Parcel Height: {height_to_report:.2f} meters\n")  # Use fitted or default height
        report_lines.append(f"Gap X: {gap_x_to_report:.2f} meters\n")  # Use fitted or default gap_x
        report_lines.append(f"Gap Y: {gap_y_to_report:.2f} meters\n")  # Use fitted or default gap_y
        report_lines.append(f"Count X: {self.count_x}\n")
        report_lines.append(f"Count Y: {self.count_y}\n")
        
        # Add spray width and corner coordinates
        report_lines.append(f"Spraying Width: {self.spraying_width_input.text()}\n")
        report_lines.append(f"Top Left Coordinates: {self.top_left_lat_input.text(), self.top_left_lon_input.text()}\n")
        report_lines.append(f"Top Right Coordinates: {self.top_right_lat_input.text(), self.top_left_lon_input.text()}\n")
        report_lines.append(f"Bottom Left Coordinates: {self.bot_left_lat_input.text(), self.bot_left_lon_input.text()}\n")
        report_lines.append(f"Bottom Right Coordinates: {self.bot_right_lat_input.text(), self.bot_right_lon_input.text()}\n")
        report_lines.append(f"Fit area: {app_state.fit}\n")
        report_lines.append("\n")



        # Add parcel structure and colors
        report_lines.append("Parcel Structure and Colors:\n")
        for i, parcel_info in enumerate(self.parcel_coordinates):
            coordinates = parcel_info['coordinates']
            color = parcel_info['color']
            # Find the button name corresponding to the color using the color_to_button_map
            button_name = self.color_to_button_map.get(color, "Unknown")

            report_lines.append(f"Parcel {i+1}:\n")
            report_lines.append(f"  Color: {self.hex_to_color_name(color)}\n")
            report_lines.append(f"  Liquid Name: {button_name}\n")
            report_lines.append("  Coordinates:\n")
            for coord in coordinates:
                report_lines.append(f"    - Lat: {coord['lat']}, Lon: {coord['lng']}\n")
            report_lines.append("\n")

        # Ensure paths are generated for all colors
        report_lines.append("Generated Paths by Color:\n")
        for parcel_info in self.parcel_coordinates:
            color = parcel_info['color']
            if color == "white":
                continue
            if color not in self.paths_by_color:
                self.current_color = color  # Set current color
                self.generate_path()  # Generate the path if it doesn't exist


        if self.paths_by_color:
            for color, paths in self.paths_by_color.items():
                report_lines.append(f"  Color: {self.hex_to_color_name(color)}\n")
                button_name = self.color_to_button_map.get(color, "Unkown")
                report_lines.append(f"  Liquid Name: {button_name}\n")
                            # Find the button number associated with the color
                button_number = None
                for btn_widget in self.color_button_widgets:
                    if btn_widget.color_hex == color:
                        button_number = btn_widget.button_number
                        break
                
                # Append parameters for the button, if found
                if button_number and button_number in self.button_params:
                    params = self.button_params[button_number]
                    report_lines.append(f"  Parameters:\n")
                    report_lines.append(f"    Application Dose: {params.get('application_dose', 'N/A')}\n")
                    report_lines.append(f"    Nozzle Rate: {params.get('nozzle_rate', 'N/A')}\n")
                    report_lines.append(f"    Nozzle Number: {params.get('nozzle_number', 'N/A')}\n")
                    report_lines.append(f"    Altitude: {params.get('altitude', 'N/A')}\n")
                    report_lines.append(f"    {self.calculated_speed_label.text()}\n")
                else:
                    report_lines.append(f"  Parameters: Not available\n")

                report_lines.append(f"  Path Coordinates:\n")
                for i in range(0, len(paths), 2):
                    report_lines.append(f"    Segment {i // 2 + 1}:\n")
                    report_lines.append(f"      Start: Lat: {paths[i][0]}, Lon: {paths[i][1]}\n")
                    report_lines.append(f"      End: Lat: {paths[i+1][0]}, Lon: {paths[i+1][1]}\n")
                report_lines.append("\n")
        else:
            report_lines.append("  No paths generated yet.\n")

        report_lines.append("="*50 + "\n")

        file_path = os.path.join(reports_dir, f"{app_state.timestamp}_parcel_report.txt")

        with open(file_path, "w") as report_file:
            report_file.writelines(report_lines)

        self.show_info("Report created successfully", f"Report generated and saved at '{file_path}'")

    def hex_to_color_name(self, hex_code):
        hex_color_dict = {
            "#ff0000": "Red",
            "#0000ff": "Blue",
            "#ffff00": "Yellow",
            "#00ffff": "Cyan",
            "#ff00ff": "Magenta",
            "#808080": "Gray",
            "#8b0000": "Dark red",
            "#006400": "Dark green",
            "#00008b": "Dark blue",
            "#b8860b": "Dark yellow",
            "#ffffff": "White",
            # Add more colors as needed
        }

        hex_code = hex_code.lower()
        
        # Ensure the hex code starts with '#'
        if not hex_code.startswith("#"):
            hex_code = "#" + hex_code

        return hex_color_dict.get(hex_code, "White")


    def clear_parcels(self):
        logger.debug("clearing parcels")
        # Batch JS code to remove parcels
        js_code = ""

        # Remove parcel polygons
        if self.parcel_js_references:
            for js_ref in self.parcel_js_references:
                js_code += f"{js_ref}.remove();\n"  # Batch remove parcels in one go
            self.parcel_js_references = []  # Clear the list of references

        # Remove the current path
        if self.current_path is not None:
            js_code += f"{self.current_path}.remove();\n"
            self.update_total_length_label(0)
            self.current_path = None

        # Remove the start and end markers
        if self.current_start_marker is not None:
            js_code += f"{self.current_start_marker}.remove();\n"
            self.current_start_marker = None
        if self.current_end_marker is not None:
            js_code += f"{self.current_end_marker}.remove();\n"
            self.current_end_marker = None

        # Remove parcel markers
        if hasattr(self, 'parcel_marker_js_references') and self.parcel_marker_js_references:
            for marker_ref in self.parcel_marker_js_references:
                js_code += f"{marker_ref}.remove();\n"
            self.parcel_marker_js_references = []

        # Only run JavaScript if there is something to remove
        if js_code.strip():
            self.map_widget.view.page().runJavaScript(js_code)




    def set_button_names(self, button_names):
        logger.debug(f"setting button names with the value of: {button_names}")
        self.button_names = button_names
        self.color_to_button_map = {widget.color_hex: widget.button_name for widget in self.color_button_widgets}


    def set_current_color(self, button, color):
        logger.debug(f"setting current color with the value of: {button}, {color}")

        # If there's a previously selected button, save its parameters
        if self.prev_button is not None and not self.file_opened:
            logger.debug(f"Saving params for previous button: {self.prev_button.button_number}")
            self.button_params[self.prev_button.button_number] = {
                "application_dose": self.application_dose_input.text(),
                "nozzle_rate": self.nozzle_rate_input.text(),
                "nozzle_number": self.nozzle_number_input.text(),
                "altitude": self.set_alt_input.text(),
            }


        # Update the previous button reference
        self.prev_button = button
        # Handle color input (convert to hex)
        if isinstance(color, QColor):
            self.current_color = color.name()  # Convert QColor to hex
        else:
            self.current_color = QColor(color).name()  # Convert string to hex

        # Attempt to generate the path
        path_generated_successfully = self.generate_path()

        # Only calculate velocity if path generation was successful
        if path_generated_successfully:
            self.calculate_velocity()
        else:
            logger.warning("Path generation failed, skipping velocity calculation.")

        # Load the current button's params if available; otherwise, use defaults
        if button.button_number in self.button_params:
            logger.debug(f"Loading params for current button: {button.button_number}")
            self.params = self.button_params[button.button_number]
        else:
            # Set default params if the button doesn't have saved params
            self.params = {
                "application_dose": "300",
                "nozzle_rate": "0.8",
                "nozzle_number": "4",
                "altitude": "25",
            }

        # Update the input fields with the current button's params
        self.application_dose_input.blockSignals(True)
        self.nozzle_rate_input.blockSignals(True)
        self.nozzle_number_input.blockSignals(True)
        self.set_alt_input.blockSignals(True)
        
        self.application_dose_input.setText(str(self.params["application_dose"]))
        self.nozzle_rate_input.setText(str(self.params["nozzle_rate"]))
        self.nozzle_number_input.setText(str(self.params["nozzle_number"]))
        self.set_alt_input.setText(str(self.params["altitude"]))

        self.application_dose_input.blockSignals(False)
        self.nozzle_rate_input.blockSignals(False)
        self.nozzle_number_input.blockSignals(False)
        self.set_alt_input.blockSignals(False)

        self.calculate_velocity()

        # Update the button text based on the selected color
        self.update_button_text(self.current_color)

        # Reset borders on all buttons but keep their colors
        for btn in self.color_buttons:
            background_color = btn.styleSheet().split(';')[0]
            btn.setStyleSheet(f"{background_color}; border: none;")

        # Set the selected button with a new style (add a border)
        button.setStyleSheet(f"{button.styleSheet()}; border: 2px solid black;")

        # Keep reference to the currently selected button
        self.current_color_button = button


    def update_button_text(self, color_hex):
        logger.debug(f"updating button text with the value of: {color_hex}")
        """Update the button text based on the selected color's hex code."""
        # Map the hex color to the button name using the color_to_button_map
        self.color_to_button_map = {widget.color_hex: widget.button_name for widget in self.color_button_widgets}
        self.button_name = self.color_to_button_map.get(color_hex, "Unknown")
        
        # Update the button text to show the selected color name
        self.generate_mission.setText(f"Generate Mission for {self.button_name}")

        # Optionally update the button style to reflect the selected color
        self.generate_mission.setStyleSheet(f"background-color: {color_hex}; color: black;")



    def save(self):
        logger.debug("saving field coordinates")
        self.clear_parcels()
        self.paths_by_color = {}
        self.current_path = None

        try:
            t_l_lat = float(self.top_left_lat_input.text())
            t_l_lon = float(self.top_left_lon_input.text())
            t_r_lat = float(self.top_right_lat_input.text())
            t_r_lon = float(self.top_right_lon_input.text())
            b_l_lat = float(self.bot_left_lat_input.text())
            b_l_lon = float(self.bot_left_lon_input.text())
            b_r_lat = float(self.bot_right_lat_input.text())
            b_r_lon = float(self.bot_right_lon_input.text())
        except:
            self.show_warning(self.tr("Wrong Input"), self.tr("Please check inputs for coordinates"))
            return

        area_corners = [
            [t_l_lat, t_l_lon],  # Top-left
            [t_r_lat, t_r_lon],  # Top-right
            [b_r_lat, b_r_lon],  # Bottom-right
            [b_l_lat, b_l_lon]   # Bottom-left
        ]
        
        is_fit = self.fit.isChecked()
        app_state.fit = is_fit
        if is_fit:
            # Calculate the distance between the corners (top-left and top-right for width, top-left and bottom-left for height)
            top_left = (t_l_lat, t_l_lon)
            top_right = (t_r_lat, t_r_lon)
            bottom_left = (b_l_lat, b_l_lon)

            # Calculate total width and height using haversine formula or simple Euclidean distance
            def haversine(lat1, lon1, lat2, lon2):
                from math import radians, cos, sin, sqrt, atan2
                
                # Approximate radius of earth in km
                R = 6371.0
                
                lat1, lon1 = radians(lat1), radians(lon1)
                lat2, lon2 = radians(lat2), radians(lon2)

                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                
                return R * c * 1000  # Return distance in meters

            total_width = haversine(t_l_lat, t_l_lon, t_r_lat, t_r_lon)  # Distance between top-left and top-right corners
            total_height = haversine(t_l_lat, t_l_lon, b_l_lat, b_l_lon)  # Distance between top-left and bottom-left corners

            # Calculate the new parcel width, height, gap_x, and gap_y based on the total area and the number of parcels
            self.exact_width = total_width / self.count_x  # Adjust width to fit within the area
            self.exact_height = total_height / self.count_y  # Adjust height to fit within the area
            self.width = round(self.exact_width)
            self.height = round(self.exact_height)

            # Update the labels with the fitted dimensions using self.tr
            self.width_label.setText(self.tr("Parcel Width: {0:.2f} meters (≈ {1})").format(self.exact_width, self.width))
            self.height_label.setText(self.tr("Parcel Height: {0:.2f} meters (≈ {1})").format(self.exact_height, self.height))
            self.gap_x_layout.setText(self.tr("Gap X: {0:.2f} meters").format(self.gap_x))
            self.gap_y_layout.setText(self.tr("Gap Y: {0:.2f} meters").format(self.gap_y))
            self.total_width.setText(self.tr("Total Width: {0:.2f} meters").format(total_width))
            self.total_height.setText(self.tr("Total Height: {0:.2f} meters").format(total_height))

            
        else:
            try:
                total_width = self.width * self.count_x + (self.count_x - 1) * self.gap_x
                total_height = self.height * self.count_y + (self.count_y - 1) * self.gap_y

                # Update the labels with the fitted dimensions using self.tr
                self.width_label.setText(self.tr("Parcel Width: {0:.2f} meters").format(self.width))
                self.height_label.setText(self.tr("Parcel Height: {0:.2f} meters").format(self.height))
                self.gap_x_layout.setText(self.tr("Gap X: {0:.2f} meters").format(self.gap_x))
                self.gap_y_layout.setText(self.tr("Gap Y: {0:.2f} meters").format(self.gap_y))
                self.total_width.setText(self.tr("Total Width: {0:.2f} meters").format(total_width))
                self.total_height.setText(self.tr("Total Height: {0:.2f} meters").format(total_height))
            except:
                self.width = app_state.width
                self.height = app_state.height
                self.gap_x = app_state.gap_x
                self.gap_y = app_state.gap_y
                self.count_x = app_state.count_x
                self.count_y = app_state.count_y
                total_width = self.width * self.count_x + (self.count_x - 1) * self.gap_x
                total_height = self.height * self.count_y + (self.count_y - 1) * self.gap_y

                # Update the labels with the fitted dimensions using self.tr
                self.width_label.setText(self.tr("Parcel Width: {0:.2f} meters").format(self.width))
                self.height_label.setText(self.tr("Parcel Height: {0:.2f} meters").format(self.height))
                self.gap_x_layout.setText(self.tr("Gap X: {0:.2f} meters").format(self.gap_x))
                self.gap_y_layout.setText(self.tr("Gap Y: {0:.2f} meters").format(self.gap_y))
                self.total_width.setText(self.tr("Total Width: {0:.2f} meters").format(total_width))
                self.total_height.setText(self.tr("Total Height: {0:.2f} meters").format(total_height))
        try:
            generator = ParcelGenerator(area_corners, self.width, self.height, self.gap_x, self.gap_y, self.count_x, self.count_y, is_fit, self.color_codes_list)
            self.parcel_coordinates = (generator.generate_parcel_coordinates())
        except:
            self.show_warning(self.tr("Saving Failed!"), self.tr("Please check the input fields and try again."))
            return
        

        js_code = "var parcels = [];\n"  # Initialize the parcels array
        for i, parcel_info in enumerate(self.parcel_coordinates):
            coordinates = parcel_info['coordinates']
            color = parcel_info['color']
            js_code += f"""
            var parcelCoords{i} = {coordinates};
            var parcel{i} = new google.maps.Polygon({{
                paths: parcelCoords{i},
                editable: false,
                draggable: false,
                strokeColor: '#000000',
                strokeOpacity: 0.8,
                strokeWeight: 1,
                fillColor: '{color}',
                fillOpacity: 0.35,
                map: map
            }});
            parcels.push(parcel{i});
            """
            self.parcel_js_references.append(f"parcel{i}")  # Store JavaScript reference

        # self.map_widget.view.page().runJavaScript(js_code)

        # Convert the input strings to float for latitude and longitude
        t_l_lat = float(self.top_left_lat_input.text())
        t_l_lon = float(self.top_left_lon_input.text())
        t_r_lat = float(self.top_right_lat_input.text())
        t_r_lon = float(self.top_right_lon_input.text())
        b_l_lat = float(self.bot_left_lat_input.text())
        b_l_lon = float(self.bot_left_lon_input.text())
        b_r_lat = float(self.bot_right_lat_input.text())
        b_r_lon = float(self.bot_right_lon_input.text())

        # Calculate the center for latitude and longitude
        center_lat = (t_l_lat + b_l_lat + t_r_lat + b_r_lat) / 4
        center_lon = (t_l_lon + t_r_lon + b_l_lon + b_r_lon) / 4

        if t_l_lat:
            # JavaScript code to update the map center and zoom level
            zoom_level = 18  # Set your desired zoom level here
            js_code = f"""
            map.setCenter({{ lat: parseFloat({center_lat}), lng: parseFloat({center_lon}) }});
            map.setZoom({zoom_level});
            """
            # self.map_widget.view.page().runJavaScript(js_code)

        self.map_widget.generate_parcels(self.parcel_coordinates, center_lat, center_lon, zoom_level)
        self.change_language(app_state.language)

    def window(self, window):
        logger.debug(f"window defined for the value of: {window}")
        self.main_window = window

    def back(self):
        logger.debug("directing to the main window")
        # When coming back to the main window, save the state again
        try:
            app_state.save_state(
                self.button_names,
                self.width,
                self.height,
                self.gap_x,
                self.gap_y,
                self.count_x,
                self.count_y,
                self.colored_parcels
            )
        except:
            from parcel_main import MainWindow
            self.main_window = MainWindow()
        
        try:
            if not self.main_window:
                from parcel_main import MainWindow
                self.main_window = MainWindow()
        except:
            from parcel_main import MainWindow
            self.main_window = MainWindow()

        app_state.colored_parcels = self.colored_parcels
        app_state.file_opened = self.file_opened
        app_state.button_params = self.button_params
        app_state.acc_buffer = self.acc_buffer

        self.main_window.initialize_params(app_state)

        planning_window_geometry = self.geometry()
        self.main_window.setGeometry(planning_window_geometry)

        self.main_window.show()
        self.hide()

    def get_color(self, i):
        logger.debug(f"color getting for the value of: {i}")
        try:
            return self.color_codes_list[i]
        except:
            return "#964B00"
        
    def show_warning(self, title, content):
        logger.debug(f"showing warning with the value of: {title, content}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(self.tr(title))
        msg.setInformativeText(content)
        msg.setWindowTitle(self.tr("Warning"))
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        ret = msg.exec()
        
        if ret == QMessageBox.StandardButton.Ok:
            print("User clicked OK")
        else:
            print("User clicked Cancel or closed the dialog")

    def show_info(self, title, content):
        logger.debug(f"showing info with the value of: {title, content}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)  # Set the icon to Information
        msg.setText(title)
        msg.setInformativeText(content)
        msg.setWindowTitle(self.tr("Information"))  # Set the title to "Information"
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)  # Only show the OK button
        msg.setDefaultButton(QMessageBox.StandardButton.Ok)  # Set OK as the default button
        ret = msg.exec()

        if ret == QMessageBox.StandardButton.Ok:
            print("User clicked OK")
        
    def get_all_parcels(self):
        logger.debug("getting all parcels")
        return self.parcel_coordinates
    
    def calculate_top_center(self, top_left, top_right):
        """Calculates the top center of a parcel"""
        logger.debug(f"calculating top center for the value of: {top_left, top_right}")
        lat1, lon1 = float(top_left['lat']), float(top_left['lng'])
        lat2, lon2 = float(top_right['lat']), float(top_right['lng'])
        center_lat = (lat1 + lat2) / 2
        center_lon = (lon1 + lon2) / 2
        return (center_lat, center_lon)

    def calculate_bottom_center(self, bottom_left, bottom_right):
        """Calculates the bottom center of a parcel"""
        logger.debug(f"calculating bottom center for the value of: {bottom_left, bottom_right}")
        lat1, lon1 = float(bottom_left['lat']), float(bottom_left['lng'])
        lat2, lon2 = float(bottom_right['lat']), float(bottom_right['lng'])
        center_lat = (lat1 + lat2) / 2
        center_lon = (lon1 + lon2) / 2
        return (center_lat, center_lon)


    def generate_path(self):
        """
        Validates if the parcel height can be fully divided by the spray width and generates the path accordingly.
        If the parcel height cannot be divided evenly, show a warning message.
        Additionally, it saves parcel points to redisplay later.
        """
        logger.debug("Generating path")
        
        # Get the spraying width from the input
        try:
            spraying_width = float(self.spraying_width_input.text())
        except ValueError:
            self.show_warning(self.tr("Invalid Input"), self.tr("Please enter a valid spraying width."))
            return False

        all_parcels = self.get_all_parcels()
        if all_parcels is None:
            self.show_warning(self.tr("First Save the Area Coordinates"), self.tr("To generate a path you should save the coordinates first."))
            return False
        if self.current_color is None:
            self.show_warning(self.tr("First Choose a Color"), self.tr("To generate a path you should choose a color first."))
            return False

        # Check if the path for the current color already exists
        if self.current_color in self.paths_by_color:
            logger.debug(f"Path for color {self.current_color} already exists. Displaying saved path.")
            self.path = self.paths_by_color[self.current_color]
            parcel_points = self.parcel_points_by_color.get(self.current_color, [])
            self.draw_path_on_map(self.path, parcel_points)
            total_distance = self.calculate_total_distance(self.path)
            self.update_total_length_label(total_distance)
            return True  # Exit the method since the path is already generated

        # Check if the parcel height can be fully divided by the spraying width
        if self.width % spraying_width != 0:
            self.show_warning(self.tr("Spraying Width Error"), self.tr("The parcel height cannot be evenly divided by the spraying width."))
            return

        # Prepare to store the parcel points and paths
        if self.current_color in self.paths_by_color:
            self.paths_by_color[self.current_color] = []
            self.parcel_points_by_color[self.current_color] = []

        num_passes = int(self.width / spraying_width)
        color_parcels = []
        parcel_points = []
        path = []

        # Generate the passes and calculate top and bottom coordinates for each parcel
        for parcel in all_parcels:
            if parcel['color'] == self.current_color:
                for i in range(num_passes):
                    # Calculate the top and bottom coordinates for each pass
                    factor = (i + 0.5) * spraying_width / self.width  # How far from top to bottom
                    pass_top = self.calculate_intermediate_point(parcel['coordinates'][0], parcel['coordinates'][1], factor)
                    pass_bottom = self.calculate_intermediate_point(parcel['coordinates'][3], parcel['coordinates'][2], factor)
                    color_parcels.append({'top_center': pass_top, 'bottom_center': pass_bottom})
                    path.append(pass_top)
                    path.append(pass_bottom)
                    self.path_color = parcel['color']
                    # Store the parcel points to redisplay later
                    parcel_points.append({'top': pass_top, 'bottom': pass_bottom})

        # Check if multiple parcels exist for scanning
        if len(color_parcels) > 1:
            self.path, total_distance, parcel_points = self.create_scanning_path(color_parcels)
            self.button_name = self.color_to_button_map.get(self.current_color, "Unknown")
            self.update_total_length_label(total_distance)
        elif len(color_parcels) == 1:
            self.path, total_distance, parcel_points = self.create_scanning_path(color_parcels)
            self.update_total_length_label(total_distance)
        else:
            return True

        self.path_coordinates = self.path

        # Store the generated path and parcel points by color
        self.paths_by_color[self.current_color] = self.path
        self.parcel_points_by_color[self.current_color] = parcel_points

        # Draw the path and parcel points on the map
        self.draw_path_on_map(self.path, parcel_points)

        # Calculate and update total distance
        total_distance = self.calculate_total_distance(self.path)
        self.update_total_length_label(total_distance)

        # Ensure the path was generated
        if self.path is None or len(self.path) == 0:
            return False  # Path generation failed

        return True  # Path generation was successful


    def calculate_total_distance(self, path_coordinates):
        logger.debug(f"Calculating total distance for path: {path_coordinates}")
        total_distance = 0
        for i in range(len(path_coordinates) - 1):
            total_distance += self.haversine_distance(path_coordinates[i], path_coordinates[i + 1])
        return total_distance

    def calculate_intermediate_point(self, point1, point2, factor):
        """
        Calculate an intermediate point between two points, determined by the factor.
        Factor should be a value between 0 and 1, where 0 is point1 and 1 is point2.
        """
        logger.debug(f"calculating intermediate point with the value of: {point1, point2, factor}")
        lat1, lon1 = float(point1['lat']), float(point1['lng'])
        lat2, lon2 = float(point2['lat']), float(point2['lng'])
        
        intermediate_lat = lat1 + factor * (lat2 - lat1)
        intermediate_lon = lon1 + factor * (lon2 - lon1)
        
        return (intermediate_lat, intermediate_lon)

    def create_scanning_path(self, parcels):
        logger.debug(f"creating scanning path with the value of: {parcels}")
        """
        This function ensures each parcel is fully scanned from top-to-bottom or bottom-to-top,
        then transitions to the next parcel's center (either top or bottom) based on the shortest distance.
        """
        # Start at the first parcel
        current_index = 0
        n = len(parcels)
        visited = [False] * n
        visited[current_index] = True
        path = []
        total_distance = 0
        parcel_points = []

        # Initially start scanning the first parcel from top to bottom
        parcels[current_index]['top_center_unbuffered'] = parcels[current_index]['top_center']
        parcels[current_index]['bottom_center_unbuffered'] = parcels[current_index]['bottom_center']
        parcels[current_index]['top_center'], parcels[current_index]['bottom_center'] = self.add_acceleration_buffer(
            parcels[current_index]['top_center'],
            parcels[current_index]['bottom_center'],
            self.acc_buffer
        )
        path.append(parcels[current_index]['top_center'])
        path.append(parcels[current_index]['bottom_center'])
        parcel_points.append({
            'start': parcels[current_index]['top_center_unbuffered'],
            'end': parcels[current_index]['bottom_center_unbuffered']
        })
        current_position = parcels[current_index]['bottom_center']
        total_distance += self.haversine_distance(parcels[current_index]['top_center'], current_position)

        for _ in range(n - 1):
            nearest_index = None
            nearest_distance = float('inf')
            next_position = None
            next_scan_order = None

            # Find the nearest unvisited parcel by comparing distances to top and bottom centers
            for i in range(n):
                if not visited[i]:
                    # Calculate distance from current position to both top and bottom of the next parcel
                    distance_to_top = self.haversine_distance(current_position, parcels[i]['top_center'])
                    distance_to_bottom = self.haversine_distance(current_position, parcels[i]['bottom_center'])

                    # Choose the shorter distance and decide the scan order
                    if distance_to_top < distance_to_bottom:
                        distance = distance_to_top
                        scan_order = 'top_to_bottom'
                        position = parcels[i]['top_center']
                    else:
                        distance = distance_to_bottom
                        scan_order = 'bottom_to_top'
                        position = parcels[i]['bottom_center']

                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_index = i
                        next_scan_order = scan_order
                        next_position = position

            # Now, based on the chosen scan order, scan the next parcel
            if next_scan_order == 'top_to_bottom':
                parcels[nearest_index]['top_center_unbuffered'] = parcels[nearest_index]['top_center']
                parcels[nearest_index]['bottom_center_unbuffered'] = parcels[nearest_index]['bottom_center']
                parcels[nearest_index]['top_center'], parcels[nearest_index]['bottom_center'] = self.add_acceleration_buffer(
                    parcels[nearest_index]['top_center'],
                    parcels[nearest_index]['bottom_center'],
                    self.acc_buffer
                )
                path.append(parcels[nearest_index]['top_center'])
                path.append(parcels[nearest_index]['bottom_center'])
                parcel_points.append({
                    'start': parcels[nearest_index]['top_center_unbuffered'],
                    'end': parcels[nearest_index]['bottom_center_unbuffered']
                })
                total_distance += nearest_distance
                total_distance += self.haversine_distance(parcels[nearest_index]['top_center'], parcels[nearest_index]['bottom_center'])
                current_position = parcels[nearest_index]['bottom_center']
            else:
                parcels[nearest_index]['bottom_center_unbuffered'] = parcels[nearest_index]['bottom_center']
                parcels[nearest_index]['top_center_unbuffered'] = parcels[nearest_index]['top_center']
                parcels[nearest_index]['bottom_center'], parcels[nearest_index]['top_center'] = self.add_acceleration_buffer(
                    parcels[nearest_index]['bottom_center'],
                    parcels[nearest_index]['top_center'],
                    self.acc_buffer
                )
                path.append(parcels[nearest_index]['bottom_center'])
                path.append(parcels[nearest_index]['top_center'])
                parcel_points.append({
                    'start': parcels[nearest_index]['bottom_center_unbuffered'],
                    'end': parcels[nearest_index]['top_center_unbuffered']
                })
                total_distance += nearest_distance
                total_distance += self.haversine_distance(parcels[nearest_index]['bottom_center'], parcels[nearest_index]['top_center'])
                current_position = parcels[nearest_index]['top_center']

            visited[nearest_index] = True

        return path, total_distance, parcel_points


    def add_acceleration_buffer(self, start_point, end_point, distance=2):
        """
        Extend the path by adding extra space for speeding up and slowing down.
        This function will extend the start_point by `distance` meters before it and the end_point
        by `distance` meters after it in the same direction.

        :param start_point: The starting coordinates of the path (lat, lng).
        :param end_point: The ending coordinates of the path (lat, lng).
        :param distance: The distance to extend (in meters).
        :return: The new start and end coordinates with extended path.
        """
        logger.debug(f"adding acceleration buffer with the value of: {start_point, end_point, distance}")
        # Convert lat/lng to radians
        lat1, lon1 = math.radians(start_point[0]), math.radians(start_point[1])
        lat2, lon2 = math.radians(end_point[0]), math.radians(end_point[1])

        # Calculate the bearing (direction) from start_point to end_point
        bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2),
                            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))

        # Earth's radius in meters
        R = 6371000

        # Extend the start point by `-distance` meters (going backwards)
        extended_start_lat = math.asin(math.sin(lat1) * math.cos(distance / R) +
                                    math.cos(lat1) * math.sin(distance / R) * math.cos(bearing + math.pi))
        extended_start_lon = lon1 + math.atan2(math.sin(bearing + math.pi) * math.sin(distance / R) * math.cos(lat1),
                                            math.cos(distance / R) - math.sin(lat1) * math.sin(extended_start_lat))

        # Extend the end point by `distance` meters (going forwards)
        extended_end_lat = math.asin(math.sin(lat2) * math.cos(distance / R) +
                                    math.cos(lat2) * math.sin(distance / R) * math.cos(bearing))
        extended_end_lon = lon2 + math.atan2(math.sin(bearing) * math.sin(distance / R) * math.cos(lat2),
                                            math.cos(distance / R) - math.sin(lat2) * math.sin(extended_end_lat))

        # Convert extended coordinates back to degrees
        extended_start_point = (math.degrees(extended_start_lat), math.degrees(extended_start_lon))
        extended_end_point = (math.degrees(extended_end_lat), math.degrees(extended_end_lon))

        return extended_start_point, extended_end_point


    def haversine_distance(self, coord1, coord2):
        """Calculate the great-circle distance between two points on the Earth's surface in meters."""
        logger.debug(f"calculating haversine distance with the value of: {coord1, coord2}")
        # Ensure coordinates are being parsed as floats
        lat1, lon1 = float(coord1[0]), float(coord1[1])
        lat2, lon2 = float(coord2[0]), float(coord2[1])
        
        # Earth’s radius in meters (not kilometers)
        R = 6371000  # meters

        # Convert degrees to radians
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        # Haversine formula
        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c  # Distance in meters
        return distance  # Return the distance in meters

    def draw_path_on_map(self, path_coordinates, parcel_points):
        logger.debug(f"drawing path on the map with the value of: {path_coordinates}")

        js_code = ""

        # JavaScript to remove the previous path if it exists
        if self.current_path is not None:
            js_code += f"{self.current_path}.remove();\n"

        # JavaScript to remove the previous start and end markers if they exist
        if self.current_start_marker is not None:
            js_code += f"{self.current_start_marker}.remove();\n"
        if self.current_end_marker is not None:
            js_code += f"{self.current_end_marker}.remove();\n"

        # Remove previous parcel markers
        if hasattr(self, 'parcel_marker_js_references') and self.parcel_marker_js_references:
            for marker_ref in self.parcel_marker_js_references:
                js_code += f"{marker_ref}.remove();\n"
            self.parcel_marker_js_references = []

        # Check if there are coordinates to work with
        if len(path_coordinates) == 0:
            logger.error("No path coordinates provided.")
            return

        # JavaScript to add a marker at the start point (first coordinate) with an "S"
        start_lat, start_lng = path_coordinates[0]
        js_code += f"""
        var startMarker = L.marker([{start_lat}, {start_lng}], {{
            title: 'Start Point',
            icon: L.divIcon({{
                className: 'custom-start-marker',
                html: '<div style="background-color:#FF0000; border-radius:50%; width:20px; height:20px; line-height:20px; text-align:center; color:white;">S</div>',
                iconSize: [20, 20]
            }})
        }}).addTo(window.mapObject);\n"""

        # JavaScript to add a marker at the end point (last coordinate) with an "F"
        end_lat, end_lng = path_coordinates[-1]
        js_code += f"""
        var endMarker = L.marker([{end_lat}, {end_lng}], {{
            title: 'End Point',
            icon: L.divIcon({{
                className: 'custom-end-marker',
                html: '<div style="background-color:#0000FF; border-radius:50%; width:20px; height:20px; line-height:20px; text-align:center; color:white;">F</div>',
                iconSize: [20, 20]
            }})
        }}).addTo(window.mapObject);\n"""

        # JavaScript to draw the new path
        js_code += f"""
        var pathCoordinates = [{", ".join(f"[{coord[0]}, {coord[1]}]" for coord in path_coordinates)}];
        var parcelPath = L.polyline(pathCoordinates, {{
            color: '#FF0000',
            weight: 2,
            opacity: 1.0,
            smoothFactor: 1
        }}).addTo(window.mapObject);\n"""

        # Add markers at the start and end of each parcel
        for idx, parcel_point in enumerate(parcel_points):
            start_lat, start_lng = parcel_point['start']
            end_lat, end_lng = parcel_point['end']

            # Add marker at start
            marker_start_name = f"parcelStartMarker{idx}"
            js_code += f"""
            var {marker_start_name} = L.marker([{start_lat}, {start_lng}], {{
                title: 'Parcel Start Point {idx+1}',
                icon: L.divIcon({{
                    className: 'custom-parcel-marker',
                    html: '<div style="background-color:#000000; border-radius:50%; width:5px; height:5px;"></div>',
                    iconSize: [5, 5]
                }})
            }}).addTo(window.mapObject);\n"""
            self.parcel_marker_js_references.append(marker_start_name)

            # Add marker at end
            marker_end_name = f"parcelEndMarker{idx}"
            js_code += f"""
            var {marker_end_name} = L.marker([{end_lat}, {end_lng}], {{
                title: 'Parcel End Point {idx+1}',
                icon: L.divIcon({{
                    className: 'custom-parcel-marker',
                    html: '<div style="background-color:#000000; border-radius:50%; width:5px; height:5px;"></div>',
                    iconSize: [5, 5]
                }})
            }}).addTo(window.mapObject);\n"""
            self.parcel_marker_js_references.append(marker_end_name)

        # Run the accumulated JavaScript code
        self.map_widget.view.page().runJavaScript(js_code)

        # Update the references for the current path, start marker, and end marker
        self.current_path = 'parcelPath'
        self.current_start_marker = 'startMarker'
        self.current_end_marker = 'endMarker'


    def update_total_length_label(self, total_distance):
        """Update the label with the total path length"""
        logger.debug(f"updating total length with the value of: {total_distance}")
        if total_distance >= 1000:
            self.total_length_label.setText(f"Total Path Length: {total_distance / 1000:.2f} km")
        else:
            self.total_length_label.setText(f"Total Path Length: {total_distance:.2f} meters")

    def create_mavlink_script(self, path_coordinates):
        """
        Generate a MAVLink script from the given path coordinates.
        :param path_coordinates: A list of tuples (lat, lon) representing the path.
        """
        logger.debug(f"creating mavlink script with the value of: {path_coordinates}")
        if not path_coordinates:
            self.show_warning(self.tr("Mission cannot be created"), self.tr("To generate the mission successfully save the map location and generate the path."))
            return

        if self.current_path is None:
            self.show_warning(self.tr("Mission cannot be created"), self.tr("To generate the mission successfully pick the color for the mission"))
            return

        if self.current_color is None:
            self.show_warning(self.tr("Mission cannot be created"), self.tr("To generate the mission successfully pick the color for the mission"))
            return

        name = self.hex_to_color_name(self.current_color)

        # Get the calculated ground speed
        try:
            ground_speed_m_s = self.velocity_results.get("ground_speed_m_s")
        except:
            self.show_warning(self.tr("Mission cannot be created"), self.tr("To generate the mission successfully firstly pick the color for the mission"))
            return

        if not ground_speed_m_s:
            self.show_warning(self.tr("Speed Not Calculated"), self.tr("Please calculate the velocity before generating the mission."))
            return

        # Get the altitude from the input
        try:
            altitude = float(self.set_alt_input.text())
            if altitude <= 0:
                raise ValueError
        except ValueError:
            self.show_warning(self.tr("Invalid Altitude"), self.tr("Please enter a valid altitude."))
            return

        # Get the home coordinates
        try:
            home_lat = float(self.top_left_lat_input.text())
            home_lon = float(self.top_left_lon_input.text())
        except ValueError:
            self.show_warning(self.tr("Invalid lat - lon", "Please enter a valid coordinate."))
            return

        mavlink_data = ["QGC WPL 110"]
        seq = 0
        # Add home waypoint (this can be adjusted if you have a specific home location)
        mavlink_data.append(f"{seq}\t1\t0\t16\t0\t0\t0\t0\t{home_lat}\t{home_lon}\t1.990000\t1")
        seq += 1
        # Add takeoff command
        mavlink_data.append(f"{seq}\t0\t3\t22\t0\t0\t0\t0\t0\t0\t{altitude}\t1")
        seq += 1
        # Set the ground speed
        mavlink_data.append(f"{seq}\t0\t3\t178\t1\t{ground_speed_m_s}\t-1\t0\t0\t0\t0\t1")
        seq += 1

        # Get parcel_points for the current color
        parcel_points = self.parcel_points_by_color.get(self.current_color, [])

        if not parcel_points:
            self.show_warning(self.tr("No Parcel Points"), self.tr("No parcel points found for the current color."))
            return

        # Ensure the path coordinates match the parcel points
        if len(path_coordinates) != 2 * len(parcel_points):
            self.show_warning(self.tr("Data Mismatch"), self.tr("Path coordinates do not match parcel points."))
            return

        # Iterate over parcels
        for idx, parcel_point in enumerate(parcel_points):
            # Indices for path_coordinates
            i = idx * 2

            # Start point with acceleration buffer
            lat_start_buffer, lon_start_buffer = path_coordinates[i]
            # End point with acceleration buffer
            lat_end_buffer, lon_end_buffer = path_coordinates[i + 1]

            # Actual parcel start and end points from parcel_points
            lat_start_parcel, lon_start_parcel = parcel_point['start']
            lat_end_parcel, lon_end_parcel = parcel_point['end']

            # Waypoint to approach start point (with acceleration buffer)
            mavlink_data.append(f"{seq}\t0\t3\t16\t0\t0\t0\t0\t{lat_start_buffer}\t{lon_start_buffer}\t{altitude}\t1")
            seq += 1

            # Waypoint at start of parcel (where spraying begins)
            mavlink_data.append(f"{seq}\t0\t3\t183\t0\t1\t0\t0\t{lat_start_parcel}\t{lon_start_parcel}\t{altitude}\t1")
            seq += 1

            # Waypoint at end of parcel (where spraying ends)
            mavlink_data.append(f"{seq}\t0\t3\t183\t0\t0\t0\t0\t{lat_end_parcel}\t{lon_end_parcel}\t{altitude}\t1")
            seq += 1

            # Waypoint to move to the end point with acceleration buffer
            mavlink_data.append(f"{seq}\t0\t3\t16\t0\t0\t0\t0\t{lat_end_buffer}\t{lon_end_buffer}\t{altitude}\t1")
            seq += 1

        # Add return-to-launch command (MAV_CMD_NAV_RETURN_TO_LAUNCH)
        mavlink_data.append(f"{seq}\t0\t3\t20\t0\t0\t0\t0\t0\t0\t0\t1")

        # Define the file path
        button_name = self.color_to_button_map.get(self.current_color, "Unknown")
        file_path = os.path.join(missions_dir, f"{name}_{button_name}_{app_state.timestamp}_generated_mavlink_script.waypoints")

        # Save to file
        with open(file_path, "w") as file:
            file.write("\n".join(mavlink_data))

        self.show_info("Mission created successfully", f"MAVLink script generated and saved at '{file_path}'")

    def remove_acceleration_buffer(self, start_point, end_point, distance=2):
        """
        Remove the acceleration buffer from a point to get the actual parcel point.
        :param start_point: The starting point with buffer (lat, lon).
        :param end_point: The end point (lat, lon).
        :param distance: The buffer distance in meters.
        :return: The new point without the buffer.
        """
        logger.debug(f"Removing acceleration buffer with the value of: {start_point, end_point, distance}")
        # Convert lat/lon to radians
        lat1, lon1 = math.radians(start_point[0]), math.radians(start_point[1])
        lat2, lon2 = math.radians(end_point[0]), math.radians(end_point[1])

        # Calculate the bearing from start_point to end_point
        bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2),
                            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))

        # Earth's radius in meters
        R = 6371000

        # Move 'distance' meters from start_point towards end_point along the bearing
        # This effectively removes the acceleration buffer
        new_lat = math.asin(math.sin(lat1) * math.cos(distance / R) +
                            math.cos(lat1) * math.sin(distance / R) * math.sin(bearing))
        new_lon = lon1 + math.atan2(math.sin(bearing) * math.sin(distance / R) * math.cos(lat1),
                                    math.cos(distance / R) - math.sin(lat1) * math.sin(new_lat))

        # Convert back to degrees
        new_start_point = (math.degrees(new_lat), math.degrees(new_lon))

        return new_start_point
    
    def confirm_quit(self):
        """Show a confirmation dialog before quitting."""
        # Create a message box for the quit confirmation
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Quit")
        msg_box.setText("Do you want to quit without saving?")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        # Add buttons for "Save and Quit," "Quit without Saving," and "Cancel"
        save_and_quit_button = msg_box.addButton("Save and Quit", QMessageBox.ButtonRole.AcceptRole)
        quit_without_saving_button = msg_box.addButton("Quit without Saving", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)

        # Execute the message box and handle the user's choice
        msg_box.exec()

        # Determine which button was clicked and return the corresponding value
        if msg_box.clickedButton() == save_and_quit_button:
            return "save_and_quit"
        elif msg_box.clickedButton() == quit_without_saving_button:
            return "quit_without_saving"
        else:
            return "cancel"

    def closeEvent(self, event):
        """Override the closeEvent to show the confirmation dialog when clicking the window close button."""
        user_choice = self.confirm_quit()

        # Handle the user's choice
        if user_choice == "save_and_quit":
            self.map_widget.save_map_coordinates()  # Save the map coordinates
            self.save_config()
            self.save_settings_to_config(self.get_current_language(), self.night_mode_action.isChecked())
            event.accept()  # Close the window
        elif user_choice == "quit_without_saving":
            self.map_widget.save_map_coordinates()
            self.save_settings_to_config(self.get_current_language(), self.night_mode_action.isChecked())
            event.accept()  # Close the window without saving
        else:
            event.ignore()  # Cancel the close event

    def get_current_language(self):
        if self.lang_action_en.isChecked():
            return 'en'
        elif self.lang_action_es.isChecked():
            return 'es'
        return 'en'  # Default to English if none is selected

    def load_coordinates_from_config(self):
        config = configparser.ConfigParser()

        # Check if the config file exists
        if os.path.exists(self.config_file):
            print(f"Config file found at: {self.config_file}")
            config.read(self.config_file)
            
            # Debug: Print config sections
            print(f"Config sections: {config.sections()}")
            
            if 'Location' in config:
                # Attempt to get latitude, longitude, and zoom from the config file
                try:
                    self.top_left_lat_input.setText((config.get("Location", "a-lat")))
                    self.top_left_lon_input.setText((config.get("Location", "a-lon")))
                    self.top_right_lat_input.setText((config.get("Location", "b-lat")))
                    self.top_right_lon_input.setText((config.get("Location", "b-lon")))
                    self.bot_left_lat_input.setText((config.get("Location", "c-lat")))
                    self.bot_left_lon_input.setText((config.get("Location", "c-lon")))
                    self.bot_right_lat_input.setText((config.get("Location", "d-lat")))
                    self.bot_right_lon_input.setText((config.get("Location", "d-lon")))
                except Exception as e:
                    print(f"Error reading config values: {e}")
                    # Return default values if there's an error
                    return (37.32500, -6.02884), 15
            else:
                print("No 'Location' section in the config file.")
                return (37.32500, -6.02884), 15
        else:
            print("Config file does not exist.")
            # Return default values if the file does not exist
            return (37.32500, -6.02884), 15
        

    def save_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)
        config['Location'] = {
            'a-lat': str(float(self.top_left_lat_input.text())),
            'a-lon': str(float(self.top_left_lon_input.text())),
            'b-lat': str(float(self.top_right_lat_input.text())),
            'b-lon': str(float(self.top_right_lon_input.text())),
            'c-lat': str(float(self.bot_left_lat_input.text())),
            'c-lon': str(float(self.bot_left_lon_input.text())),
            'd-lat': str(float(self.bot_right_lat_input.text())),
            'd-lon': str(float(self.bot_right_lon_input.text())),
            'zoom': str(18)
        }
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)

    def save_settings_to_config(self, language, night_mode):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)
        if 'Settings' not in config:
            config['Settings'] = {}
        config['Settings']['language'] = language
        config['Settings']['night_mode'] = str(night_mode)
        with open(self.config_file, 'w') as configfile:
            config.write(configfile)


if __name__ == "__main__":
    logger.info("Starting planner")

    app = QApplication(sys.argv)
    icon_path = "C:\\Users\\Getac\\Documents\\Omer Mersin\\codes\\parcel_planner\\DRONETOOLS.ico"
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    window = PlannerMainWindow()
    window.show()

    sys.exit(app.exec())