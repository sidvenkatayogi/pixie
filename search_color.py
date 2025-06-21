import colors as c
import numpy as np
import os
from PIL import Image
from imagehash import colorhash
from hashDB import HashDB
from vectorDB import VectorDB
import time

regex = r"\((\d+),\s+(\d+),\s+(\d+)\)"

def search(rgb= None, path= None, k = None):
    query = None
    query_image = None
    if rgb and len(rgb) == 3:
        query = rgb
        query_image = Image.new('RGB', (10, 10), rgb)
    elif path:
        query = path
        query_image = Image.open(path)
    else:
        raise Exception("Enter RGB values or image path")

    db = VectorDB.get_DB(name= "colors")

    images = None
    if k == None:
        k = len(db)
    if type(db) == VectorDB:
        images = db.knn(c.get_dominant_colors(query_image, num_colors= 3), k= k)
    elif type(db) == HashDB:
        images = db.knn(colorhash(query_image, binbits = 7), k= k)
    return [query] + images



if __name__ == "__main__":
    k = 5
    query = Image.new('RGB', (10, 10), (204, 12, 12))
    path = ""
    query = Image.open(path)
    images = search(query, k)

    for img, distance in images:
        print(img + " " + str(distance))
        image = Image.open(img)
        image.show(title=os.path.basename(img))
        input()
    #     time.sleep(1)