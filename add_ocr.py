from PIL import Image
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import torch
import os
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import json

# db_path = ""

client = chromadb.PersistentClient()

# emb_fn = SentenceTransformerEmbeddingFunction(
#     model_name="all-MiniLM-L6-v2"
# )

predictor = ocr_predictor(
    det_arch="db_mobilenet_v3_large",
    reco_arch="crnn_mobilenet_v3_small",
    pretrained=True,
)

collection = client.get_or_create_collection(
    name= "textual_collection",
    # embedding_function= emb_fn
    )

images = {}

def add_images_to_collection(folder_path, explore = False):

    image_paths = []
    
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
                image = DocumentFile.from_images(image_path)
                result = predictor(image)
                text = result.render()
                if text != "":
                    collection.add(
                        ids= [image_path],
                        documents= [text],
                        # metadatas= [result.export()[0]]
                    )
                    images[image_path] = result.export()
            except Exception as e:
                print(f"Error processing {image_path}: {e}")


image_folder_path= "images"

add_images_to_collection(image_folder_path, explore= True)

with open("boxes.json", "w") as file: 
        json.dump(images, file)