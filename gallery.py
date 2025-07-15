import sys
import os
import json
import numpy as np
from PIL import Image
import random
import colorsys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, 
                             QGraphicsPixmapItem, QVBoxLayout, QHBoxLayout, QWidget, 
                             QPushButton, QSlider, QLabel, QLineEdit, QComboBox, QFileDialog, 
                             QFrame, QColorDialog, QButtonGroup, QRadioButton, QGroupBox, 
                             QSpacerItem, QDialog, QSizePolicy, QProgressDialog, QMessageBox, 
                             QCheckBox, QMenu)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QElapsedTimer, QTimer, pyqtSignal, QSize, QThread

from view import CustomGraphicsView
from vectorDB import VectorDB
from accessDBs import add_color, search_color, add_visual, search_visual, search_clip
from colors import get_dominant_colors, show_palette
from colorpicker import colorPicker
import vcolorpicker

# from PIL.ImageQt import ImageQt # only works for PyQt6

class ImageGalleryApp(QMainWindow):
    def __init__(self, uuid, collection_data, font= "Arial"):
        super().__init__()
        self.font = font
        self.landing_page = None
        self.uuid = uuid
        self.collection_data = collection_data
        self.color_db = VectorDB.get_DB(self.uuid)
        self.setWindowTitle(f"Mosaic View - {collection_data["name"]}")
        self.setGeometry(100, 100, 1400, 768)

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_e_timer = QElapsedTimer()
        self.FPS = 60
        # in ms
        self.animation_time = 0.0
        self.animation_duration = 2000

        self.zoom_animation_timer = QTimer()
        self.zoom_animation_timer.timeout.connect(self.update_zoom)
        self.zoom_animation_e_timer = QElapsedTimer()
        
        self.zoom_duration = self.animation_duration
        self.zoom_start_scale = 0.1
        self.zoom_target_rect = QRectF()
        self.zoom_animating = False

        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene, self)
        # self.view.kinetic_timer.setInterval(int(1000/self.FPS))
        self.loadonce = False
        self.image_data = {}
        self.pixmaps = {}
        self.STD_SIZE = 512
        self.STD_SPACE = self.STD_SIZE * 1.5
        
        

        self.selected_color = QColor(255, 255, 255)  # Default white

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
                    preview = None
                    c = False
                    if isinstance(self.image_data[item].get("colors"), (list, np.ndarray)):
                        c = True
                        colors = self.image_data[item]["colors"]
                        image = show_palette(colors)
                        
                        # Create color palette preview dialog
                        preview = QDialog()
                        preview.setWindowTitle("Color Palette")
                        preview.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
                        preview_layout = QVBoxLayout(preview)
                        
                        # Convert PIL image to QPixmap
                        if image.mode != 'RGB':
                            image = image.convert('RGB')

                        data = image.tobytes("raw", "RGB")
                        qimage = QImage(data, image.size[0], image.size[1], image.size[0] * 3, QImage.Format_RGB888)

                        palette_pixmap = QPixmap.fromImage(qimage)
                        palette_label = QLabel()
                        palette_label.setPixmap(palette_pixmap)
                        preview_layout.addWidget(palette_label)
                        
                    # Create context menu
                    menu = QMenu()
                    query_visual = menu.addAction("Find Visually Similar")
                    query_color = menu.addAction("Find Colorfully Similar")
                    open_palette = None
                    if c:
                        open_palette = menu.addAction("Show Color Palette")
                    open_file = menu.addAction("Open Image")
                    open_location = menu.addAction("Show in Folder")
                    
                    # Show menu and get selected action
                    action = menu.exec_(event.screenPos())
                    if action == query_color:
                        if self.search_type_combo.currentText() != "Color Search":
                            self.search_type_combo.setCurrentText("Color Search")
                        if self.color_search_mode.currentText() != "Reference Image":
                            self.color_search_mode.setCurrentText("Reference Image")
                        self.color_image_path_label.setText(f"Selected: {path}")
                        self.query_image_path = path
                        self.generateGallery()
                    elif action == open_palette:
                        if preview:
                            preview.exec_()
                    elif action == query_visual:
                        if self.search_type_combo.currentText() != "Image Similarity Search (DINO)":
                            self.search_type_combo.setCurrentText("Image Similarity Search (DINO)")
                        self.image_path_label.setText(f"Selected: {path}")
                        self.query_image_path = path
                        self.generateGallery()
                    elif action == open_file:
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

        title = QLabel("Mosaic Controls")
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
        self.image_count_slider.setMinimum(1)
        self.image_count_slider.setMaximum(self.collection_data["image_count"])
        self.image_count_slider.setValue(max(1, int(self.collection_data["image_count"] * 0.5)))
        self.image_count_slider.valueChanged.connect(self.updateImageCountLabel)
        
        self.image_count_label = QLabel(str(max(1, int(self.collection_data["image_count"] * 0.5))))
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

        size_layout.addStretch()

        self.size_input = QLineEdit()
        self.size_input.setFont(QFont(self.font, 11))
        self.size_input.setText(str(self.STD_SIZE))
        self.size_input.setFixedWidth(70)
        self.size_input.setAlignment(Qt.AlignRight)
        size_layout.addWidget(self.size_input)

        size_layout.addWidget(QLabel("px"))  # Add px label
        layout.addWidget(size_container)

        fps_container = QWidget()
        fps_layout = QHBoxLayout(fps_container)
        fps_layout.setContentsMargins(0, 0, 0, 0)

        fps_label = QLabel("Animation FPS:")
        fps_label.setFont(QFont(self.font, 11))
        fps_layout.addWidget(fps_label)

        self.fps_input = QLineEdit()
        self.fps_input.setFont(QFont(self.font, 11))
        self.fps_input.setText(str(self.FPS))
        self.fps_input.setFixedWidth(70)
        self.fps_input.setAlignment(Qt.AlignRight)
        fps_layout.addWidget(self.fps_input)
        layout.addWidget(fps_container)

        self.loadonce_checkbox = QCheckBox("Load all images at once")
        self.loadonce_checkbox.setFont(QFont(self.font, 11))
        self.loadonce_checkbox.setChecked(True)
        layout.addWidget(self.loadonce_checkbox)

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
            # just gonna let dino do image search
            # search_types.append("Image Content Search (CLIP)")

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
        self.generate_button = QPushButton("Generate Mosaic")
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
        self.clear_button = QPushButton("Clear Mosaic")
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
    
    def toggleControlPanel(self):
        if self.control_panel.isVisible():
            self.control_panel.hide()
            self.toggle_panel_button.setText("<")  # Left arrow to show
        else:
            self.control_panel.show()
            self.toggle_panel_button.setText(">")  # Right arrow to hide

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

    def selectColor(self):
        # default Qt color picker
        # color = QColorDialog.getColor(self.selected_color, self, "Select Color")

        # i like this color picker the best
        # https://orthallelous.wordpress.com/2018/12/19/custom-color-dialog/
        color = colorPicker.getColor(self.selected_color, self, "Select Color")

        if color.isValid():
            self.selected_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}; border: 2px solid #666;")

        # this is a more modern custom color picker
        # vcolorpicker.useLightTheme(True)
        # current_rgb = (self.selected_color.red(), 
        #           self.selected_color.green(), 
        #           self.selected_color.blue())
        # color = vcolorpicker.getColor(current_rgb)  # Pass RGB tuple instead of QColor
        # if color:  # vcolorpicker returns None if canceled
        #     # Convert float RGB values (0-1) to integer RGB values (0-255)
        #     rgb_int = tuple(int(c) for c in color)
        #     self.selected_color = QColor(*rgb_int)  # Convert RGB tuple back to QColor
        #     self.color_button.setStyleSheet(
        #         f"background-color: {self.selected_color.name()}; border: 2px solid #666;"
        #     )
    
    def queryImageDialog(self):
        """Select query image for similarity search"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Query Image", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if file_path:
            self.query_image_path = file_path

    def selectImage(self):
        self.queryImageDialog()
        file_path = self.query_image_path
        filename = os.path.basename(file_path)
        self.image_path_label.setText(f"Selected: {filename}")

    def selectColorImage(self):
        self.queryImageDialog()
        file_path = self.query_image_path
        filename = os.path.basename(file_path)
        self.color_image_path_label.setText(f"Selected: {filename}")

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

    def clearSearchControls(self):
        # Remove all widgets from search controls layout
        while self.search_controls_layout.count():
            child = self.search_controls_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

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
    
    def setupImageSearchControls(self):
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
    
    def onSearchTypeChanged(self, search_type):
        if search_type == "Color Search":
            self.setupColorSearchControls()
        elif search_type == "Text Search (CLIP)":
            self.setupTextSearchControls()
        elif search_type == "Image Similarity Search (DINO)":
            self.setupImageSearchControls()
        elif search_type == "Image Content Search (CLIP)":
            self.setupImageSearchControls()
    
    def updateImageCountLabel(self, value):
        self.image_count_label.setText(str(value))


    def createIndex(self, index_type):
        """Create similarity search index"""
        if not self.collection_data:
            return
        

        class IndexCreationWorker(QThread):
            progress = pyqtSignal(str)
            finished = pyqtSignal()
            error = pyqtSignal(str)
            
            def __init__(self, key, folder, explore, index_type, progress_dialog):
                super().__init__()
                self.key = key
                self.folder = folder 
                self.explore = explore
                self.index_type = index_type
                self.progress_dialog = progress_dialog

            def run(self):
                try:
                    self.progress.emit(f"Creating {self.index_type.upper()} index...")
                    add_visual(self.key, self.folder, self.explore, model=self.index_type, progress= self.progress_dialog)
                    self.finished.emit()
                except Exception as e:
                    self.error.emit(str(e))
        
        # Show progress dialog
        progress_dialog = QProgressDialog(f"Creating {index_type.upper()} index...", None, 0, self.collection_data["image_count"], self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowFlag(Qt.WindowCloseButtonHint, False)
        progress_dialog.show()
        
        # Start worker
        self.index_worker = IndexCreationWorker(
            # self.collection_data['name'],
            self.uuid,
            self.collection_data['folder'], 
            self.collection_data['subfolders'],
            index_type,
            progress_dialog
        )
        
        def on_finished():
            progress_dialog.close()
            # self.updateSearchModeOptions()
            self.collection_data[index_type] = True
            QMessageBox.information(self, "Success", f"{index_type.upper()} index created successfully!")

            collections = []
            with open("collections.json", 'r') as f:
                collections = json.load(f)
                collections[self.uuid] = self.collection_data
            
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
            # search_types.append("Image Content Search (CLIP)")
            
            # Remove CLIP index creation button if it exists
            if (self, 'create_clip_btn') and self.create_clip_btn:
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

    def clearGallery(self):
        # Stop animations
        self.animation_timer.stop()
        self.zoom_animation_timer.stop()
        
        # Stop any active worker threads
        if hasattr(self, 'index_worker') and self.index_worker:
            if self.index_worker.isRunning():
                self.index_worker.terminate()
                self.index_worker.wait()

        # Clear scene
        self.scene.clear()
        self.image_data.clear()
        
        # Reset view
        self.view.resetTransform()
        self.view.centerOn(0, 0)
        
        # Reset animation state
        self.animation_time = 0.0
        self.zoom_animating = False

    def generateGallery(self):
        # Clear existing gallery first
        self.clearGallery()
        
        # Get parameters from UI
        num_images = self.image_count_slider.value()
        database = self.uuid
        search_type = self.search_type_combo.currentText()
        layout_type = self.layout_buttons.checkedId()
        image_size = self.size_input.text()
        fps = self.fps_input.text()
        self.loadonce = self.loadonce_checkbox.isChecked()

        try:
            image_size = int(image_size)
            # Reasonable size limits
            if image_size > 2048:
                self.STD_SIZE = 2048
            elif image_size < 32:
                self.STD_SIZE = 32
            else:
                self.STD_SIZE = image_size
        except ValueError:
            pass

        self.STD_SPACE = self.STD_SIZE * 1.5
        self.size_input.setText(str(self.STD_SIZE))

        try:
            fps = int(fps)
            # Reasonable size limits
            if fps > 360:
                self.FPS = 360
            elif image_size < 12:
                self.FPS = 12
            else:
                self.FPS = fps

            # self.view.kinetic_timer.setInterval(int(1000/self.FPS))
            # self.view.FPS = self.FPS
        except ValueError:
            pass

        self.fps_input.setText(str(self.FPS))
        

        try:
            # Perform search based on type
            images = []
            
            if search_type == "Color Search":
                # Check which mode is being used
                mode = self.color_search_mode.currentText()
                
                if mode == "Reference Image":
                    # Use image path for color search
                    if hasattr(self, 'query_image_path') and self.query_image_path:
                        images = search_color(database, path=self.query_image_path, k=num_images)
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
                    
            elif search_type == "Text Search (CLIP)":
                if hasattr(self, 'text_input') and self.text_input.text().strip():
                    query = self.text_input.text().strip()
                    images = search_clip(name=database, query=query, k=num_images)
                else:
                    QMessageBox.warning(self, "Warning", "Please enter a text query")
                    return
                    
            elif search_type == "Image Similarity Search (DINO)":
                if hasattr(self, 'query_image_path') and self.query_image_path:
                    images = search_visual(name=database, file_path=self.query_image_path, k=num_images)
                else:
                    print("No reference image selected for visual similarity")
                    return
                
            elif search_type == "Image Content Search (CLIP)":
                if hasattr(self, 'query_image_path') and self.query_image_path:
                    images = search_clip(database, query_image_path=self.query_image_path, k=num_images)
                else:
                    print("No reference image selected for image search")
                    return
            
            if len(images) == 0:
                QMessageBox.warning(self, "Error", "No images found! Check if the collection folder contains images")
                return
            
            # Apply layout based on selection
            if layout_type == 0:  # Circles
                self.circles(images)
            elif layout_type == 1:  # Circles by Hue
                self.circlesh(images)
            elif layout_type == 2:  # Hexagons
                self.hexagons(images)
                
        except Exception as e:
            print(f"Error generating gallery: {e}")
            QMessageBox.warning(self, "Error", f"{e}")
    
    # zoom stuff
    def calculate_bounds(self):
        if not self.image_data:
            return QRectF(0, 0, 0, 0)

        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

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

        content_width = max_x - min_x
        content_height = max_y - min_y

        margin_x = content_width * 1
        margin_y = content_height * 1

        # Create expanded scene rect
        expanded_rect = QRectF(
            min_x - margin_x,
            min_y - margin_y,
            content_width + 2 * margin_x,
            content_height + 2 * margin_y
        )

        self.view.scene().setSceneRect(expanded_rect)

        # Return the original content bounds (not expanded)
        return QRectF(min_x, min_y, content_width, content_height)

    def ease_out_cubic(self, t):
        return 1 - (1 - t)**3 if t != 1 else 1
    def ease_out_exp(self, t):
        return 1 - np.exp(-10 * t) if t != 1 else 1 # for floating point
    def ease_out_pow(self, t, pow=2):
        return 1-(t-1)**pow
    def start_zoom(self, margin_p=0.1, duration_ms=1000, start_scale=0.1):
        
        bounds = self.calculate_bounds()
        
        margin_x = bounds.width() * margin_p
        margin_y = bounds.height() * margin_p
        
        self.zoom_target_rect = QRectF(
            bounds.x() - margin_x,
            bounds.y() - margin_y,
            bounds.width() + 2 * margin_x,
            bounds.height() + 2 * margin_y
        )
        
        self.zoom_start_scale = start_scale
        self.zoom_elapsed = 0
        self.zoom_animating = True
        # sw = self.zoom_target_rect.width() * start_scale
        # sh = self.zoom_target_rect.height() * start_scale
        # start_rect = QRectF(-sw/2,-sh/2,sw,sh)

        start_rect = QRectF(-self.STD_SPACE/2, -self.STD_SPACE/2, self.STD_SPACE, self.STD_SPACE)
        
        self.view.fitInView(start_rect, Qt.KeepAspectRatio)
        
        self.zoom_animation_timer.start(int(1000/self.FPS))
        self.zoom_animation_e_timer.start()

    def update_zoom(self):
        if not self.zoom_animating:
            return
        # self.zoom_elapsed += int(1000/self.FPS)/1000
        self.zoom_elapsed = self.zoom_animation_e_timer.elapsed()
        self.zoom_elapsed = min(self.zoom_elapsed, self.zoom_duration)
        t = self.zoom_elapsed / self.zoom_duration
        if t >= 1:
            self.view.fitInView(self.zoom_target_rect, Qt.KeepAspectRatio)
            self.zoom_animation_timer.stop()
            self.zoom_animating = False
            return
        
        eased_progress = self.ease_out_pow(t, 6)
        
        current_scale = self.zoom_start_scale + (1.0 - self.zoom_start_scale) * eased_progress
        
        current_rect = QRectF(
            self.zoom_target_rect.center().x() - (self.zoom_target_rect.width() * current_scale) / 2,
            self.zoom_target_rect.center().y() - (self.zoom_target_rect.height() * current_scale) / 2,
            self.zoom_target_rect.width() * current_scale,
            self.zoom_target_rect.height() * current_scale
        )
        
        self.view.fitInView(current_rect, Qt.KeepAspectRatio)

    def animate_zoom_delayed(self, delay_ms=100, duration_ms=1000):
        def x():
            if self.loadonce:
                self.start_zoom(duration_ms=duration_ms)
            else:
                return
        
        QTimer.singleShot(delay_ms, x)

    # rotation
    def update_animation(self):
        # self.animation_time += int(1000/self.FPS)/1000
        self.animation_time = self.animation_e_timer.elapsed()
        t = min(self.animation_time/self.animation_duration, 1)
        for item, data in self.image_data.items():
            
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

                self.image_data[item]['w'] = data['w_0'] * (1 - self.ease_out_exp(t))

                # self.image_data[item]['w'] *= (1 - min((self.animation_time/self.animation_duration)**25, 1)) # reverse to initial position
                
                # self.image_data[item]['w'] *= (-self.ease_out_exp(t) + 1) # reverse to initial position
            

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
            # start = time.time()
            # Create progress dialog
            progress = QProgressDialog("Rendering images...", None, 0, len(image_info), self)
            progress.setWindowTitle("Loading")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setCancelButton(None)
            progress.setWindowFlag(Qt.WindowCloseButtonHint, False)
            progress.setFont(QFont(self.font, 11))
            progress.setStyleSheet("""
                QProgressDialog {
                    background-color: white;
                    min-width: 300px;
                    min-height: 50px;
                }
                QProgressBar {
                    text-align: center;
                    border: 1px solid #ccc;
                    border-radius: 2px;
                    margin: 10px;
                }
            """)
            
            progress.show()

            pixmaps = []
            for i, image in enumerate(image_info):
                pixmaps.append(self.imageToQPixmap(image))
                progress.setValue(i + 1)
                QApplication.processEvents()
            # end = time.time()
            # print(f"{end-start} seconds")
            return pixmaps
        else:
            image = image_info

            if "image" in image:
                image = image["image"]
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                w, h = image.size
                ar = w/h
                
                if max(h, w) == h:
                    image = image.resize((int(self.STD_SIZE * ar), self.STD_SIZE))
                else:
                    image = image.resize((self.STD_SIZE, int(self.STD_SIZE / (ar+1))))

                w, h = image.size

                data = image.tobytes("raw", "RGB")
                qimage = QImage(data, w, h, w * 3, QImage.Format_RGB888)

                pixmap = QPixmap.fromImage(qimage)
            else:
                pixmap = image.get("pixmap")
                if isinstance(image.get("path"), str):
                    # pixmap = self.pixmaps.get(image.get("path"))
                    if not pixmap:
                        pixmap = QPixmap(image["path"])
                        # self.pixmaps[image.get("path")] = pixmap
                h = pixmap.height()
                w = pixmap.width()
                if w == 0 and h == 0:
                    QMessageBox.critical(self, "Error", f"Images not found. Please recreate the collection or revert the names of any relevant folders.")
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
    

    def add_to_scene(self, x, y, image, path, colors= None, h=10, s=255, l=128, r=0, initial_angle=0, direction=0):
        pixmap = None
        # path = None
        
        if isinstance(image, QPixmap):
            pixmap = image
        else:
            pixmap = self.imageToQPixmap(image)
        

        item = QGraphicsPixmapItem(pixmap)
        item.setPos((-pixmap.width() / 2) + x, (-pixmap.height() / 2) + y)
        self.scene.addItem(item)
        
        v = 600
        w = v * direction / (r + 1)
        self.image_data[item] = {
            'r': r,
            'th_0': initial_angle,
            'w_0': w,
            'w': w,
            'path': path,
            'colors': colors
        }

    

    def circles(self, images):
        paths = []
        colors = []
        for image in images:
            paths.append(image.get("path"))
            colors.append(image.get("colors"))

        for i in range(len(colors)):
            if np.all(colors[i] != None):
                colors[i] = colors[i].reshape(int(len(colors[i])/4), 4)

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
            self.add_to_scene(x=x, y=y, image=image, path=paths[i], colors= colors[i], h=th, r=r, initial_angle=th, 
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

        self.animate_zoom_delayed(delay_ms=0, duration_ms=self.zoom_duration)
        self.animation_timer.start(int(1000/self.FPS))
        self.animation_e_timer.start()
        self.animation_time = 0

    def getHue(self, image_info):
        if isinstance(image_info, list):
            hueinfo = []
            for image in image_info:
                hueinfo.append(self.getHue(image))
            return hueinfo
        else:
            image = image_info

            l = []
            if "colors" in image:
                l = image["colors"]
                
            else:
                if np.all(self.color_db.get_vector(image["path"]) != None):
                    l = self.color_db.get_vector(image["path"])
                else:
                    l = get_dominant_colors(Image.open(image["path"]).convert('RGB'))
                image["colors"] = l

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

            return {"pixmap": image, "hue": avg_hue, "colors": l}

    # makes circular rings, but tries to order images in rings by hue
    def circlesh(self, images):
        paths = []
        colors = []
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

                self.add_to_scene(x=x, y=y, image=image["pixmap"], path=paths[imgct], colors= image.get("colors"), h=th, r=r, initial_angle=th, 
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
        self.animate_zoom_delayed(delay_ms=0, duration_ms=self.zoom_duration)
        self.animation_timer.start(int(1000/self.FPS))
        self.animation_e_timer.start()
        self.animation_time = 0


    def hexagons(self, images):
        paths = []
        colors = []
        for image in images:
            paths.append(image.get("path"))
            colors.append(image.get("colors"))

        for i in range(len(colors)):
            if np.all(colors[i] != None):
                colors[i] = colors[i].reshape(int(len(colors[i])/4), 4)

        if self.loadonce:
            images = self.imageToQPixmap(images)

        # center image @ (0, 0)
        self.add_to_scene(x= 0, y= 0, colors= colors[0], image= images[0], path=paths[0])

        imgct = 1 # image count

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

                self.add_to_scene(x=x, y=y, image=image, path= paths[imgct], colors= colors[imgct], h=th, r=radius, initial_angle=th, direction= 1)
                imgct += 1
                
                QApplication.processEvents()

        self.animate_zoom_delayed(delay_ms=0, duration_ms=self.zoom_duration)
        self.animation_timer.start(int(1000/self.FPS))
        self.animation_e_timer.start()
        self.animation_time = 0



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageGalleryApp()
    window.show()
    
    # Remove the automatic execution code and let the GUI handle everything
    sys.exit(app.exec_())