import vigra
import numpy
import matplotlib
#import qimage2ndarray 
from PyQt4.QtGui import QImage
from qimage2ndarray import gray2qimage, array2qimage, alpha_view, rgb_view, byte_view

clrmap = cm.get_cmap('jet')

x = arange(256);

cnrm = matplotlib.colors.Normalize(vmin = min(x), vmax =max(x))

smap = matplotlib.cm.ScalarMappable(norm = cnrm, cmap = clrmap)

smap.set_array(x);


#colortable = smap.to_rgba(x);

colortable = smap.to_rgba(x, bytes = True);

# note the order of the axes here !
img = QImage(alexa.shape[1], alexa.shape[0], QImage.Format_ARGB32)

a = numpy.asanyarray(alexa, dtype = numpy.uint32)

# aa is an array
aa = vigra.colors.applyColortable(a, colortable, byte_view(img)); # requires qimage2ndarray

# cimg2 copies aa into a new Vigra Image (ARGB)
cimg2 = vigra.VigraArray(aa, axistags = vigra.VigraArray.defaultAxistags('xyc'))

### find out colormaps currently available in matplotlib

from pylab import *
from numpy import outer
rc('text', usetex=False)
a=outer(arange(0,1,0.01),ones(10))
figure(figsize=(10,5))
subplots_adjust(top=0.8,bottom=0.05,left=0.01,right=0.99)
maps=[m for m in cm.datad if not m.endswith("_r")]  ### this idiom is called a list comprehension
maps.sort()
l=len(maps)+1
for i, m in enumerate(maps):
subplot(1,l,i+1)
axis("off")
imshow(a,aspect='auto',cmap=get_cmap(m),origin="lower")
title(m,rotation=90,fontsize=10)
savefig("colormaps.png",dpi=100,facecolor='gray')
