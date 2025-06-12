# TODO refactor this to use a database parent class and hashdb and vectordb to be children of that class
import numpy as np
import colors
import imagehash
import time

class HashDB:
    def __init__(self):
        self.hash_data = {}
        self.hash_index = {}
        self.timeadding = 0
        self.timeidxing = 0

    def add_hash(self, id, hash):
        """
        Adds a hash to database

        Args:
            id (str or int): unique id for the vector
            vec (numpy.ndarray): the vector to be stored
        """

        # start_time = time.perf_counter()
        self.hash_data[id] = hash
        self.hash_index[id] = {}
        # end_time = time.perf_counter()
        # self.timeadding += (end_time - start_time)

        # start_time = time.perf_counter()
        self.update_index(id, hash)
        # end_time = time.perf_counter()
        # self.timeidxing += (end_time - start_time)
        


    def add_hashes(self, ids, hashes):
        for id, hash in zip(ids, hashes):
            self.add_hashes(id, hash)


    def get_hash(self, id):
        return self.hash_data.get(id)

    def update_index(self, id, hash):
        """
        Update the index

        Args:
            id (str or int)
            vec (numpy.ndarray)
        """
        for id2, hash2 in self.hash_data.items():
            # distance = colors.multidist(hash, hash2)
            distance = (hash - hash2)
            self.hash_index[id2][id] = distance

    def knn(self, query, k = 5):
        results = []
        # for rgbf in query:
        for id, hash in self.hash_data.items():
            # distance = colors.multidist(query, vec, id)
            distance = np.abs(query - hash)
            results.append((id, distance))
        results.sort(key= lambda x: x[1])
        # print(results)
        return results[:k]