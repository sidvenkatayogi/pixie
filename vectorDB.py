import numpy as np
import colors

class VectorDB:
    def __init__(self):
        self.vector_data = {}
        self.vector_index = {}

    def add_vector(self, id, vec):
        """
        Adds a vector to database

        Args:
            id (str or int): unique id for the vector
            vec (numpy.ndarray): the vector to be stored
        """
        self.vector_data[id] = vec
        self.vector_index[id] = {}
        self.update_index(id, vec)

    def get_vector(self, id):
        return self.vector_data.get(id)

    def update(self, id, vec):
        """
        Update the index

        Args:
            id (str or int)
            vec (numpy.ndarray)
        """
        for id2, vec2 in self.vector_data.items():
            distance = colors.dist(vec, vec2)
            self.vector_index[id2][id] = distance

    def knn(self, query, k = 5):
        results = []
        for id, vec in self.vector_data.items():
            distance = colors.dist(query, vec)
            results.append((id, distance))
        results.sort(key= lambda x: x[1], reverse= True)
        return results[:k]
