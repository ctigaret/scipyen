"""scipyen_colormaps

Brings matplotlib's cm and colors modules together with cmocean (if available)

and our ow custom color maps

Currently registered color palettes:

Palette name            Type    Id          Values          Comments:
================================================================================
"standardPalette"       list    "std",      (r,g,b)         standard KDE    
                                "kde",      tuple of int
                                "standard"
                                                                
"standardPaletteDict"   dict    "stdd",     as above        standard KDE
                                "kded", 
                                "standardd"

"svgPalette"            dict    "svg",      as above        X11/SVG standard
                                "x11"

"qtGlobalColors"        dict    "qt"        int (0..19)     Qt standard

"qtGlobalColorsQual"    dict    "qqt"       as above        Qt standard;
                                                            Keys are 'qualified'
                                                            e.g. 'QtCore.Qt.blue'
                                                            instead of 'blue'
                                                            
"mplBase"               dict    "base",     str, in hex     matplotlib base
                                "mplbase"   format          colors
                                            (#rrggbb)              
                                            
"mplCSS4"               dict    "css",      as above        matplotlib CSS/X11
                                "css4",                     colors (same as
                                "mplcss",                   X11/SVG standard)
                                "mplcss4", 
                                "mplx11"
                                
"mplTab"                dict    "tab",      as above        matplotlib TABLEAU
                                "mpltab"                    colors
                                
"mplKXCD"               dict    "kxcd",     as above        matplotlib KXCD
                                "mplkxcd"                   colors    
                                
"mplColors"             dict    "mpl",      as above        all of matplotlib
                                "mat"                       paletted merged 
                                                            into a dict
                                                            
================================================================================
"""
import os,traceback, warnings, inspect
import numbers
import itertools
import types
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
from core.utilities import unique

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
    papayawhip	 = (255, 239, 213),
    peachpuff	= (255, 218, 185),
    peru	= (205, 133, 63),
    pink	= (255, 192, 203),
    plum	= (221, 160, 221),
    powderblue	 = (176, 224, 230),
    purple = (128, 0, 128),
    red	= (255, 0, 0),
    rosybrown	= (188, 143, 143),
    royalblue	= ( 65, 105, 225),
    saddlebrown	= (139, 69, 19),
    salmon	 = (250, 128, 114),
    sandybrown	 = (244, 164, 96),
    seagreen	= ( 46, 139, 87),
    seashell	= (255, 245, 238),
    sienna	 = (160, 82, 45),
    silver	 = (192, 192, 192),
    skyblue	= (135, 206, 235),
    slateblue	= (106, 90, 205),
    slategray	= (112, 128, 144),
    slategrey	= (112, 128, 144),
    snow	= (255, 250, 250),
    springgreen 	= ( 0, 255, 127),
    steelblue 	= ( 70, 130, 180),
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

all_palettes = Bunch(
    standardColors=standardPaletteDict,
    qtGlobalColors=qtGlobalColors,
    svgColors=svgPalette,
    matlabColors=mplColors,
    )
        
class ColorPalette(object):
    def __init__(self, collection_name:typing.Optional[str]="all", fmt:QtGui.QColor.NameFormat=QtGui.QColor.HexRgb,
                 **color_collections):
        """
        collection_name: str (optional, default is "all")
            Only used when color_collections (see below) is empty
            
        color_collections: mapping name:str = color_collection:dict 
            
            Each color collection is either:
            * a mapping name:str = colorspec:(as below)
            * a sequence (tuple, list) of colorspecs
            
            A colorspec is either:
            * a hexformat str (#rrggbb or #aarrggbb)
            * a str (found as key in any of the other color collection dicts)
                -> useful for making aliases to defined colors
            * a 3-tuple (R, G, B) of:
                - float with values in [0,1] (matplotlib style)
                - int with values in [0,255] (Qt style)
            * a 4-tuple (R, G, B, A) of int with values in [0,1] (Qt style)
            * an int (with value in range(20)) or QtCore.QtGlobalColor
            
        fmt: QtGui.QColor.NameFormat (either QtGui.QColor.HexRgb or QtGui.QColor.HexArgb)
            For creating string representations of color.name()

        """
        
        #print(f"ColorPalette._init__({collection_name},{color_collections})")
        
        if isinstance(fmt, bool):
            fmt = QtGui.QColor.HexArgb if fmt else QtGui.QColor.HexRgb
            
        elif isinstance(fmt, int):
            fmt = QtGui.QColor.HexRgb if fmt == 0 else QtGui.QColor.HexArgb
            
        elif not isinstance(fmt, QtGui.QColor.NameFormat):
            raise TypeError("'fmt' expected to be a QtGui.QColor.NameFormat, injt or bool; got %s instead" % type(fmt).__name__)
        
        self._fmt_ = fmt
        
        if len(color_collections) == 0:
            if isinstance(collection_name, str):
                g = globals()
                
                if isinstance(g.get(collection_name, None), Bunch):
                    color_collections.update({collection_name: g[collection_name]})
                    
                elif collection_name in ("a", "all"):
                    color_collections.update(all_palettes)
                    
                else:
                    color_collections.update({collection_name: getPalette(collection_name)})
                
        self._mappings_ = Bunch((n, m if isinstance(m, dict) else Bunch(map(lambda x: (get_name_color(x, "all")[0], x), m))) for n,m in color_collections.items())
        
    def __getitem_mappings__(self, key):#, default=None):
        yield from (m.get(key, None) for m in self._mappings_.values())
        #yield from (m.get(key, default) for m in self._mappings_.values())
        
    def __contains__(self, key):
        """Implements 'key in obj' idiom.
        Note that this is a strict comparison and therefore useful for testing
        existence of a color name in this palette.
        
        NOTE that a color 'name' is the free-form str - the name assigned to a 
        color in the palette, which is not necessarily the hex rgb or hex argb 
        string format returned by QtGui.QColor.name()
        
        For loose comparisons, see self.has_color() and self.has_color_name()
        """
        return key in self.keys()
    
    def has_color(self, color_or_spec):
        """
        """
        if isinstance(color_or_spec, QtGui.QColor):
            hexspec = color_or_spec.name(self._fmt_)
            rgbspec = color_or_spec.getRgb()
            frgbspec = color_or_spec.getRgbF() # matlab style floats
            
            return any(map(lambda x: any(self._eq_spec_(x, y, False, False) for y in (hexspec, rgbspec, frgbspec)), self.values()))
            
        return any(map(lambda x: self._eq_spec_(color_or_spec, x, False, False), self.values()))
        
    def has_color_name(self, name):
        """Alias for 'name in self'
        """
        return name in self.keys()
    
    def name_index(self, name):
        """Get the index of name in self.keys()
        Python3.6: Order of key/value pairs is guaranteed to be the same with 
        every iteration
        """
        return self.index(name, as_key=True)
        #if self.has_color_name(name):
            #return [k for k in self.keys()].index(name)
            
    def index(self, color_or_spec, as_key=False):
        """Get the index of the color or color spec in sef.values()
        Python3.6: Order of key/value pairs is guaranteed to be the same with 
        every iteration
        """
        if isinstance(color_or_spec, QtGui.QColor):
            hexspec = color_or_spec.name(self._fmt_)
            rgbspec = color_or_spec.getRgb()
            frgbspec = color_or_spec.getRgbF() # matlab style floats
            ndx = [k[0] for k in filter(lambda x: any(self._eq_spec_(x[1], y, False, False) for y in (hexspec,rgbspec,frgbspec)), enumerate(self.values()))]

        else:
            if as_key and self.has_color_name(color_or_spec):
                return [k for k in self.keys()].index(color_or_spec)
            
            ndx = [k[0] for k in filter(lambda x: self._eq_spec_(x[1], color_or_spec, False, False), enumerate(self.values()))]
            
        if len(ndx):
            if len(ndx) == 1:
                return ndx[0]
            
            return ndx
            
    
    def __getitem__(self, key):
        """Implements obj[key] (subscript access, or "bracket syntax"").
        Returns a colorspec, a tuple of colorspecs (if key is present several times)
        or None if key is not found.
        """
        if key in self.keys():
            ret = tuple((v for v in self.__getitem_mappings__(key) if v is not None))
            
            if len(ret):
                if len(ret) > 1:
                    ret = unique(ret)
                if len(ret) == 1:
                    return ret[0]
                return ret
            
        elif key in self._mappings_:
            return self._mappings_[key]
            
    def __len__(self):
        return sum((len(m) for m in self._mappings_.values()))
            
    def __str__(self):
        from pprint import pformat
        d = dict((k,v) for k,v in self.items())
        return pformat(d)
    
    def __repr__(self):
        ret = [f"{self.__class__}"]
        ret.append(f"{len(self)}")
        ret.append(self.__str__())
        return "\n".join(ret)
    
    @staticmethod
    def _eq_spec_(x, y, cs, ts):
        """x, y: color specifications: string including hex strings, and numeric
        tuples (int or float)
        
        cs: bool: True specifies that str colorspec comparison is case-sensitive
        
        For hex strings, when one of the specs is of the form #rrggbb and the 
        other is #aarrggbb then the shorter one is augmented with 'ff'
        
        ts:bool: True specifies that tuple colorspec comparison is strict, i.e.,
            len of the tuple and type of the tuple's elements must be the same
            When False, the following happens:
            
            1) when at least one of the compared specs contains floats, the other
            is converted to floats by normalizing the values to 255
            
            when one spec is a 3-tuple, and the other is a 4-tuple, the shorter
            spec is epxanded with the maximum alpha value (either int 255 or 
            float 1.0, depending on the tuple's element type)
        
        """
        if isinstance(x, str) and isinstance(y, str):
            if x.startswith("#") and y.startswith("#"):
                if len(x) == 7 and len(y) == 9:
                    x = f"#ff{x[1:]}" if x.islower() else f"#FF{x[1:]}"
                elif len(x) == 9 and len(y) == 7:
                    y = f"#ff{y[1:]}" if y.islower() else f"#FF{y[1:]}"
                    
            #print(f"ColorPalette._eq_spec_: {x} vs {y}")
            if not cs:
                return x.lower() == y.lower()
            
            return x == y
        
        elif isinstance(x, tuple) and isinstance(y, tuple):
            if not ts:
                if all((isinstance(v, int) for v in list(x)+list(y))):
                    if len(x) == 3 and len(y) == 4:
                        x = tuple(list(x)+[255])
                        
                    if len(x) == 4 and len(y) == 3:
                        y = tuple(list(y)+[255])
                        
                    return x == y
                        
                else:
                    if all((isinstance(v, int) for v in x)) and all((isinstance(v, float) for v in y)):
                        # int x, float y
                        x = tuple(map(lambda v: float(v)/255, x))
                        
                    elif all((isinstance(v, float) for v in x)) and all((isinstance(v, int) for v in y)):
                        # float x and int y
                        y = tuple(map(lambda v: float(v)/255, y))
                        
                    if len(x) == 3 and len(y) == 4:
                        x = tuple(list(x)+[1.])
                        
                    if len(x) == 4 and len(y) == 3:
                        y = tuple(list(y)+[1.])
                        
                    return x == y
                
            return x == y
                    
        return x == y
            
    def _make_qcolor_(self, colorspec):
        if isinstance(colorspec, (tuple, list)):
            if len(colorspec) in range(3,5) and all(isinstance(v, numbers.Number) for v in colorspec):
                return QtGui.QColor(*mpl2rgb(colorspec))
                #yield QtGui.QColor(*mpl2rgb(colorspec))
            
            else:
                return [q for q in map(lambda x: self._make_qcolor_(x), colorspec)]
                #yield from (self._make_qcolor_(spec) for spec in colorspec)
            
        elif isinstance(colorspec, str):
            if QtGui.QColor.isValidColor(colorspec):
                return QtGui.QColor(colorspec)
                #yield QtGui.QColor(colorspec)

        elif isinstance(colorspec, QtCore.Qt.GlobalColor):
            return QtGui.QColor(colorspec)
            #yield QtGui.QColor(colorspec)
            
        elif isinstance(colorspec, int) and colorspec in range(20):
            return QtGui.QColor(colorspec)
            #yield QtGui.QColor(colorspec)
        
    def values(self):
        """Iterator for the color specs in this palette
        """
        #yield from itertools.chain(*((lambda x: x if not isinstance(x, str) else x if case_sensitive else x.lower() for x in m.values()) for m in self._mappings_.values()))
        yield from itertools.chain(*(m.values() for m in self._mappings_.values()))

    def keys(self):
        """Iterator for color names in this palette
        """
        yield from itertools.chain(*(m.keys() for m in self._mappings_.values()))
        
    def items(self):
        """Iterator for (color name, color spec) in the ColorPalette's collections
        """
        #yield from itertools.chain(*((lambda x: (x[0], x[1] if not isinstance(x, str) else x if case_sensitive else x.lower()) for x in m.items()) for m in self._mappings_.values()))
        yield from itertools.chain(*(m.items() for m in self._mappings_.values()))
        
    @property
    def color_collections(self):
        """Iterates through the color collections used in this ColorPalette
        """
        yield from self._mappings_.value()
        
    def color_collection(self, name):
        """Returns a color collection in this ColorPalette palette by its name
        """
        return self._mappings_.get(name, None)
    
    @property
    def nameFormat(self):
        return self._fmt_
    
    @nameFormat.setter
    def nameFormat(self, val:QtGui.QColor.NameFormat=QtGui.QColor.HexRgb):
        self._fmt_ = val
        
    @property
    def collection_names(self):
        """Iterator for the color collection names in this ColorPalette
        """
        yield from self._mappings_.keys()
    
    @property
    def contents(self):
        """Iterator (name, color collection) for this ColorPalette
        """
        yield from self._mappings_.items()
        
    @property
    def number_of_collections(self):
        return len(self._mappings_)
    
    @property
    def qcolors(self):
        """Iterator for the QColor objects encoded in this ColorPalette
        """
        yield from map(lambda x: next(self._make_qcolor_(x)), self.values())
        
    @property
    def named_qcolors(self):
        """Iterator for (name, QColor).
        'name' is the palette name of the QColor, which is not necessarily what
        is returned by QColor.name()
        """
        return map(lambda x: (x[0], self._make_qcolor_(x[1])), self.items())
        #yield from map(lambda x: (x[0], next(self._make_qcolor_(x[1]))), self.items())
        
    def qcolor(self, key):
        if isinstance(key, QtGui.QColor):
            return key
        #print(f"ColorPalette.qcolor({key})")
        colorspec = self[key]

        #ret = [q for q in next(self._make_qcolor_(colorspec))]
        ret = self._make_qcolor_(colorspec)
            
        if isinstance(ret, (tuple, list)) and len(ret):
            return ret[0]
        
        return ret
        
    def key(self, colorspec, show_source:bool=False, case_sensitive=False, tuple_strict=False):
        """Iterator for the keys (names) of the color given a colorspec.
        A colorspec may be mapped ot mroe than one key (or name)
        Optionally, the iterator contains the name of the color dictionary where
        the key->colorspec mapping resides, inside this ColorPalette
        """
        if show_source:
            yield from itertools.chain.from_iterable(((k,n) for k, v in m.items() if self._eq_spec_(v, colorspec, case_sensitive, tuple_strict)) for n,m in self._mappings_.items())
        else:
            yield from itertools.chain.from_iterable((k for k, v in m.items() if self._eq_spec_(v, colorspec, case_sensitive, tuple_strict)) for n,m in self._mappings_.items())
    
        #if show_source:
            #yield from itertools.chain.from_iterable(((k,n) for k, v in m.items() if v == colorspec) for n,m in self._mappings_.items())
        #else:
            #yield from itertools.chain.from_iterable((k for k, v in m.items() if v == colorspec) for n,m in self._mappings_.items())
    
    def colorname(self, spec:typing.Union[str, tuple, list, QtGui.QColor], 
                  show_source:bool=False, 
                  case_sensitive=False,
                  tuple_strict=False,
                  single:bool=False):
        if isinstance(spec, QtGui.QColor):
            spec = spec.name(self._fmt_)
            #print(f"ColorPalette.colorname(QColor): spec = {spec}")
            
        ret = unique([n for n in self.key(spec, show_source=show_source, 
                                          case_sensitive=case_sensitive, 
                                          tuple_strict=tuple_strict)])
        
        if len(ret):
            if single or len(ret) == 1:
                return ret[0]
            return ret

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
    
    if all((isinstance(v, float) and v >= 0 and v <= 1 for v in val)):
        if len(val) != 3:
            raise ValueError("Expecting an R, G, B triplet; got %s instead" % str(val))
        return tuple((map(lambda f: int(round(f*255)), val)))
    
    elif all((isinstance(v, int) and v in range(256) for v in val)):
        if len(val) not in range(3,5):
            raise ValueError("Expecting an R,G,B or R,G,B,A tuple; gt %s instead" % str(val))
        return val
    
    else:
        raise ValueError("Sequence must contain floats in [0,1] or integers in [0,255]")
        
def qcolor(val:typing.Union[QtGui.QColor, int, str, typing.Sequence[typing.Union[int, float]]]) -> QtGui.QColor:
    """Returns a QColor based on val.
    
    Parameters:
    ===========
    'val' QtGui.QColor, QtCore.Qt.GlobalColor, a str (standard color name) or a 
        colorspec, which is one of:
        * hex-format string (#rrggbb or #aarrggbb)
        * 3- or 4-tuple of int with values in [0,255] (R,G,B or A,R,G,B)
        * matplotlib style float triplet with values in [0,1] (r,g,b)
        
    Bypasses the palette lookup for all val types except when val is a str, in
    which case returns the color stored in ALL palettes registered with this
    module.
    """
    if isinstance(val, QtGui.QColor):
        return val
    
    elif isinstance(val, QtCore.Qt.GlobalColor):
        return QtGui.QColor(val)
    
    elif isinstance(val, (tuple, list)):
        return QtGui.QColor.fromRgb(*mpl2rgb(val))
    
    elif isinstance(val, int):
        if val in range(len(qtGlobalColors)):
            # 0, 1 and 19 are 'color0', 'color1' and the transparent color
            return QtGui.QColor(val)
        
        else:
            return QtGui.QColor() # invalid color!
    
    elif isinstance(val, str):
        if QtGui.QColor.isValidColor(val):
            # this should take care of hex string representations e.g. #ffaabbcc
            # as well as gobal color names e.g. "blue", "red", etc
            return QtGui.QColor(val)
        
        else: # this will almost never get executed but keep here as safety net
            palette = getPalette("all")
            
            if val in palette:
                return paletteQColor(palette, val)
                
            else:
                return QtGui.QColor()# invalid color!
    else:
        warnings.warn(f"Invalid color specification: {val}")
        return QtGui.QColor()# invalid color!
        #raise TypeError("Expecting a QColor, numeric 3- or 4-tuple, or str (color name or Hex representation); got %s instead" % val)
            
def hexpalette(palette:typing.Union[dict, tuple, list], alpha:bool=True) -> dict:
    fmt = QtGui.QColor.HexArgb if alpha else QtGui.QColor.HexRgb
    if isinstance(palette, dict):
        return dict((k, qcolor(c).name(fmt).lower()) for k,c in palette.items())
    
    elif isinstance(palette, (tuple, list)):
        return dict(("%i" % k, qcolor(c).name(fmt).lower()) for k,c in enumerate(palette))
    
    else:
        raise TypeError("Palette expected a dict or sequence; got %s instead" % type(palette).__name__)
        
def get_name_color(x:typing.Union[str, tuple, list, QtCore.Qt.GlobalColor, QtGui.QColor], 
                   palette:typing.Optional[typing.Union[dict, tuple, list, str, ColorPalette]]=None, 
                   alpha:bool=False,
                   case_sensitive=False,
                   tuple_strict=False) -> typing.Generator[typing.Tuple[str, QtGui.QColor], None, None]:
    """Return a tuple (color name, QColor) given 'x' and optionally, a palette.
    
    """
    fmt = QtGui.QColor.HexArgb if alpha else QtGui.QColor.HexRgb
    
    color = qcolor(x)
    
    
    if palette is None:
        palette = ColorPalette(fmt=fmt)
    
    #print(f"get_name_color: {x} -> color = {color}")
    
    if isinstance(palette, str):
        palette = getPalette(palette)
        
    elif isinstance(palette, (tuple, list)):
        palette = dict(map(lambda c: get_name_color(c,ColorPalette(palette=all_palettes)), palette))
        
    elif isinstance(palette, ColorPalette):
        if x in palette:
            #print(f"get_name_color from ColorPalette: {x} found")
            color = palette.qcolor(x)
            #print(f"get_name_color from ColorPalette: color = {color}")
            return(x, color)
            
        name = palette.colorname(color, 
                                 case_sensitive=case_sensitive, 
                                 tuple_strict=tuple_strict,
                                 single=True)
        
        if name is None:
            name = color.name(fmt)
        
        #print(f"get_name_color for {color} from ColorPalette: name = {name}")
        return (name, color)
        
    elif not isinstance(palette, dict):
        raise TypeError(f"'palette' expected a str, sequence, or dict; got {type(palette).__name__} instead")
        
    if palette:
        if isinstance(x, str):
            if x.startswith("#"):
                if len(x) == 7:
                    hpal = hexpalette(palette, alpha=False)
                elif len(x) == 9:
                    hpal = hexpalette(palette, alpha=True)
                else:
                    raise ValueError("%s is not a valid color string")
                
                if x in hpal.values():
                    nn,cc = zip(*hpal.items())
                    index = cc.index(x)
                    return (nn[index], QtGui.QColor(cc[index]))
                
            elif x in palette:
                return (x, paletteQColor(palette, x))
                
        elif isinstance(x, (tuple, list, int, QtCore.Qt.GlobalColor)):
            if x in palette.values():
                nn,cc = zip(*palette.items())
                index = cc.index(x)
                colorspec = cc[index]
                color = QtGui.QColor(*colorspec) if isinstance(colorspec, (tuple, list)) else QtGui.QColor(colorspec)
                return (nn[index], color)
            
        elif isinstance(x, QtGui.QColor):
            #print(x.name(fmt))
            hpal = hexpalette(palette, alpha=alpha)
            if x in hpal.values():
                nn,cc = zip(*hpal.items())
                index = cc.index(x)
                return (nn[index], QtGui.QColor(cc[index]))
                
    name = x if isinstance(x, str) else color.name(fmt) # fallback!
    return (name, color)
    
def standardQColor(i:int) -> QtGui.QColor:
    return paletteQColor(standardPalette, i)

def svgQColor(i:str) -> QtGui.QColor:
    return paletteQColor(svgPalette, i)

def getPalette(name:str="std"):
    """Returns a defined palette in this module by ann Id (str).
    
    If no such symbol exist, return standardPalette by default.
    For valid palette Id see module docstring
    
    In addition the Id "all" returns a dict with the following palettes merged:
    standardPaletteDict,qtGlobalColors,svgPalette,mplTab,mplXKCD
    
    (mplCSS4 is left out because it contains the same entries as the svgPalette)
    
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
        return mplCSS4 # same as svgPalette but in hexrgb format
    
    elif name in ("tab",  "mpltab"):
        return mplTab
    
    elif name in ("kxcd", "mplkxcd"):
        return mplXKCD
    
    elif name in ("mpl",  "mat"):
        return mplColors
    
    elif name in ("qt",):
        return qtGlobalColors
    
    elif name in ("a", "all"):
        ret = dict()
        for d in (qtGlobalColors,svgPalette,mplTab,mplXKCD):
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
    if isinstance(x, (tuple, list)):
        yield QtGui.QColor(*mpl2rgb(x))
    
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
        
        
#def paletteQColors(palette:typing.Union[dict, tuple, list, str, ColorPalette]) -> typing.Generator[typing.Iterator[QtGui.QColor],
                                                                                #None,
                                                                                #None]:
    #"""Iterates color entries in a color palette
    
    #Parameters: 
    #===========
    #WARNING: the type of the parameters is not checked; if any exception are 
    #raised the function will return an invalid QColor.

    #palette: A sequence, a mapping, or a str (palette name)
        #When a sequence, its elements can be:
        #a) sequences of 3 or 4 int elements: (r, g, b) , or (r, g, b, a)
            #(with 3 elements alpha channel a = 255 is implied)
        #b) QtCore.Qt.GlobalColor objects
        #c) QtGui.QColor objects
        #d) str - color name
            #Either a simple color name (e.g., "red") - represeting an internal
            #Qt.GlobalColor (e.g. QtCore.Qt.red)
            
            #or name qualified by dot-separated prefix e.g. "QtCore.Qt.red" 
            #(which in this example evaluates to the same color as above); 
            
            #Allowed values for the prefix are (case-insensitive):
            #"Qt", "QtCore", "QtCore.Qt", "standard", and "SVG"
            
            #this form allows the indirect  use of colors from several pre-defined
            #palettes including the Qt.GlobalColor and palettes that store colors
            #as name = value mapping.
            
        #When a mapping (dict), it must contain str keys mapped to:
            #a) tuples of int values with 3 or 4 elements as above
            #b) a QtCore.Qt.GlobalColor object,
            #c) QtGui.QColor object
            #d) a str (another color name, either simple or qualified as above)
            
        #When a str, this identifies a registered color palette.
        
        #See this module's documentation for available palettes
    #"""
    #if isinstance(palette, dict):
        #iterable = palette.values()
    #else:
        #iterable = palette

    #return (next(c, QtGui.QColor()), palette)

def paletteQColor(palette:typing.Union[dict, list, tuple, str, ColorPalette], 
                  index:typing.Union[int, str]) -> QtGui.QColor:
    """Retrieve color entry from a color palette.
    
    Parameters: 
    ===========
    WARNING: the type of the parameters is not checked; if any exception are 
    raised the function will return an invalid QColor.

    palette: A sequence, a mapping, or a str (palette name)
            When a sequence, its elements can be:
            a) sequences of 3 or 4 int elements: (r, g, b) , or (r, g, b, a)
                (with 3 elements alpha channel a = 255 is implied)
            b) QtCore.Qt.GlobalColor objects (or int)
            c) QtGui.QColor objects
            d) str - color name (as found in palettes)
                Either a simple color name (e.g., "red") - represeting an 
                internal Qt.GlobalColor (e.g. QtCore.Qt.red)
                
                or a qualified name e.g., "QtCore.Qt.red" 
                (which in this example evaluates to the same QColor as above); 
                
                Allowed values for the prefix are (case-insensitive):
                "Qt", "QtCore", "QtCore.Qt", "standard", and "SVG"
                
                this form allows the indirect use of colors from several pre-defined
                palettes including the Qt.GlobalColor and palettes that store colors
                as name = value mapping.
                
            When a mapping (dict), it must contain str keys mapped to:
                a) tuples of int values with 3 or 4 elements as above
                b) a QtCore.Qt.GlobalColor object,
                c) QtGui.QColor object
                d) a str (another color name, either simple or qualified as above)
            
            When a str, this the name of a registered color palette, or "all"
        
                                                                    
    index: int or str
        Index into the palette. 
        
        For sequence palettes this is expected to be an int with value in the 
        semi-open interval [0 - len(palette)).
        
        For dict palettes, this should be a str and present among the palette's 
        keys.
        
    
    """
    if isinstance(palette, str):
        palette = getPalette(palette)
        
    try:# CAUTION 2021-05-17 11:21:42 raise error if index is inappropriate for palette
        if isinstance(palette, (dict, tuple, list)):
            entry = palette[index] 
            return next(genPaletteQColor(entry), QtGui.QColor())
        
        elif isinstance(palette, ColorPalette):
            return palette.qcolor(index)
            
    except:
        return QtGui.QColor()
        
def register_colormaps(colormap_dict, prefix:typing.Optional[str]=None, 
                       N:typing.Optional[int]=256,
                       gamma:typing.Optional[float]=1.0):
    """Register in matplotlib, custom colormaps collected in a dictionary.
    
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
    """Registers a custom colormap with matplotlib.
    """
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
        * Scipyen's configuration directory
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
    
defaultPalette = ColorPalette()
