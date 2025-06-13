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

cont = 1
while cont < 3:
    query = input("Search: ")

    print("Getting results...")

    results= collection.query(query_texts=[query], n_results= 5, include= ["distances"])
    # print(results["metadatas"])

    for image_id, distance in zip(results["ids"][0], results["distances"][0]):
        image_path = image_id
        # img = Image.open(image_path)
        data[image_path]
        # plt.imshow(np.array(img))
        # plt.title(f"{image_path} : {distance}")
        # plt.show()
        print(f"{image_path} : {distance}")



        original_image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(original_image)

        ocr_data = data[image_path]

        # 3. Define visualization parameters
        bbox_color = (255, 0, 0)  # Red for bounding boxes
        text_color = (0, 0, 0)   # Black for text
        line_width = 2           # Thickness of bounding box lines

        font_size = 15
        font = ImageFont.truetype("arial.ttf", font_size)

        page_data = ocr_data["pages"][0] # Access the first page's data
        img_width, img_height = original_image.size
        for block in page_data.get("blocks", []):
            for line in block.get("lines", []):
                for word in line.get("words", []):
                    # Get relative coordinates [ymin, xmin, ymax, xmax] from doctr
                    # ymin_rel, xmin_rel, ymax_rel, xmax_rel = word["geometry"]
                    (xmin_rel, ymin_rel), (xmax_rel, ymax_rel) = word["geometry"]

                    # Convert relative coordinates to absolute pixel coordinates
                    # Note: doctr's geometry is relative to its detected page dimensions.
                    # We convert them to the actual image dimensions.
                    xmin_abs = int(xmin_rel * img_width)
                    ymin_abs = int(ymin_rel * img_height)
                    xmax_abs = int(xmax_rel * img_width)
                    ymax_abs = int(ymax_rel * img_height)

                    # Draw bounding box
                    draw.rectangle(
                        [(xmin_abs, ymin_abs), (xmax_abs, ymax_abs)],
                        outline=bbox_color,
                        width=line_width
                    )

                    # Draw text
                    word_text = word["value"]
                    # Position text slightly above the bounding box
                    text_x = xmin_abs
                    text_y = ymin_abs - font_size - 2

                    # Adjust text position if it goes off the top of the image
                    if text_y < 0:
                        text_y = ymax_abs + 2 # Place below the box if no space above

                    draw.text((text_x, text_y), word_text, fill=text_color, font=font)

        # 5. Save the visualized image
        original_image.show()

        cont = int(input("ENTER (1) for next image, (2) to next search, or (3) to exit: "))
        print(cont)
        if cont == 2:
            break
print("done")