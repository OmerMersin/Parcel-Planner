import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QSplitter, QFormLayout, QPushButton, QGridLayout, QSizePolicy, QMessageBox, QGraphicsEllipseItem, QToolBar, QFileDialog
from PyQt6.QtCore import Qt, QUrl, QEvent, pyqtSignal, QSystemSemaphore, QSharedMemory 
from PyQt6.QtGui import QBrush, QColor, QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import time
import logging
from logging.handlers import RotatingFileHandler
import os
import json


log_file_path = os.path.join(os.path.dirname(__file__), "app.log")
sys.stdout = open(log_file_path, "w")
sys.stderr = open(log_file_path, "w")

def resource_path(relative_path):
    """ Get absolute path to resource, works for development and for PyInstaller """
    try:
        # When running as an executable, use the folder where the .exe is located
        base_path = os.path.dirname(sys.executable)
    except AttributeError:
        # When running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Generate the log file name once
log_file_name = f"{time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
log_file_path = os.path.join(resource_path('logs'), log_file_name)

def create_logger():
    logs_dir = resource_path('logs')

    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Use the pre-generated log file name
    log_file = log_file_path

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Prevent adding duplicate handlers
    if not hasattr(logger, 'handler_set'):
        handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=3)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.handler_set = True  # Custom attribute to prevent re-adding handlers

    return logger

# Initialize the logger in the main module
logger = create_logger()


class AppState:
    def __init__(self):
        self.button_names = {i: f"{i}" for i in range(1, 11)}  # Default button names
        self.width = 3.0
        self.height = 5.0
        self.gap_x = 0.3
        self.gap_y = 1.0
        self.count_x = 6
        self.count_y = 5
        self.colored_parcels = {}
        self.timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        self.location = [[37.32500, -6.02884], [37.32490, -6.02861], [37.32466, -6.02899], [37.32427,-6.02829]]
        self.spraying_width = 1.5
        self.fit = False
        self.paths_by_color = {}
        self.application_dose = 300
        self.nozzle_rate = 0.8
        self.nozzle_number = 4
        self.altitude = 25
        self.parcel_coordinates = []
        self.button_params = {}
        self.acc_buffer = 2.0
        self.file_opened = False

    
    def save_state(self, button_names, width, height, gap_x, gap_y, count_x, count_y, colored_parcels):
        self.button_names = button_names
        self.width = width
        self.height = height
        self.gap_x = gap_x
        self.gap_y = gap_y
        self.count_x = count_x
        self.count_y = count_y
        self.colored_parcels = colored_parcels
        self.paths_by_color = self.paths_by_color


app_state = AppState() 

class ColorButtonWidget(QWidget):
    color_clicked = pyqtSignal(str)
    button_named = pyqtSignal(dict)

    def __init__(self, number, color_name, button_name):
        super().__init__()

        self.color_name = color_name  # Store the color name
        self.button_name = button_name
        self.button_names = app_state.button_names  # Adjust range based on the number of buttons
        self.button_number = int(self.button_names[int(self.button_name)])
        self.count_x = 0
        self.count_y = 0

        self.color_hex = QColor(color_name).name()

        # Create a QPushButton for the button functionality
        self.button = QPushButton(str(number))
        self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Style to give the white background just behind the text
        self.button.setStyleSheet(
            f"""
            background-color: {color_name};  /* Full button color */
            color: black;  /* Text color */
            padding: 5px;  /* Space around the text */
            border-radius: 15px;  /* Rounded corners for the button */
            border: none;  /* Remove any borders */
            """
        )

        # Create an internal QLabel to mimic the text background effect
        self.text_background_label = QLabel(self.button.text())
        self.text_background_label.setStyleSheet(
            """
            background-color: white;  /* White background just behind the text */
            padding: 3px;  /* Add some padding for spacing */
            border-radius: 5px;  /* Rounded background for text */
            """
        )
        self.text_background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set the text inside the button to transparent and stack QLabel over it
        self.button.setText("")  # Remove default text
        button_layout = QVBoxLayout(self.button)
        button_layout.addWidget(self.text_background_label)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setContentsMargins(0, 0, 0, 0)

        # Connect left-click signal to emit color
        self.button.clicked.connect(self.on_button_click)

        # Create a QLineEdit for the editable area
        self.editable_area = QLineEdit()
        self.editable_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.editable_area.hide()  # Initially hidden, shown on right-click

        # Make the QLineEdit focusable and editable
        self.editable_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.editable_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.editable_area.setStyleSheet(f"background-color: {color_name};")
        self.editable_area.editingFinished.connect(self.on_editing_finished)

        # Layout to arrange the button and line edit
        layout = QHBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.editable_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.setLayout(layout)

        # Install an event filter to detect right-clicks on the button
        self.button.installEventFilter(self)

    def on_button_click(self, color_name):
        # Emit the color of the button when clicked
        self.color_clicked.emit(self.color_name)

    def eventFilter(self, obj, event):
        if obj == self.button and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:  # Detect right-click
                # Switch to editable mode on right-click
                self.editable_area.setText(self.text_background_label.text())
                self.button.hide()
                self.editable_area.show()
                self.editable_area.setFocus()
                return True
        return super().eventFilter(obj, event)

    def on_editing_finished(self):
        # Switch back to button mode after editing is done
        new_text = self.editable_area.text()
        self.text_background_label.setText(new_text)
        self.editable_area.hide()
        self.update_button_names(self, self.button_name)
        self.button_named.emit(self.button_names) 
        self.button.show()

    def update_button_names(self, button_widget, button_name):
        self.button_names[self.button_number] = button_widget.text_background_label.text()
        self.button_named.emit(self.button_names)
        self.button_name = button_widget.text_background_label.text()


class ParcelField(QWidget):
    def __init__(self):
        super().__init__()
        logger.debug("ParcelField initialized")

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)
        self.margin = 20

        self.parcels = []
        self.current_color = QColor("white")
        self.parcel_colors = {}  # Dictionary to store parcel color mappings
        self.parcel_identifiers = {}  # Initialize the dictionary for parcel identifiers
        self.color_buttons = [] 


    def update_field(self, width, height, gap_x, gap_y, count_x, count_y, structure_changed=False):
        logger.debug(f"updating field with the value of: {width, height, gap_x, gap_y, count_x, count_y}")
        saved_colors = self.get_colored_parcels()
        self.count_x = count_x
        self.count_y = count_y

        self.total_width = self.view.width()
        self.total_height = self.view.height()

        total_parcel_width = (count_x * width) + ((count_x - 1) * gap_x)
        total_parcel_height = (count_y * height) + ((count_y - 1) * gap_y)

        available_width = self.total_width - 2 * self.margin
        available_height = self.total_height - 2 * self.margin
        scale_x = available_width / total_parcel_width if total_parcel_width != 0 else 1
        scale_y = available_height / total_parcel_height if total_parcel_height != 0 else 1

        scale_factor = min(scale_x, scale_y)

        scaled_width = width * scale_factor
        scaled_height = height * scale_factor
        scaled_gap_x = gap_x * scale_factor
        scaled_gap_y = gap_y * scale_factor

        offset_x = self.margin + (available_width - (count_x * scaled_width + (count_x - 1) * scaled_gap_x)) / 2
        offset_y = self.margin

        self.scene.clear()
        self.parcels.clear()
        self.parcel_identifiers.clear()

        for j in range(count_y):
            for i in range(count_x):
                x = offset_x + i * (scaled_width + scaled_gap_x)
                y = offset_y + j * (scaled_height + scaled_gap_y)
                parcel = QGraphicsRectItem(x, y, scaled_width, scaled_height)
                parcel.setBrush(QColor("white"))
                parcel.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
                parcel.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsFocusable)
                parcel_id = j * count_x + i
                self.parcel_identifiers[parcel] = parcel_id
                parcel.mousePressEvent = self.on_parcel_click
                self.scene.addItem(parcel)
                self.parcels.append(parcel)

        self.add_axis_labels(total_parcel_width, total_parcel_height, scale_factor, offset_x, offset_y)
        self.view.setScene(self.scene)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.add_corner_labels(scaled_width, scaled_height, scaled_gap_x, scaled_gap_y, offset_x, offset_y, count_x, count_y)
        self.restore_parcels_with_colors(saved_colors)
        if structure_changed:
            valid_parcel_ids = set(self.parcel_identifiers.values())
            self.parcel_colors = {pid: color_info for pid, color_info in self.parcel_colors.items() if pid in valid_parcel_ids}

        # Restore colors for the parcels
        self.restore_parcels_with_colors(self.parcel_colors)


    
    def add_corner_labels(self, parcel_width, parcel_height, gap_x, gap_y, offset_x, offset_y, count_x, count_y):
        """Add A, B, C, D markers at the corners of the parcel grid."""
        logger.debug("adding corner labels A, B, C, D")

        # Coordinates for A (Top-left corner of the first parcel)
        x_a = offset_x
        y_a = offset_y
        self.add_label_to_corner("A", x_a, y_a)

        # Coordinates for B (Top-right corner of the top-right parcel)
        x_b = offset_x + (count_x - 1) * (parcel_width + gap_x) + parcel_width
        y_b = offset_y
        self.add_label_to_corner("B", x_b, y_b)

        # Coordinates for C (Bottom-left corner of the bottom-left parcel)
        x_c = offset_x
        y_c = offset_y + (count_y - 1) * (parcel_height + gap_y) + parcel_height
        self.add_label_to_corner("C", x_c, y_c)

        # Coordinates for D (Bottom-right corner of the bottom-right parcel)
        x_d = offset_x + (count_x - 1) * (parcel_width + gap_x) + parcel_width
        y_d = offset_y + (count_y - 1) * (parcel_height + gap_y) + parcel_height
        self.add_label_to_corner("D", x_d, y_d)

    def add_label_to_corner(self, text, x, y):
        """Helper function to add a label with a circle at a given position."""
        logger.debug(f"adding label {text} at position ({x}, {y})")
        
        # Draw a small circle
        circle_radius = 10
        circle = QGraphicsEllipseItem(x - circle_radius, y - circle_radius, circle_radius * 2, circle_radius * 2)
        circle.setBrush(QBrush(Qt.GlobalColor.white))
        self.scene.addItem(circle)

        # Add text inside the circle
        label = QGraphicsTextItem(text)
        
        # Calculate the bounding rectangle of the text to get its dimensions
        bounding_rect = label.boundingRect()

        # Center the text within the circle based on its bounding rect and circle size
        label.setPos(x - bounding_rect.width() / 2, y - bounding_rect.height() / 2)
        
        # Set the color for the text
        label.setDefaultTextColor(Qt.GlobalColor.black)
        self.scene.addItem(label)


    def add_axis_labels(self, total_width, total_height, scale_factor, offset_x, offset_y):
        logger.debug(f"adding axis labels with the value of: {total_width, total_height, scale_factor, offset_x, offset_y}")
        displayed_width = total_width * scale_factor
        displayed_height = total_height * scale_factor

        x_label = QGraphicsTextItem(f"Total X: {total_width}m")
        y_label = QGraphicsTextItem(f"Total Y: {total_height}m")

        x_label.setPos(offset_x + displayed_width / 2 - x_label.boundingRect().width() / 2, self.total_height - self.margin + 5)
        y_label.setPos(self.margin - y_label.boundingRect().width() - 5, offset_y + displayed_height / 2 - y_label.boundingRect().height() / 2)

        self.scene.addItem(x_label)
        self.scene.addItem(y_label)

    def set_current_color(self, button_widget, color):
        if isinstance(color, QColor):
            self.current_color = color
        else:
            self.current_color = QColor(color)        
        # Reset borders on all buttons but keep their colors
        for btn_widget in self.color_buttons:
            # Reset the style of each button (remove borders and restore color)
            btn_widget.button.setStyleSheet(f"padding: 5px; border-radius: 15px; background-color: {btn_widget.color_hex}; border: none;")
        
        # Set the selected button with a new style (add border)
        button_widget.button.setStyleSheet(f"background-color: {button_widget.color_hex}; border: 2px solid black;")

        # Keep reference to the currently selected button
        self.current_color_button = button_widget


    def get_colored_parcels(self):
        logger.debug("getting colored parcels")
        return self.parcel_colors

    def reset_parcels(self):
        logger.debug("reseting parcels")
        for parcel in self.parcels:
            parcel.setBrush(QColor("white"))

    def restore_parcels_with_colors(self, parcel_data):
        """
        Restore parcels based on saved color and position data efficiently.
        """
        logger.debug("Restoring parcel colors")

        # Create a mapping from parcel_id to parcel
        parcel_id_to_parcel = {self.parcel_identifiers[parcel]: parcel for parcel in self.parcels}

        for parcel_id_str, value in parcel_data.items():
            parcel_id = int(parcel_id_str)
            color, x, y = value

            # Get the parcel directly from the mapping
            parcel = parcel_id_to_parcel.get(parcel_id)
            if parcel:
                parcel.setBrush(QBrush(QColor(color)))
                self.parcel_colors[parcel_id] = (color, x, y)

    def on_parcel_click(self, event):
        logger.debug("A parcel clicked")
        parcel = self.scene.itemAt(event.scenePos(), self.view.transform())

        if isinstance(parcel, QGraphicsRectItem):
            parcel_id = self.parcel_identifiers.get(parcel)  # Get the parcel ID using the parcel identifier dictionary

            if parcel_id is not None:
                # Left-click changes the parcel's color to the currently selected color
                if event.button() == Qt.MouseButton.LeftButton:
                    # Calculate the row and column numbers for the clicked parcel
                    column_number = parcel_id % self.count_x  # Calculate column
                    row_number = parcel_id // self.count_x  # Calculate row
                    user_choice = None  # Initialize user_choice to avoid UnboundLocalError

                    # Calculate the IDs of the directly above and below parcels (if they exist)
                    above_parcel_id = parcel_id - self.count_x if row_number > 0 else None
                    below_parcel_id = parcel_id + self.count_x if row_number < self.count_y - 1 else None

                    # Check if the parcel above or below has the same color as the current one
                    warning_message = ""

                    # Check the color of the parcel directly above (if it exists)
                    if above_parcel_id is not None and above_parcel_id in self.parcel_colors:
                        above_parcel_color = self.parcel_colors[above_parcel_id][0]
                        if above_parcel_color == self.current_color.name():
                            warning_message += "The parcel directly above this one has the same color.\n"

                    # Check the color of the parcel directly below (if it exists)
                    if below_parcel_id is not None and below_parcel_id in self.parcel_colors:
                        below_parcel_color = self.parcel_colors[below_parcel_id][0]
                        if below_parcel_color == self.current_color.name():
                            warning_message += "The parcel directly below this one has the same color.\n"

                    # If either warning condition was triggered, ask the user
                    if warning_message:
                        user_choice = self.show_warning_rep(
                            "Duplicate Color",
                            warning_message + "Do you want to apply this color?"
                        )
                        # If the user clicks "Cancel", return without applying the color
                        if user_choice == "Cancel":
                            return  # Exit without applying the color

                    # Save the previous color in case we need to revert
                    previous_color = self.parcel_colors.get(parcel_id, ("white", parcel.rect().x(), parcel.rect().y()))[0]
                    self.parcel_colors[parcel_id] = (self.current_color.name(), parcel.rect().x(), parcel.rect().y())
                    parcel.setBrush(QBrush(self.current_color))

                    # If the user cancels, revert to the previous color
                    if user_choice == "Cancel":
                        self.parcel_colors[parcel_id] = (previous_color, parcel.rect().x(), parcel.rect().y())
                        parcel.setBrush(QBrush(QColor(previous_color)))

                # Left-click changes the parcel's color to the currently selected color
                if event.button() == Qt.MouseButton.LeftButton:
                    # Check if the current color has already been used count_x times
                    color_usage_count = sum(
                        1 for color_data in self.parcel_colors.values()
                        if color_data[0] == self.current_color.name()
                    )

                    if color_usage_count > self.count_x:
                        user_choice = self.show_warning_rep(
                            "Color Usage Limit Reached",
                            f"The color '{self.hex_to_color_name(self.current_color.name())}' has already been used {color_usage_count} times, which exceeds the maximum allowed ({self.count_x}).\nDo you still want to apply this color?"
                        )
                        if user_choice == "Cancel":
                            return  # Prevent applying the color
                        # If user clicks "Apply", proceed to apply the color

                    # Apply the color
                    self.parcel_colors[parcel_id] = (self.current_color.name(), parcel.rect().x(), parcel.rect().y())
                    parcel.setBrush(QBrush(self.current_color))

                # Right-click resets the parcel's color to white
                elif event.button() == Qt.MouseButton.RightButton:
                    if parcel_id in self.parcel_colors:
                        del self.parcel_colors[parcel_id]
                    parcel.setBrush(QBrush(QColor("white")))

        event.accept()



    def show_warning(self, title, content):
        logger.debug(f"showing warning with the value of: {title, content}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(title)
        msg.setInformativeText(content)
        msg.setWindowTitle("Warning")

        # Add custom buttons for the specific action (Skip and Stay)
        skip_button = msg.addButton("Continue Next Page", QMessageBox.ButtonRole.AcceptRole)
        stay_button = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(stay_button)  # Set "Stay" as the default button

        msg.exec()

        # Return "Apply" or "Cancel" depending on what button was clicked
        if msg.clickedButton() == skip_button:
            return "Skip"
        else:
            return "Cancel"
    
    def show_warning_rep(self, title, content):
        logger.debug(f"showing warning with the value of: {title, content}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(title)
        msg.setInformativeText(content)
        msg.setWindowTitle("Warning")

        # Add custom buttons for the specific action (Apply and Cancel)
        apply_button = msg.addButton("Apply", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(cancel_button)  # Set "Cancel" as the default button

        msg.exec()

        # Return "Apply" or "Cancel" depending on what button was clicked
        if msg.clickedButton() == apply_button:
            return "Apply"
        else:
            return "Cancel"

    
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

    def check_all_colors_used(self):
        """
        Check if any color is used more times than the number of columns.
        Also, check if any rows have empty (white) parcels.
        Show a warning if any color exceeds the limit or if there are empty parcels.
        Allow the user to proceed if they choose.
        """
        logger.debug("Checking for overused colors and rows with empty parcels.")

        # Initialize a dictionary to count usage of each color
        color_usage_counts = {}

        # Initialize a list to keep track of rows with empty parcels
        empty_rows = []

        # Count the usage of each color (excluding white)
        for color_data in self.parcel_colors.values():
            color = color_data[0]
            if color != "white":
                color_usage_counts[color] = color_usage_counts.get(color, 0) + 1

        # Check for empty parcels in each row
        for row in range(self.count_y):
            empty_parcel_found = False

            # Check each parcel in the row
            for parcel_id in range(row * self.count_x, (row + 1) * self.count_x):
                if parcel_id not in self.parcel_colors or self.parcel_colors[parcel_id][0] == "white":
                    empty_parcel_found = True
                    break  # No need to check the rest of the row

            if empty_parcel_found:
                empty_rows.append(row + 1)  # Use row+1 for display (1-indexed)

        # Check if any color exceeds the number of columns (count_x)
        overused_colors = {}
        for color, count in color_usage_counts.items():
            if count > self.count_x:
                overused_colors[color] = count

        # Prepare the warning message if there are overused colors or empty rows
        if overused_colors or empty_rows:
            warning_message = ""

            # Add overused color information to the message
            if overused_colors:
                for color, count in overused_colors.items():
                    color_name = self.hex_to_color_name(color)
                    warning_message += f"Color '{color_name}' is used {count} times, which exceeds the number of columns ({self.count_x}).\n"

            # Add empty parcel information to the message
            if empty_rows:
                empty_rows_str = ", ".join(str(row) for row in empty_rows)
                warning_message += f"Rows {empty_rows_str} have empty (white) parcels.\n"

            # Show the warning message and ask if the user wants to proceed
            user_choice = self.show_warning(
                "Grid Check",
                warning_message + "Do you want to proceed anyway?"
            )

            # Check which button the user clicked
            if user_choice == "Cancel":
                return False  # Return False to indicate the user wants to stay

        # If no issues or user chooses to proceed, return True
        return True

    def fill_non_clicked_parcels(self):
        """
        Fill all parcels that have not been clicked (not colored) with brown color.
        """
        for parcel in self.parcels:
            parcel_id = self.parcel_identifiers[parcel]
            if parcel_id not in self.parcel_colors:
                # Fill with default brown color if not already colored
                parcel.setBrush(QBrush(QColor("white")))
                self.parcel_colors[parcel_id] = ("white", parcel.rect().x(), parcel.rect().y())

                

import ctypes
# Define Windows API function to get the console window handle
kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')

def hide_console():
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, 0)  # 0 = SW_HIDE

def show_console():
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, 1)  # 1 = SW_SHOW

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.debug("MainWindow initialized")

        self.setWindowTitle("Parcel Planner")
        self.map_view = QWebEngineView()
        self.map_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.map_view.setUrl(QUrl("http://localhost:8000/map.html"))
        from planner import PlannerMainWindow
        self.second_window = PlannerMainWindow()
        self.second_window.hide()
        self.file_opened = False
        self.prev_count_x = None
        self.prev_count_y = None
        icon_path = "C:\\Users\\Getac\\Documents\\Omer Mersin\\codes\\parcel_planner\\DRONETOOLS.ico"
        app_icon = QIcon(icon_path)
        self.setWindowIcon(app_icon)

        logger.debug("Setting up UI")
        self.parcel_field = ParcelField()
        self.create_toolbar()

        self.width_label = QLabel("Parcel Width:")
        self.width_input = QLineEdit("3.0")
        self.width_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.width_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.width_input.setAlignment(Qt.AlignmentFlag.AlignRight)


        self.height_label = QLabel("Parcel Height:")
        self.height_input = QLineEdit("5.0")
        self.height_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.height_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.height_input.setAlignment(Qt.AlignmentFlag.AlignRight)


        self.gap_x_label = QLabel("Gap X:")
        self.gap_x_input = QLineEdit("0.3")
        self.gap_x_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gap_x_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gap_x_input.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.gap_y_label = QLabel("Gap Y:")
        self.gap_y_input = QLineEdit("1.0")
        self.gap_y_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gap_y_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gap_y_input.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.meter_label = QLabel("meters")
        width_layout = QHBoxLayout()
        width_layout.addWidget(self.width_label)
        width_layout.addWidget(self.width_input)  # Add QLineEdit to the layout
        width_layout.addWidget(self.meter_label)  # Add QLabel to the layout

        self.meter_label = QLabel("meters")
        height_layout = QHBoxLayout()
        height_layout.addWidget(self.height_label)
        height_layout.addWidget(self.height_input)  # Add QLineEdit to the layout
        height_layout.addWidget(self.meter_label)  # Add QLabel to the layout

        self.meter_label = QLabel("meters")
        gap_x_layout = QHBoxLayout()
        gap_x_layout.addWidget(self.gap_x_label)
        gap_x_layout.addWidget(self.gap_x_input)  # Add QLineEdit to the layout
        gap_x_layout.addWidget(self.meter_label)  # Add QLabel to the layout

        self.meter_label = QLabel("meters")
        gap_y_layout = QHBoxLayout()
        gap_y_layout.addWidget(self.gap_y_label)
        gap_y_layout.addWidget(self.gap_y_input)  # Add QLineEdit to the layout
        gap_y_layout.addWidget(self.meter_label)  # Add QLabel to the layout

        self.empty_label = QLabel("           ")
        count_x_layout = QHBoxLayout()
        self.count_x_label = QLabel("Parcels on X axis:")
        self.count_x_input = QLineEdit("6")
        self.count_x_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.count_x_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.count_x_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        count_x_layout.addWidget(self.count_x_label)
        count_x_layout.addWidget(self.count_x_input)
        count_x_layout.addWidget(self.empty_label)

        self.empty_label = QLabel("           ")
        count_y_layout = QHBoxLayout()
        self.count_y_label = QLabel("Parcels on Y axis:")
        self.count_y_input = QLineEdit("5")
        self.count_y_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.count_y_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.count_y_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        count_y_layout.addWidget(self.count_y_label)
        count_y_layout.addWidget(self.count_y_input)
        count_y_layout.addWidget(self.empty_label)


        self.clear_button = QPushButton("Clear Parcels")
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_parcels)

        self.plan_button = QPushButton("Planning Window")
        self.plan_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.plan_button.clicked.connect(self.planning)


        form_layout = QFormLayout()
        form_layout.addRow(width_layout)
        form_layout.addRow(height_layout)
        form_layout.addRow(gap_x_layout)
        form_layout.addRow(gap_y_layout)
        form_layout.addRow(count_x_layout)
        form_layout.addRow(count_y_layout)
        form_layout.addRow(self.clear_button)

        self.button_names = {i: f"{i}" for i in range(1, 11)}  # Adjust range based on the number of buttons

        right_panel = QWidget()
        right_panel.setLayout(form_layout)

        # Create the color buttons
        self.color_buttons = []
        self.color_button_widgets = []  # List to store ColorButtonWidget references
        self.color_layout = QGridLayout()

        # Mapping Qt.GlobalColor to color names as strings for use in stylesheets
        colors = [
            (Qt.GlobalColor.red, "#FF0000"), 
            (Qt.GlobalColor.blue, "#0000FF"),
            (Qt.GlobalColor.yellow, "#FFFF00"), 
            (Qt.GlobalColor.cyan, "#00FFFF"),
            (Qt.GlobalColor.magenta, "#FF00FF"), 
            (Qt.GlobalColor.gray, "#808080"),
            (Qt.GlobalColor.darkRed, "#8B0000"), 
            (Qt.GlobalColor.darkGreen, "#006400"),
            (Qt.GlobalColor.darkBlue, "#00008B"), 
            (Qt.GlobalColor.darkYellow, "#B8860B")
        ]

        for i, (color, color_name) in enumerate(colors):
            button_name = self.button_names[i + 1]
            color_button_widget = ColorButtonWidget(i + 1, color_name, button_name=button_name)
            self.color_layout.addWidget(color_button_widget, i // 2, i % 2)
            self.color_buttons.append(color_button_widget)
            self.parcel_field.color_buttons.append(color_button_widget)
            self.color_button_widgets.append(color_button_widget)  # Store the reference
            color_button_widget.button.clicked.connect(lambda _, b=color_button_widget, col=color_name: self.parcel_field.set_current_color(b, col))
            color_button_widget.button_named.connect(lambda button_name=i: self.set_button_names(button_name))

        form_layout.addRow(self.color_layout)
        form_layout.addRow(self.plan_button)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.parcel_field)
        splitter.addWidget(right_panel)
        splitter.setSizes([900, 100])

        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.addWidget(splitter)
        self.setCentralWidget(container)
        self.showMaximized()

        self.width_input.textChanged.connect(self.update_layout)
        self.height_input.textChanged.connect(self.update_layout)
        self.gap_x_input.textChanged.connect(self.update_layout)
        self.gap_y_input.textChanged.connect(self.update_layout)
        self.count_x_input.textChanged.connect(self.update_layout)
        self.count_y_input.textChanged.connect(self.update_layout)

        # # to center (unreasonable)
        # self.parcel_field.update_field(3, 5, 100, 1, 6, 5)
        # self.parcel_field.update_field(3, 5, 0.3, 1, 6, 5)
        self.restore_state()

    def resizeEvent(self, event):
        self.update_layout()
        super().resizeEvent(event)

    def create_toolbar(self):
        """Create and add the toolbar to the main window."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Add an action with an icon
        open_action = QAction(QIcon("open.png"), "Open", self)
        open_action.setStatusTip("Open a file")
        open_action.triggered.connect(self.open_file)  # Connect to a custom function
        toolbar.addAction(open_action)

        # Add a separator to the toolbar
        toolbar.addSeparator()

        # Add another action, for example, Save
        save_action = QAction(QIcon("save.png"), "Save", self)
        save_action.setStatusTip("Save your work")
        save_action.triggered.connect(self.save_file)  # Connect to a custom function
        toolbar.addAction(save_action)

        # Add a Quit action
        # quit_action = QAction(QIcon("quit.png"), "Quit", self)
        # quit_action.setStatusTip("Quit the application")
        # quit_action.triggered.connect(self.confirm_quit)  # Connect to the quit confirmation dialog
        # toolbar.addAction(quit_action)

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

    def open_file(self):
        logger.debug("Open file action triggered")

        # Create a file dialog for selecting the file to open
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open Text File")
        file_dialog.setNameFilter("Text Files (*.txt)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)  # Only allow selecting existing files

        if file_dialog.exec():  # If a file is selected
            file_path = file_dialog.selectedFiles()[0]
            logger.info(f"File selected: {file_path}")

            # Open the file and parse the JSON data
            try:
                with open(file_path, 'r') as file:
                    loaded_data = json.load(file)  # Parse the JSON data
                    logger.info(f"Loaded data: {loaded_data}")
                    
                    # Call a method to restore the state using the loaded data
                    self.restore_app_state(loaded_data)
            except Exception as e:
                logger.error(f"Error opening or parsing file: {e}")
                self.show_warning("Open Failed", f"Failed to open app state: {e}")

    def restore_app_state(self, data):
        logger.debug(f"Restoring app state with data: {data}")

        try:

            # Block signals temporarily to avoid triggering updates too early
            self.width_input.blockSignals(True)
            self.height_input.blockSignals(True)
            self.gap_x_input.blockSignals(True)
            self.gap_y_input.blockSignals(True)
            self.count_x_input.blockSignals(True)
            self.count_y_input.blockSignals(True)

            # Restore the parameters from the loaded data
            self.button_names = {int(k): v for k, v in data['button_names'].items()}
            self.width = data['width']
            self.height = data['height']
            self.gap_x = data['gap_x']
            self.gap_y = data['gap_y']
            self.count_x = data['count_x']
            self.count_y = data['count_y']
            app_state.location = data["location"]
            app_state.spraying_width = data["spraying_width"]
            app_state.fit = data["fit"]
            app_state.button_params = data["params"]
            app_state.acc_buffer = data["acc_buffer"]


            # Update the UI with restored values
            self.width_input.setText(str(self.width))
            self.height_input.setText(str(self.height))
            self.gap_x_input.setText(str(self.gap_x))
            self.gap_y_input.setText(str(self.gap_y))
            self.count_x_input.setText(str(self.count_x))
            self.count_y_input.setText(str(self.count_y))

            logger.debug(f"Restored UI fields: {self.width}, {self.height}, {self.gap_x}, {self.gap_y}, {self.count_x}, {self.count_y}")

            # Unblock signals after all fields have been updated
            self.width_input.blockSignals(False)
            self.height_input.blockSignals(False)
            self.gap_x_input.blockSignals(False)
            self.gap_y_input.blockSignals(False)
            self.count_x_input.blockSignals(False)
            self.count_y_input.blockSignals(False)

            # Update the parcel field layout before restoring colors
            self.parcel_field.update_field(self.width, self.height, self.gap_x, self.gap_y, self.count_x, self.count_y, structure_changed=True)

            # Restore the parcels
            self.parcel_field.fill_non_clicked_parcels()
            self.parcel_field.restore_parcels_with_colors(data['colored_parcels'])
            # Update the button names on the UI
            for i, (button_number, button_name) in enumerate(self.button_names.items()):
                self.color_button_widgets[i].text_background_label.setText(button_name)
                self.color_button_widgets[i].button_names = self.button_names
                self.color_button_widgets[i].button_name = button_name

            logger.info("App state restored successfully.")
            self.show_info("Restore Successful", "Planner state has been restored successfully.")
            self.file_opened = True
        except Exception as e:
            logger.error(f"Error restoring app state: {e}")
            self.show_warning("Restore Failed", f"Failed to restore app state: {e}")
            


    def save_file(self):
        logger.debug("Save file action triggered")
        self.colored_parcels = self.parcel_field.get_colored_parcels()
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
        # Create a save file dialog
        options = QFileDialog.Option.DontUseNativeDialog
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Save File")
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("Text Files (*.txt)")
        file_dialog.setDefaultSuffix("txt")  # Default file extension

        # Generate a default filename based on the current timestamp
        default_file_name = f"app_state_{time.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        file_dialog.selectFile(default_file_name)  # Automatically fill in the file name

        # If the user selects a file and clicks save
        if file_dialog.exec():
            save_path = file_dialog.selectedFiles()[0]  # Get the file path
            logger.info(f"Saving file to: {save_path}")

            # Collect the application state
            app_state_data = {
                'button_names': self.button_names,
                'width': self.width,
                'height': self.height,
                'gap_x': self.gap_x,
                'gap_y': self.gap_y,
                'count_x': self.count_x,
                'count_y': self.count_y,
                'colored_parcels': self.parcel_field.get_colored_parcels(),
                "location": app_state.location,
                "spraying_width": app_state.spraying_width,
                "fit": app_state.fit,
                'parcel_coordinates': app_state.parcel_coordinates,
                'paths_by_color': app_state.paths_by_color,
                'params': app_state.button_params,
                'acc_buffer': app_state.acc_buffer
            }

            try:
                # Save the app state data to the chosen file in JSON format
                with open(save_path, 'w') as save_file:
                    json.dump(app_state_data, save_file, indent=4)
                logger.info(f"Application state successfully saved to {save_path}")
                self.show_info("Save Successful", "App state has been saved successfully.")
            except Exception as e:
                logger.error(f"Failed to save file: {e}")
                self.show_warning("Save Failed", f"Failed to save app state: {e}")

    def show_info(self, title, content):
            logger.debug(f"showing info with the value of: {title, content}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)  # Set the icon to Information
            msg.setText(title)
            msg.setInformativeText(content)
            msg.setWindowTitle("Information")  # Set the title to "Information"
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)  # Only show the OK button
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)  # Set OK as the default button
            ret = msg.exec()

            if ret == QMessageBox.StandardButton.Ok:
                print("User clicked OK")

    def show_warning(self, title, content):
            logger.debug(f"showing warning with the value of: {title, content}")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(title)
            msg.setInformativeText(content)
            msg.setWindowTitle("Warning")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            ret = msg.exec()
            
            if ret == QMessageBox.StandardButton.Ok:
                print("User clicked OK")
            else:
                print("User clicked Cancel or closed the dialog")

    def update_layout(self):
        logger.debug("layout updating")
        valid_inputs = True
        structure_changed = False

        try:
            new_width = float(self.width_input.text())
            self.width = new_width  # Update only if the conversion is successful
        except ValueError:
            if self.width_input.text() != "":
                logger.error(f"Invalid input for width: {self.width_input.text()}")
                self.show_warning("Invalid Input", f"Invalid input for width: {self.width_input.text()}")
                self.width_input.setText(str(self.width))  # Revert to last valid input
            valid_inputs = False

        try:
            new_height = float(self.height_input.text())
            self.height = new_height
        except ValueError:
            if self.height_input.text() != "":
                logger.error(f"Invalid input for height: {self.height_input.text()}")
                self.show_warning("Invalid Input", f"Invalid input for height: {self.height_input.text()}")
                self.height_input.setText(str(self.height))
            valid_inputs = False

        try:
            new_gap_x = float(self.gap_x_input.text())
            self.gap_x = new_gap_x
        except ValueError:
            if self.gap_x_input.text() != "":
                logger.error(f"Invalid input for gap X: {self.gap_x_input.text()}")
                self.show_warning("Invalid Input", f"Invalid input for gap X: {self.gap_x_input.text()}")
                self.gap_x_input.setText(str(self.gap_x))
            valid_inputs = False

        try:
            new_gap_y = float(self.gap_y_input.text())
            self.gap_y = new_gap_y
        except ValueError:
            if self.gap_y_input.text() != "":
                logger.error(f"Invalid input for gap Y: {self.gap_y_input.text()}")
                self.show_warning("Invalid Input", f"Invalid input for gap Y: {self.gap_y_input.text()}")
                self.gap_y_input.setText(str(self.gap_y))
            valid_inputs = False

        try:
            new_count_x = int(self.count_x_input.text())
            if self.prev_count_x is not None and new_count_x != self.prev_count_x:
                structure_changed = True
            self.prev_count_x = new_count_x
            self.count_x = new_count_x
            if int(self.count_x_input.text()) > 20:
                self.count_x = 20
            elif int(self.count_x_input.text()) == 0:
                self.count_x = 1
        except ValueError:
            if self.count_x_input.text() != "":
                logger.error(f"Invalid input for count X: {self.count_x_input.text()}")
                self.show_warning("Invalid Input", f"Invalid input for count X: {self.count_x_input.text()}")
                self.count_x_input.setText(str(self.count_x))
            valid_inputs = False

        try:
            new_count_y = int(self.count_y_input.text())
            if self.prev_count_y is not None and new_count_y != self.prev_count_y:
                structure_changed = True
            self.prev_count_y = new_count_y
            self.count_y = new_count_y
            if int(self.count_y_input.text()) > 10:
                self.count_y = 10
            elif int(self.count_y_input.text()) == 0:
                self.count_y = 1
        except ValueError:
            if self.count_y_input.text() != "":
                logger.error(f"Invalid input for count Y: {self.count_y_input.text()}")
                self.show_warning("Invalid Input", f"Invalid input for count Y: {self.count_y_input.text()}")
                self.count_y_input.setText(str(self.count_y))
            valid_inputs = False

        # Only update the field if all inputs are valid
        if valid_inputs:
            self.parcel_field.update_field(self.width, self.height, self.gap_x, self.gap_y, self.count_x, self.count_y, structure_changed)
            
            self.update_color_buttons(self.count_y)

    def update_color_buttons(self, count_y):
        """
        Dynamically update the number of color buttons based on count_y value.
        """
        logger.debug(f"Updating color buttons to match count_y={count_y}")

        # Remove all current color buttons from the layout
        for i in reversed(range(self.color_layout.count())):
            widget = self.color_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)

        # Now, create new buttons according to the count_y value
        for i in range(count_y):
            button_color = self.color_button_widgets[i].color_name
            button_widget = self.color_button_widgets[i]
            self.color_layout.addWidget(button_widget, i // 2, i % 2)

        # Re-layout the color button grid
        self.color_layout.update()


    def show_warning(self, title, content):
        logger.debug(f"showing warning with the value of: {title, content}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(title)
        msg.setInformativeText(content)
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        ret = msg.exec()
        
        if ret == QMessageBox.StandardButton.Ok:
            print("User clicked OK")

    def clear_parcels(self):
        logger.debug("clearing parcels")
        self.parcel_field.reset_parcels()
        self.parcel_field.parcel_colors.clear()

    def set_button_names(self, button_names):
        logger.debug("setting button name")
        self.button_names = button_names

    def initialize_params(self, app_state):
        logger.debug(f"initializing with the params: {app_state}")
        self.width = app_state.width
        self.height = app_state.height
        self.gap_x = app_state.gap_x
        self.gap_y = app_state.gap_y
        self.count_x = app_state.count_x
        self.count_y = app_state.count_y
        self.button_names = app_state.button_names
        for i, (button_number, button_name) in enumerate(self.button_names.items()):
            self.color_button_widgets[i].text_background_label.setText(button_name)
            self.color_button_widgets[i].button_names = self.button_names
            self.color_button_widgets[i].button_name = button_name
        self.colored_parcels = app_state.colored_parcels
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
        app_state.location = app_state.location
        app_state.spraying_width = app_state.spraying_width
        app_state.fit = app_state.fit
        self.file_opened = app_state.file_opened
        app_state.button_params = app_state.button_params
        app_state.acc_buffer = app_state.acc_buffer
        self.parcel_field.update_field(self.width, self.height, self.gap_x, self.gap_y, self.count_x, self.count_y)
        self.restore_state()
        
    def planning(self):
        logger.debug(f"changing page to planning")
        # Before moving to the planning window, check if all colors are used
        # Fill non-clicked parcels with white before switching to the planning window
        self.parcel_field.fill_non_clicked_parcels()
        if self.parcel_field.check_all_colors_used():
            # Proceed to the planning window if all colors are used or user chose to skip
            pass
        else:
            # Stay on the current page if user chose to stay
            logger.debug("User chose to stay on the current page.")
            return

        # Save the state before opening the second window
        self.colored_parcels = self.parcel_field.get_colored_parcels()
        sorted_parcels = sorted(self.colored_parcels.items(), key=lambda item: item[0])
        sorted_parcel_dict = {item[0]: item[1][0] for item in sorted_parcels}

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
        # Initialize second window with saved state
        self.second_window.initialize_with_parcels(sorted_parcel_dict)
        self.second_window.initialize_params(app_state)

        main_window_geometry = self.geometry()
        self.second_window.setGeometry(main_window_geometry)

        self.second_window.window(self)

        # Switch to the second window
        self.second_window.show()
        self.hide()

    def restore_state(self):
        logger.debug(f"restoring state")
        # Restore the button names and layout parameters
        self.button_names = app_state.button_names
        self.width_input.setText(str(app_state.width))
        self.height_input.setText(str(app_state.height))
        self.gap_x_input.setText(str(app_state.gap_x))
        self.gap_y_input.setText(str(app_state.gap_y))
        self.count_x_input.setText(str(app_state.count_x))
        self.count_y_input.setText(str(app_state.count_y))
        self.parcel_field.update_field(app_state.width, app_state.height, app_state.gap_x, app_state.gap_y, app_state.count_x, app_state.count_y, structure_changed=True)

        # Restore the parcel colors and positions
        self.parcel_field.restore_parcels_with_colors(app_state.colored_parcels)

    def closeEvent(self, event):
        """Override the closeEvent to show the confirmation dialog when clicking the window close button."""
        user_choice = self.confirm_quit()

        # Handle the user's choice
        if user_choice == "save_and_quit":
            self.map_widget.save_map_coordinates()  # Save the map coordinates
            self.save_config()
            event.accept()  # Close the window
        elif user_choice == "quit_without_saving":
            self.second_window.map_widget.save_map_coordinates()
            self.second_window.save_config()
            event.accept()  # Close the window without saving
        else:
            event.ignore()  # Cancel the close event

if __name__ == "__main__":
    logger.info("Starting parcel_main")
    hide_console()
    app = QApplication(sys.argv)
    icon_path = "C:\\Users\\Getac\\Documents\\Omer Mersin\\codes\\parcel_planner\\DRONETOOLS.ico"
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    # Ensure single instance
    semaphore = QSystemSemaphore('MyUniqueAppSemaphore', 1)
    semaphore.acquire()
    
    shared_memory = QSharedMemory('MyUniqueAppSharedMemory')
    if not shared_memory.create(1):
        print("Another instance is already running.")
        sys.exit(app.exec())
    
    window = MainWindow()
    window.show()

    sys.exit(app.exec())