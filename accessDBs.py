from PIL import Image
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import numpy as np
from tqdm import tqdm
import torch
import torchvision.transforms.v2 as tfms
import os
from imagehash import colorhash
from vectorDB import VectorDB
from hashDB import HashDB
from colors import get_dominant_colors
import torch
import faiss
import json
import time
import open_clip
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

dino = torch.hub.load('facebookresearch/dino:main', 'dino_vits16')
device = 'cuda' if torch.cuda.is_available() else 'cpu'

transform = tfms.Compose([
    tfms.Resize(size= (224, 224), interpolation= 1),
    # tfms.CenterCrop(224),
    tfms.ToImage(),
    tfms.ToDtype(torch.float32, scale=True),
    tfms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


# open_clip.list_pretrained()
open_clip_model_name = "ViT-B-32"
open_clip_pretrained_weights = "laion2b_s34b_b79k"

clip_model, clip_preprocess, clip_tokenizer = open_clip.create_model_and_transforms(
    open_clip_model_name,
    pretrained=open_clip_pretrained_weights,
    device=device
)


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


def add_visual(name, folder_path, explore=False, batch_size=64, model="dino"):
    image_paths = get_files(folder_path, explore)
    all_embeddings = []
    current_batch_images = []

    current_preprocess = None
    if model == "dino":
        current_preprocess = transform
    elif model == "clip":
        current_preprocess = clip_preprocess
    else:
        raise ValueError("Model must be 'dino' or 'clip'")


    for i, path in enumerate(tqdm(image_paths, desc=f"Creating Embeddings with {model.upper()}...")):
        image = Image.open(path).convert("RGB")
        transformed_image = current_preprocess(image)
        current_batch_images.append(transformed_image)

        if len(current_batch_images) == batch_size or i == len(image_paths) - 1:
            batch_tensor = torch.stack(current_batch_images).to(device)
            with torch.no_grad():
                if model == "dino":
                    embeddings_batch = dino(batch_tensor)
                elif model == "clip":
                    embeddings_batch = clip_model.encode_image(batch_tensor)
                    # embeddings_batch = embeddings_batch / embeddings_batch.norm(p=2, dim=-1, keepdim=True)

            all_embeddings.append(embeddings_batch.cpu())
            current_batch_images = []

    vectors = torch.cat(all_embeddings, dim=0).numpy().astype(np.float32)

    d = len(vectors[0])
    index = None
    if model == "dino":
        index = faiss.IndexFlatIP(d)
    elif model == "clip":
        index = faiss.IndexFlatL2(d)

    index = faiss.IndexIDMap(index)

    ids = np.array(range(len(image_paths)))
    index.add_with_ids(vectors, ids)

    # os.makedirs("database", exist_ok=True)
    faiss.write_index(index, os.path.join("collections", name, f"{name}_{model}.index"))
    with open(os.path.join("collections", name, f"{name}_{model}_paths.json"), "w") as f:
        json.dump(image_paths, f)

    print(f"FAISS index and paths saved for {name} using {model.upper()} model.")



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
    db.save_DB(folder_name= name)


def search_visual(name, file_path, k = -1):
    start_time = time.time()
    index = faiss.read_index(os.path.join("collections", name, f"{name}_dino.index"))
    end_time = time.time()
    print(f"Loading time: {end_time - start_time:.3f} seconds")

    if k == -1:
        k = index.ntotal

    query_image = Image.open(file_path).convert("RGB").resize((224, 224))
    query_tensor = transform(query_image).unsqueeze(0).to(device)
    
    start_time = time.time()
    with torch.no_grad():
        query_embedding = dino(query_tensor).cpu().numpy()
    end_time = time.time()
    print(f"embeddding time: {end_time - start_time:.3f} seconds")
    
    start_time = time.time()
    distances, indices = index.search(query_embedding, k)
    end_time = time.time()
    print(f"search time: {end_time - start_time:.3f} seconds")
    indices = indices[0]
    distances = distances[0]
    # Load the original image paths to map back to filenames
    with open(os.path.join("collections", name, f"{name}_dino_paths.json"), "r") as f:
        image_paths = json.load(f)
        
    results = []
    for i in range(len(indices)):
        results.append({"path": image_paths[i], "distance": distances[i]})

    results.sort(key= lambda x: x["distance"])
    return results


def search_clip(name, query : str, k = -1):
    start_time = time.time()

    index = faiss.read_index(os.path.join("collections", name, f"{name}_clip.index"))
    end_time = time.time()
    print(f"Loading index time: {end_time - start_time:.3f} seconds")

    if k == -1:
        k = index.ntotal

    start_time = time.time()
    text_tokens = open_clip.tokenize(query).to(device)

    with torch.no_grad():
        query_embedding = clip_model.encode_text(text_tokens)
        query_embedding = query_embedding.cpu().numpy()
    end_time = time.time()
    print(f"Embedding query time: {end_time - start_time:.3f} seconds")

    start_time = time.time()
    distances, indices = index.search(query_embedding, k)
    end_time = time.time()
    print(f"Search time: {end_time - start_time:.3f} seconds")

    indices = indices[0]
    distances = distances[0]

    with open(os.path.join("collections", name, f"{name}_clip_paths.json"), "r") as f:
        image_paths = json.load(f)

    results = []
    for i in range(len(indices)):
        if indices[i] < len(image_paths):
            results.append({"path": image_paths[indices[i]], "distance": distances[i]})

    results.sort(key=lambda x: x["distance"])
    return results


def search_color(name, rgb= None, path= None, k = 5):
    query_image = None
    # query_pixmap = None

    if rgb and len(rgb) == 3:
        query_image = Image.new('RGB', (10, 10), rgb)
        # query_pixmap = imageToQPixmap(query_image)
    elif path:
        query_image = Image.open(path, mode= "r")
        # query_pixmap = QPixmap(path)
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

    for i, image in enumerate(images):
        # images[i][0] = Image.open(image[0])
        images[i]["path"] = image["path"]

    if path:
        return [{"path": path, "distance": 0, "colors": vec}] + images
    else:
        return [{"image": query_image, "distance": 0, "colors": vec}] + images

def add_index(self, name, directory, explore, by):
        if by == "color":
            add_color(name=name, folder_path=directory, explore=explore)
        else:
            add_visual(name=name, folder_path=directory, explore=explore, model= by)

if __name__ == "__main__":
    pass
    # add_visual(name= "pinterest", folder_path= r"gallery-dl\pinterest\sidvenkatayogii\Reference")
    # print(search_visual(name="pinterest", file_path= r"gallery-dl\pinterest\sidvenkatayogii\Reference\pinterest_921478773727505082.jpg"))
