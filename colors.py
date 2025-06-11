from PIL import Image
import numpy as np
import os
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

def get_dominant_colors(pil_img, palette_size=16, num_colors=10):
    # Resize image to speed up processing
    img = pil_img.resize((int(pil_img.width/100), int(pil_img.height/100)), resample= 0)
    # img.show()

    # Reduce colors (uses k-means internally)
    paletted = img.convert('P', palette=Image.ADAPTIVE, colors= palette_size)

    # Find the colors that occurs most often
    palette = paletted.getpalette()
    color_counts = sorted(paletted.getcolors(), reverse=True)

    dominant_colors = []
    max = color_counts[0][0]

    i = 0
    while len(dominant_colors) < num_colors and i < len(color_counts):
        if color_counts[i][0] > (0.05 * max): # if color is too insignificant, not dominant
            palette_index = color_counts[i][1]

            # palette is 1 x (3*num palette colors)
            rgb = palette[palette_index*3:palette_index*3+3]
            # only add colors if they are distinct from other dominant colors
            if (i == 0 or all(dist(c1, rgb) > 100 for c1 in dominant_colors)):
                palette_index = color_counts[i][1]
                dominant_colors.append(palette[palette_index*3:palette_index*3+3])
        i += 1

    return dominant_colors


# weighted Euclidean distance
# formula: https://www.compuphase.com/cmetric.htm#:~:text=A%20low%2Dcost%20approximation)
def dist(c1, c2):
    c1r, c1g, c1b = c1
    c2r, c2g, c2b = c2

    rm = (c1r + c2r)/2
    r = c1r - c2r
    g = c1g - c2g
    b = c1b - c2b

    x = (2 + rm/256)*(r**2)
    y =  4*(g**2)
    z = (2 + ((255-rm)/256))*(b**2)

    return np.sqrt(x + y + z)


def create_bar(height, width, color):
    bar = np.zeros((height, width, 3), np.uint8)
    bar[:] = color
    red, green, blue = int(color[2]), int(color[1]), int(color[0])
    return bar, (red, green, blue)


def show(path):
    img = Image.open(path)
    bars = []
    for color in get_dominant_colors(img, num_colors= 5):
        bar, rgb = create_bar(200, 200, color)
        bars.append(bar)

    img_bar = np.hstack(bars)
    img.show(title=os.path.basename(path))
    Image.fromarray(img_bar).show(title='Dominant colors')
    input()

dir = "images"
client = chromadb.PersistentClient()
collection = chromadb.create_collection(name="colors")
for f in os.listdir(dir):
    if os.path.isdir(f):
        for p in os.listdir(f):
            show(os.path.join(dir, p))


for file in files:
    colors = get_dominant_colors(file)
    fids = [file]*len(colors)
    collection.add(
        embeddings= colors,
        ids = fids,
    )