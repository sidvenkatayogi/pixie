# TODO 
# make it auto scale to a good starting view
# fuck chromadb, restart with faiss

import sys
import os
import numpy as np
import random
import colorsys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsPixmapItem, QVBoxLayout, QWidget)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, pyqtSignal, QSize
import time

# from search_color import search
# from add_color import add
from accessDBs import add_color, search_color, add_visual, search_visual
from colors import get_dominant_colors

import PIL
from PIL import Image
from PIL.ImageQt import ImageQt # only works for PyQt6
 
from tqdm import tqdm

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gallery")
        self.setGeometry(100, 100, 1024, 768)

        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)

        # self.image_data = []
        self.image_data = {}
        self.STD_SIZE = 512
        self.STD_SPACE = self.STD_SIZE * 1.25
        
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.FPS = 48
        
        self.animation_timer.start(int(1/self.FPS * 1000))
        
        self.animation_time = 0.0

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.view)
        self.setCentralWidget(central_widget)

    def imageToQPixmap(self, images):
        pixmaps = []
        
        for image in tqdm(images, desc= "Scaling..."):
            pixmap = image.get("pixmap")

            if image.get("image") == Image:
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

            pixmaps.append(pixmap)
            
        return pixmaps

    def generate_dummy_image(self, size, color, text= ""):
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(color)

        painter = QPainter(image)
        painter.setPen(Qt.black) # Text color
        painter.setFont(QFont("Arial", 20))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, text)
        painter.end()

        return QPixmap.fromImage(image)

    def add_to_scene(self, x, y, image : QPixmap, h=10, s=255, l=128, r=0, initial_angle=0, direction=0):
        pixmap = image
        
        item = QGraphicsPixmapItem(pixmap)

        # center image on position
        item.setPos((-pixmap.width() / 2) + x, (-pixmap.height() / 2) + y)
        self.scene.addItem(item)
        
        base_speed = 1000  # degrees per frame

        # direction: (1 = clockwise, -1 = counterclockwise)
        w = base_speed * direction / (r + 1)# angular velocity
        
        self.image_data[item] = {'r': r,
                             'th_0': initial_angle,
                             'w': w,}

    def update_animation(self):
        self.animation_time += (int(1/self.FPS * 1000) / 1000) # 60 FPS
        
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

            self.add_to_scene(x=x, y=y, image=image, h=th, r=r, initial_angle=th, 
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
        # self.animation_timer.start(int(1/self.FPS * 1000))  # ~60 FPS (16ms intervals)

    # makes circular rings, but tries to order images in rings by hue
    def circlesh(self, images):
        imgs = images
        pixmaps = self.imageToQPixmap(imgs)
        images = []
        # get hue
        for image, pixmap in zip(imgs, pixmaps):
            l = []
            if "colors" in image:
                l = image["colors"]
            else:
                print(9)
                l = get_dominant_colors(Image.open(image["path"]))

            l = l.reshape(int(len(l)/4), 4)
            image = image["pixmap"]
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

            images.append({"pixmap": pixmap, "hue": avg_hue})

        # center image is added within loop
        r = 0
        # number of images in ring
        n = 1
        total = 0

        # ths is the thetas (angles) for each image in a ring
        # defined better at end of loop body
        ths = np.array([0])
        
        # every iteration of this loop is a new ring
        # this structure is because n is random and different for each ring
        while len(images) > 0:
            # list of images in the current ring
            imgs = []
            for i in range(n):
                total += 1
                if len(images) > 0:
                    imgs.append(images.pop(0))

            # sort by hue
            # this doesn't find the absolute best order-
            # -to minimize the distance from where the image should actually be based on hue (while evenly spacing images)
            # but it's a simple solution that adds a little structure to the ring order
            imgs.sort(key= lambda x: x["hue"])

            for image in imgs:
                # "pop" the first element/angle to put image on
                th = ths[0] % 360
                ths = np.delete(ths, 0)
                
                # instead of evenly spacing the images out, you can just use the hue as the angle
                # this doesn't create a clean circle but will show hue distribution better
                th = image["hue"] * 360

                x = r * np.cos(th / 360 * 2 * np.pi) * self.STD_SPACE
                y = -r * np.sin(th / 360 * 2 * np.pi) * self.STD_SPACE

                self.add_to_scene(x=x, y=y, image=image["pixmap"], h=th, r=r, initial_angle=th, 
                            direction= (int(r) % 2) * 2 - 1) # alternate rotation every ring
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
        # self.animation_timer.start(int(1/self.FPS * 1000))  # ~60 FPS (16ms intervals)
            

    def hexagons(self, images):
        images = self.imageToQPixmap(images)

        # center image @ (0, 0)
        self.add_to_scene(x= 0, y= 0, image= images[0])

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

                self.add_to_scene(x=x, y=y, image=image, h=th, 
                           r=radius, initial_angle=th, direction= 1)
                
                # QApplication.processEvents()
        # self.animation_timer.start(int(1/self.FPS * 1000))  # ~60 FPS (16ms intervals)


if __name__ == "__main__":
    # start_time = time.time()
    # add_content(name= "pinterest", folder_path= r"gallery-dl\pinterest\sidvenkatayogii\Reference")
    # end_time = time.time()
    # print(f"Elapsed time: {end_time - start_time:.3f} seconds")

    app = QApplication(sys.argv)
    window = ImageGalleryApp()
    window.show()
    
    while window.animation_time < 3:
        app.processEvents()

    print("out")
    # window.animation_timer.start()
    # window.animation_timer.stop()
    
    start_time = time.time()
    # images = search_color("pinterest", path= r"gallery-dl\pinterest\sidvenkatayogii\Reference\pinterest_921478773764303738.jpg", k = 500)
    # images = search_content("pinterest", query_image_path= r"gallery-dl\pinterest\sidvenkatayogii\Reference\pinterest_921478773764303738.jpg", k = 5)
    images = search_visual("pinterest", file_path= r"images\alariko\C8wimbaqyU5.jpg", k = 300)
    end_time = time.time()
    print(f"Elapsed time: {end_time - start_time:.3f} seconds")
    # creates PyQt6 QImage
    # imgqt = ImageQt(images[0])
    # qimage = imgqt.copy()
    # for i in images[1:]:
    #     print(i[1])



    window.circles(images)
    # print("done")
    # window.hexagons(images)
    # # window.circles(np.arange(0, 300))
    # # window.hexagons(np.arange(0, 300))
    sys.exit(app.exec_())