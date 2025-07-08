# TODO improve dominant colors
from PIL import Image
import numpy as np
import os
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

def get_dominant_colors(image, palette_size=16, num_colors=5):
    # Resize image to speed up processing
    if image.width >= 512 and image.height >= 512:
        img = image.resize((int(image.width/100), int(image.height/100)), resample= 0)
    else:
        img = image

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
            rgbf = palette[palette_index*3:palette_index*3+3] + [color_counts[i][0]]
            # only add colors if they are distinct from other dominant colors
            if (i == 0 or all(dist(c1[:3], rgbf[:3]) > 100 for c1 in dominant_colors)):
                palette_index = color_counts[i][1]
                dominant_colors.append(rgbf)
        i += 1
    dominant_colors = np.array(dominant_colors).reshape(-1)

    return dominant_colors


# https://gist.github.com/earthbound19/e7fe15fdf8ca3ef814750a61bc75b5ce
def gammaToLinear(x):
    if x >= 0.04045:
        return ((x + 0.055)/(1 + 0.055))**2.4
    else:
        return x / 12.92
def rgbToLab(c):
    r, g, b = c[:3]

    r = gammaToLinear(r / 255)
    g = gammaToLinear(g / 255)
    b = gammaToLinear(b / 255)

    #   // This is the Oklab math:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;
#   // Math.crb (cube root) here is the equivalent of the C++ cbrtf function here: https://bottosson.github.io/posts/oklab/#converting-from-linear-srgb-to-oklab
    l = np.cbrt(l)
    m = np.cbrt(m)
    s = np.cbrt(s)

    return [l * +0.2104542553 + m * +0.7936177850 + s * -0.0040720468,
            l * +1.9779984951 + m * -2.4285922050 + s * +0.4505937099,
            l * +0.0259040371 + m * +0.7827717662 + s * -0.8086757660]

def labdist(c1, c2):
    l1, a1, b1 = rgbToLab(c1)
    l2, a2, b2 = rgbToLab(c2)

    return np.sqrt((l1-l2)**2 + (a1-a2)**2 + (b1-b2**2))

# weighted Euclidean distance
# formula: https://www.compuphase.com/cmetric.htm#:~:text=A%20low%2Dcost%20approximation)
def dist(c1, c2):
    c1r, c1g, c1b, = c1[:3]
    c2r, c2g, c2b = c2[:3]

    rm = (c1r + c2r)/2
    r = c1r - c2r
    g = c1g - c2g
    b = c1b - c2b

    x = (2 + rm/256)*(r**2)
    y =  4*(g**2)
    z = (2 + ((255-rm)/256))*(b**2)

    if len(c1) == 4:
        c1f = c1[3]
        c2f = c2[3]
        return np.sqrt(x + y + z) / ((c1f**2)*(c2f**2))
    else:
        return np.sqrt(x + y + z)
    
def multidist(i1, i2, id= None):
    i1 = i1.reshape(int(len(i1)/4), 4)
    i2 = i2.reshape(int(len(i2)/4), 4)
    distance = 0
    tf = 0
    for i, rgbf1 in enumerate(i1):
        for j, rgbf2 in enumerate(i2):
            f1 = rgbf1[-1]
            f2 = rgbf2[-1]
            # distance += np.log((dist(rgbf1[:3], rgbf2[:3]) / (i + 1) / (j + 1))  + 1)
            # distance += dist(rgbf1[:3], rgbf2[:3]) / (i + 1)**1.42 / (j + 1)**1.41
            distance += dist(rgbf1[:3], rgbf2[:3]) * (f1 * f2)
            tf += f1 * f2
            # distance += dist(rgbf1[:3], rgbf2[:3]) / (i + j + 1)
    distance /= tf
    return distance


def create_bar(height, width, color):
    bar = np.zeros((height, width, 3), np.uint8)
    bar[:] = color[:3]
    red, green, blue = int(color[2]), int(color[1]), int(color[0])
    return bar, (red, green, blue)


# def show(path):
def show_palette(cols):
    # img = Image.open(path)
    bars = []
    # cols = get_dominant_colors(img, num_colors= 5)
    for color in cols.reshape(int(len(cols)/4), 4):
        bar, rgb = create_bar(200, 200, color)
        bars.append(bar)

    img_bar = np.hstack(bars)
    # img.show(title=os.path.basename(path))
    # Image.fromarray(img_bar).show(title='Dominant colors')
    return Image.fromarray(img_bar)


if __name__ == "__main__":
    dir = r"gallery-dl\pinterest\sidvenkatayogii\Reference"
    for p in os.listdir(dir):
        show_palette(os.path.join(dir, p))
        input("ENTER for next image")