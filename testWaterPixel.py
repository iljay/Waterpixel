#%%
import numpy as np
from scipy import ndimage
import skimage
import matplotlib.pyplot as plt
from PIL import Image, ImageOps, ImageDraw
import os
import cv2
import math

img_path = 'BSDS300/images/train/176035.jpg'
im = Image.open(img_path)
im = im.resize((400,300))
np_img = np.array(im)
CELL_RADIUS = 20
RHO=2/3
K=10

def morphological_grad(img, k_val=3, gauss_sigma=2):
    if img.ndim >= 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = ndimage.gaussian_filter(img,gauss_sigma)
    grad = cv2.morphologyEx(img, cv2.MORPH_GRADIENT, np.ones((k_val, k_val)))
    grad = grad / grad.max()
    return grad

class Cell():
    def __init__(self,x,y,r,rho,img):
        # Should be gradient image with uint8 values here
        if img.max() <= 1:
            img = (img*255).astype(np.uint8)
        self.img = img
        self.center = (x,y)
        self.corner = (
            self.constrain(int(y-r),0,self.img.shape[0]-1),
            self.constrain(int(x-r*np.sqrt(3)/2),0,self.img.shape[1]-1),
            self.constrain(int(y+r),0,self.img.shape[0]-1),
            self.constrain(int(x+r*np.sqrt(3)/2),0,self.img.shape[1]-1))
        self.rad = r
        self.rho = rho
        self.values, self.mask = self.get_values()
        self.marker = self.get_marker()
        
    
    def constrain(self,val,min_val, max_val):
        return max(min_val, min(val,max_val))    

    def get_center(self):
        return (self.constrain(int(self.center[1]),0,self.img.shape[0]-1), self.constrain(int(self.center[0]),0,self.img.shape[1]-1))

    def get_values(self):
        msk = Image.new("L", (self.img.shape[1] + 2*self.rad, self.img.shape[0] + 2*self.rad))
        msk_d = ImageDraw.Draw(msk)
        poly = [(self.rad + self.center[0] + math.cos(th) * self.rad * self.rho, 
                 self.rad + self.center[1] + math.sin(th) * self.rad * self.rho) 
                 for th in [math.pi/6 + i * 2 * math.pi / 6 for i in range(6)]]
        msk_d.polygon(poly, fill=1)
        msk = np.array(msk, dtype=np.uint8)
        msk = msk[self.rad:-self.rad, self.rad:-self.rad]
        values = self.img * msk
        return values, msk
    
    def get_marker(self):
        marker = np.zeros(self.img.shape)
        crop_img = self.img[self.corner[0]:self.corner[2], self.corner[1]:self.corner[3]]
        crop_mask = self.mask[self.corner[0]:self.corner[2], self.corner[1]:self.corner[3]]
        minima_img = np.zeros(crop_img.shape, dtype=np.uint8)
        minima_img[np.where(crop_img == crop_img.min())] = 1
        minima_crop = minima_img * crop_mask
        (totalLabels, label_ids, stats, centroid) = cv2.connectedComponentsWithStats(minima_crop)
        idx, max_area = 0, 0.0
        for j in range(1,totalLabels):
            area = stats[j, cv2.CC_STAT_AREA]
            if area > max_area:
                idx = j
                max_area = area
        if idx == 0:
            marker[self.constrain(int(self.center[1]),0,self.img.shape[0]-1), self.constrain(int(self.center[0]),0,self.img.shape[1]-1)] = 1
        else:
            indexes = np.where(label_ids==idx)
            marker[(indexes[0] + self.corner[0], indexes[1] + self.corner[1])] = 1
        return marker
    
def compute_cells(img, radius=CELL_RADIUS, rho=RHO):
    W,H = img.shape
    cells = []
    hex_wid = radius * np.sqrt(3)
    hex_hei = radius * 1.5
    for i in range(int(W/hex_hei)+1):
        for j in range(int(H/hex_wid)+1):
            center = (i*hex_hei, j*hex_wid) if i%2==0 else (i*hex_hei, j*hex_wid+hex_wid/2)
            cells.append(Cell(center[1], center[0], radius, rho, img))
    return cells

def get_glob_marker_center(cells):
    glob_marker_center = np.zeros(cells[0].img.shape)
    for i,cell in enumerate(cells):
        glob_marker_center[cell.get_center()] = 1
    return glob_marker_center

def get_glob_marker_distinct(cells):
    glob_marker_distinct = np.zeros(cells[0].img.shape)
    for i,cell in enumerate(cells):
        glob_marker_distinct += cell.marker * (i+1)
    return glob_marker_distinct

def DF(a,b,i,j,dist_map):
    return 2*abs(a*dist_map[i+a,j+b,1]) + 2*abs(b*dist_map[i+a,j+b,2]) + a**2 + b**2

def DL_distance_map(markers):
    W,H = markers.shape
    dist_map = np.zeros((W,H,3))
    for i in range(W):
        for j in range(H):
            if markers[i,j] != 0:
                dist_map[i,j] = np.array([0,0,0])
            else:
                dist_map[i,j] = np.array([np.inf,0,0])

    V_minus = [(-1,-1),(-1,0),(-1,1),(0,-1)]
    for i in range(1,W):
        for j in range(1,H-1):
            if markers[i,j] != 0:
                continue
            a,b = min((dist_map[i+elt[0],j+elt[1],0] + DF(elt[0],elt[1],i,j,dist_map), elt) for elt in V_minus)[1]
            dist_map[i,j,1], dist_map[i,j,2] = dist_map[i+a,j+b,1]+a, dist_map[i+a,j+b,2]+b
            dist_map[i,j,0] = dist_map[i+a,j+b,0] + DF(a,b,i,j,dist_map)

    V_plus = [(1,1),(1,0),(1,-1),(0,1),(0,0)]
    for i in range(W-2,-2,-1):
        for j in range(H-2,-2,-1):
            if markers[i,j] != 0:
                continue
            a,b = min((dist_map[i+elt[0],j+elt[1],0] + DF(elt[0],elt[1],i,j,dist_map), elt) for elt in V_plus)[1]
            dist_map[i,j,1], dist_map[i,j,2] = dist_map[i+a,j+b,1]+a, dist_map[i+a,j+b,2]+b
            dist_map[i,j,0] = dist_map[i+a,j+b,0] + DF(a,b,i,j,dist_map)

    return dist_map[:,:,0]

def compute_reg_grad(g_img, dist_map, k=K, cell_dist=CELL_RADIUS):
    return g_img + k * (2/cell_dist) * np.sqrt(dist_map)

def compute_segmentation(img, labels):
    waterpix_mask = (labels == 0) * 255
    if img.ndim >= 3:
        waterpix_mask = np.tile(np.expand_dims(waterpix_mask, axis=-1),3)
    waterpix_mask = skimage.morphology.dilation(waterpix_mask)
    return np.where(waterpix_mask, waterpix_mask, img)

def waterpixel(img, cell_rad, k, rho, marker_center=False):
    g_img = morphological_grad(img)
    cells = compute_cells(g_img, radius=cell_rad, rho=rho)
    glob_marker_distinct = get_glob_marker_distinct(cells)

    if marker_center:
        glob_marker_center = get_glob_marker_center(cells)
        dist_map = DL_distance_map(glob_marker_center)
    else:
        dist_map = DL_distance_map(glob_marker_distinct)

    reg_g_img = compute_reg_grad(g_img*255, dist_map, k, cell_dist=CELL_RADIUS)

    plt.imshow(reg_g_img)
    plt.show()

    labels = skimage.segmentation.watershed(reg_g_img, glob_marker_distinct, watershed_line=True)
    waterpix_img = compute_segmentation(img,labels)
    return waterpix_img

# img_gray = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
w_img = waterpixel(np_img, 20, 25, 2/3)
plt.imshow(w_img)  #
plt.show()