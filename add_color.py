import colors as c
import numpy as np
import os
from PIL import Image
from imagehash import colorhash
from hashDB import HashDB
from vectorDB import VectorDB
import time
from tqdm import tqdm

def add(dir, name):
    db = VectorDB(name= name)
    explore = False
    image_paths = []
    for file in tqdm(os.listdir(dir), desc= f"Exploring... ({dir})", disable= not explore):
        # print(folder_path)
        file_path = os.path.join(dir, file)
        if os.path.isfile(file_path) and file.lower().endswith((".png", ".jpg", ".jpeg")):
            image_paths.append(file_path)

    for path in tqdm(image_paths, desc= f"Creating Embeddings and Adding to DB... ({dir})"):
        try:
            if type(db) == VectorDB:
                cols = c.get_dominant_colors(Image.open(path, mode= "r"), num_colors= 3)
                db.add_vector(id= path,vec= cols)
            elif type(db) == HashDB:
                hash = colorhash(Image.open(path), binbits = 7)
                db.add_hash(path, hash)
        except Exception as e:
            print(f"error with {path} : {e}")
    db.save_DB()



if __name__ == "__main__":
    dir = r"gallery-dl\pinterest\sidvenkatayogii\Reference"

    # db = HashDB()

    add(dir, "pinterest")
