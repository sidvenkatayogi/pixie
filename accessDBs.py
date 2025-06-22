from PIL import Image
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import torch
import os
from imagehash import colorhash
from vectorDB import VectorDB
from hashDB import HashDB
from colors import get_dominant_colors
import torch
from PyQt5.QtGui import QPixmap, QImage
# db_path = ""

client = None
emb_fn = None

def imageToQPixmap(image : Image):
    if image.mode != 'RGB':
        image = image.convert('RGB')
        
    w, h = image.size

    data = image.tobytes("raw", "RGB")
    qimage = QImage(data, w, h, w * 3, QImage.Format_RGB888)

    return QPixmap.fromImage(qimage)

def get_files(folder_path, explore = False):
    image_paths = []
    for file in tqdm(os.listdir(folder_path), desc= f"Exploring... ({folder_path})", disable= not explore):
        # print(folder_path)
        file_path = os.path.join(folder_path, file)
        if explore and os.path.isdir(file_path):
            image_paths += get_files(file_path, True)
        elif os.path.isfile(file_path) and file.lower().endswith((".png", ".jpg", ".jpeg")):
            image_paths.append(file_path)

    return image_paths


def add_content(name, folder_path, explore= False):
    image_paths = []
    image_paths = get_files(folder_path, explore)

    client = chromadb.PersistentClient()
    emb_fn = OpenCLIPEmbeddingFunction(model_name= "ViT-B-32",
                                   checkpoint= "laion2b_s34b_b79k",
                                #    device= "cuda" if torch.cuda.is_available() else "cpu")
                                   device= "cpu")
    
    collection = client.get_or_create_collection(name= name,
                                                embedding_function= emb_fn,
                                                data_loader= ImageLoader())
    print("hi")
    if (len(image_paths) > 0):
        for path in tqdm(image_paths, desc= f"Creating Embeddings and Adding to DB..."):
            image = np.array(Image.open(path))
            collection.add(
                ids= [path],
                images= [image]
            )
            # print(path)
    print("bye")
            


def add_color(name, folder_path, explore= False):
    image_paths = []
    image_paths = get_files(folder_path, explore)

    db = None
    try:
        db = VectorDB.get_DB(name= name)
    except Exception as e:
        db = VectorDB(name= name)

    for path in tqdm(image_paths, desc= f"Creating Embeddings and Adding to DB..."):
        try:
            if type(db) == VectorDB:
                if not db.get_vector(path):
                    cols = get_dominant_colors(Image.open(path, mode= "r"), num_colors= 3)
                    db.add_vector(id= path,vec= cols)
            elif type(db) == HashDB:
                hash = colorhash(Image.open(path), binbits = 7)
                db.add_hash(path, hash)
        except Exception as e:
            print(f"Error processing {path} : {e}")
    db.save_DB()


def search_content(name, query_text= None, query_image= None, query_image_path= None, k = 5):
    client = chromadb.PersistentClient()
    collection = client.get_or_create_collection(name= name,)
                                                # embedding_function= emb_fn,
                                                # data_loader= ImageLoader())
    
    results = []
    print(f"Collection '{name}' count: {collection.count()}")
    if query_image:
        results = collection.query(query_images=[query_image], n_results= k, include= ["distances"])
    elif query_text:
        results = collection.query(query_texts=[query_text], n_results= k, include= ["distances"])
    elif query_image_path:
        results = collection.query(query_images=[np.array(Image.open(query_image_path, mode= "r"))], n_results= k, include= ["distances"])
    else:
        raise Exception("Enter a text query, PIL Image, or image path")
    
    images = [[] * k]
    print(results)
    for i, r in enumerate(results["ids"]):
        query_pixmap = imageToQPixmap(Image.open(r, mode="r"))
        images[i]["pixmap"] = query_pixmap
        images[i]["path"] = r

    for i, d in enumerate(results["distances"]):
        images[i]["distance"] = d

    return images


def search_color(name, rgb= None, image= None, path= None, k = 5):
    query_image = None
    query_pixmap = None

    if rgb and len(rgb) == 3:
        query_image = Image.new('RGB', (10, 10), rgb)
        query_pixmap = imageToQPixmap(query_image)
    elif image:
        query_image = image
        query_pixmap = imageToQPixmap(query_image)
    elif path:
        query_image = Image.open(path, mode= "r")
        query_pixmap = QPixmap(path)
    else:
        raise Exception("Enter RGB values ((R, G, B)), PIL Image, or image path (str)")

    db = VectorDB.get_DB(name= name)

    images = []

    # if k == None:
    #     k = len(db)
    vec = []
    if type(db) == VectorDB:
        vec = get_dominant_colors(query_image, num_colors= 3)
        images = db.knn(vec, k= k)
    elif type(db) == HashDB:
        images = db.knn(colorhash(query_image, binbits = 7), k= k)

    for i, image in enumerate(tqdm(images, desc= "Loading Pixmaps...")):
        # images[i][0] = Image.open(image[0])
        images[i]["pixmap"] = QPixmap(image["path"])

        
    return [{"pixmap": query_pixmap, "distance": 0, "colors": vec}] + images

if __name__ == "__main__":
    print(search_content(name= "pinterest", query_text= "water"))
