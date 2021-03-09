"""scipyen_colormaps

Brings matplotlib's cm and colors modules together with cmocean (if available)

and our ow custom color maps

"""

# NOTE: 2020-11-28 10:20:06
# upgrade to matplotlib 3.3.x
# register new colormaps upon importing this module

# TODO: color map editor
# TODO: mechanism to save new colormaps created/changed with the editor, in a file/collection of files
# TODO:     to be loaded at runtime

from matplotlib import cm as cm
from matplotlib import colors as colors

try:
    import cmocean # some cool palettes/luts
    # NOTE 2021-03-09 16:44:36
    # the following is not reuired as these will be registered in matplotlib.cm._cmap_registry
    # upon importing the cmocean module, with the "cmo." prefix added to their name
    #for k, cmap in cmocean.cm.cmap_d.items():
        #cm.register_cmap(name=k, cmap=cmap)
    #del(k, cmap)
except:
    pass

# Each row in the table for a given color is a sequence of x, y0, y1 tuples. In each sequence, x must increase monotonically from 0 to 1. For any input value z falling between x[i] and x[i+1], the output value of a given color will be linearly interpolated between y1[i] and y0[i+1]:
#
# row i:   x  y0  y1
#                /
#               /
# row i+1: x  y0  y1
#
# Hence y0 in the first row and y1 in the last row are never used.

# The format to specify these colormaps allows discontinuities at the anchor 
# points. Each anchor point is specified as a row in a matrix of the form [x[i] 
# yleft[i] yright[i]], where x[i] is the anchor, and yleft[i] and yright[i] are 
# the values of the color on either side of the anchor point.

# If there are no discontinuities, then yleft[i]=yright[i]
    
__green_fire_blue_data = {"red": [(0.0,  0.0,  0.0), 
                                  (0.5,  0.0,  0.0), 
                                  (0.75, 1.0,  1.0), 
                                  (1.0,  1.0,  1.0)],
                        "green": [(0.0,  0.0,  0.0), 
                                  (0.5,  1.0,  1.0), 
                                  (1.0,  1.0,  1.0)],
                         "blue": [(0.0,  0.0,  0.0), 
                                  (0.25, 0.66, 0.66), 
                                  (0.5,  0.0,  0.0), 
                                  (0.75, 0.0,  1.0), 
                                  (1.0,  1.0,  1.0)]}

#__thermal_lut_ij_data__ = {"red":[(0.275, 0.0, 0.45), 
                                  #(0.275, 0.0, 0.45),
                                  #(0.275, 0.0, 0.45),
                                  #(0.23, 0.08, 0.45)],
                            #"green":[]\,
                            #"blue":[]\}
#_cm.register_cmap(name="GreenFireBlue", data=__green_fire_blue_data, lut=256)

CustomColorMaps = {"GreenFireBlue": __green_fire_blue_data}

def register_colormaps(colormap_dict):
    """Register custom colormaps collected in a dictionary.
    
    Parameters:
    ----------
    colormap_dict: dict with 
        keys: str = name of the colormap
        values: dict: a colormap cdict with three elements ("red", "green", "blue")
            supplied as the "segmentdata" para,eter to the function
            matplotlib.colors.LinearSegmentedColormap()
    
    """
    for cmap in colormap_dict:
        if cmap not in cm._cmap_registry:
            cm.register_cmap(name = cmap, cmap = colors.LinearSegmentedColormap(name=cmap, segmentdata=colormap_dict[cmap]))

#map(lambda x: cm.register_cmap(name=x, cmap = colors.LinearSegmentedColormap(name=x, segmentdata=CustomColorMaps[x])), CustomColorMaps.keys())

#for k in CustomColorMaps.keys():
    #cm.register_cmap(name=k, cmap = colors.LinearSegmentedColormap(name=k, segmentdata=CustomColorMaps[k]))
    

def get(name, lut=None, default=None):
    if isinstance(name, str) and len(name.strip()) and name in cm._cmap_registry:
        return cm.get_cmap(name=name, lut=lut)
        #return cm._cmap_registry[name]
    
    elif isinstance(name, colors.Colormap):
        return name
    
    else:
        if default is None:
            return cm.get_cmap(name="gray", lut=lut)
        
        elif isinstance(default, str) and default in cm._cmap_registry:
            return cm.get_cmap(name=default, lut=lut)
        
        return cm.get_cmap(name="gray", lut=lut)
    
cm.register_cmap(name="None", cmap=cm.get_cmap(name="gray"))
register_colormaps(CustomColorMaps)
    
