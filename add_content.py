from PIL import Image
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import torch
import os

# db_path = ""

client = chromadb.PersistentClient()

import torch

emb_fn = OpenCLIPEmbeddingFunction(model_name= "ViT-B-32",
                                   checkpoint= "laion2b_s34b_b79k",
                                   device= "cuda" if torch.cuda.is_available() else "cpu")

collection = client.get_or_create_collection(
    name= "multimodal_collection",
    embedding_function= emb_fn,
    data_loader= ImageLoader()
    )

def add_images_to_collection(folder_path, explore = False):

    image_paths = []

    # [os.path.join(folder_path, file) for file in os.listdir(folder_path) 
    #                if os.path.isfile(os.path.join(folder_path, file)) and file.lower().endswith((""))]
    
    for file in tqdm(os.listdir(folder_path), desc= f"Exploring... ({folder_path})", disable= not explore):
        # print(folder_path)
        file_path = os.path.join(folder_path, file)
        if explore and os.path.isdir(file_path):
            add_images_to_collection(file_path, explore)
        elif os.path.isfile(file_path) and file.lower().endswith((".png", ".jpg", ".jpeg")):
            image_paths.append(file_path)

    if (len(image_paths) > 0):
        for image_path in tqdm(image_paths, desc= f"Creating Embeddings and Adding to DB... ({folder_path})"):
            try:
                image = np.array(Image.open(image_path))
                collection.add(
                    # ids= [os.path.basename(image_path)],
                    ids= [image_path], # id is 
                    images= [image]
                )
            except Exception as e:
                print(f"Error processing {image_path}: {e}")


image_folder_path= "images"

add_images_to_collection(image_folder_path, explore= True)