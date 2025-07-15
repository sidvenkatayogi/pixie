# TODO improve dominant colors
from PIL import Image
import numpy as np
import os
from skimage.color import rgb2lab

def get_dominant_colors(image, palette_size=16, num_colors=5):
    # Resize image to speed up processing
    # if image.width >= 512 and image.height >= 512:
    #     img = image.resize((int(image.width/100), int(image.height/100)), resample= 0)
    # else:
    #     img = image
    if image.mode != 'RGB':
        image = image.convert('RGB')
    img = image.resize((64, 64), resample= 0)
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


def dist(c1, c2):
    c1r, c1g, c1b, = c1[:3]
    c2r, c2g, c2b = c2[:3]

    r = c1r - c2r
    g = c1g - c2g
    b = c1b - c2b

    return np.sqrt(r**2 + g**2 + b**2)

# weighted Euclidean distance
# formula: https://www.compuphase.com/cmetric.htm#:~:text=A%20low%2Dcost%20approximation)
def wdist(c1, c2):
    c1r, c1g, c1b, = c1[:3]
    c2r, c2g, c2b = c2[:3]

    rm = (c1r + c2r)/2
    r = c1r - c2r
    g = c1g - c2g
    b = c1b - c2b

    x = (2 + rm/256)*(r**2)
    y =  4*(g**2)
    z = (2 + ((255-rm)/256))*(b**2)

    return np.sqrt(x + y + z)


def labdist(c1, c2):
    # Ensure RGB is normalized (0–1) for skimage
    rgb1 = np.array(c1[:3]) / 255.0
    rgb2 = np.array(c2[:3]) / 255.0

    # Convert to Lab
    lab1 = rgb2lab([[rgb1]])[0][0]
    lab2 = rgb2lab([[rgb2]])[0][0]

    delta_e = np.linalg.norm(lab1 - lab2)

    return delta_e
    

def multidist(i1, i2):
    i1 = i1.reshape(int(len(i1)/4), 4)
    i2 = i2.reshape(int(len(i2)/4), 4)
    distance = 0
    tf = 0
    for j, rgbf1 in enumerate(i1):
        for k, rgbf2 in enumerate(i2):
            f1 = rgbf1[-1]
            f2 = rgbf2[-1]
            distance += labdist(rgbf1[:3], rgbf2[:3]) * np.sqrt(f1 * f2)
            tf += np.sqrt(f1 * f2)
    distance /= tf
    return distance


def create_bar(height, width, color):
    bar = np.zeros((height, width, 3), np.uint8)
    bar[:] = color[:3]
    return bar

def show_palette(cols):
    bars = []
    for color in cols:
        bar = create_bar(200, 200, color)
        bars.append(bar)

    img_bar = np.hstack(bars)
    return Image.fromarray(img_bar)