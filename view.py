from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter

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