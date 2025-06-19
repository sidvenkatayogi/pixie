import colors as c
import numpy as np
import os
from PIL import Image
from imagehash import colorhash
from hashDB import HashDB
from vectorDB import VectorDB
import time

db = VectorDB.get_DB(name= "colors")

k = 5
query = Image.new('RGB', (10, 10), (204, 12, 12))
# path = ""
# query = Image.open(path)

def search(query : str, k = 5):
    Image.open(query)
    images = None
    if type(db) == VectorDB:
        images = db.knn(c.get_dominant_colors(query, num_colors= 3), k= k)
    elif type(db) == HashDB:
        images = db.knn(colorhash(query, binbits = 7), k= k)
    return images


# images = search(query, k)



# for img, distance in images:
#     print(img + " " + str(distance))
#     image = Image.open(img)
#     image.show(title=os.path.basename(img))
#     time.sleep(1)
