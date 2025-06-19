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

db = VectorDB(name= "colors")
# db = HashDB()

add(dir, db)

db.save_DB()
