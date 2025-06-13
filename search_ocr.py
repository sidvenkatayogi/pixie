# from PIL import Image
from PIL import Image, ImageDraw, ImageFont
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import os
import torch
import matplotlib.pyplot as plt
import timeit
import json
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

client = chromadb.PersistentClient()

# emb_fn = SentenceTransformerEmbeddingFunction(
#     model_name="all-MiniLM-L6-v2"
# )

collection = client.get_collection(
    name= "textual_collection",
    # embedding_function= emb_fn,
    )

with open('boxes.json', 'r') as file:
    data = json.load(file)


predictor = ocr_predictor(
    det_arch="db_mobilenet_v3_large",
    reco_arch="crnn_mobilenet_v3_large",
    pretrained=True,
)

cont = 1


while cont < 3:
    query = input("Search: ")

    print("Getting results...")

    results= collection.query(query_texts=[query], n_results= 5, include= ["distances"])
    # print(results["metadatas"])

    for image_id, distance in zip(results["ids"][0], results["distances"][0]):
        image_path = image_id
        # img = Image.open(image_path)
        # data[image_path]
        # plt.imshow(np.array(img))
        # plt.title(f"{image_path} : {distance}")
        # plt.show()
        print(f"{image_path} : {distance}")
        image = DocumentFile.from_images(image_path)
        result = predictor(image)
        result.show()

        cont = int(input("ENTER (1) for next image, (2) to next search, or (3) to exit: "))
        print(cont)
        if cont == 2:
            break
print("done")