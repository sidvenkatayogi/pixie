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
# db_path = ""

client = None
emb_fn = None

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
                                   device= "cuda" if torch.cuda.is_available() else "cpu")
    
    collection = client.get_or_create_collection(name= name,
                                                embedding_function= emb_fn,
                                                data_loader= ImageLoader())
    if (len(image_paths) > 0):
        for path in tqdm(image_paths, desc= f"Creating Embeddings and Adding to DB..."):
            try:
                image = np.array(Image.open(path))
                collection.add(
                    ids= [path],
                    images= [image]
                )
            except Exception as e:
                print(f"Error processing {path}: {e}")


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
    
    if not client:
        client = chromadb.PersistentClient()
    if not emb_fn:
        emb_fn = OpenCLIPEmbeddingFunction(model_name= "ViT-B-32",
                                           checkpoint= "laion2b_s34b_b79k",
                                           device= "cuda" if torch.cuda.is_available() else "cpu")
        
    collection = client.get_or_create_collection(name= name,
                                                embedding_function= emb_fn,
                                                data_loader= ImageLoader())
    
    results = []
    if query_image:
        results = collection.query(query_images=[query_image], n_results= k, include= ["distances"])
    elif query_text:
        results = collection.query(query_texts=[query_text], n_results= k, include= ["distances"])
    elif query_image_path:
        results = collection.query(query_images=[Image.open(query_image_path, read= "r")], n_results= k, include= ["distances"])
    else:
        raise Exception("Enter a text query, PIL Image, or image path")
    
    images = []
    for r in results:
        images.append(Image.open(r, mode="r"))

    return images


def search_color(name, rgb= None, image= None, path= None, k = 5):
    query = None
    query_image = None

    if rgb and len(rgb) == 3:
        query = rgb
        query_image = Image.new('RGB', (10, 10), rgb)
    elif image:
        query_image = image
    elif path:
        query_image = Image.open(query, read= "r")
    else:
        raise Exception("Enter RGB values ((R, G, B)), PIL Image, or image path (str)")

    db = VectorDB.get_DB(name= name)

    images = []

    # if k == None:
    #     k = len(db)
    if type(db) == VectorDB:
        images = db.knn(get_dominant_colors(query_image, num_colors= 3), k= k)
    elif type(db) == HashDB:
        images = db.knn(colorhash(query_image, binbits = 7), k= k)

    for i, image in enumerate(images):
        images[i][0] = Image.open(image[0])
        
    return [query_image] + images