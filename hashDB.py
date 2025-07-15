"""I made this class for image hashing by color but I endeed up making my own way of comparing images by color
it uses the imagehash library and clusters images into a hash
i don't really get how the clustering worked though so i didn't use it and just used a vector approach
utilizing this in the future, maybe combiend with vectors, could be a significant performance improvement"""

import numpy as np
import colors
import imagehash

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
            id (str or int): unique id for the hash
            hash (imagehash.ImageHash): the hash to be stored
        """
        self.hash_data[id] = hash
        self.hash_index[id] = {}
        self.update_index(id, hash)

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
            hash (imagehash.ImageHash)
        """
        for id2, hash2 in self.hash_data.items():
            distance = (hash - hash2)
            self.hash_index[id2][id] = distance

    def knn(self, query, k = 5):
        results = []
        for id, hash in self.hash_data.items():
            distance = np.abs(query - hash)
            results.append((id, distance))
        results.sort(key= lambda x: x[1])
        return results[:k]