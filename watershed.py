#create a python function that apply the watershed transform to an image named image

#do the necessary imports
import numpy as np
import matplotlib.pyplot as plt
from skimage import io
from skimage import color
from skimage import filters
from skimage import morphology
from skimage import feature
from skimage import segmentation
from skimage import measure
from skimage import util
from skimage import transform
from skimage import draw
from skimage import exposure
from skimage import feature
from skimage import io, color, filters, morphology, feature, segmentation, measure, util, transform, draw, exposure
from scipy import ndimage as ndi
from scipy import signal as sig
from scipy import stats as st

from skimage.morphology import watershed
from skimage.feature import peak_local_max




def watershed(image):
    #1. apply the distance transform to the image
    distance = ndi.distance_transform_edt(image)
    
    #2. apply the watershed transform to the distance image
    local_maxi = peak_local_max(distance, indices=False, footprint=np.ones((3, 3)), labels=image)
    markers = ndi.label(local_maxi)[0]
    labels = watershed(-distance, markers, mask=image)
    
    #3. return the labels
    return labels

# Path: watershed.py
# apply the watershed transform to the image
labels = watershed(image)

# Path: watershed.py
# display the labels
plt.imshow(labels, cmap='gray')
plt.show()









