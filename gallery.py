import sys
import os
import numpy as np
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout, QWidget)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF
import time
import search_color
class CustomGraphicsView(QGraphicsView):
    """
    A custom QGraphicsView that enables interactive panning and zooming.
    """
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing) # For smoother rendering
        self.setRenderHint(QPainter.SmoothPixmapTransform) # For smoother image scaling

        # Set up interactive features
        self.setDragMode(QGraphicsView.NoDrag) # Initial drag mode
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse) # Zoom/Pan around mouse cursor
        # self.setTransformationAnchor(QGraphicsView.NoAnchor) # Zoom/Pan around mouse cursor
        # self.setResizeAnchor(QGraphicsView.AnchorUnderMouse) # Resize around mouse cursor

        self.panning = False
        self.last_pos = QPointF()

        # Set the initial view to be centered around (0,0) and perhaps scale it
        # The scene rect is typically infinite, but we can set a hint.
        # self.scene().setSceneRect(-4000, -4000, 8000, 8000) # Example large scene area
        self.centerOn(0, 0) # Center the view on the origin

    def mousePressEvent(self, event):
        """
        Starts panning when the left mouse button is pressed.
        """
        if event.button() == Qt.LeftButton: # Use left button for panning
            self.panning = True
            self.last_pos = event.pos()
            print
            self.setCursor(Qt.ClosedHandCursor) # Change cursor to indicate dragging
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Performs panning if the panning flag is active.
        """
        if self.panning:
            # Calculate the difference in scene coordinates
            old_scene_pos = self.mapToScene(self.last_pos)
            new_scene_pos = self.mapToScene(event.pos())
            delta = old_scene_pos - new_scene_pos
            
            self.last_pos = event.pos()
            
            # Get current center and adjust it
            current_center = self.mapToScene(self.viewport().rect().center())
            new_center = current_center + delta
            self.centerOn(new_center)
            
            event.accept()
        # else:
        #     super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Stops panning when the left mouse button is released.
        """
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor) # Restore cursor
            event.accept()
        # else:
        #     super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """
        Handles zooming using the mouse wheel.
        """
        zoom_in_factor = 1.25 # How much to zoom in/out
        zoom_out_factor = 1 / zoom_in_factor

        # Determine zoom factor based on wheel direction
        if event.angleDelta().y() > 0: # Scroll up (zoom in)
            zoom_factor = zoom_in_factor
        else: # Scroll down (zoom out)
            zoom_factor = zoom_out_factor

        # Get the scene position under the mouse before zooming
        mouse_scene_pos = self.mapToScene(event.pos())
        
        # Apply the scaling transformation
        self.scale(zoom_factor, zoom_factor)
        
        # Get the scene position under the mouse after zooming
        new_mouse_scene_pos = self.mapToScene(event.pos())
        
        # Calculate the difference and adjust the view center
        delta = new_mouse_scene_pos - mouse_scene_pos
        current_center = self.mapToScene(self.viewport().rect().center())
        new_center = current_center - delta
        self.centerOn(new_center)
        
        event.accept()



class ImageGalleryApp(QMainWindow):
    """
    Main application window for the image gallery.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive Image Gallery")
        self.setGeometry(100, 100, 1024, 768) # Initial window size

        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)

        # self.setup_images()
        # self.hex_spiral(np.arange(0, 580))

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.view)
        self.setCentralWidget(central_widget)

    def generate_dummy_image(self, size, text, color):
        """
        Generates a QPixmap with a specific size, text, and background color.
        This avoids needing external image files for the example.
        """
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(color) # Fill with background color

        painter = QPainter(image)
        painter.setPen(Qt.black) # Text color
        font = QFont("Arial", 20)
        painter.setFont(font)
        text_rect = QRectF(0, 0, size, size)
        painter.drawText(text_rect, Qt.AlignCenter, text)
        painter.end()

        return QPixmap.fromImage(image)

    def setup_images(self):
        """
        Adds dummy images to the scene at fixed coordinates.
        The (0,0) coordinate is the center of your scene.
        """
        # Example images at different fixed coordinates
        # Image 1: At (0, 0) - the center of the coordinate space
        pixmap1 = self.generate_dummy_image(150, "Image 1 (0,0)", QColor(255, 180, 180))
        item1 = QGraphicsPixmapItem(pixmap1)
        item1.setPos(-pixmap1.width() / 2, -pixmap1.height() / 2) # Center the image at (0,0)
        self.scene.addItem(item1)

        # Image 2: At (500, 200)
        pixmap2 = self.generate_dummy_image(200, "Image 2 (500,200)", QColor(180, 255, 180))
        item2 = QGraphicsPixmapItem(pixmap2)
        item2.setPos(500, 200)
        self.scene.addItem(item2)

        # Image 3: At (-300, 400)
        pixmap3 = self.generate_dummy_image(100, "Image 3 (-300,400)", QColor(180, 180, 255))
        item3 = QGraphicsPixmapItem(pixmap3)
        item3.setPos(-300, 400)
        self.scene.addItem(item3)

        # Image 4: At (700, -500)
        pixmap4 = self.generate_dummy_image(180, "Image 4 (700,-500)", QColor(255, 255, 180))
        item4 = QGraphicsPixmapItem(pixmap4)
        item4.setPos(700, -500)
        self.scene.addItem(item4)

        # Image 5: At (-800, -100)
        pixmap5 = self.generate_dummy_image(120, "Image 5 (-800,-100)", QColor(255, 180, 255))
        item5 = QGraphicsPixmapItem(pixmap5)
        item5.setPos(-800, -100)
        self.scene.addItem(item5)

        print(f"Added {len(self.scene.items())} images to the scene.")
        print("Scene origin (0,0) is in the center of the initial view.")
        print("Use left mouse button to drag/pan, mouse wheel to zoom.")

    def render(self, size, x, y, name, h = 10, s = 255, l = 128):
        color = QColor()
        color.setHsl(int(h), int(s), int(l), alpha=255)
        # pixmap = self.generate_dummy_image(size, f"{name} ({x},{y})", color)
        pixmap = self.generate_dummy_image(size, f"", color)
        item = QGraphicsPixmapItem(pixmap)
        
        item.setPos((-pixmap.width() / 2) + x, (-pixmap.height() / 2) + y)
        self.scene.addItem(item)
        # print(f"rendered: {name} ({x},{y})")

    def hex_spiral(self, images):
        sq = 256
        # self.render(sq, images[0][0], last_pos[0], last_pos[1])
        self.render(sq, 0, 0, 0)
        level = 0
        for level in range(1, int(np.ceil((-3 + np.sqrt(12 * len(images) - 3)) / 6) + 1)):
            sides = []
            for c in range(0, 6):
                sides.append(list(range((c * level) + 1, ((c+1) * level) + 1)))

            # print(sides)
            print(f"level {level}")
            h = 0

            start = (level - 1) * level * 3 + 1
            end = min(start + level * 6, len(images))
            for i, image in enumerate(images[start : end]):
                if i % 6 == 0:
                    random.shuffle(sides)
                    # pass

                idx = random.randint(0, len(sides[i % 6]) - 1)
                # idx = 0
                place = sides[i % 6].pop(idx)


                placem = place % level
                x, y = 0, 0
                if place <= level: # tr diagonal
                    x = (level * sq) - ((place - 1) * (sq / 2))
                    y = -(place - 1) * sq
                elif place <= level * 2: # t line
                    x = level * sq/2 - (place - level - 1) * sq
                    y = -level * sq
                elif place <= level * 3: # tl diagonal
                    x = -(level * sq/2) - ((place - (level * 2) - 1)) * (sq / 2)
                    y = -level * sq + (place - (level * 2) - 1) * sq
                elif place <= level * 4: # bl diagonal
                    x = -level * sq + (place - (level * 3) - 1) * sq/2
                    y = (place - (level * 3) - 1) * sq
                elif place <= level * 5: # b line
                    x = -level * sq / 2 + (place - (level * 4) - 1) * sq
                    y = level * sq
                elif place <= level * 6: # br diagonal
                    x = level * sq/2 + (place - (level * 5) - 1) * sq/2
                    y = level * sq - (place - (level * 5) - 1) * sq

                h = place / (level * 6) * 359

                # h %= 360

                self.render(size=sq, x=x, y=y, name=image, h= h)
                
                QApplication.processEvents()
                # time.sleep(0.003)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageGalleryApp()
    window.show()
    window.hex_spiral(np.arange(0, 102700))
    sys.exit(app.exec_())

