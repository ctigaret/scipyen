"""custom_colormaps"""


# TODO: color map editor
# TODO: mechanism to save new colormaps created/changed with the editor, in a file/collection of files
# TODO:     to be loaded at runtime

from matplotlib import cm as _cm
from matplotlib import colors as _colors

# The format to specify these colormaps allows discontinuities at the anchor 
# points. Each anchor point is specified as a row in a matrix of the form [x[i] 
# yleft[i] yright[i]], where x[i] is the anchor, and yleft[i] and yright[i] are 
# the values of the color on either side of the anchor point.

# If there are no discontinuities, then yleft[i]=yright[i]
    
__green_fire_blue_data = {"red": [(0.0,0.0,0.0), 
                                  (0.5, 0.0, 0.0), 
                                  (0.75,1.0,1.0), 
                                  (1.0, 1.0, 1.0)],
                        "green": [(0.0, 0.0, 0.0), 
                                  (0.5, 1.0, 1.0), 
                                  (1.0, 1.0, 1.0)],
                         "blue": [(0.0, 0.0, 0.0), 
                                  (0.25, 0.66, 0.66), 
                                  (0.5, 0.0, 0.0), 
                                  (0.75, 0.0, 1.0), 
                                  (1.0, 1.0, 1.0)]}

#__thermal_lut_ij_data__ = {"red":[(0.275, 0.0, 0.45), 
                                  #(0.275, 0.0, 0.45),
                                  #(0.275, 0.0, 0.45),
                                  #(0.23, 0.08, 0.45)],
                            #"green":[]\,
                            #"blue":[]\}
#_cm.register_cmap(name="GreenFireBlue", data=__green_fire_blue_data, lut=256)

CustomColorMaps = {"GreenFireBlue": __green_fire_blue_data}

def register_custom_colormaps(lut=256):
    #_cm.register_cmap(cmap = _cm.LinearSegmentedColormap(name=k, data=CustomColorMaps[k], lut=lut))
    for k in CustomColorMaps.keys():
        _cm.register_cmap(cmap = _cm.LinearSegmentedColormap(name=k, data=CustomColorMaps[k], lut=lut))
        #_cm.register_cmap(name=k, data=CustomColorMaps[k], lut=lut)
