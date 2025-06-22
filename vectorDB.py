import numpy as np
import colors
import os
import json
import pickle
from tqdm import tqdm

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class NumpyDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)
    def object_hook(self, obj):
        # """
        # Converts lists back into NumPy arrays if applicable.
        # """
        # if isinstance(obj, list):
        #     return np.array(obj)
        # return obj
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
        # self.update_index(id, vec)


    def add_vectors(self, ids, vecs):
        for id, vec in zip(ids, vecs):
            self.add_vector(id, vec)


    def get_vector(self, id):
        return np.asarray(self.vector_data.get(id))

    def update_index(self, id, vec):
        """
        Update the index

        Args:
            id (str or int)
            vec (numpy.ndarray)
        """
        for id2, vec2 in self.vector_data.items():
            distance = colors.multidist(vec, vec2)
            self.vector_index[id2][id] = distance

    def __len__(self):
        return len(self.vector_data)

    def knn(self, query, k = 5):
        results = []
        # print(self.vector_data.items())
        for id, vec in tqdm(self.vector_data.items(), desc= "Searching DB..."):
            distance = colors.multidist(query, vec, id)
            results.append({"path": id, "distance": distance, "colors": vec})
        results.sort(key= lambda x: x["distance"])
        return results[:k]
    
    def save_DB(self, folder_name= "vectorDBn"):
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        d = {self.name : {"data" : self.vector_data, "index" : self.vector_index}}

        with open(os.path.join(folder_name, f"{self.name}.json"), "w") as f:
            json.dump(d, f, cls= NumpyEncoder, indent=4)

    @classmethod
    def get_DB(cls, name, folder_name= "vectorDBn"):
        d = {}
        with open(os.path.join(folder_name, f"{name}.json"), "r") as f:
            d = json.load(f, cls= NumpyDecoder)

        vd = d[name]["data"]
        vi = d[name]["index"]

        return cls(name= name, vector_data= vd, vector_index= vi)