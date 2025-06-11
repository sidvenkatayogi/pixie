from PIL import Image
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import os

import matplotlib.pyplot as plt

# db_path = ""

# client = chromadb.PersistentClient(path=db_path)
client = chromadb.PersistentClient()

collection = client.get_or_create_collection(
    name= "multimodal_collection",
    embedding_function= OpenCLIPEmbeddingFunction(),
    data_loader= ImageLoader()
    )

query = input("Search: ")

print("Getting results...")

results= collection.query(query_texts=[query], n_results= 5, include= ["distances"])
# print(results)
for image_id, distance in zip(results["ids"][0], results["distances"][0]):
    image_path = image_id
    img = Image.open(image_path)
    
    plt.imshow(np.array(img))
    plt.title(f"{image_path} : {distance}")
    plt.show()
    cont = input("ENTER (1) for next image, or (2) to exit: ")
    if cont == "2":
        break
print("done")


