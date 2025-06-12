import colors as c
import numpy as np
import os
from PIL import Image
from imagehash import colorhash
from hashDB import HashDB
from vectorDB import VectorDB
import time



def add(dir, db):
    for f in os.listdir(dir):
        path = os.path.join(dir, f)
        if os.path.isdir(path):
            add(path, db)
        else:
            if type(db) == VectorDB:
                cols = c.get_dominant_colors(Image.open(path), num_colors= 3)
                db.add_vector(id= path,vec= cols)
            elif type(db) == HashDB:
                hash = colorhash(Image.open(path), binbits = 7)
                db.add_hash(path, hash)

dir = "images"

db = VectorDB()
# db = HashDB()

add(dir, db)

k = 5

query = Image.new('RGB', (10, 10), (255, 255, 255))
# path = ""
# query = Image.open(path)

if type(db) == VectorDB:
    images = db.knn(c.get_dominant_colors(query, num_colors= 3), k= k)
elif type(db) == HashDB:
    images = db.knn(colorhash(query, binbits = 7), k= k)
    
for img, distance in images:
    print(img + " " + str(distance))
    image = Image.open(img)
    image.show(title=os.path.basename(img))
    time.sleep(1)
    # input()
