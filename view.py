from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtGui import QPainter
import time
from collections import deque
import numpy as np

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent_window, fps=60):
        super().__init__(scene)
        self.parent_window = parent_window
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # smooth rendering and scaling
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.NoDrag) # custom

        # zoom/pan about mouse cursor
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        self.panning = False
        self.last_pos = QPointF()

        # kinetic panning variables
        self.velocity = QPointF(0, 0)
        self.kinetic_timer = QTimer()
        self.kinetic_timer.timeout.connect(self.update_kinetic_pan)
        self.FPS = fps
        self.kinetic_timer.setInterval(int(1000/self.FPS))
        
        self.mouse_history = deque(maxlen=5)  # Keep last 5 positions
        self.last_time = 0
        
        self.friction = 0.95
        self.min_velocity = 1  # stop kinetic panning below this velocity
        self.velocity_scale = 0.5

        self.centerOn(0, 0)

    # start panning
    def mousePressEvent(self, event):
        if hasattr(self.parent_window, 'zoom_animating') and self.parent_window.zoom_animating:
            self.parent_window.zoom_animation_timer.stop()
            self.parent_window.zoom_animating = False

        if event.button() == Qt.LeftButton: # use left button for panning
            # stop any ongoing kinetic panning
            self.kinetic_timer.stop()
            self.velocity = QPointF(0, 0)
            
            self.panning = True
            self.last_pos = event.pos()
            self.last_time = time.time()
            
            # clear mouse history and start tracking
            self.mouse_history.clear()
            self.mouse_history.append((event.pos(), self.last_time))
            
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    # track mouse position and pan
    def mouseMoveEvent(self, event):
        if self.panning:
            current_time = time.time()
            
            # add current position to history
            self.mouse_history.append((event.pos(), current_time))
            
            old_scene_pos = self.mapToScene(self.last_pos)
            new_scene_pos = self.mapToScene(event.pos())
            
            delta = new_scene_pos - old_scene_pos
            
            # pan in opposite direction
            current_center = self.mapToScene(self.viewport().rect().center())
            new_center = current_center - delta
            self.centerOn(new_center)
            
            self.last_pos = event.pos()
            self.last_time = current_time
            event.accept()

    # stop panning when mouse released
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            
            self.calculate_velocity()
            
            if np.sqrt(self.velocity.x()**2 + self.velocity.y()**2) > self.min_velocity:
                self.kinetic_timer.start()
            
            event.accept()

    # calculate velocity from recent mouse movement
    def calculate_velocity(self):
        
        if len(self.mouse_history) < 2:
            self.velocity = QPointF(0, 0)
            return
        
        # calculate average velocity
        recent_positions = list(self.mouse_history)[-3:]  # last 3 positions
        
        if len(recent_positions) < 2:
            self.velocity = QPointF(0, 0)
            return
        
        start_pos, start_time = recent_positions[0]
        end_pos, end_time = recent_positions[-1]
        
        time_diff = end_time - start_time
        if time_diff <= 0:
            self.velocity = QPointF(0, 0)
            return
        
        start_scene = self.mapToScene(start_pos)
        end_scene = self.mapToScene(end_pos)
        
        velocity_x = (end_scene.x() - start_scene.x()) / time_diff
        velocity_y = (end_scene.y() - start_scene.y()) / time_diff
        
        self.velocity = QPointF(-velocity_x * self.velocity_scale, 
                               -velocity_y * self.velocity_scale)

    def update_kinetic_pan(self):
        self.velocity *= self.friction
        # print(self.velocity)
        # stop if velocity is too small
        if np.sqrt(self.velocity.x()**2 + self.velocity.y()**2) < self.min_velocity:
            self.kinetic_timer.stop()
            self.velocity = QPointF(0, 0)
            return
        
        dt = 1.0 / self.FPS
        
        current_center = self.mapToScene(self.viewport().rect().center())
        new_center = current_center + self.velocity * dt
        self.centerOn(new_center)

    # zoom with mouse wheel
    def wheelEvent(self, event):
        if hasattr(self.parent_window, 'zoom_animating') and self.parent_window.zoom_animating:
            self.parent_window.zoom_animation_timer.stop()
            self.parent_window.zoom_animating = False

        zoom_factor = 1.25

        mouse_scene_pos = self.mapToScene(event.pos())

        # apply zoom
        if event.angleDelta().y() > 0: # scroll up (zoom in)
            self.scale(zoom_factor, zoom_factor)
        else: # scroll down (zoom out)
            self.scale(1 / zoom_factor, 1 / zoom_factor)
        
        new_mouse_scene_pos = self.mapToScene(event.pos())
        
        delta = new_mouse_scene_pos - mouse_scene_pos
        current_center = self.mapToScene(self.viewport().rect().center())
        new_center = current_center - delta
        self.centerOn(new_center)
        
        event.accept()