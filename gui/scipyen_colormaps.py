"""scipyen_colormaps

Brings matplotlib's cm and colors modules together with cmocean (if available)

and our ow custom color maps

"""
import os,traceback, warnings
import numbers
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
from traitlets import Bunch
from PyQt5 import QtCore, QtGui

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

standardPalette = (
    (255, 255, 255), # "white"
    (192, 192, 192), # "light gray"
    (160, 160, 160), # "gray"
    (128, 128, 128), # "dark gray"
    (  0,   0,   0), # "black"
    (255, 128, 128), # "light red"
    (255, 192, 128), # "light orange"
    (255, 255, 128), # "light yellow"
    (128, 255, 128), # "light green"
    (128, 255, 255), # "cyan blue"
    (128, 128, 255), # "light blue"
    (255, 128, 255), # "light violet"
    (255,   0,   0), # "red"
    (255, 128,   0), # "orange"
    (255, 255,   0), # "yellow"
    (  0, 255,   0), # "green"
    (  0, 255, 255), # "light blue"
    (  0,   0, 255), # "blue"
    (255,   0, 255), # "violet"
    (128,   0,   0), # "dark red"
    (128,  64,   0), # "dark orange"
    (128, 128,   0), # "dark yellow"
    (  0, 128,   0), # "dark green"
    (  0, 128, 128), # "dark light blue"
    (  0,   0, 128), # "dark blue"
    (128,   0, 128)  # "dark violet"
)

standardPaletteDict = Bunch({
    "white":            (255, 255, 255), # 
    "light gray":       (192, 192, 192), # 
    "gray":             (160, 160, 160), # 
    "dark gray":        (128, 128, 128), # 
    "black":            (  0,   0,   0), # 
    "light red":        (255, 128, 128), # 
    "light orange":     (255, 192, 128), # 
    "light yellow":     (255, 255, 128), # 
    "light green":      (128, 255, 128), # 
    "cyan blue":      (128, 255, 255), # 
    "light blue":       (128, 128, 255), # 
    "light violet":     (255, 128, 255), # 
    "red":              (255,   0,   0), # 
    "orange":           (255, 128,   0), # 
    "yellow":           (255, 255,   0), # 
    "green":            (  0, 255,   0), # 
    "light blue":       (  0, 255, 255), # 
    "blue":             (  0,   0, 255), # 
    "violet":           (255,   0, 255), # 
    "dark red":         (128,   0,   0), # 
    "dark orange":      (128,  64,   0), # 
    "dark yellow":      (128, 128,   0), # 
    "dark green":       (  0, 128,   0), # 
    "dark light blue":  (  0, 128, 128), # 
    "dark blue":        (  0,   0, 128), # 
    "dark violet":      (128,   0, 128)  # 
})

svgPalette = Bunch(
    aliceblue	= (240, 248, 255),
    antiquewhite	= (250, 235, 215),
    aqua	= ( 0, 255, 255),
    aquamarine	= (127, 255, 212),
    azure	= (240, 255, 255),
    beige	= (245, 245, 220),
    bisque	= (255, 228, 196),
    black	= ( 0, 0, 0),
    blanchedalmond	= (255, 235, 205),
    blue	= ( 0, 0, 255),
    blueviolet	= (138, 43, 226),
    brown	= (165, 42, 42),
    burlywood	= (222, 184, 135),
    cadetblue	= ( 95, 158, 160),
    chartreuse	= (127, 255, 0),
    chocolate	= (210, 105, 30),
    coral	= (255, 127, 80),
    cornflowerblue	= (100, 149, 237),
    cornsilk	= (255, 248, 220),
    crimson	= (220, 20, 60),
    cyan	= ( 0, 255, 255),
    darkblue	= ( 0, 0, 139),
    darkcyan	= ( 0, 139, 139),
    darkgoldenrod	= (184, 134, 11),
    darkgray	= (169, 169, 169),
    darkgreen	= ( 0, 100, 0),
    darkgrey	= (169, 169, 169),
    darkkhaki	= (189, 183, 107),
    darkmagenta	= (139, 0, 139),
    darkolivegreen	= ( 85, 107, 47),
    darkorange	= (255, 140, 0),
    darkorchid	= (153, 50, 204),
    darkred	= (139, 0, 0),
    darksalmon	= (233, 150, 122),
    darkseagreen	= (143, 188, 143),
    darkslateblue	= ( 72, 61, 139),
    darkslategray	= ( 47, 79, 79),
    darkslategrey	= ( 47, 79, 79),
    darkturquoise	= ( 0, 206, 209),
    darkviolet	= (148, 0, 211),
    deeppink	= (255, 20, 147),
    deepskyblue	= ( 0, 191, 255),
    dimgray	= (105, 105, 105),
    dimgrey	= (105, 105, 105),
    dodgerblue	= ( 30, 144, 255),
    firebrick	= (178, 34, 34),
    floralwhite	= (255, 250, 240),
    forestgreen	= ( 34, 139, 34),
    fuchsia	= (255, 0, 255),
    gainsboro	= (220, 220, 220),
    ghostwhite	= (248, 248, 255),
    gold	= (255, 215, 0),
    goldenrod	= (218, 165, 32),
    gray	= (128, 128, 128),
    grey	= (128, 128, 128),
    green	= ( 0, 128, 0),
    greenyellow	= (173, 255, 47),
    honeydew	= (240, 255, 240),
    hotpink	= (255, 105, 180),
    indianred	= (205, 92, 92),
    indigo	= ( 75, 0, 130),
    ivory	= (255, 255, 240),
    khaki	= (240, 230, 140),
    lavender	= (230, 230, 250),
    lavenderblush	= (255, 240, 245),
    lawngreen	= (124, 252, 0),
    lemonchiffon	= (255, 250, 205),
    lightblue	= (173, 216, 230),
    lightcoral	= (240, 128, 128),
    lightcyan	= (224, 255, 255),
    lightgoldenrodyellow	= (250, 250, 210),
    lightgray	= (211, 211, 211),
    lightgreen	= (144, 238, 144),
    lightgrey	= (211, 211, 211),
    lightpink	= (255, 182, 193),
    lightsalmon	= (255, 160, 122),
    lightseagreen	= ( 32, 178, 170),
    lightskyblue	= (135, 206, 250),
    lightslategray	= (119, 136, 153),
    lightslategrey	= (119, 136, 153),
    lightsteelblue	= (176, 196, 222),
    lightyellow	= (255, 255, 224),
    lime	= ( 0, 255, 0),
    limegreen	= ( 50, 205, 50),
    linen	= (250, 240, 230),
    magenta	= (255, 0, 255),
    maroon	= (128, 0, 0),
    mediumaquamarine	= (102, 205, 170),
    mediumblue	= ( 0, 0, 205),
    mediumorchid	= (186, 85, 211),
    mediumpurple	= (147, 112, 219),
    mediumseagreen	= ( 60, 179, 113),
    mediumslateblue	= (123, 104, 238),
    mediumspringgreen	= ( 0, 250, 154),
    mediumturquoise	= ( 72, 209, 204),
    mediumvioletred	= (199, 21, 133),
    midnightblue	= ( 25, 25, 112),
    mintcream	= (245, 255, 250),
    mistyrose	= (255, 228, 225),
    moccasin	= (255, 228, 181),
    navajowhite	= (255, 222, 173),
    navy	= ( 0, 0, 128),
    oldlace	= (253, 245, 230),
    olive	= (128, 128, 0),
    olivedrab	= (107, 142, 35),
    orange	= (255, 165, 0),
    orangered	= (255, 69, 0),
    orchid	= (218, 112, 214),
    palegoldenrod	= (238, 232, 170),
    palegreen	= (152, 251, 152),
    paleturquoise	= (175, 238, 238),
    palevioletred	= (219, 112, 147),
    papayawhip	= (255, 239, 213),
    peachpuff	= (255, 218, 185),
    peru	= (205, 133, 63),
    pink	= (255, 192, 203),
    plum	= (221, 160, 221),
    powderblue	= (176, 224, 230),
    purple	= (128, 0, 128),
    red	= (255, 0, 0),
    rosybrown	= (188, 143, 143),
    royalblue	= ( 65, 105, 225),
    saddlebrown	= (139, 69, 19),
    salmon	= (250, 128, 114),
    sandybrown	= (244, 164, 96),
    seagreen	= ( 46, 139, 87),
    seashell	= (255, 245, 238),
    sienna	= (160, 82, 45),
    silver	= (192, 192, 192),
    skyblue	= (135, 206, 235),
    slateblue	= (106, 90, 205),
    slategray	= (112, 128, 144),
    slategrey	= (112, 128, 144),
    snow	= (255, 250, 250),
    springgreen	= ( 0, 255, 127),
    steelblue	= ( 70, 130, 180),
    tan	= (210, 180, 140),
    teal	= ( 0, 128, 128),
    thistle	= (216, 191, 216),
    tomato	= (255, 99, 71),
    turquoise	= ( 64, 224, 208),
    violet	= (238, 130, 238),
    wheat	= (245, 222, 179),
    white	= (255, 255, 255),
    whitesmoke	= (245, 245, 245),
    yellow	= (255, 255, 0),
    yellowgreen	= (154, 205, 50),
    )

qtGlobalColors = Bunch((x,n) for x, n in vars(QtCore.Qt).items() if isinstance(n, QtCore.Qt.GlobalColor))
qtGlobalColorsQual = Bunch(("QtCore.Qt.%s" % x,n) for x, n in vars(QtCore.Qt).items() if isinstance(n, QtCore.Qt.GlobalColor))

# NOTE: 2021-05-17 15:44:15 Matplotlib color palettes are dicts that map a color
# name (str) to a str in the "#rrggb" format EXCEPT for BASE_COLORS where the 
# name is mapped to a 3- tuple of r, g, b floats (0-1)!
mplBase = Bunch((x, mpl.colors.rgb2hex(tuple(float(v) for v in y))) for x,y in colors.BASE_COLORS.items())    # matplotlib base colors
mplCSS4 = Bunch(colors.CSS4_COLORS)    # matplotlib X11/CSS4 colors - the same as matplotlib's SVG palette
mplTab  = Bunch(colors.TABLEAU_COLORS) # matplotlib Tableau colors
mplXKCD = Bunch(colors.XKCD_COLORS)    # matplotlib XKCD colors

mplColors = Bunch()
for d in (mplBase, mplCSS4, mplTab, mplXKCD):
    mplColors.update(d)
    
del d

# NOTE: 2021-05-17 10:11:57
# About color lookup tables ImageJ "style"
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

def rgb2mpl(val:typing.Union[list, tuple]):
    """Converts Qt style R, G, B (int) triplet into matplotlib R,G,B (float).
    Performs the inverse of mpl2rgb.
    """
    if not isinstance(val, (tuple, list)):
        raise TypeError("Expecting a sequence; got %s instead" % str(val))
    
    if all((v >= 0 and v <= 1 for v in val)):
        if len(val) != 3:
            raise ValueError("Expecting an R, G, B triplet; got %s instead" % str(val))
        return val
    
    elif all((isinstance(v, int) and v in range(256) for v in val)):
        if len(val) not in range(3,5):
            raise ValueError("Expecting an R, G, B (A) sequence; got %s instead" % str(val))
        return tuple((v/255. for v in val[0:3]))
    
    else:
        raise ValueError("Sequence must contain floats in [0,1] or integers in [0,255]")
        
def mpl2rgb(val:typing.Union[list, tuple]):
    """Converts matplotlib style R,G,B (float) triplet into Qt R, G, B (int)
    Performs the inverse of rgb2mpl.
    """
    if not isinstance(val, (tuple, list)):
        raise TypeError("Expecting a sequence; got %s instead" % str(val))
    if len(val) != 3:
        raise ValueError("Expecting an R, G, B triplet; got %s instead" % str(val))
    
    if all((v >= 0 and v <= 1 for v in val)):
        return tuple((int(v*255) for v in val))
    
    elif all((isinstance(v, int) and v in range(256) for v in val)):
        return val
    
    else:
        raise ValueError("Sequence must contain floats in [0,1] or integers in [0,255]")
        
def qcolor(val):
    if isinstance(val, QtGui.QColor):
        return val
    
    elif isinstance(val, (tuple, list)):
        return QtGui.QColor.fromRgb(*mpl2rgb(val))
    
    elif isinstance(val, str):
        if QtGui.QColor.isValidColor(val):
            return QtGui.QColor(val)
        
        elif val in standardPaletteDict:
            return QtGui.QColor.fromRgb(standardPaletteDict[val])
            
        elif val in svgPalette:
            return QtGui.QColor.fromRgb(svgPalette[val])
        
        elif val in qtGlobalColors:
            return QtGui.QColor(val)
        
        elif val in mplColors:
            return QtGui.QColor(mplColors[val])
        
        elif val in mplColors.values():
            return QtGui.QColor(val)
        
    else:
        raise TypeError("Expecting a QColor, numeric 3- or 4-tuple, or str (color name or Hex representation); got %s instead" % val)
            
        

def standardQColor(i:int) -> QtGui.QColor:
    return paletteQColor(standardPalette, i)

def svgQColor(i:str) -> QtGui.QColor:
    return paletteQColor(svgPalette, i)

def getPalette(name:str="std"):
    """Returns a defined palette in this module by its module symbol (name).
    
    If no such symbol exist, return standardPalette by default
    
    """
    if len(name.strip()) == 0:
        return
    
    name = name.lower()
    
    if name in ("std", "kde", "standard"):
        return standardPalette
    
    elif name in ("stdd", "kded", "standardd"):
        return standardPaletteDict
    
    elif name in ("svg",  "x11"):
        return svgPalette
    
    elif name in ("base", "mplbase"):
        return mplBase
    
    elif name in ("css",  "css4", "mplcss", "mplcss4", "mplx11"):
        return mplCSS4
    
    elif name in ("tab",  "mpltab"):
        return mplTab
    
    elif name in ("kxcd", "mplkxcd"):
        return mplXKCD
    
    elif name in ("mpl",  "mat"):
        return mplColors
    
    elif name in ("qt",):
        return qtGlobalColors
    
    elif name ("a", "all"):
        ret = dict()
        for d in (standardPaletteDict,qtGlobalColors,svgPalette,mplColors):
            ret.update(d)
            
        return ret
    
    else:
        return standardPalette
    
    
def genPaletteQColor(x) -> typing.Generator[QtGui.QColor, None, None]:
    """QColor generator from color palette entries.
    
    To use, call 'next(...)', or better still pass a default value as well, i.e.:
    next(..., QtGui.QColor()) e.g.:
    
    [next(c) for c in map(genPaletteQColor, standardPalette)] -> list of QtGui.QColor objects
    
    or
    
    [next(c, QGui.QColor()) for c in map(genPaletteQColor, standardPalette)] -> list of QtGui.QColor objects
    
    """
    if isinstance(x, (tuple, list)) and len(x) in (3,4):
        if all([isinstance(v, int) for v in x]):
            yield QtGui.QColor(*x)
            
        elif all([isinstance(v, float) for v in x]):
            yield QtGui.QColor(*(map(lambda f: int(round(f*255)), x))) # convert 0..1 float into 0..25 int values
    
    elif isinstance(x, (QtGui.QColor, QtCore.Qt.GlobalColor)):
        yield QtGui.QColor(x)
    
    elif isinstance(x, str) and len(x.strip()):
        #print("x", x)
        parts = x.lower().split(".")
        if len(parts) > 1:
            if any(s in x for s in ["qt", "qtcore"]):#  Qt global colors
                yield QtGui.QColor(eval("QtCore.Qt.%s" % parts[-1]))
            elif any([s in parts for s in ("std", "kde", "standard")]):
                yield QtGui.QColor(standardPaletteDict[parts[-1]])
            elif any([s in parts for s in ("svg", "x11")]):
                yield QtGui.QColor(svgPalette[parts[-1]])
            elif any([s in parts for s in ("base", "mplbase")]):
                yield QtGui.QColor(mplBase[parts[-1]])
            elif any([any([s in p for s in ("css", "mplx11")] for p in parts)]):
                yield QtGui.QColor(mplCSS4[parts[-1]])
            elif any(["tab" in p for p in parts]):
                yield QtGui.QColor(mplTab[parts[-1]])
            elif any(["xkcd" in p for p in parts]):
                yield QtGui.QColor(mplXKCD[parts[-1]])
            #elif any([s in parts for s in ("mpl", "mat")]):
            elif any([any([s in p for s in ("mpl", "mat")] for p in parts)]):
                yield QtGui.QColor(mplColors[parts[-1]])
                
            yield QtGui.QColor() # invalid color
            
        elif len(parts) == 1:
            if parts[0] in qtGlobalColors.keys():
                yield qtGlobalColors[parts[0]]
            elif parts[0].startswith("#"): # #rgb or rgba format
                yield QtGui.QColor(parts[0])
            else:
                yield QtGui.QColor(parts[0]) # may be invalid!
            
    yield QtGui.QColor() # invalid color
        
        
def paletteQColors(palette:typing.Union[dict, tuple, list, str]) -> typing.Generator[typing.Iterator[QtGui.QColor],
                                                                                None,
                                                                                None]:
    """Iterates color entries in a color palette
    
    Parameters: 
    ===========
    WARNING: the type of the parameters is not checked; if any exception are 
    raised the function will return an invalid QColor.

    palette: A sequence, a mapping, or a str (palette name)
        When a sequence, its elements can be:
        a) sequences of 3 or 4 int elements: (r, g, b) , or (r, g, b, a)
            (with 3 elements alpha channel a = 255 is implied)
        b) QtCore.Qt.GlobalColor objects
        c) QtGui.QColor objects
        d) str - color name
            Either a simple color name (e.g., "red") - represeting an internal
            Qt.GlobalColor (e.g. QtCore.Qt.red)
            
            or name qualified by dot-separated prefix e.g. "QtCore.Qt.red" 
            (which in this example evaluates to the same color as above); 
            
            Allowed values for the prefix are (case-insensitive):
            "Qt", "QtCore", "QtCore.Qt", "standard", and "SVG"
            
            this form allows the indirect  use of colors from several pre-defined
            palettes including the Qt.GlobalColor and palettes that store colors
            as name = value mapping.
            
        When a mapping (dict), it must contain str keys mapped to:
            a) tuples of int values with 3 or 4 elements as above
            b) a QtCore.Qt.GlobalColor object,
            c) QtGui.QColor object
            d) a str (another color name, either simple or qualified as above)
            
        When a str, this identifies a registered color palette.
        
        Currently registered color palettes are gioen in the next table:
        
        Palette name            Type    Identifiers                 Comments:
        ========================================================================
        "standardPalette"       list    "std",  "kde",  "standard", standard KDE
        "standardPaletteDict"   dict    "stdd", "kded", "standardd" standard KDE
        "qtGlobalColor"         dict    "qt"                        Qt.GlobalColor colors
        "svgPalette"            dict    "svg",  "x11"               X11/SVG standard
        "mplBase"               dict    "base", "mplbase"           matplotlib base
        "mplCSS4"               dict    "css",  "css4", "mplcss",   matplotlib CSS/X11
                                        "mplcss4", "mplx11"
        "mplTab"                dict    "tab",  "mpltab"            matplotlib TABLEAU
        "mplKXCD"               dict    "kxcd", "mplkxcd"           matplotlib KXCD colors
        "mplColors"             dict    "mpl",  "mat"               all matplotlib
                                                                    paletted listed above
                                                                    merged into a dict
        <no name>               dict    "all", "a"                  All of the above
                                                                    merged into a dict
        ========================================================================
    """
    if isinstance(palette, dict):
        iterable = palette.values()
    else:
        iterable = palette

    return (next(c, QtGui.QColor()), palette)

def paletteQColor(palette:typing.Union[dict, list, tuple, str], index:typing.Union[int, str]) -> QtGui.QColor:
    """Retrieve color entry from a color palette.
    
    Parameters: 
    ===========
    WARNING: the type of the parameters is not checked; if any exception are 
    raised the function will return an invalid QColor.

    palette: A sequence, a mapping, or a str (palette name)
        When a sequence, its elements can be:
        a) sequences of 3 or 4 int elements: (r, g, b) , or (r, g, b, a)
            (with 3 elements alpha channel a = 255 is implied)
        b) QtCore.Qt.GlobalColor objects
        c) QtGui.QColor objects
        d) str - color name
            Either a simple color name (e.g., "red") - represeting an internal
            Qt.GlobalColor (e.g. QtCore.Qt.red)
            
            or name qualified by dot-separated prefix e.g. "QtCore.Qt.red" 
            (which in this example evaluates to the same color as above); 
            
            Allowed values for the prefix are (case-insensitive):
            "Qt", "QtCore", "QtCore.Qt", "standard", and "SVG"
            
            this form allows the indirect  use of colors from several pre-defined
            palettes including the Qt.GlobalColor and palettes that store colors
            as name = value mapping.
            
        When a mapping (dict), it must contain str keys mapped to:
            a) tuples of int values with 3 or 4 elements as above
            b) a QtCore.Qt.GlobalColor object,
            c) QtGui.QColor object
            d) a str (another color name, either simple or qualified as above)
            
        When a str, this identifies a registered color palette.
        
        Currently registered color palettes are gioen in the next table:
        
        Palette name            Type    Identifiers                 Comments:
        ========================================================================
        "standardPalette"       list    "std",  "kde",  "standard", standard KDE
        "standardPaletteDict"   dict    "stdd", "kded", "standardd" standard KDE
        "svgPalette"            dict    "svg",  "x11"               X11/SVG standard
        "mplBase"               dict    "base", "mplbase"           matplotlib base
        "mplCSS4"               dict    "css",  "css4", "mplcss",   matplotlib CSS/X11
                                        "mplcss4", "mplx11"
        "mplTab"                dict    "tab",  "mpltab"            matplotlib TABLEAU
        "mplKXCD"               dict    "kxcd", "mplkxcd"           matplotlib KXCD colors
        "mplColors"             dict    "mpl",  "mat"               all matplotlib
                                                                    paletted listed above
                                                                    merged into a dict
                                                                    
        ========================================================================
                                                                    
    index: int or str
        Index into the palette. 
        
        For sequence palettes this is expected to be an int with value in the 
        semi-open interval [0 - len(palette)).
        
        For dict palettes, this should be a str and present among the palette's 
        keys.
        
    
    """
    if isinstance(palette, str):
        palette = getPalette(palette)
    try:
        entry = palette[index] # CAUTION 2021-05-17 11:21:42 raise error if index is inappropriate for palette
        return next(genPaletteQColor(entry), QtGui.QColor())
            
    except:
        return QtGui.QColor()
        
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
    
