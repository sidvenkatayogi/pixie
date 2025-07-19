from PIL import Image
import numpy as np
from skimage.color import rgb2lab
import colorsys

def get_dominant_colors(image, palette_size=8, num_colors=5):
    """
    Get the dominant colors of an image

    Args:
        palette_size (int, optional): number of colors to reduce the image to before picking dominant colors
        num_colors (int, optional): the maximum number of colors to return

    Returns:
        numpy.ndarray with the following structure:
            [red (of most dominant color), blue, green, frequency, red (of 2nd most dominant color), blue, green, frequency, ...]
    """
    # resize image to speed up processing
    if image.mode != 'RGB':
        image = image.convert('RGB')
    img = image.resize((128, 128), resample= 0)
    
    # reduce colors (uses k-means internally)
    paletted = img.convert('P', palette=Image.ADAPTIVE, colors= palette_size)

    # find the colors that occurs most often
    palette = paletted.getpalette()
    color_counts = sorted(paletted.getcolors(), reverse=True)

    dominant_colors = []
    max = color_counts[0][0] # frequency of most dominant color

    i = 0
    while len(dominant_colors) < num_colors and i < len(color_counts):
        if color_counts[i][0] > (0.001 * max): # if color is too insignificant, not dominant
            palette_index = color_counts[i][1]

            # palette is 1 x (3*num palette colors)
            rgbf = palette[palette_index*3:palette_index*3+3] + [color_counts[i][0]]
            # only add colors if they are distinct from other dominant colors
            if (i == 0 or all(labdist(c1[:3], rgbf[:3]) > 20 for c1 in dominant_colors)):
                palette_index = color_counts[i][1]
                dominant_colors.append(rgbf)
        i += 1

    dominant_colors = np.array(dominant_colors).reshape(-1)

    return dominant_colors


def dist(c1, c2):
    """
    Get euclidean distance between 2 3D vectors

    Args:
        c1 (list or numpy.ndarray): first/starting vector
        c2 (list or numpy.ndarray): second/end vector

    Returns:
        float
    """
    c1x, c1y, c1z, = c1[:3]
    c2x, c2y, c2z = c2[:3]

    x = c1x - c2x
    y = c1y - c2y
    z = c1z - c2z

    return np.sqrt(x**2 + y**2 + z**2)

def wdist(c1, c2):
    """
    Get weighted euclidean color distance between 2 RGB vectors\n
    formula: https://www.compuphase.com/cmetric.htm#:~:text=A%20low%2Dcost%20approximation)

    Args:
        c1 (list or numpy.ndarray): first/starting vector
        c2 (list or numpy.ndarray): second/end vector

    Returns:
        float
    """
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
    """
    Get euclidean color distance in LAB color space between 2 RGB vectors

    Args:
        c1 (list or numpy.ndarray): first/starting RGB vector
        c2 (list or numpy.ndarray): second/end RGB vector

    Returns:
        float
    """
    rgb1 = np.array(c1[:3]) / 255.0
    rgb2 = np.array(c2[:3]) / 255.0

    lab1 = rgb2lab([[rgb1]])[0][0]
    lab2 = rgb2lab([[rgb2]])[0][0]

    delta_e = np.linalg.norm(lab1 - lab2)

    return delta_e
    

def multidist(i1, i2, k = 4):
    """
    Get color distance of 2 color vectors representing multiple colors by weighting distances by frequency of color

    Args:
        i1 (list or numpy.ndarray): first/starting RGBF vector with the following structure:
            [red (of most dominant color), blue, green, frequency, red (of 2nd most dominant color), blue, green, frequency, ...]
        i2 (list or numpy.ndarray): second/end RGBF vector with the following structure:
            [red (of most dominant color), blue, green, frequency, red (of 2nd most dominant color), blue, green, frequency, ...]
        k (int): max number of colors to compare in each set
    Returns:
        float
    """
    i1 = i1.reshape(int(len(i1)/4), 4)
    i2 = i2.reshape(int(len(i2)/4), 4)
    i1 = i1[:min(len(i1),k)]
    i2 = i2[:min(len(i2),k)]

    distance = 0
    tf = 0
    d = {}
    maxf1 = i1[0][3]
    maxf2 = i2[0][3]
    for j, rgbf1 in enumerate(i1): # i also tried a rank wise weighting using j and k but it didn't work as well
        for m, rgbf2 in enumerate(i2):
            # cache each pair bc labdist is symmetric
            key = tuple(sorted([tuple(rgbf1), tuple(rgbf2)]))
            if key in d:
                distance += d[key][0]
                tf += d[key][1]
            else:
                h1, s1, v1 = colorsys.rgb_to_hsv(rgbf1[0]/255, rgbf1[1]/255, rgbf1[2]/255)
                h2, s2, v2 = colorsys.rgb_to_hsv(rgbf2[0]/255, rgbf2[1]/255, rgbf2[2]/255)
                hd = (min(abs(h1 - h2), 1 - abs(h1 - h2))*2) # try distance in both directions bc hue is circular and convert between 0-1
                hw = 300 # this seemed high at first but it gave me goood visual results
                sw = (s1 + s2)/2 # saturation weight, more saturation means weigh hue more
                v = (1 - abs((v1+v2)/2 - 0.2)/0.8) # value weight, low-medium value means weigh hue and penalty more
                p = hw * hd * sw * v # penalize different hue when it's saturated and low-medium value
                
                # normalize frequency by the frequency of the most dominant color
                f1 = rgbf1[-1]/maxf1
                f2 = rgbf2[-1]/maxf2
                gmf = np.sqrt(f1 * f2) # lower power on frequencies reduces noise on colorful images
                labd = (labdist(rgbf1[:3], rgbf2[:3]) + p) * gmf # weight by the 2 frequencies
                distance += labd
                tf += gmf
                d[key] = (labd, gmf)
    # normalize by how many colors there was so that sets with lower number of colors don't have lower distance
    # i think the tf should've done this but the above problem was happening so I did this
    distance /= (len(i1) * len(i2))
    distance = (distance / tf) if tf != 0 else 0 # normalize by earlier weights
    return distance

def create_bar(height, width, color):
    """
    Create solid bar of input color

    Args:
        height (int): height of bar
        width (int): width of bar
        color (list or numpy.ndarray): RGB color for the bar

    Returns:
        numpy.ndarray with dtype numpy.uint8 representing solid image with shape (height, width, 3)
    """
    bar = np.zeros((height, width, 3), np.uint8)
    bar[:] = color[:3]
    return bar

def show_palette(cols):
    """
    Create palette image of solid color bars

    Args:
        cols (numpy.ndarray): colors for the palette with the following structure:
        [[red, green, blue],
         [red, green, blue],
         [...]]

    Returns:
        numpy.ndarray with dtype numpy.uint8 representing solid image with shape (height, width, 3)
    """
    bars = []
    for color in cols:
        bar = create_bar(200, 200, color)
        bars.append(bar)

    img_bar = np.hstack(bars)
    return Image.fromarray(img_bar)