import sys
import os
import numpy as np
import random
import colorsys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout, 
                             QHBoxLayout, QWidget, QPushButton, QSlider, QLabel,
                             QLineEdit, QComboBox, QFileDialog, QFrame, QColorDialog,
                             QButtonGroup, QRadioButton, QGroupBox, QSpacerItem,
                             QSizePolicy, QProgressDialog, QMessageBox, QCheckBox, QMenu)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, pyqtSignal, QSize, QThread
import time
import json
# from search_color import search
# from add_color import add
from accessDBs import add_color, search_color, add_visual, search_visual, search_clip
from colors import get_dominant_colors

import PIL
from PIL import Image
# from PIL.ImageQt import ImageQt # only works for PyQt6

from tqdm import tqdm

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # smooth rendering and scaling
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.NoDrag)
        # zoom/pan about mouse cursor
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.panning = False
        self.last_pos = QPointF()

        self.scene().setSceneRect(-2000*10, -2000*10, 4000*10, 4000*10)
        self.centerOn(0, 0)

    # start panning
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: # use left button for panning
            self.panning = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    # track mouse position and pan
    def mouseMoveEvent(self, event):
        if self.panning:
            # calculate the difference in scene coordinates
            old_scene_pos = self.mapToScene(self.last_pos)
            new_scene_pos = self.mapToScene(event.pos())
            delta = old_scene_pos - new_scene_pos
            
            # current mouse pos
            self.last_pos = event.pos()
            
            # get current center and adjust it
            current_center = self.mapToScene(self.viewport().rect().center())
            new_center = current_center + delta
            self.centerOn(new_center)
            event.accept()

    # stop panning when mouse released
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()

    # zoom with mouse wheel
    def wheelEvent(self, event):
        zoom_factor = 1.25

        # get scene position under mouse before zooming
        mouse_scene_pos = self.mapToScene(event.pos())

        # apply zoom transformation
        if event.angleDelta().y() > 0: # scroll up (zoom in)
            self.scale(zoom_factor, zoom_factor)
        else: # scroll down (zoom out)
            self.scale(1 / zoom_factor, 1 / zoom_factor)
        
        # get scene position under mouse after zooming
        new_mouse_scene_pos = self.mapToScene(event.pos())
        
        # calculate difference and adjust view
        delta = new_mouse_scene_pos - mouse_scene_pos
        current_center = self.mapToScene(self.viewport().rect().center())
        new_center = current_center - delta
        self.centerOn(new_center)
        
        event.accept()


class ImageGalleryApp(QMainWindow):
    def __init__(self, collection_data, font= "Arial"):
        super().__init__()
        self.font = font
        self.landing_page = None
        self.collection_data = collection_data
        self.current_search_mode = "browse"  # browse, color, clip, dino
        self.setWindowTitle("Image Gallery")
        self.setGeometry(100, 100, 1400, 768)

        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        self.loadonce = False
        self.image_data = {}
        self.STD_SIZE = 512
        self.STD_SPACE = self.STD_SIZE * 1.25
        
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.FPS = 48
        self.animation_time = 0.0

        self.zoom_animation_timer = QTimer()
        self.zoom_animation_timer.timeout.connect(self.update_zoom)
        
        self.zoom_start_time = 0
        self.zoom_duration = 2500
        self.zoom_start_scale = 0.1
        self.zoom_target_rect = QRectF()
        self.zoom_animating = False

        self.selected_color = QColor(0, 0, 0)  # Default white
        self.selected_image_path = ""

        self.scene.contextMenuEvent = self.sceneContextMenuEvent

        self.setupUI()

    def sceneContextMenuEvent(self, event):
        """Handle right-click context menu in scene"""
        # Get item under cursor
        item = self.scene.itemAt(event.scenePos(), self.view.transform())
        if isinstance(item, QGraphicsPixmapItem) and self.image_data[item]["path"]:
            # Find the image path for this item
            # for data_item, data in self.image_data.items():
            #     if data_item == item:
                    path = self.image_data[item]["path"]
                    # Create context menu
                    menu = QMenu()
                    open_file = menu.addAction("Open Image")
                    open_location = menu.addAction("Show in Folder")
                    
                    # Show menu and get selected action
                    action = menu.exec_(event.screenPos())
                    
                    if action == open_file:
                        self.openImage(path)
                    elif action == open_location:
                        self.showInFolder(path)

    def openImage(self, path):
        """Open image with default system viewer"""
        if path:
            import subprocess
            import os
            if os.name == 'nt':  # Windows
                os.startfile(path)
            else:  # macOS and Linux
                subprocess.call(('xdg-open', path))

    def showInFolder(self, path):
        """Show image in its folder"""
        if path:
            import subprocess
            import os
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', '/select,', os.path.normpath(path)])
            elif os.name == 'darwin':  # macOS
                subprocess.run(['open', '-R', path])
            else:  # Linux
                subprocess.run(['xdg-open', os.path.dirname(path)])
    def returnToHome(self):
        if self.landing_page:
            self.landing_page.show()
        self.close()

    # def setupUI(self):
    #     main_widget = QWidget()
    #     main_layout = QHBoxLayout(main_widget)
        
    #     # graphics view (left side)
    #     main_layout.addWidget(self.view, 3)  # Give more space to the view
        
    #     # Control panel (right side)
    #     control_panel = self.createControlPanel()
    #     main_layout.addWidget(control_panel, 1)  # Smaller space for controls
        
    #     self.setCentralWidget(main_widget)
    def setupUI(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Create view container
        view_container = QWidget()
        view_layout = QVBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add view to container
        view_layout.addWidget(self.view)
        
        # Create and style toggle button
        self.toggle_panel_button = QPushButton(">")
        self.toggle_panel_button.setFont(QFont(self.font, 12))
        self.toggle_panel_button.setFixedSize(24, 24)
        self.toggle_panel_button.clicked.connect(self.toggleControlPanel)
        self.toggle_panel_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(240, 240, 240, 180);
                border: 2px solid #616161;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: rgba(224, 224, 224, 220);
            }
        """)
        
        # Create a parent widget for the button and set its layout
        button_widget = QWidget(self.view)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(10, 10, 10, 10)
        button_layout.addWidget(self.toggle_panel_button)
        button_layout.addStretch()
        
        # Position the button widget in the top-right corner
        button_widget.setGeometry(self.view.width() - 44, 0, 44, 44)
        
        # Make button widget stay in top-right corner when view is resized
        self.view.resizeEvent = lambda e: button_widget.setGeometry(
            self.view.width() - 44, 0, 44, 44
        )
        
        # Add view container and control panel to main layout
        main_layout.addWidget(view_container, 3)

        # Control panel (right side)
        self.control_panel = self.createControlPanel()
        main_layout.addWidget(self.control_panel, 1)
        
        self.setCentralWidget(main_widget)

    def toggleControlPanel(self):
        if self.control_panel.isVisible():
            self.control_panel.hide()
            self.toggle_panel_button.setText("<")  # Left arrow to show
        else:
            self.control_panel.show()
            self.toggle_panel_button.setText(">")  # Right arrow to hide

    def createControlPanel(self):
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.StyledPanel)
        control_frame.setMinimumWidth(300)
        control_frame.setMaximumWidth(350)
        
        layout = QVBoxLayout(control_frame)

        home_button_layout = QHBoxLayout()
        home_button_layout.addStretch(3)  # Push button to right

        self.home_button = QPushButton("Back to Home")
        self.home_button.setFont(QFont(self.font, 15))
        
        self.home_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.home_button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: black;
                border: 2px solid #616161;
                padding: 8px;
                font-size: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d6d6d6;
            }
        """)

        self.home_button.clicked.connect(self.returnToHome)
        home_button_layout.addWidget(self.home_button)
        layout.addLayout(home_button_layout)

        title = QLabel("Gallery Controls")
        title.setFont(QFont(self.font, 16, QFont.Bold))
        title.setStyleSheet("margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout_group = QGroupBox("Layout Type")
        layout_group.setFont(QFont(self.font, 11))
        layout_group_layout = QVBoxLayout(layout_group)
        
        self.layout_buttons = QButtonGroup()
        self.circles_radio = QRadioButton("Circles")
        self.circles_radio.setFont(QFont(self.font, 11))
        self.circlesh_radio = QRadioButton("Circles by Hue")
        self.circlesh_radio.setFont(QFont(self.font, 11))
        self.hexagons_radio = QRadioButton("Hexagons")
        self.hexagons_radio.setFont(QFont(self.font, 11))
        
        self.circles_radio.setChecked(True)  # default
        
        self.layout_buttons.addButton(self.circles_radio, 0)
        self.layout_buttons.addButton(self.circlesh_radio, 1)
        self.layout_buttons.addButton(self.hexagons_radio, 2)
        
        layout_group_layout.addWidget(self.circles_radio)
        layout_group_layout.addWidget(self.circlesh_radio)
        layout_group_layout.addWidget(self.hexagons_radio)
        
        layout.addWidget(layout_group)
        
        image_count_label = QLabel("Number of Images:")
        image_count_label.setFont(QFont(self.font, 11))
        layout.addWidget(image_count_label)
        self.image_count_slider = QSlider(Qt.Horizontal)
        self.image_count_slider.setMinimum(2)
        self.image_count_slider.setMaximum(self.collection_data["image_count"])
        self.image_count_slider.setValue(max(2, int(self.collection_data["image_count"] * 0.5)))
        self.image_count_slider.valueChanged.connect(self.updateImageCountLabel)
        
        self.image_count_label = QLabel(str(max(2, int(self.collection_data["image_count"] * 0.5))))
        self.image_count_label.setFont(QFont(self.font, 11))
        self.image_count_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.image_count_slider)
        layout.addWidget(self.image_count_label)
        
        size_container = QWidget()
        size_layout = QHBoxLayout(size_container)
        size_layout.setContentsMargins(0, 0, 0, 0)

        size_label = QLabel("Image Size:")
        size_label.setFont(QFont(self.font, 11))
        size_layout.addWidget(size_label)

        self.size_input = QLineEdit()
        self.size_input.setFont(QFont(self.font, 11))
        self.size_input.setText(str(self.STD_SIZE))
        self.size_input.setFixedWidth(70)
        self.size_input.setAlignment(Qt.AlignRight)
        # self.size_input.textChanged.connect(self.onSizeChanged)
        size_layout.addWidget(self.size_input)

        size_layout.addWidget(QLabel("px"))  # Add px label
        layout.addWidget(size_container)

        self.loadonce_checkbox = QCheckBox("Load all images at once")
        self.loadonce_checkbox.setFont(QFont(self.font, 11))
        self.loadonce_checkbox.toggled.connect(self.onLoadModeChanged)
        layout.addWidget(self.loadonce_checkbox)
        
            
        # # Create container for load/size options
        # options_container = QWidget()
        # options_layout = QHBoxLayout(options_container)
        # options_layout.setContentsMargins(0, 0, 0, 0)
        # # Add checkbox to left side
        # self.loadonce_checkbox = QCheckBox("Load all at once")
        # self.loadonce_checkbox.setFont(QFont(self.font, 11))
        # self.loadonce_checkbox.toggled.connect(self.onLoadModeChanged)
        # options_layout.addWidget(self.loadonce_checkbox)
        # # Add size input to right side
        # size_container = QWidget()
        # size_layout = QHBoxLayout(size_container)
        # size_layout.setContentsMargins(0, 0, 0, 0)

        # size_label = QLabel("Image Size:")
        # size_label.setFont(QFont(self.font, 11))
        # size_layout.addWidget(size_label)

        # self.size_input = QLineEdit()
        # self.size_input.setFont(QFont(self.font, 11))
        # self.size_input.setText(str(self.STD_SIZE))
        # self.size_input.setFixedWidth(70)
        # self.size_input.setAlignment(Qt.AlignRight)
        # # self.size_input.textChanged.connect(self.onSizeChanged)
        # size_layout.addWidget(self.size_input)
        # pxlabel = QLabel("px")
        # pxlabel.setFont(QFont(self.font, 11))
        # size_layout.addWidget(pxlabel)
        # options_layout.addWidget(size_container)


        # # Add the container to main layout
        # layout.addWidget(options_container)

        # ADD THE SEARCH/LOAD SECTION HERE
        self.search_frame = QFrame()
        self.search_frame.setFrameStyle(QFrame.StyledPanel)
        search_layout = QVBoxLayout(self.search_frame)
        
        # Create index buttons
        self.create_index_widget = QWidget()
        create_index_layout = QVBoxLayout(self.create_index_widget)
        
        if not self.collection_data["clip"]:
            self.create_clip_btn = QPushButton("Create CLIP Index")
            self.create_clip_btn.setFont(QFont(self.font, 11))
            self.create_clip_btn.clicked.connect(lambda: self.createIndex("clip"))
            search_layout.addWidget(self.create_clip_btn)
        if not self.collection_data["dino"]:
            self.create_dino_btn = QPushButton("Create DINO Index")
            self.create_dino_btn.setFont(QFont(self.font, 11))
            self.create_dino_btn.clicked.connect(lambda: self.createIndex("dino"))
            create_index_layout.addWidget(self.create_dino_btn)
            search_layout.addWidget(self.create_index_widget)
        
        if not (self.collection_data["clip"] and self.collection_data["dino"]):
            # ADD THE SEARCH FRAME TO THE MAIN LAYOUT
            layout.addWidget(self.search_frame)

        # Search type selection
        search_group = QGroupBox("Search Type")
        search_group.setFont(QFont(self.font, 12))
        search_group_layout = QVBoxLayout(search_group)
        
        # Modify the search type combo box population
        self.search_type_combo = QComboBox()
        self.search_type_combo.setFont(QFont(self.font, 11))
        search_types = ["Color Search"]  # Color search always available

        # Add CLIP text search if supported
        if self.collection_data.get("clip", False):
            search_types.append("Text Search (CLIP)")
            search_types.append("Image Content Search (CLIP)")

        # Add Visual Similarity if DINO supported  
        if self.collection_data.get("dino", False):
            search_types.append("Image Similarity Search (DINO)")

        self.search_type_combo.addItems(search_types)
        self.search_type_combo.currentTextChanged.connect(self.onSearchTypeChanged)
        
        search_group_layout.addWidget(self.search_type_combo)
        layout.addWidget(search_group)
        
        # Dynamic search controls container
        self.search_controls_frame = QFrame()
        self.search_controls_layout = QVBoxLayout(self.search_controls_frame)
        layout.addWidget(self.search_controls_frame)
        
        # Initialize with color search controls
        self.setupColorSearchControls()

        
        # Generate button
        self.generate_button = QPushButton("Generate Gallery")
        self.generate_button.setFont(QFont(self.font, 14))
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #e0ffe0;
                color: #3d8b40;
                border: 2px solid #79b879;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #79b879;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.generate_button.clicked.connect(self.generateGallery)
        layout.addWidget(self.generate_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear Gallery")
        self.clear_button.setFont(QFont(self.font, 14))
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #ffe0e0;
                color: #872222;
                border: 2px solid #9c5959;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #9c5959;
            }
            QPushButton:pressed {
                background-color: #872222;
            }
        """)
        self.clear_button.clicked.connect(self.clearGallery)
        layout.addWidget(self.clear_button)
        
        # Add spacer to push everything to top
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)
        
        return control_frame
    
    # def onSizeChanged(self, text):
    #     """Handle image size input changes"""
    #     try:
    #         size = int(text)
    #         # if 64 <= size <= 2048:  # Reasonable size limits
                
    #             # # Clear gallery if any images are displayed
    #             # if len(self.image_data) > 0:
    #             #     self.clearGallery()
    #         if size > 2048:
    #             self.STD_SIZE = 2048
    #         elif size < 64:
    #             self.STD_SIZE = 64
    #         else:
    #             self.STD_SIZE = size

    #         self.STD_SPACE = self.STD_SIZE * 1.25
    #         self.size_input.setText(str(self.STD_SIZE))
        
    #     except ValueError:
    #         pass  # Invalid input, ignore

    def onRGBInputChanged(self, text):
        try:
            if ',' in text:
                rgb_values = [int(x.strip()) for x in text.split(',')]
                if len(rgb_values) == 3 and all(0 <= val <= 255 for val in rgb_values):
                    r, g, b = rgb_values
                    self.selected_color = QColor(r, g, b)
                    self.color_button.setStyleSheet(f"background-color: {self.selected_color.name()}; border: 2px solid #666;")
        except ValueError:
            pass  # Invalid input, ignore

    def selectColorImage(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Reference Image for Color Search", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if file_path:
            self.selected_color_image_path = file_path
            filename = os.path.basename(file_path)
            self.color_image_path_label.setText(f"Selected: {filename}")
    def clearSearchControls(self):
        # Remove all widgets from search controls layout
        while self.search_controls_layout.count():
            child = self.search_controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def setupColorSearchControls(self):
        self.clearSearchControls()
        
        # Color search mode selection
        mode_label = QLabel("Search by:")
        mode_label.setFont(QFont(self.font, 11))
        self.search_controls_layout.addWidget(mode_label)
        
        self.color_search_mode = QComboBox()
        self.color_search_mode.setFont(QFont(self.font, 11))
        self.color_search_mode.addItems(["RGB Color Picker", "Reference Image"])
        self.color_search_mode.currentTextChanged.connect(self.onColorSearchModeChanged)
        self.search_controls_layout.addWidget(self.color_search_mode)
        
        # Container for dynamic controls
        self.color_controls_container = QWidget()
        self.color_controls_layout = QVBoxLayout(self.color_controls_container)
        self.search_controls_layout.addWidget(self.color_controls_container)
        
        # Initialize with color picker mode
        self.setupColorPickerControls()

    def setupColorImageControls(self):
        # Image selector
        image_label = QLabel("Reference Image:")
        image_label.setFont(QFont(self.font, 11))
        self.color_controls_layout.addWidget(image_label)
        
        self.color_image_path_label = QLabel("No image selected")
        self.color_image_path_label.setFont(QFont(self.font, 10))
        self.color_image_path_label.setWordWrap(True)
        self.color_image_path_label.setStyleSheet("border: 2px solid #ccc; padding: 5px; background-color: #ffffff;")
        self.color_controls_layout.addWidget(self.color_image_path_label)
        
        self.select_color_image_button = QPushButton("Select Image")
        self.select_color_image_button.setFont(QFont(self.font, 11))
        self.select_color_image_button.clicked.connect(self.selectColorImage)
        self.color_controls_layout.addWidget(self.select_color_image_button)
    def setupColorPickerControls(self):
        # Color picker button
        color_label = QLabel("Select Color:")
        color_label.setFont(QFont(self.font, 11))
        self.color_controls_layout.addWidget(color_label)
        
        self.color_button = QPushButton()
        self.color_button.setFixedHeight(40)
        self.color_button.setStyleSheet(f"background-color: {self.selected_color.name()}; border: 2px solid #666;")
        self.color_button.clicked.connect(self.selectColor)
        self.color_controls_layout.addWidget(self.color_button)
        
        # # Optional: RGB input field for manual entry
        # rgb_label = QLabel("Or enter RGB values:")
        # self.color_controls_layout.addWidget(rgb_label)
        
        # self.rgb_input = QLineEdit()
        # self.rgb_input.setPlaceholderText("R,G,B (e.g., 255,128,0)")
        # self.rgb_input.textChanged.connect(self.onRGBInputChanged)
        # self.color_controls_layout.addWidget(self.rgb_input)


    def onColorSearchModeChanged(self, mode):
        # Clear existing controls
        while self.color_controls_layout.count():
            child = self.color_controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if mode == "RGB Color Picker":
            self.setupColorPickerControls()
        else:  # Reference Image
            self.setupColorImageControls()

    def setupTextSearchControls(self):
        self.clearSearchControls()
        
        # Text input
        text_label = QLabel("Search Query:")
        text_label.setFont(QFont(self.font, 11))
        self.search_controls_layout.addWidget(text_label)
        
        self.text_input = QLineEdit()
        self.text_input.setFont(QFont(self.font, 11))
        self.text_input.setPlaceholderText("Enter search text...")
        self.search_controls_layout.addWidget(self.text_input)
    
    def setupVisualSimilarityControls(self):
        self.clearSearchControls()
        
        # Image selector
        image_label = QLabel("Reference Image:")
        image_label.setFont(QFont(self.font, 11))
        self.search_controls_layout.addWidget(image_label)
        
        self.image_path_label = QLabel("No image selected")
        self.image_path_label.setFont(QFont(self.font, 11))
        self.image_path_label.setWordWrap(True)
        self.image_path_label.setStyleSheet("border: 2px solid #ccc; padding: 5px; background-color: #ffffff;")
        self.search_controls_layout.addWidget(self.image_path_label)
        
        self.select_image_button = QPushButton("Select Image")
        self.select_image_button.setFont(QFont(self.font, 11))
        self.select_image_button.clicked.connect(self.selectImage)
        self.search_controls_layout.addWidget(self.select_image_button)
    
    def setupImageSearchControls(self):
        # Same as visual similarity for now
        self.setupVisualSimilarityControls()
    
    def onSearchTypeChanged(self, search_type):
        if search_type == "Color Search":
            self.setupColorSearchControls()
        elif search_type == "Text Search (CLIP)":
            self.setupTextSearchControls()
        elif search_type == "Image Similarity Search (DINO)":
            self.setupVisualSimilarityControls()
        elif search_type == "Image Content Search (CLIP)":
            self.setupImageSearchControls()
    
    def selectColor(self):
        color = QColorDialog.getColor(self.selected_color, self, "Select Color")
        if color.isValid():
            self.selected_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}; border: 2px solid #666;")
    
    def selectImage(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Reference Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if file_path:
            self.selected_image_path = file_path
            # Show just the filename for brevity
            filename = os.path.basename(file_path)
            self.image_path_label.setText(f"Selected: {filename}")
    
    def updateImageCountLabel(self, value):
        self.image_count_label.setText(str(value))
    
    def clearGallery(self):
        # Stop animations
        self.animation_timer.stop()
        self.zoom_animation_timer.stop()
        
        # Clear scene
        self.scene.clear()
        self.image_data.clear()
        
        # Reset view
        self.view.resetTransform()
        self.view.centerOn(0, 0)
        
        # Reset animation state
        self.animation_time = 0.0
        self.zoom_animating = False

    def add_index(self, name, directory, explore, by):
        if by == "color":
            add_color(name=name, folder_path=directory, explore=explore)
        else:
            add_visual(name=name, folder_path=directory, explore=explore, model= by)

    def onSearchModeChanged(self, mode):
        """Handle search mode change"""
        self.current_search_mode = mode.lower().replace(" search", "")
        self.setupSearchInput()

    def onLoadModeChanged(self, checked):
        """Handle load mode change"""
        self.loadonce = checked

    def setupSearchInput(self):
        """Setup search input based on current mode"""
        # Clear existing input widgets
        for i in reversed(range(self.search_input_layout.count())):
            self.search_input_layout.itemAt(i).widget().setParent(None)
        
        if self.current_search_mode == "browse":
            return
        
        if self.current_search_mode == "color":
            # Color search input
            self.search_input_layout.addWidget(QLabel("Search by:"))
            
            color_mode_combo = QComboBox()
            color_mode_combo.addItems(["RGB Color", "Query Image"])
            self.search_input_layout.addWidget(color_mode_combo)
            
            # RGB input
            self.rgb_input = QLineEdit()
            self.rgb_input.setPlaceholderText("R,G,B (e.g., 255,0,0)")
            self.search_input_layout.addWidget(self.rgb_input)
            
            # Image selection
            image_select_btn = QPushButton("Select Query Image")
            image_select_btn.clicked.connect(self.selectQueryImage)
            self.search_input_layout.addWidget(image_select_btn)
            
        elif self.current_search_mode == "clip":
            # CLIP search input
            self.search_input_layout.addWidget(QLabel("Search by:"))
            
            clip_mode_combo = QComboBox()
            clip_mode_combo.addItems(["Text Query", "Query Image"])
            self.search_input_layout.addWidget(clip_mode_combo)
            
            # Text input
            self.text_input = QLineEdit()
            self.text_input.setPlaceholderText("Enter text description...")
            self.search_input_layout.addWidget(self.text_input)
            
            # Image selection
            image_select_btn = QPushButton("Select Query Image") 
            image_select_btn.clicked.connect(self.selectQueryImage)
            self.search_input_layout.addWidget(image_select_btn)
            
        elif self.current_search_mode == "dino":
            # DINO search input
            self.search_input_layout.addWidget(QLabel("Query Image:"))
            image_select_btn = QPushButton("Select Query Image")
            image_select_btn.clicked.connect(self.selectQueryImage)
            self.search_input_layout.addWidget(image_select_btn)
        
        # Search button
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.performSearch)
        self.search_input_layout.addWidget(search_btn)

    def selectQueryImage(self):
        """Select query image for similarity search"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Query Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if file_path:
            self.query_image_path = file_path
            # Show selected image path
            if hasattr(self, 'query_image_label'):
                self.query_image_label.setText(f"Selected: {os.path.basename(file_path)}")

    def createIndex(self, index_type):
        """Create similarity search index"""
        if not self.collection_data:
            return
            
        from accessDBs import add_visual
        from PyQt5.QtCore import QThread, pyqtSignal
        
        class IndexCreationWorker(QThread):
            progress = pyqtSignal(str)
            finished = pyqtSignal()
            error = pyqtSignal(str)
            
            def __init__(self, name, folder, explore, index_type):
                super().__init__()
                self.name = name
                self.folder = folder 
                self.explore = explore
                self.index_type = index_type
                
            def run(self):
                try:
                    self.progress.emit(f"Creating {self.index_type.upper()} index...")
                    add_visual(self.name, self.folder, self.explore, model=self.index_type)
                    self.finished.emit()
                except Exception as e:
                    self.error.emit(str(e))
        
        # Show progress dialog
        progress_dialog = QProgressDialog(f"Creating {index_type.upper()} index...", "Cancel", 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # Start worker
        self.index_worker = IndexCreationWorker(
            self.collection_data['name'],
            self.collection_data['folder'], 
            self.collection_data['subfolders'],
            index_type
        )
        
        def on_finished():
            progress_dialog.close()
            # self.updateSearchModeOptions()
            self.collection_data[index_type] = True
            QMessageBox.information(self, "Success", f"{index_type.upper()} index created successfully!")

            collections = []
            with open("collections.json", 'r') as f:
                collections = json.load(f)
                for i, c in enumerate(collections):
                    if c["name"] == self.collection_data["name"]:
                        collections[i][index_type] = self.collection_data[index_type]
            
            with open("collections.json", 'w') as f:
                json.dump(collections, f, indent=2)

            self.updateUIAfterIndexCreation()
            
        def on_error(error_msg):
            progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to create index: {error_msg}")
        
        self.index_worker.finished.connect(on_finished)
        self.index_worker.error.connect(on_error)
        self.index_worker.start()


    def updateUIAfterIndexCreation(self):
        """Update UI elements after creating a new index"""
        # Clear and recreate search types
        search_types = ["Color Search"]  # Color search always available
        
        if self.collection_data.get("clip", False):
            search_types.append("Text Search (CLIP)")
            search_types.append("Image Content Search (CLIP)")
            
            # Remove CLIP index creation button if it exists
            if hasattr(self, 'create_clip_btn') and self.create_clip_btn:
                self.create_clip_btn.setParent(None)
                self.create_clip_btn.deleteLater()
                self.create_clip_btn = None
        
        if self.collection_data.get("dino", False):
            search_types.append("Image Similarity Search (DINO)")
            
            # Remove DINO index creation button if it exists
            if hasattr(self, 'create_dino_btn') and self.create_dino_btn:
                self.create_dino_btn.setParent(None)
                self.create_dino_btn.deleteLater()
                self.create_dino_btn = None
        
        # Hide or remove the search frame if both indices are created
        if self.collection_data.get("clip", False) and self.collection_data.get("dino", False):
            if hasattr(self, 'search_frame'):
                self.search_frame.hide()  # or use .deleteLater() to remove it completely
        
        # Update search type combo box
        current_search_type = self.search_type_combo.currentText()
        self.search_type_combo.clear()
        self.search_type_combo.addItems(search_types)
        
        # Try to restore previous selection if it still exists
        index = self.search_type_combo.findText(current_search_type)
        if index >= 0:
            self.search_type_combo.setCurrentIndex(index)


    def performSearch(self):
        """Perform similarity search based on current mode"""
        if not self.collection_data or self.current_search_mode == "browse":
            return
            
        from accessDBs import search_color, search_clip, search_visual
        
        try:
            results = []
            name = self.collection_data['name']
            
            if self.current_search_mode == "color":
                if hasattr(self, 'query_image_path'):
                    results = search_color(name, path=self.query_image_path)
                elif hasattr(self, 'rgb_input') and self.rgb_input.text():
                    rgb_text = self.rgb_input.text().strip()
                    rgb = tuple(map(int, rgb_text.split(',')))
                    results = search_color(name, rgb=rgb)
                    
            elif self.current_search_mode == "clip":
                if hasattr(self, 'text_input') and self.text_input.text():
                    results = search_clip(name, self.text_input.text())
                elif hasattr(self, 'query_image_path'):
                    # For CLIP image search, you'd need to modify accessDBs.py
                    pass
                    
            elif self.current_search_mode == "dino":
                if hasattr(self, 'query_image_path'):
                    results = search_visual(name, self.query_image_path)
            
            # Display results
            self.displaySearchResults(results)
            
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Search failed: {str(e)}")

    def displaySearchResults(self, results):
        """Display search results in the grid"""
        # Clear current grid
        self.clearImageGrid()
        
        # Load results based on loadonce setting
        if self.loadonce:
            # Load all at once
            for result in results:
                self.addImageToGrid(result['path'])
        else:
            # Load sequentially with delay
            self.search_results = results
            self.current_result_index = 0
            self.loadNextSearchResult()

    def loadNextSearchResult(self):
        """Load next search result sequentially"""
        if hasattr(self, 'search_results') and self.current_result_index < len(self.search_results):
            result = self.search_results[self.current_result_index]
            self.addImageToGrid(result['path'])
            self.current_result_index += 1
            
            # Schedule next load
            QTimer.singleShot(100, self.loadNextSearchResult)

    def generateGallery(self):
        # Clear existing gallery first
        self.clearGallery()
        
        # Get parameters from UI
        num_images = self.image_count_slider.value()
        database = self.collection_data["name"]
        search_type = self.search_type_combo.currentText()
        layout_type = self.layout_buttons.checkedId()
        image_size = self.size_input.text()

        try:
            image_size = int(image_size)
            # if 64 <= size <= 2048:  # Reasonable size limits
                
                # # Clear gallery if any images are displayed
                # if len(self.image_data) > 0:
                #     self.clearGallery()
            if image_size > 2048:
                self.STD_SIZE = 2048
            elif image_size < 64:
                self.STD_SIZE = 64
            else:
                self.STD_SIZE = image_size

            self.STD_SPACE = self.STD_SIZE * 1.25
            
        
        except ValueError:
            pass  # Invalid input, ignore

        self.size_input.setText(str(self.STD_SIZE))

        try:
            # Perform search based on type
            images = []
            
            if search_type == "Color Search":
                # Check which mode is being used
                if hasattr(self, 'color_search_mode'):
                    mode = self.color_search_mode.currentText()
                    
                    if mode == "Reference Image":
                        # Use image path for color search
                        if hasattr(self, 'selected_color_image_path') and self.selected_color_image_path:
                            images = search_color(database, path=self.selected_color_image_path, k=num_images)
                        else:
                            QMessageBox.warning(self, "Warning", "Please select a reference image for color search")
                            return
                    else:  # RGB Color Picker mode
                        # Use RGB values from color picker or manual input
                        if hasattr(self, 'rgb_input') and self.rgb_input.text().strip():
                            # Use manual RGB input if available
                            try:
                                rgb_text = self.rgb_input.text().strip()
                                rgb_values = tuple(int(x.strip()) for x in rgb_text.split(','))
                                if len(rgb_values) == 3:
                                    images = search_color(database, rgb=rgb_values, k=num_images)
                                else:
                                    raise ValueError("Invalid RGB format")
                            except ValueError:
                                QMessageBox.warning(self, "Warning", "Please enter valid RGB values (e.g., 255,128,0)")
                                return
                        else:
                            # Use color picker
                            rgb_values = (self.selected_color.red(), self.selected_color.green(), self.selected_color.blue())
                            images = search_color(database, rgb=rgb_values, k=num_images)
                else:
                    # Fallback to old behavior
                    rgb_values = (self.selected_color.red(), self.selected_color.green(), self.selected_color.blue())
                    images = search_color(database, rgb=rgb_values, k=num_images)
                    
            elif search_type == "Text Search (CLIP)":
                if hasattr(self, 'text_input') and self.text_input.text().strip():
                    query = self.text_input.text().strip()
                    images = search_clip(name=database, query=query, k=num_images)
                else:
                    print("No text query entered")
                    return
                    
            elif search_type == "Image Similarity Search (DINO)":
                if hasattr(self, 'selected_image_path') and self.selected_image_path:
                    images = search_visual(name=database, file_path=self.selected_image_path, k=num_images)
                else:
                    print("No reference image selected for visual similarity")
                    return
                    
            elif search_type == "Image Content Search (CLIP)":
                if hasattr(self, 'selected_image_path') and self.selected_image_path:
                    images = search_clip(database, query_image_path=self.selected_image_path, k=num_images)
                else:
                    print("No reference image selected for image search")
                    return
            
            if len(images) == 0:
                print("No images found")
                return
            
            # Apply layout based on selection
            # self.loadonce = False
            
            if layout_type == 0:  # Circles
                self.circles(images)
            elif layout_type == 1:  # Circles by Hue
                self.circlesh(images)
            elif layout_type == 2:  # Hexagons
                self.hexagons(images)
                
        except Exception as e:
            print(f"Error generating gallery: {e}")
    
    def calculate_bounds(self):
        
        min_x = min_y = max_x = max_y = 0
        
        for item in self.image_data.keys():
            rect = item.boundingRect()
            pos = item.pos()
            
            l = pos.x()
            t = pos.y()
            r = pos.x() + rect.width()
            b = pos.y() + rect.height()
            
            min_x = min(min_x, l)
            min_y = min(min_y, t)
            max_x = max(max_x, r)
            max_y = max(max_y, b)
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)


    def start_zoom(self, margin_p=0.1, duration_ms=2500, start_scale=0.1):
        bounds = self.calculate_bounds()
        
        margin_x = bounds.width() * margin_p
        margin_y = bounds.height() * margin_p
        
        self.zoom_target_rect = QRectF(
            bounds.x() - margin_x,
            bounds.y() - margin_y,
            bounds.width() + 2 * margin_x,
            bounds.height() + 2 * margin_y
        )
        
        self.zoom_duration = duration_ms
        self.zoom_start_scale = start_scale
        self.zoom_elapsed = 0
        # self.zoom_animating = self.loadonce
        self.zoom_animating = True
        sw = self.zoom_target_rect.width() * start_scale
        sh = self.zoom_target_rect.height() * start_scale
        start_rect = QRectF(-sw/2,-sh/2,sw,sh)
        
        self.view.fitInView(start_rect, Qt.KeepAspectRatio)
        
        self.zoom_animation_timer.start(int(1000/(self.FPS * 2)))

    def update_zoom(self):
        if not self.zoom_animating:
            return
        
        self.zoom_elapsed += int(1000/(self.FPS * 2))
        
        if self.zoom_elapsed >= self.zoom_duration:
            self.view.fitInView(self.zoom_target_rect, Qt.KeepAspectRatio)
            self.zoom_animation_timer.stop()
            self.zoom_animating = False
            return
        
        t = self.zoom_elapsed / self.zoom_duration
        
        eased_progress = self.ease_out_exp(t)
        
        current_scale = self.zoom_start_scale + (1.0 - self.zoom_start_scale) * eased_progress
        
        current_rect = QRectF(
            self.zoom_target_rect.center().x() - (self.zoom_target_rect.width() * current_scale) / 2,
            self.zoom_target_rect.center().y() - (self.zoom_target_rect.height() * current_scale) / 2,
            self.zoom_target_rect.width() * current_scale,
            self.zoom_target_rect.height() * current_scale
        )
        
        self.view.fitInView(current_rect, Qt.KeepAspectRatio)

    def animate_zoom_delayed(self, delay_ms=100, duration_ms=2500):
        def x():
            if self.loadonce:
                self.start_zoom(duration_ms=duration_ms)
            else:
                return
        
        QTimer.singleShot(delay_ms, x)

    def ease_out_cubic(self, t):
        return 1 - (1 - t)**3 if t != 1 else 1

    def ease_out_exp(self, t):
        return 1 - np.exp(-5 * t) if t != 1 else 1 # for floating point
    

    def generate_dummy_image(self, size, color, text= ""):
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(color)

        painter = QPainter(image)
        painter.setPen(Qt.black) # Text color
        painter.setFont(QFont(self.font, 20))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, text)
        painter.end()

        return QPixmap.fromImage(image)

    def imageToQPixmap(self, image_info):
        if isinstance(image_info, list):
            pixmaps = []
            for image in tqdm(image_info, desc= "Scaling..."):
                pixmaps.append(self.imageToQPixmap(image))
            return pixmaps
        else:
            image = image_info
            pixmap = image.get("pixmap")

            if "image" in image:
                image = image["image"]
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                w, h = image.size
                ar = w/h
                
                if max(h, w) == h:
                    image = image.resize((int(self.STD_SIZE * ar), self.STD_SIZE))
                else:
                    image = image.resize((self.STD_SIZE, int(self.STD_SIZE / ar)))

                w, h = image.size

                data = image.tobytes("raw", "RGB")
                qimage = QImage(data, w, h, w * 3, QImage.Format_RGB888)

                pixmap = QPixmap.fromImage(qimage)
            else:
                if isinstance(image.get("path"), str):
                    pixmap = QPixmap(image["path"])

                h = pixmap.height()
                w = pixmap.width()

                ar = w/h
                if max(h, w) == h:
                    pixmap = pixmap.scaled(int(self.STD_SIZE * ar), self.STD_SIZE,
                                        #    aspectRatioMode = Qt.KeepAspectRatio,
                                        transformMode= Qt.SmoothTransformation
                                        )
                else:
                    pixmap = pixmap.scaled(self.STD_SIZE, int(self.STD_SIZE / ar),
                                        #    aspectRatioMode = Qt.KeepAspectRatio,
                                        transformMode= Qt.SmoothTransformation
                                        )

            return pixmap
    

    def add_to_scene(self, x, y, image, path, h=10, s=255, l=128, r=0, initial_angle=0, direction=0):
        pixmap = None
        # path = None
        
        if isinstance(image, QPixmap):
            pixmap = image
        else:
            pixmap = self.imageToQPixmap(image)
        
        item = QGraphicsPixmapItem(pixmap)
        item.setPos((-pixmap.width() / 2) + x, (-pixmap.height() / 2) + y)
        self.scene.addItem(item)
        
        base_speed = 1000
        w = base_speed * direction / (r + 1)
        self.image_data[item] = {
            'r': r,
            'th_0': initial_angle,
            'w': w,
            'path': path
        }

    def update_animation(self):
        self.animation_time += (int(1000/self.FPS) / 1000) # 60 FPS
        
        for item, data in self.image_data.items():
            # item = data['item']
            r = data['r']
            th_0 = data['th_0']
            w = data['w']
            if w != 0:
                # th = th_0 + w * self.animation_time # rotation with constant w
                th = th_0 + w # reverse to initial position
                
                th = th * (2 * np.pi / 360)
                new_x = r * np.cos(th) * self.STD_SPACE
                new_y = r * np.sin(th) * self.STD_SPACE
                
                # center image on position
                pixmap = item.pixmap()
                item.setPos((-pixmap.width() / 2) + new_x, (-pixmap.height() / 2) + -new_y)
            self.image_data[item]['w'] *= 0.96 # reverse to initial position
    

    def circles(self, images):
        paths = []
        for image in images:
            paths.append(image.get("path"))

        if self.loadonce:
            images = self.imageToQPixmap(images)

        # center image is added within loop
        r = 0
        # ths is the thetas (angles) for each image in a ring
        # defined better at end of loop body
        ths = np.array([0])
        
        for i, image in enumerate(images):
            # "pop" the first element/angle to put image on
            th = ths[0] % 360
            ths = np.delete(ths, 0)

            x = r * np.cos(th / 360 * 2 * np.pi) * self.STD_SPACE
            y = -r * np.sin(th / 360 * 2 * np.pi) * self.STD_SPACE
            self.add_to_scene(x=x, y=y, image=image, path=paths[i], h=th, r=r, initial_angle=th, 
                        direction= (int(r) % 2) * 2 - 1) # alternate rotation every ring
            QApplication.processEvents()
            
            # when the angles in the ring run out, we finished the ring and start on a higher one
            if len(ths) == 0:
                r += 1
                # number of images in ring
                n = (8 * r + (r % 2) - 1 - random.randint(0, r * 2))
                step = 360 / n
                # offset the angle of the first image in ring, so there isn't just a line of images at th = 0
                # offset = step**2 # alternative offset
                # offset = random.randint(0, 359) # alternative offset
                offset = i * 10 # I just the way this offset looks
                ths = np.arange(0 + offset, 360 + offset, step)
                # shuffle if you want expanding rings instead of spiralling rings
                np.random.shuffle(ths)

        self.animate_zoom_delayed(delay_ms=0, duration_ms=2500)
        self.animation_timer.start(int(1000/self.FPS))  # ~60 FPS (16ms intervals)

    def getHue(self, image_info):
        if isinstance(image_info, list):
            hueinfo = []
            for image in tqdm(image_info, desc= "Getting Colors..."):
                hueinfo.append(self.getHue(image))
            return hueinfo
        else:
            image = image_info

            l = []
            if "colors" in image:
                l = image["colors"]
            else:
                l = get_dominant_colors(Image.open(image["path"]).convert('RGB'))

            l = l.reshape(int(len(l)/4), 4)
            tx = 0
            ty = 0
            tf = 0
            for i, rgbf in enumerate(l):
                r, g, b, f = rgbf
                hue = colorsys.rgb_to_hsv(r/255, g/255, b/255)[0]
                tx += np.cos(hue * 2 * np.pi) * f
                ty += np.sin(hue * 2 * np.pi) * f
                tf += f

            avg_hue = np.arctan2(tx/tf, ty/tf) / (2 * np.pi)

            return {"pixmap": image, "hue": avg_hue}

    # makes circular rings, but tries to order images in rings by hue
    def circlesh(self, images):
        paths = []
        for image in images:
            paths.append(image.get("path"))

        hueinfo = []

        if self.loadonce:
            hueinfo = self.getHue(images)
            pixmaps = self.imageToQPixmap(images)
            for hi, pixmap in zip(hueinfo, pixmaps):
                hi["pixmap"] = pixmap
        else:
            hueinfo = images


        # center image is added within loop
        r = 0
        # number of images in ring
        n = 1
        total = 0

        imgct = 0

        # ths is the thetas (angles) for each image in a ring
        # defined better at end of loop body
        ths = np.array([0])

        # every iteration of this loop is a new ring
        # this structure is because n is random and different for each ring
        while len(hueinfo) > 0:
            # list of images in the current ring
            imgs = []
            for i in range(n):
                if len(hueinfo) > 0:
                    total += 1
                    imgs.append(hueinfo.pop(0))

            # # sort by hue
            # # this doesn't find the absolute best order-
            # # -to minimize the distance from where the image should actually be based on hue (while evenly spacing images)
            # # but it's a simple solution that adds a little structure to the ring order
            # imgs.sort(key= lambda x: x["hue"])

            for image in imgs:
                if not self.loadonce:
                    image = self.getHue(image)

                # "pop" the first element/angle to put image on
                th = ths[0] % 360
                ths = np.delete(ths, 0)
                
                # instead of evenly spacing the images out, you can just use the hue as the angle
                # this doesn't create a clean circle but will show hue distribution better
                th = image["hue"] * 360

                x = r * np.cos(th / 360 * 2 * np.pi) * self.STD_SPACE
                y = -r * np.sin(th / 360 * 2 * np.pi) * self.STD_SPACE

                self.add_to_scene(x=x, y=y, image=image["pixmap"], path=paths[imgct], h=th, r=r, initial_angle=th, 
                            direction= (int(r) % 2) * 2 - 1) # alternate rotation every ring
                imgct += 1
            QApplication.processEvents()

            # go to next ring
            r += 1
            # number of images in ring
            n = (8 * r + (r % 2) - 1 - random.randint(0, r * 2))
            step = 360 / n
            # offset the angle of the first image in ring, so there isn't just a line of images at th = 0
            # offset = step**2 # alternative offset
            # offset = random.randint(0, 359) # alternative offset
            offset = total * 10 # I just the way this offset looks
            ths = np.arange(0 + offset, 360 + offset, step)
        self.animate_zoom_delayed(delay_ms=0, duration_ms=2500)
        self.animation_timer.start(int(1000/self.FPS))  # ~60 FPS (16ms intervals)


    def hexagons(self, images):
        paths = []
        for image in images:
            paths.append(image.get("path"))


        if self.loadonce:
            images = self.imageToQPixmap(images)

        # center image @ (0, 0)
        self.add_to_scene(x= 0, y= 0, image= images[0], path=paths[0])

        img = 1 # image count

        # level aka ring
        # calculate how many levels there are based on num images
        # derived from N rings = 1 + 6 * sum(1 to N) = 1 + 3 * N * (N + 1)
        # more info at https://www.redblobgames.com/grids/hexagons/#rings
        for level in range(1, int(np.ceil((-3 + np.sqrt(12 * len(images) - 3)) / 6) + 1)):

            # sides holds the positions of images in a side and ring
            # there are level number of images in each side
            # (level = 2) ex: 
            # sides = [[1,2], [3,4], [5,6], [7,8], [9,10], [11,12]] 
            # [3,4] is the first and second image in the top right side/diagonal
            # further logic is in later code
            sides = []
            for c in range(0, 6):
                sides.append(list(range((c * level) + 1, ((c+1) * level) + 1)))

            # index start at sum of images in previous rings
            start = (level - 1) * level * 3 + 1
            # index end, add number of images in current ring (6 * level) (or end of images in the case of partially filled ring) from start
            end = min(start + level * 6, len(images))

            for i, image in enumerate(images[start : end]):

                # shuffle sides once a image has been placed in every side
                if i % 6 == 0:
                    random.shuffle(sides)

                # randomly pick a position in the side and remove so no duplicate positions
                idx = random.randint(0, len(sides[i % 6]) - 1)
                place = sides[i % 6].pop(idx)

                x, y = 0, 0

                # ngl ik this code is so ugly and there's prob a more elegant solution but this works
                # images are placed in lines corresponding to each side of the hexagonal ring
                # (top right, top, top left, bottom left, bottom, bottom right)
                if place <= level: # tr
                    x = (level * self.STD_SPACE) - ((place - 1) * (self.STD_SPACE / 2))
                    y = -(place - 1) * self.STD_SPACE
                elif place <= level * 2: # t
                    x = level * self.STD_SPACE/2 - (place - level - 1) * self.STD_SPACE
                    y = -level * self.STD_SPACE
                elif place <= level * 3: # tl
                    x = -(level * self.STD_SPACE/2) - ((place - (level * 2) - 1)) * (self.STD_SPACE / 2)
                    y = -level * self.STD_SPACE + (place - (level * 2) - 1) * self.STD_SPACE
                elif place <= level * 4: # bl
                    x = -level * self.STD_SPACE + (place - (level * 3) - 1) * self.STD_SPACE/2
                    y = (place - (level * 3) - 1) * self.STD_SPACE
                elif place <= level * 5: # b
                    x = -level * self.STD_SPACE / 2 + (place - (level * 4) - 1) * self.STD_SPACE
                    y = level * self.STD_SPACE
                elif place <= level * 6: # br
                    x = level * self.STD_SPACE/2 + (place - (level * 5) - 1) * self.STD_SPACE/2
                    y = level * self.STD_SPACE - (place - (level * 5) - 1) * self.STD_SPACE

                # calculate actual radius (different from level)
                # for hexagons the distance from origin is different than level
                # if you use level as radius, you'll get a fixed distance and circular rings (kinda cool but not desired here)
                radius = np.sqrt(x**2 + y**2) / self.STD_SPACE
                
                # calculate the actual angle the image is at
                th = (np.arctan2(-y, x) * 360 / (2 * np.pi)) % 360  # Calculate angle

                self.add_to_scene(x=x, y=y, image=image, path= paths[img], h=th, r=radius, initial_angle=th, direction= 1)
                img += 1
                
                QApplication.processEvents()

        self.animate_zoom_delayed(delay_ms=0, duration_ms=2500)
        self.animation_timer.start(int(1000/self.FPS))  # ~60 FPS (16ms intervals)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageGalleryApp()
    window.show()
    
    # Remove the automatic execution code and let the GUI handle everything
    sys.exit(app.exec_())