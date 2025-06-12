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


    def add_vectors(self, ids, vecs):
        for id, vec in zip(ids, vecs):
            self.add_vector(id, vec)


    def get_vector(self, id):
        return self.vector_data.get(id)

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

    def knn(self, query, k = 5):
        results = []
        # for rgbf in query:
        for id, vec in self.vector_data.items():
            distance = colors.multidist(query, vec, id)
            results.append((id, distance))
        results.sort(key= lambda x: x[1])
        # print(results)
        return results[:k]