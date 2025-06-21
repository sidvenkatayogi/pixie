from search_color import search
from PIL import Image

imgs = search(query = (204, 12, 12))

paths = [i[0] for i in imgs]

print(paths)