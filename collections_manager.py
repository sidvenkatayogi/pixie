# TODO
# choose between colorpickers
# fix pannning
# fix off center loading box
# fix sorting collectoins and it opens the wong colelcton

import sys
import os
import shutil
import re
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QFrame, QScrollArea, QDialog, QLineEdit, QProgressDialog,
                             QFileDialog, QCheckBox, QMessageBox, QComboBox, QMenu, QInputDialog, QMessageBox)
from PyQt5.QtGui import QPixmap, QFontDatabase, QFont, QPainter, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer
from uuid import uuid4
from pins import download_board

class CollectionThumbnail(QFrame):
    """Widget representing a single collection thumbnail"""
    clicked = pyqtSignal(dict)
    collection_updated = pyqtSignal()  # New signal for updates
    
    def __init__(self, uuid, collection_data, parent=None, font="Arial"):
        super().__init__(parent)
        self.font = font
        self.uuid = uuid
        self.collection_data = collection_data
        self.setupUI()
        
        
    def setupUI(self):
        self.setFixedSize(200, 250)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 0px solid #ddd;
                border-radius: 8px;
                background-color: white;
            }
            QFrame:hover {
                border-color: #4CAF50;
                background-color: #d4d4d4;
            }
            QFrame:hover QLabel {
                background-color: #d4d4d4;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)

        # Add thumbnail label first
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(180, 180)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 0px solid #ccc;
                border-radius: 4px;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.thumbnail_label)
        self.loadThumbnail()  # Load thumbnail right after creating label

        # Then create info container
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 5, 0, 0)  # Added top margin
        info_layout.setSpacing(0)

        # Collection name
        name_label = QLabel(self.collection_data.get('name', 'Untitled'))
        name_label.setFont(QFont(self.font, 12, QFont.Bold))
        name_label.setAlignment(Qt.AlignLeft)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("border: none; background: transparent;")
        info_layout.addWidget(name_label)

        # Bottom row for info and menu button
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)

        # Collection info
        image_count = self.collection_data.get('image_count', 0)
        date_updated = self.collection_data.get('last_updated', '')
        info_label = QLabel(f"{image_count} Images\n{date_updated}")
        info_label.setFont(QFont(self.font, 9))
        info_label.setAlignment(Qt.AlignLeft)
        info_label.setStyleSheet("color: #666; border: none; background: transparent;")
        bottom_row.addWidget(info_label)

        # Menu button
        self.menu_button = QPushButton("Edit")
        self.menu_button.setFont(QFont(self.font, 9))
        self.menu_button.setFixedSize(40, 32)
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0);
                border: none;
                border-radius: 3px;
                font-size: 12px;
                color: #666;
                margin-top: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.9);
            }
        """)
        self.menu_button.clicked.connect(self.showMenu)
        bottom_row.addWidget(self.menu_button)

        # Add bottom row to info layout
        info_layout.addLayout(bottom_row)
        
        # Add info container to main layout
        layout.addWidget(info_container)
        
        
    def loadThumbnail(self):
        thumbnail_path = self.collection_data.get('thumbnail_path', '')
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(180, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_label.setPixmap(scaled_pixmap)
                return
        
        # Create placeholder thumbnail
        self.createPlaceholderThumbnail()

    def showMenu(self):
        menu = QMenu(self)
        menu.setFont(QFont(self.font, 10))
        rename_action = menu.addAction("Rename Collection")
        change_thumb_action = menu.addAction("Change Thumbnail")
        # TODO update collection
        delete_action = menu.addAction("Delete Collection")
        
        
        action = menu.exec_(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))
        
        if action == rename_action:
            self.renameCollection()
        elif action == change_thumb_action:
            self.changeThumbnail()
        elif action == delete_action:
            self.deleteCollection()

    def renameCollection(self):
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Collection",
            "Enter new name:",
            QLineEdit.Normal,
            self.collection_data['name']
        )
        if ok and len(new_name.strip()) > 0:
            # old_name = self.collection_data['name']  # Store old name before updating
            self.collection_data['name'] = new_name.strip()
            self.updateCollectionsFile()  # Pass old name to update method
            self.collection_updated.emit()

    def changeThumbnail(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select New Thumbnail",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        
        if file_path:
            self.collection_data['thumbnail_path'] = file_path
            self.loadThumbnail()
            self.updateCollectionsFile()
            self.collection_updated.emit()

    def deleteCollection(self):
        try:
            with open('collections.json', 'r') as f:
                collections = json.load(f)
                
            del collections[self.uuid]
                    
            with open('collections.json', 'w') as f:
                json.dump(collections, f, indent=2)
            
            shutil.rmtree(os.path.join("collections", self.uuid))

            self.collection_updated.emit()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update collection: {str(e)}")

    def updateCollectionsFile(self):
        try:
            with open('collections.json', 'r') as f:
                collections = json.load(f)
                
            collections[self.uuid] = self.collection_data
                    
            with open('collections.json', 'w') as f:
                json.dump(collections, f, indent=2)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update collection: {str(e)}")


    def createPlaceholderThumbnail(self):
        pixmap = QPixmap(180, 140)
        pixmap.fill(QColor(240, 240, 240))
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 24))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "📁")
        painter.end()
        
        self.thumbnail_label.setPixmap(pixmap)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.collection_data)


class CreateCollectionDialog(QDialog):
    """Dialog for creating a new collection"""
    
    def __init__(self, parent=None, font= "Arial"):
        super().__init__(parent)
        self.font = font
        self.current_import = 0
        self.setWindowTitle("Create New Collection")
        self.setModal(True)
        self.setFixedSize(500, 240)
        self.setupUI()
        
    def setupUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        

        self.setupFolderUI()

    def clearLayout(self, layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if isinstance(item, (QHBoxLayout, QVBoxLayout)):
                self.clearLayout(item)
            if item:    
                widgetToRemove = layout.itemAt(i).widget()
                # remove it from the layout list
                layout.removeWidget(widgetToRemove)
                # remove it from the gui
                if widgetToRemove:
                    widgetToRemove.deleteLater()

    def resetUI(self):
        self.clearLayout(self.layout)
        self.import_layout = QHBoxLayout()
        self.folder_button = QPushButton("From Folder")
        self.folder_button.clicked.connect(self.setupFolderUI)
        self.folder_button.setContentsMargins(0, 0, 5, 0)
        self.import_layout.addWidget(self.folder_button)
        

        self.pinterest_button = QPushButton("From Pinterest")
        self.pinterest_button.clicked.connect(self.setupPinterestUI)
        self.import_layout.addWidget(self.pinterest_button)

        self.import_layout.addStretch()
    
    def updateUrlStatus(self, text):
        pattern = r'(https?://)?(www\.)?pinterest\.com/([^/]+)/([^/]+)/?$'
    
        match = re.match(pattern, text)
        
        if match:
            self.url_status_label.setText(f"✓ Valid Board URL")
            self.url_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 10px;")
        else:
            self.url_status_label.setText("⚠ Invalid Board URL")
            self.url_status_label.setStyleSheet("color: #ed1111; font-weight: bold; font-size: 10px;")
    
    def setupPinterestUI(self):
        if self.current_import != 2:
            self.resetUI()
            # Main content area with two columns
            content_layout = QHBoxLayout()
            content_layout.setSpacing(15)
            
            # Left column for form fields
            left_column = QVBoxLayout()
            left_column.setSpacing(6)
            
            left_column.addLayout(self.import_layout)

            url_box = QVBoxLayout()
            # Collection name section
            url_label = QLabel("Public Board URL:")
            url_label.setFont(QFont(self.font, 9))
            url_label.setContentsMargins(3, 0, 0, 0)
            url_box.addWidget(url_label)
            
            self.url_input = QLineEdit()
            self.url_input.setFont(QFont(self.font, 9))
            self.url_input.setPlaceholderText("pinterest.com/user/board")
            self.url_input.setMinimumHeight(32)
            self.url_input.textChanged.connect(self.updateUrlStatus)
            url_box.addWidget(self.url_input)
            
            # # Folder status label
            self.url_status_label = QLabel("")
            self.url_status_label.setWordWrap(True)
            self.url_status_label.setMinimumHeight(18)
            # self.url_status_label.setStyleSheet("font-size: 10px;")
            self.url_status_label.setFont(QFont(self.font, 9))
            url_box.addWidget(self.url_status_label)
            url_box.setAlignment(Qt.AlignCenter)
            url_box.setContentsMargins(0, 0, 0, 56)
            left_column.addLayout(url_box)
            
            
            content_layout.addLayout(left_column, 2)
            
            # Right column for thumbnail and buttons
            right_column = QVBoxLayout()
            right_column.setSpacing(6)
            
            # Thumbnail preview section
            thumbnail_label = QLabel("Thumbnail Preview")
            thumbnail_label.setAlignment(Qt.AlignCenter)
            thumbnail_label.setStyleSheet("font-weight: bold; font-size: 10px; margin-bottom: 2px;")
            right_column.addWidget(thumbnail_label)
            
            self.thumbnail_preview = QLabel()
            self.thumbnail_preview.setFixedSize(120, 90)  # Slightly larger thumbnail
            self.thumbnail_preview.setAlignment(Qt.AlignCenter)
            self.thumbnail_preview.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 5px;
                    background-color: #f8f8f8;
                    color: #666;
                    font-size: 10px;
                }
            """)
            self.thumbnail_preview.setText("No thumbnail\nselected")
            right_column.addWidget(self.thumbnail_preview, 0, Qt.AlignHCenter)
            
            # Add some spacing after thumbnail
            right_column.addSpacing(6)
            
            self.choose_thumbnail_button = QPushButton("Choose Thumbnail")
            self.choose_thumbnail_button.setMinimumHeight(24)
            self.choose_thumbnail_button.setFixedWidth(120)
            self.choose_thumbnail_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.choose_thumbnail_button.clicked.connect(self.selectThumbnail)
            right_column.addWidget(self.choose_thumbnail_button, 0, Qt.AlignHCenter)
            
            # Add spacing before buttons
            right_column.addSpacing(12)
            
            # Action buttons - positioned to the right
            button_layout = QHBoxLayout()
            button_layout.addStretch()  # Push buttons to the right
            button_layout.setSpacing(8)
            
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.setMinimumHeight(26)
            self.cancel_button.setMinimumWidth(75)
            self.cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_button)
            
            self.create_button = QPushButton("Create")
            self.create_button.setMinimumHeight(26)
            self.create_button.setMinimumWidth(75)
            self.create_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    font-weight: bold;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.create_button.clicked.connect(self.createCollection)
            button_layout.addWidget(self.create_button)
            
            right_column.addLayout(button_layout)
            
            # Add stretch to push everything to top
            right_column.addStretch()
            
            content_layout.addLayout(right_column, 1)

            self.layout.addLayout(content_layout)
            
            # Initialize variables
            self.selected_folder = ""
            self.selected_thumbnail = ""
            self.current_import = 2

    def setupFolderUI(self):
        if self.current_import != 1:
            self.resetUI()

            # Main content area with two columns
            content_layout = QHBoxLayout()
            content_layout.setSpacing(15)
            
            # Left column for form fields
            left_column = QVBoxLayout()
            left_column.setSpacing(6)
            
            left_column.addLayout(self.import_layout)
            # Collection name section
            left_column.addWidget(QLabel("Collection Name:"))
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("Enter collection name...")
            self.name_input.setMinimumHeight(24)
            left_column.addWidget(self.name_input)
            
            # Folder section
            left_column.addWidget(QLabel("Folder:"))
            folder_layout = QHBoxLayout()
            folder_layout.setSpacing(6)
            
            self.folder_input = QLineEdit()
            self.folder_input.setPlaceholderText("Select folder containing images...")
            self.folder_input.setReadOnly(True)
            self.folder_input.setMinimumHeight(24)
            folder_layout.addWidget(self.folder_input)
            
            self.browse_button = QPushButton("Browse")
            self.browse_button.setMinimumHeight(24)
            self.browse_button.setMaximumWidth(65)
            self.browse_button.clicked.connect(self.selectFolder)
            folder_layout.addWidget(self.browse_button)
            
            left_column.addLayout(folder_layout)
            
            # Include subfolders checkbox
            self.subfolders_checkbox = QCheckBox("Include Subfolders")
            self.subfolders_checkbox.setStyleSheet("font-size: 11px;")

            self.subfolders_checkbox.stateChanged.connect(self.updateFolderStatus)
            left_column.addWidget(self.subfolders_checkbox)
            
            # Folder status label
            self.folder_status_label = QLabel("")
            self.folder_status_label.setWordWrap(True)
            self.folder_status_label.setMinimumHeight(18)
            self.folder_status_label.setStyleSheet("font-size: 10px;")
            left_column.addWidget(self.folder_status_label)
            
            content_layout.addLayout(left_column, 2)
            
            # Right column for thumbnail and buttons
            right_column = QVBoxLayout()
            right_column.setSpacing(6)
            
            # Thumbnail preview section
            thumbnail_label = QLabel("Thumbnail Preview")
            thumbnail_label.setAlignment(Qt.AlignCenter)
            thumbnail_label.setStyleSheet("font-weight: bold; font-size: 10px; margin-bottom: 2px;")
            right_column.addWidget(thumbnail_label)
            
            self.thumbnail_preview = QLabel()
            self.thumbnail_preview.setFixedSize(120, 90)  # Slightly larger thumbnail
            self.thumbnail_preview.setAlignment(Qt.AlignCenter)
            self.thumbnail_preview.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 5px;
                    background-color: #f8f8f8;
                    color: #666;
                    font-size: 10px;
                }
            """)
            self.thumbnail_preview.setText("No thumbnail\nselected")
            right_column.addWidget(self.thumbnail_preview, 0, Qt.AlignHCenter)
            
            # Add some spacing after thumbnail
            right_column.addSpacing(6)
            
            self.choose_thumbnail_button = QPushButton("Choose Thumbnail")
            self.choose_thumbnail_button.setMinimumHeight(24)
            self.choose_thumbnail_button.setFixedWidth(120)
            self.choose_thumbnail_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.choose_thumbnail_button.clicked.connect(self.selectThumbnail)
            right_column.addWidget(self.choose_thumbnail_button, 0, Qt.AlignHCenter)
            
            # Add spacing before buttons
            right_column.addSpacing(12)
            
            # Action buttons - positioned to the right
            button_layout = QHBoxLayout()
            button_layout.addStretch()  # Push buttons to the right
            button_layout.setSpacing(8)
            
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.setMinimumHeight(26)
            self.cancel_button.setMinimumWidth(75)
            self.cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_button)
            
            self.create_button = QPushButton("Create")
            self.create_button.setMinimumHeight(26)
            self.create_button.setMinimumWidth(75)
            self.create_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    font-weight: bold;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.create_button.clicked.connect(self.createCollection)
            button_layout.addWidget(self.create_button)
            
            right_column.addLayout(button_layout)
            
            # Add stretch to push everything to top
            right_column.addStretch()
            
            content_layout.addLayout(right_column, 1)

            self.layout.addLayout(content_layout)
            
            # Initialize variables
            self.selected_folder = ""
            self.selected_thumbnail = ""

            self.current_import = 1
        
    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.selected_folder = folder
            self.folder_input.setText(folder)
            self.updateFolderStatus()
            
    def selectThumbnail(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Thumbnail Image", 
            self.selected_folder if self.selected_folder else "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if file_path:
            self.selected_thumbnail = file_path
            self.updateThumbnailPreview()
            
    def updateFolderStatus(self):
        if self.selected_folder:
            # Count image files in folder
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'}
            image_count = 0
            
            if self.subfolders_checkbox.isChecked():
                for root, dirs, files in os.walk(self.selected_folder):
                    for file in files:
                        if os.path.splitext(file.lower())[1] in image_extensions:
                            image_count += 1
            else:
                for file in os.listdir(self.selected_folder):
                    if os.path.isfile(os.path.join(self.selected_folder, file)):
                        if os.path.splitext(file.lower())[1] in image_extensions:
                            image_count += 1
            
            if image_count > 0:
                self.folder_status_label.setText(f"✓ Found {image_count} images")
                self.folder_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 10px;")
            else:
                self.folder_status_label.setText("⚠ No supported image files found")
                self.folder_status_label.setStyleSheet("color: #ed1111; font-weight: bold; font-size: 10px;")
        else:
            self.folder_status_label.setText("")
            
    def updateThumbnailPreview(self):
        if self.selected_thumbnail and os.path.exists(self.selected_thumbnail):
            pixmap = QPixmap(self.selected_thumbnail)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_preview.setPixmap(scaled_pixmap)
                self.thumbnail_preview.setText("")  # Clear placeholder text
                
    def createCollection(self):
        self.name = None
        if self.current_import == 1:
            self.name = self.name_input.text().strip()
            if not self.name:
                QMessageBox.warning(self, "Error", "Please enter a collection name.")
                return
                
            if not self.selected_folder:
                QMessageBox.warning(self, "Error", "Please select a folder.")
                return
                
            if not os.path.exists(self.selected_folder):
                QMessageBox.warning(self, "Error", "Selected folder does not exist.")
                return
            
            if self.folder_status_label.text()=="⚠ No supported image files found":
                QMessageBox.warning(self, "Error", "No supported image files found.")
                return

            self.accept()

        elif self.current_import == 2:
            if self.url_status_label.text() == "⚠ Invalid Board URL":
                QMessageBox.warning(self, "Error", "Invalid Board URL.")
                return
            
            class IndexWorker(QThread):
                progress = pyqtSignal(int)
                finished = pyqtSignal()
                value_changed = pyqtSignal(int)  # Add signal for progress updates
                
                def __init__(self, dialog, url):  # Remove progress_dialog from constructor
                    super().__init__()
                    self.url = url
                    self.dialog = dialog
                    
                def run(self):
                    try:
                        # Create wrapper class to emit progress signals
                        # class ProgressEmitter:
                        #     def __init__(self, signal):
                        #         self.signal = signal
                        #     def setValue(self, value):
                        #         self.signal.emit(value)
                                
                        # progress_emitter = ProgressEmitter(self.value_changed)
                        self.dialog.selected_folder, self.dialog.name = download_board(self.url)
                        self.finished.emit()
                    except Exception as e:
                        print(f"Error in worker thread: {e}")

            def on_cancelled():
                if self.index_worker:
                    self.index_worker.terminate()  # Force terminate if needed
                    self.index_worker.wait()  # Wait for thread to finish

            # Show progress dialog
            progress_dialog = QProgressDialog(f"Downloading Board: {self.url_input.text().strip()}...", "Cancel", 0, 0, parent=self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            # progress_dialog.setWindowFlags(
            #     progress_dialog.windowFlags() & ~Qt.WindowCloseButtonHint
            # )
            progress_dialog.setMinimumDuration(0)
            progress_dialog.canceled.connect(on_cancelled)
            progress_dialog.show()
            
            # Start worker thread
            self.index_worker = IndexWorker(self, self.url_input.text().strip())

            def on_finished():
                progress_dialog.close()
                if not self.selected_folder:
                    QMessageBox.warning(self, "Error", "Board not found.\nPlease check for typos or connection issues.")
                    return
                
                self.selected_thumbnail = os.path.join(self.selected_folder, os.listdir(self.selected_folder)[-1])
                self.accept()
            # Connect signals
            # self.index_worker.value_changed.connect(progress_dialog.setValue)
            self.index_worker.finished.connect(on_finished)
            self.index_worker.start()
        
    def getCollectionData(self):
        data = {'name': self.name,
                'folder': self.selected_folder,
                'thumbnail_path': self.selected_thumbnail,
                'last_updated': datetime.now().strftime("%m/%d/%Y"),
                'created_date': datetime.now().isoformat()}

        try:
            data['subfolders'] = self.subfolders_checkbox.isChecked()
        except RuntimeError:
            data['subfolders'] = False
        
        return data


class CollectionsLandingPage(QMainWindow):
    """Main landing page for managing collections"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Your Collections - Image Gallery")
        self.setGeometry(100, 100, 1200, 800)
        
        self.loadCustomFont()

        # Collections data
        self.collections = {}
        self.collections_file = "collections.json"
        
        self.setupUI()
        self.loadCollections()
        self.showMaximized()
        # self.font = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont("Inter.ttc"))[0]
        # print(self.font)

    def loadCustomFont(self):
        font_id = QFontDatabase.addApplicationFont("Inter.ttc")
        if font_id != -1:
            self.font = QFontDatabase.applicationFontFamilies(font_id)[0]
        else:
            print("Error: Could not load custom font")
            self.font = "Arial"  # Fallback font

    def setupUI(self):
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Your Collections")
        title_label.setFont(QFont(self.font, 24, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Sort dropdown
        sort_label = QLabel("Sort By:")
        header_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Date Created", "Image Count"])
        # self.sort_combo.addItems(["Name", "Date Created", "Date Modified", "Image Count"])
        self.sort_combo.currentTextChanged.connect(self.sortCollections)
        header_layout.addWidget(self.sort_combo)
        
        main_layout.addLayout(header_layout)
        
        # Scroll area for collections
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # Collections container
        self.collections_widget = QWidget()
        self.collections_layout = QGridLayout(self.collections_widget)
        self.collections_layout.setSpacing(20)
        self.collections_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.collections_widget)
        main_layout.addWidget(self.scroll_area)
        
        # Empty state label (hidden by default)
        self.empty_label = QLabel("You have no collections saved. Create a new one with the + in the bottom right!")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setFont(QFont(self.font, 14))
        self.empty_label.setStyleSheet("color: #666; margin: 50px;")
        self.empty_label.hide()
        main_layout.addWidget(self.empty_label)
        
        # Plus button (bottom right)
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedSize(60, 60)
        self.plus_button.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                border: none;
                border-radius: 30px;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6b6b6b;
            }
            QPushButton:pressed {
                background-color: #3d3d3d;
            }
        """)
        self.plus_button.clicked.connect(self.createNewCollection)
        
        # Position plus button in bottom right
        self.plus_button.setParent(main_widget)
        self.plus_button.move(1120, 720)  # Adjust based on window size
        
    def resizeEvent(self, event):
        # Reposition plus button when window is resized
        super().resizeEvent(event)
        if hasattr(self, 'plus_button'):
            self.plus_button.move(self.width() - 80, self.height() - 80)
            
    def loadCollections(self):
        """Load collections from JSON file"""
        if os.path.exists(self.collections_file):
            try:
                with open(self.collections_file, 'r') as f:
                    self.collections = json.load(f)
            except Exception as e:
                print(f"Error loading collections: {e}")
                self.collections = {}
        else:
            self.collections = {}
            
        self.updateCollectionsDisplay()
        
    def saveCollections(self):
        """Save collections to JSON file"""
        try:
            with open(self.collections_file, 'w') as f:
                json.dump(self.collections, f, indent=4)
        except Exception as e:
            print(f"Error saving collections: {e}")
            
    def updateCollectionsDisplay(self):
        """Update the display of collections"""
        # Clear existing thumbnails
        for i in reversed(range(self.collections_layout.count())):
            self.collections_layout.itemAt(i).widget().setParent(None)
            
        if not self.collections:
            self.scroll_area.hide()
            self.empty_label.show()
        else:
            self.empty_label.hide()
            self.scroll_area.show()
            
            # Add collection thumbnails
            cols = 4  # Number of columns
            for i, cd in enumerate(self.collections.items()):
                uuid, collection = cd
                row = i // cols
                col = i % cols
                
                thumbnail = CollectionThumbnail(uuid, collection, font=self.font)
                thumbnail.clicked.connect(lambda: self.openCollection(uuid, collection))
                thumbnail.collection_updated.connect(self.loadCollections)  # Refresh when updated
                self.collections_layout.addWidget(thumbnail, row, col)
                
    def sortCollections(self, sort_by):
        """Sort collections based on selected criteria"""
        sorted_items = []
    
        if sort_by == "Name":
            sorted_items = sorted(
                self.collections.items(),
                key=lambda x: x[1]['name'].lower()  # x[1] is the nested dictionary, get 'name' from it
            )
        elif sort_by == "Date Created":
            sorted_items = sorted(
                self.collections.items(),
                key=lambda x: x[1]['created_date'],
                reverse=True
            )
        elif sort_by == "Date Modified":
            sorted_items = sorted(
                self.collections.items(),
                key=lambda x: x[1]['last_updated'],
                reverse=True
            )
        elif sort_by == "Image Count":
            sorted_items = sorted(
                self.collections.items(),
                key=lambda x: x[1]['image_count'],
                reverse=True
            )
        
        # Convert sorted list of tuples back to dictionary
        self.collections = dict(sorted_items)
        self.updateCollectionsDisplay()
        
    def createNewCollection(self):
        """Create a new collection"""
        dialog = CreateCollectionDialog(self, font= self.font)
        if dialog.exec_() == QDialog.Accepted:
            collection_data = dialog.getCollectionData()
            
            # Count images in the selected folder
            image_count = self.countImagesInFolder(
                collection_data['folder'], 
                collection_data['subfolders']
            )
            collection_data['color'] = True
            collection_data['dino'] = False
            collection_data['clip'] = False
            collection_data['image_count'] = image_count
            
            # Add to collections
            uuid = str(uuid4())
            self.collections[uuid] = collection_data
            self.saveCollections()
            self.updateCollectionsDisplay()

            self.createColorIndex(uuid, collection_data)
            

    def createColorIndex(self, uuid, collection_data):
        from accessDBs import add_color
        """Create color index for a collection"""
        class IndexWorker(QThread):
            progress = pyqtSignal(int)
            finished = pyqtSignal()
            value_changed = pyqtSignal(int)  # Add signal for progress updates
            
            def __init__(self, key, folder, explore):  # Remove progress_dialog from constructor
                super().__init__()
                self.key = key
                self.folder = folder
                self.explore = explore
                
            def run(self):
                try:
                    # Create wrapper class to emit progress signals
                    class ProgressEmitter:
                        def __init__(self, signal):
                            self.signal = signal
                        def setValue(self, value):
                            self.signal.emit(value)
                            
                    progress_emitter = ProgressEmitter(self.value_changed)
                    add_color(self.key, self.folder, self.explore, progress=progress_emitter)
                    self.finished.emit()
                except Exception as e:
                    print(f"Error in worker thread: {e}")

        # Show progress dialog
        progress_dialog = QProgressDialog("Creating color index...", None, 0, collection_data["image_count"], self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowFlags(
            progress_dialog.windowFlags() & ~Qt.WindowCloseButtonHint
        )
        progress_dialog.setMinimumDuration(0)
        progress_dialog.show()
        
        # Start worker thread
        self.index_worker = IndexWorker(
            uuid, 
            collection_data['folder'], 
            collection_data['subfolders']
        )
        def x():
            progress_dialog.close()
            self.openCollection(uuid, collection_data)
        # Connect signals
        self.index_worker.value_changed.connect(progress_dialog.setValue)
        self.index_worker.finished.connect(x)
        self.index_worker.start()
            
    def countImagesInFolder(self, folder, include_subfolders):
        """Count image files in a folder"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'}
        count = 0
        
        try:
            if include_subfolders:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        if os.path.splitext(file.lower())[1] in image_extensions:
                            count += 1
            else:
                for file in os.listdir(folder):
                    if os.path.isfile(os.path.join(folder, file)):
                        if os.path.splitext(file.lower())[1] in image_extensions:
                            count += 1
        except Exception as e:
            print(f"Error counting images: {e}")
            
        return count
        
    def openCollection(self, uuid, collection_data):
        # Create gallery window without parent
        self.gallery_window = ImageGalleryApp(uuid, collection_data)  # Remove parent parameter
        
        # Set window flags to make it appear in taskbar
        self.gallery_window.setWindowFlags(Qt.Window)
        
        # Store reference to landing page instead of parent
        self.gallery_window.landing_page = self
        
        self.gallery_window.showMaximized()
        self.hide()
        
        self.gallery_window.setAttribute(Qt.WA_DeleteOnClose)
        self.gallery_window.destroyed.connect(self.showMaximized)


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')

    window = CollectionsLandingPage()
    window.show()

    class ImportThread(QThread):
        finished = pyqtSignal(object)
        error = pyqtSignal(str)

        def run(self):
            try:
                # Import in thread
                global ImageGalleryApp
                from gallery import ImageGalleryApp
                
                self.finished.emit(ImageGalleryApp)
            except Exception as e:
                self.error.emit(str(e))


    progress = QProgressDialog("Loading models...", None, 0, 0, parent=window)
    progress.setWindowTitle("Loading")
    progress.setWindowModality(Qt.WindowModal)
    progress.setCancelButton(None)  # Remove cancel button
    progress.setMinimumDuration(0)  # Show immediately
    progress.setFont(QFont(window.font, 11))
    progress.setWindowFlag(Qt.WindowCloseButtonHint, False)
    progress.setStyleSheet("""
        QProgressDialog {
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 12px;
        }
        QProgressBar {
            border: 1px solid #ccc;
            border-radius: 2px;
            text-align: center;
        }
    """)
    
    progress.show()
    # app.processEvents()

    # Create and start import thread
    import_thread = ImportThread()


    def on_import_finished(ImageGalleryApp):
        progress.setLabelText("Done. Welcome to Image Gallery!")
        QTimer.singleShot(750, progress.close)
        # progress.close()
        # globals()['ImageGalleryApp'] = ImageGalleryApp

    def on_import_error(error_msg):
        progress.close()
        QMessageBox.critical(window, "Error", f"Failed to load models: {error_msg}")
        sys.exit(1)

    import_thread.finished.connect(on_import_finished)
    import_thread.error.connect(on_import_error)
    import_thread.start()
    # global ImageGalleryApp
    # from gallery import ImageGalleryApp
    # progress.close()
    sys.exit(app.exec_())


if __name__ == "__main__":
    
    main()
    print("done")