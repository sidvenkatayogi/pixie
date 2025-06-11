from PIL import Image
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import os
import torch
import matplotlib.pyplot as plt
import timeit

client = chromadb.PersistentClient()

emb_fn = OpenCLIPEmbeddingFunction(model_name= "ViT-B-32",
                                   checkpoint= "laion2b_s34b_b79k",
                                   device= "cuda" if torch.cuda.is_available() else "cpu")

collection = client.get_collection(
    name= "multimodal_collection",
    embedding_function= emb_fn,
    data_loader= ImageLoader()
    )

cont = 1
while cont < 3:
    query = input("Search: ")

    print("Getting results...")

    results= collection.query(query_texts=[query], n_results= 5, include= ["distances"])

    for image_id, distance in zip(results["ids"][0], results["distances"][0]):
        image_path = image_id
        img = Image.open(image_path)
        
        plt.imshow(np.array(img))
        plt.title(f"{image_path} : {distance}")
        plt.show()

        cont = int(input("ENTER (1) for next image, (2) to next search, or (3) to exit: "))
        print(cont)
        if cont == 2:
            break
print("done")
