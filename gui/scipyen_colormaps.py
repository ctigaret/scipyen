"""scipyen_colormaps

Brings matplotlib's cm and colors modules together with cmocean (if available)

and our ow custom color maps

"""
import os,traceback, warnings
# NOTE: 2020-11-28 10:20:06
# upgrade to matplotlib 3.3.x
# register new colormaps upon importing this module

# TODO: color map editor
# TODO: mechanism to save new colormaps created/changed with the editor, in a file/collection of files
# TODO:     to be loaded at runtime
import typing
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.mlab as mlb
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


try:
    import cmasher
except:
    pass

from core import scipyen_config as scipyenconf

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

def register_colormaps(colormap_dict, prefix:typing.Optional[str]=None, 
                       N:typing.Optional[int]=256,
                       gamma:typing.Optional[float]=1.0):
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
        if isinstance(prefix, str) and len(prefix.strip()):
            cmap = "%s.%s" % (prefix, cmap)
            
        if cmap not in cm._cmap_registry:
            cdata = colormap_dict[cmap]
            register_colormap(cdata, name=cmap, prefix=None, N=N, gamma=gamma)
            

def register_colormap(cdata, name:typing.Optional[str]=None, 
                      prefix:typing.Optional[str]=None,
                      N:typing.Optional[int]=None, 
                      gamma:typing.Optional[float]=0.1):
    
    if isinstance(cdata, dict) and all([s in cdata for s in ("red", "green", "blue")]):
        if not (isinstance(name, str) and len(name.strip())):
            name = "LinearSegmentedMap"
            
        if isinstance(prefix, str) and len(prefix.strip()):
            name = "%s.%s" % (prefix, name)
            
        if name in cm._cmap_registry:
            warnings.warn("Colormap %s is already registered; this will overwrite it")
    
        cm.register_cmap(name = name, cmap = colors.LinearSegmentedColormap(name=name, segmentdata=cdata, N=N, gamma=gamma))
        
    elif isinstance(cdata, (tuple, list)) and all([(isinstance(rgb, (tuple, list)) and len(rgb) == 3) for rgb in cdata]):
        if not (isinstance(name, str) and len(name.strip())):
            name = "ListedMap"
            
        if isinstance(prefix, str) and len(prefix.strip()):
            name = "%s.%s" % (prefix, name)
            
        if name in cm._cmap_registry:
            warnings.warn("Colormap %s is already registered; this will overwrite it")
    
        cm.register_cmap(name=name, cmap=colors.ListedColormap(np.array(cdata), name=name, N=N))
        
    elif isinstance(cdata, np.array) and cdata.shape[1] == 3:
        if not (isinstance(name, str) and len(name.strip())):
            name = "ListedMap"
            
        if isinstance(prefix, str) and len(prefix.strip()):
            name = "%s.%s" % (prefix, name)
            
        if name in cm._cmap_registry:
            warnings.warn("Colormap %s is already registered; this will overwrite it")
    
        cm.register_cmap(name=name, cmap=colors.ListedColormap(cdata, name=name, N=N))
        
    elif isinstance(cdata, colors.Colormap):
        if isinstance(name, str) and len(name.strip()):
            if isinstance(prefix, str) and len(prefix.strip()):
                name = "%s.%s" % (prefix, name)
                
            cm.register_cmap(name=name, cmap=cdata)
            
        else:
            cm.register_cmap(cmap=cdata)
            
    else:
        warnings.warn("Cannot interpret color data for %s" % cmap)
        

def get(name, lut=None, default=None):
    if isinstance(name, str) and len(name.strip()):
        if name in cm._cmap_registry:
            return cm.get_cmap(name=name, lut=lut)

        else:
            if default is None:
                return cm.get_cmap(name="gray", lut=lut)
            
            elif isinstance(default, str) and default in cm._cmap_registry:
                return cm.get_cmap(name=default, lut=lut)
            
            return cm.get_cmap(name="gray", lut=lut)
        #return cm._cmap_registry[name]
    
    elif isinstance(name, colors.Colormap):
        return name
    
    else:
        if default is None:
            return cm.get_cmap(name="gray", lut=lut)
        
        elif isinstance(default, str) and default in cm._cmap_registry:
            return cm.get_cmap(name=default, lut=lut)
        
        return cm.get_cmap(name="gray", lut=lut)
    
def plot_linearmap(cdict):
    newcmp = colors.LinearSegmentedColormap('testCmap', segmentdata=cdict, N=256)
    rgba = newcmp(np.linspace(0, 1, 256))
    fig, ax = plt.subplots(figsize=(4, 3), constrained_layout=True)
    col = ['r', 'g', 'b']
    for xx in [0.25, 0.5, 0.75]:
        ax.axvline(xx, color='0.7', linestyle='--')
    for i in range(3):
        ax.plot(np.arange(256)/256, rgba[:, i], color=col[i])
    ax.set_xlabel('index')
    ax.set_ylabel('RGB')
    plt.show()
    
def read_colormap(filename:str, name:typing.Optional[str]=None, 
                  prefix:typing.Optional[str]=None,
                  N:int=256, gamma:float=1.0, register:bool=False):
    """Reads a colormap from a file generates with save_colormap()
    
    Parameters:
    ===========
    filename:str - a relative or absolute path name; if filename does not
    contain a directory name, then it is looked for in the following places,
    (in order):
        * the current working directory
        * Scipoyen's configuration directory
        * gui/rgb sub-directory in Scipyen's distribution
    
    name:str (optional default is None)
        Name of the colormap. When None or an empty string, the colormap gets 
        its name fromt hen basename of the file
    
    N:int (default: 256) number of colors 
    
    gamma:float default 1.0
        Used for linear segmented color maps only
        
    register:bool, default is False
        When True, also register the colormap
    
    Returns
    =======
    
    A LinearSegmentedColormap or a ListedColormap (both defined in matplotlib.colors)
    according to the contents of the file. The color map is NOT registered with
    matplotlib.cm module (use register_colormap() for this purpose)
    
    NOTE: While the function can distinguish between LinearSegmentedColormap and 
    ListedColormap, it does NOT check the validity of the numeric values, which 
    must all be in the closed interval [0,1].
    
    """
    if not os.path.isfile(filename): # not found in current working directory
        if len(os.path.dirname(filename)) == 0: # only basename is supplied => try to find the colormap file name in the known places
            fn1 = os.path.join(scipyenconf.scipyen_config_dir, filename) # check Sciopyen's configuration directory
            
            if not os.path.isfile(fn1): # not in Scipyen's configuration directory
                fn1 = os.path.join(os.path.dirname(__file__), "rgb", filename) # check Scipyen's distribution directory
                
                if not os.path.isfile(fn1): # not there either => raise exception
                    raise FileNotFoundError(filename)
                
                else:
                    filename = fn1
                    
            else:
                filename = fn1
                
        else: # filename includes at least a directory name, but was not found
            # this means that the relative or absolute path is wrong
            raise FileNotFoundError(filename)
            
        
    if not (isinstance(name, str) and len(name.strip())):
        name = os.path.splitext(os.path.basename(filename))[0]
        
    df = pd.read_csv(filename, sep=None, engine="python") # guess delimiter
        
    if all([s in df.columns for s in ("c", "x", "y0", "y1")]):
        # linear segmented color map
        r_array = np.array(df.loc[df.c == "r", "x":"y1"])
        g_array = np.array(df.loc[df.c == "g", "x":"y1"])
        b_array = np.array(df.loc[df.c == "b", "x":"y1"])
        
        cdict = {"red":     [tuple(r_array[k,:]) for k in range(r_array.shape[0])],
                 "green":   [tuple(g_array[k,:]) for k in range(g_array.shape[0])],
                 "blue":    [tuple(b_array[k,:]) for k in range(b_array.shape[0])]}
        
        cmap = colors.LinearSegmentedColormap(name=name, segmentdata=cdict, N=N, gamma=gamma)
        
        if register:
            register_colormap(cmap, name=name, prefix=prefix, N=N, gamma=gamma)
        
        return cmap
    
    elif all([s in df.columns for s in ("r","g","b")]):
        # listed color map
        cmap = colors.ListedColormap(np.aray(df), name=name, N=N)
        if register:
            register_colormap(cmap, name=name, prefix=prefix, N=N, gamma=gamma)
        
        return cmap
    
    else:
        raise RuntimeError("Cannot interpret %s" % filename)
    
def save_colormap(cmap:typing.Union[colors.LinearSegmentedColormap, colors.ListedColormap],
                  filename:typing.Optional[str]=None,
                  distribute:bool=False,
                  sep:str=","):
    """
    Saves the colormap to an ASCII file.
    
    Parameters:
    ===========
    cmap: a LinearSegmentedColormap or ListedColormap (both deifned in matplotlib.colors module)
    
    filename: str (optional, default is None)
        When given as a full path the colormap will be saved to this filename;
        the path can be relative tot he current working directory, or an absolute
        path.
        
        When filename does not contain a directory (i.e., only the basename of 
        the file is given) the file will be saved in Scipyen's configuration 
        directory - typically, $HOME/.config/Scipyen - or in the "rgb" directory
        of this module, depending on the "distribute" parameter (see next)
        
    distribute: bool, default is False
        Used to select the directory where the colormap is saved to, unless a
        directory name is already included in "filename".
        
        When False (default) the colormap is saved in Scipyen's configuration 
        directory - typically, $HOME/.config/Scipyen
        
        When True, the colormap is saved in the "rgb" sub-directory in Scipyen's
        "gui" directory, and thus it WILL be synchronized with the guthub repo
        (hence, "distributed"). NOTE that this requires write access to Scipyen's
        file tree.
        
    sep:str Separator character for the output file; default is "," (comma)
    """
        
    if isinstance(filename, str) and len(filename):
        # enforce "txt" extension
        filename = "%s.txt" % os.path.splitext(filename)[0]
    
    else:
        filename = "%s.txt" % cmap.split(".")[-1] # remove any possible prefix
        
        
    # prepend the config directory if filename not given as full path
    if len(os.path.dirname(filename)) == 0:
        if distribute:
            targetdir = os.path.join(os.path.dirname(__file__), "rgb")
            
        else:
            targetdir = scipyenconf.scipyen_config_dir
        
        filename = os.path.join(targetdir, filename)
    
    if isinstance(cmap, colors.LinearSegmentedColormap):
        r_array = np.array(cmap._segmentdata["red"])
        r_data = np.concatenate([np.atleast_2d(["r"] * r_array.shape[0]).T, r_array], axis=1)
        g_array = np.array(cmap._segmentdata["green"])
        g_data = np.concatenate([np.atleast_2d(["g"] * g_array.shape[0]).T, g_array], axis=1)
        b_array = np.array(cmap._segmentdata["blue"])
        b_data = np.concatenate([np.atleast_2d(["b"] * b_array.shape[0]).T, b_array], axis=1)
        
        rgb_data = np.concatenate([r_data, g_data, b_data], axis=0)
        
        df = pd.DataFrame({"c":rgb_data[:,0], "x":rgb_data[:,1], "y0":rgb_data[:,2], "y1":rgb_data[:,3]})
        
    elif isinstance(cmap, colors.ListedColormap):
        rgb_array = np.array(cmap.colors)
        df = pd.DataFRame({"r":rgb_array[:,0], "g":rgb_array[:,1], "b":rgb_array[:,2]})
        
    else:
        return
    
    try:
        df.to_csv(filename, index=False) # will raise OSError i user cannot wite to the desination directory
        
    except:
        traceback.print_exc()
    
    
    

cm.register_cmap(name="None", cmap=cm.get_cmap(name="gray"))

register_colormaps(CustomColorMaps)
    
