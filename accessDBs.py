
import numpy as np
import sys
import os
import faiss
import json
import time
import torch
import torchvision.transforms.v2 as tfms
import open_clip
from tqdm import tqdm
from PIL import Image
from imagehash import colorhash
from vectorDB import VectorDB
from hashDB import HashDB
from colors import get_dominant_colors

os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE" # quick fix for a faiss bug

if hasattr(sys, '_MEIPASS'):
    torch.hub.set_dir(os.path.join(sys._MEIPASS, 'models', 'torch_hub'))
    openclip_cache = os.path.join(sys._MEIPASS, 'models', 'openclip')
else:
    torch.hub.set_dir('./models/torch_hub')
    openclip_cache = './models/openclip'

dino = torch.hub.load('facebookresearch/dino:main', 'dino_vits16')
device = 'cuda' if torch.cuda.is_available() else 'cpu'

transform = tfms.Compose([
    tfms.Resize(size= (224, 224), interpolation= 1),
    tfms.ToImage(),
    tfms.ToDtype(torch.float32, scale=True),
    # tfms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

open_clip_model_name = "ViT-B-32"
open_clip_pretrained_weights = "laion2b_s34b_b79k"

clip_model, clip_preprocess, clip_tokenizer = open_clip.create_model_and_transforms(
    open_clip_model_name,
    pretrained=open_clip_pretrained_weights,
    device=device,
    cache_dir=openclip_cache
)


def get_files(folder_path, explore = False):
    """
    Get all the image file paths within a folder

    Args:
        folder_path (str): folder of images
        explore (bool, optional): True if including subfolders, default False

    Returns:
        list[str]
    """
    image_paths = []
    for file in tqdm(os.listdir(folder_path), desc= f"Exploring... ({folder_path})", disable= not explore):
        # print(folder_path)
        file_path = os.path.join(folder_path, file)
        if explore and os.path.isdir(file_path):
            image_paths += get_files(file_path, True)
        elif os.path.isfile(file_path) and file.lower().endswith((".png", ".jpg", ".jpeg")):
            image_paths.append(file_path)

    return image_paths


def add_visual(name, folder_path, explore=False, batch_size=32, model="dino", progress=None):
    """
    Add images from a folder to a FAISS index using an image embedding model

    Args:
        name (str): name for the index
        folder_path (str): folder of images
        explore (bool, optional): True if including subfolders, default False
        batch_size (int, optional): batch size for embedding
        model (str, optional): embedding model to use (must be either "dino" or "clip"). default "dino"
        progress (QProgressDialog, optional): proress dialog to update while adding images, default None
    """
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
        
        # batching
        if len(current_batch_images) == batch_size or i == len(image_paths) - 1:
            batch_tensor = torch.stack(current_batch_images).to(device)
            with torch.no_grad():
                if model == "dino":
                    embeddings_batch = dino(batch_tensor)
                elif model == "clip":
                    embeddings_batch = clip_model.encode_image(batch_tensor)
            if i == len(image_paths) - 1:
                time.sleep(0.3)
            all_embeddings.append(embeddings_batch.cpu())
            current_batch_images = []
        if progress:
            progress(i + 1)

    vectors = torch.cat(all_embeddings, dim=0).numpy().astype(np.float32)

    if model == "dino":
        faiss.normalize_L2(vectors)

    d = len(vectors[0])
    index = None

    # use inner product for dino and euclidean for clip
    if model == "dino":
        index = faiss.IndexFlatIP(d)
    elif model == "clip":
        index = faiss.IndexFlatL2(d)

    index = faiss.IndexIDMap(index)

    # numeric ids (maps to paths)
    ids = np.array(range(len(image_paths)))
    index.add_with_ids(vectors, ids)

    # save paths to a json file to map to embeddings with numeric ids
    faiss.write_index(index, os.path.join("collections", name, f"{name}_{model}.index"))
    with open(os.path.join("collections", name, f"{name}_{model}_paths.json"), "w") as f:
        json.dump(image_paths, f)


def add_color(name, folder_path, explore= False, progress=None):
    """
    Add images from a folder to a Vector_DB using a color index and save to JSON

    Args:
        name (str): name for the Vector_DB
        folder_path (str): folder of images
        explore (bool, optional): True if including subfolders, default False
        progress (QProgressDialog, optional): proress dialog to update while adding images, default None
    """
    image_paths = []
    image_paths = get_files(folder_path, explore)

    db = None
    db = VectorDB.get_DB(name= name)
    if not db:
        db = VectorDB(name= name)

    for i, path in enumerate(tqdm(image_paths, desc= f"Creating Embeddings and Adding to DB...")):
        try:
            if type(db) == VectorDB:
                if db.get_vector(path) == None:
                    cols = get_dominant_colors(Image.open(path, mode= "r"), num_colors= 5)
                    db.add_vector(id= path,vec= cols)
            elif type(db) == HashDB:
                hash = colorhash(Image.open(path), binbits = 7)
                db.add_hash(path, hash)
        except Exception as e:
            print(f"Error processing {path} : {e}")
        if progress:
            progress(i + 1)
            
    db.save_DB()


def search_visual(name, file_path, k = 5):
    """
    Get the k nearest neighbors of a dino index using a query image

    Args:
        name (str): name of index to search
        file_path (str): path of image to embed into DINO and query
        k (int, optional): number of nearest neighbors to return, default 5


    Returns:
            list[dict]: sorted by distance list of k nearest neighbors represented by a dictionary with keys:
                "path" (Any): the respective image path to the image embedding
                "distance" (float): distance to the query
    """
    index = faiss.read_index(os.path.join("collections", name, f"{name}_dino.index"))

    if k == -1:
        k = index.ntotal

    query_image = Image.open(file_path).convert("RGB").resize((224, 224))
    query_tensor = transform(query_image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        query_embedding = dino(query_tensor).cpu().numpy()
        faiss.normalize_L2(query_embedding)
    
    distances, indices = index.search(query_embedding, k)
    indices = indices[0]
    distances = distances[0]

    # load the original image paths to map back to embeddings
    with open(os.path.join("collections", name, f"{name}_dino_paths.json"), "r") as f:
        image_paths = json.load(f)
        
    results = []
    for i in range(len(indices)):
        if indices[i] < len(image_paths):
            results.append({"path": image_paths[indices[i]], "distance": distances[i]})

    # not actually distance its similarity so reverse
    results.sort(key= lambda x: x["distance"], reverse= True)

    return [{"path": file_path, "distance": 0}] + results


def search_clip(name, query : str, k = 5):
    """
    Get the k nearest neighbors of a dino index using a query text

    Args:
        name (str): name of index to search
        query (str): text to embed into CLIP and query
        k (int, optional): number of nearest neighbors to return, default 5

    Returns:
            list[dict]: sorted by distance list of k nearest neighbors represented by a dictionary with keys:
                "path" (Any): the respective image path to the image embedding
                "distance" (float): distance to the query
    """

    index = faiss.read_index(os.path.join("collections", name, f"{name}_clip.index"))

    if k == -1:
        k = index.ntotal

    text_tokens = open_clip.tokenize(query).to(device)

    with torch.no_grad():
        query_embedding = clip_model.encode_text(text_tokens)
        query_embedding = query_embedding.cpu().numpy()

    distances, indices = index.search(query_embedding, k)

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
    """
    Get the k nearest neighbors of a color index using either rgb values or query image

    Args:
        name (str): name of index to search
        rgb (tuple, optional): if querying by color, tuple of RGB values in the form (R, G, B). default None (then must input path)
        path (str, optional): if querying by image, path of image to query. default None (then must input rgb)
        k (int, optional): number of nearest neighbors to return, default 5

    Returns:
            list[dict]: sorted by distance list of k nearest neighbors represented by a dictionary with keys:
                "path" (str): the respective image path to the color vector. the first dict in the list is the query, and if an RGB query was used, "path" is replaced with
                "image" (PIL.Image): solid color image of query color. only present if element is the first in the list and query was rgb
                "distance" (float): distance to the query
                "colors" (numpy.ndarray): the color vector of an image which has the following structure:\n
                [red (of most dominant color), blue, green, frequency, red (of 2nd most dominant color), blue, green, frequency, ...]
    """
    query_image = None

    if rgb and len(rgb) == 3:
        query_image = Image.new('RGB', (10, 10), rgb)
    elif path:
        query_image = Image.open(path, mode= "r")
    else:
        raise Exception("Enter RGB values ((R, G, B)), PIL Image, or image path (str)")

    # you can create a Hash_DB but im just using Vector_DB
    db = VectorDB.get_DB(name= name)

    images = []

    vec = []
    if type(db) == VectorDB:
        vec = get_dominant_colors(query_image, num_colors= 5)
        images = db.knn(vec, k= k)
    elif type(db) == HashDB:
        images = db.knn(colorhash(query_image, binbits = 7), k= k)

    for i, image in enumerate(images):
        images[i]["path"] = image["path"]

    if path:
        return [{"path": path, "distance": 0, "colors": vec}] + images
    else:
        return [{"image": query_image, "distance": 0, "colors": vec}] + images

if __name__ == "__main__":
    pass
    # add_visual(name= "pinterest", folder_path= r"gallery-dl\pinterest\sidvenkatayogii\Reference")
    # print(search_visual(name="pinterest", file_path= r"gallery-dl\pinterest\sidvenkatayogii\Reference\pinterest_921478773727505082.jpg"))
