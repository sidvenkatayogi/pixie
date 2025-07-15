import numpy as np
import colors
import os
import json
import pickle
from tqdm import tqdm

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        Converts numpy.ndarray to list for encoding into a JSON
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class NumpyDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
    def object_hook(self, obj):
        """
        Converts lists back into NumPy arrays if applicable.
        """
        for key, value in obj.items():
            if isinstance(value, list):
                obj[key] = np.array(value)
            elif isinstance(value, dict):
                obj[key] = self.object_hook(value)
        return obj
    

class VectorDB:
    def __init__(self, name, vector_data = {}, vector_index = {}):
        self.name = name
        self.vector_data = vector_data
        self.vector_index = vector_index

    def add_vector(self, id, vec):
        """
        Adds a vector to database

        Args:
            id (str or int): unique id for the vector
            vec (numpy.ndarray): the vector to be stored
        """
        self.vector_data[id] = vec
        self.vector_index[id] = {}
        # if you want to update all the vector distances every add
        # self.update_index(id)


    def add_vectors(self, ids, vecs):
        """
        Adds multiple vectors to database

        Args:
            ids (list or numpy.ndarray): ids for each respective vector
            vecs (list or numpy.ndarray): vectors for each respective id
        """
        for id, vec in zip(ids, vecs):
            self.add_vector(id, vec)


    def get_vector(self, id):
        """
        Get a vector by its id

        Args:
            id (Any): unique id for the vector to get

        Returns:
            numpy.ndarray or None if vector not found
        """
        if np.any(self.vector_data.get(id) != None):
            return np.asarray(self.vector_data.get(id))
        else:
            return None

    def update_index(self, id):
        """
        Update the index realting a vector to each other vector

        Args:
            id (str or int): unique id for the vector to be indexed
        """
        vec = self.get_vector(id)
        for id2, vec2 in self.vector_data.items():
            distance = colors.multidist(vec, vec2)
            self.vector_index[id2][id] = distance

    def __len__(self):
        return len(self.vector_data)

    def knn(self, query, k = 5):
        """
        Get the k nearest neighbors of a query vector

        Args:
            query (numpy.ndarray): the query vector
            k (int, optional): the number of nearest neighbors to return. default 5

        Returns:
            list[dict]: list of k nearest neighbors represented by a dictionary with keys:
                "path" (Any): the id of the vector
                "distance" (float): distance to the query vector
                "colors" (numpy.ndarray): the vector of the neighbor
        """
        results = []
        for id, vec in tqdm(self.vector_data.items(), desc= "Searching DB..."):
            distance = colors.multidist(query, vec)
            results.append({"path": id, "distance": distance, "colors": vec})
        results.sort(key= lambda x: x["distance"])
        return results[:k]
    
    def save_DB(self):
        """
        Save the Vector_DB object to JSON at the path: ./collections/self.name/self.name.json
        """
        if not os.path.exists(os.path.join("collections", self.name)):
            os.makedirs(os.path.join("collections", self.name))

        d = {self.name : {"data" : self.vector_data, "index" : self.vector_index}}

        with open(os.path.join("collections", self.name, f"{self.name}.json"), "w") as f:
            json.dump(d, f, cls= NumpyEncoder, indent=4)

    @classmethod
    def get_DB(cls, name):
        """
        Load a Vector_DB by its name

        Args:
            name (str): name of existing Vector_DB to load

        Returns:
            Vector_DB or None if not found
        """
        
        if not os.path.exists(os.path.join("collections", name, f"{name}.json")):
            return None
        
        d = {}
        with open(os.path.join("collections", name, f"{name}.json"), "r") as f:
            d = json.load(f, cls= NumpyDecoder)

        vd = d[name]["data"]
        vi = d[name]["index"]

        return cls(name= name, vector_data= vd, vector_index= vi)