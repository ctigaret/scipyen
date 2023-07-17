import numbers, os, typing, inspect, traceback
from enum import IntEnum, auto
from pprint import pprint
#from collections import OrderedDict
from traitlets import Bunch

import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
# from PyQt5.uic import loadUiType as __loadUiType__

import sip # for sip.cast

from core.prog import (safeWrapper, no_sip_autoconversion)
from core.traitcontainers import DataBag

from .scipyen_colormaps import (qtGlobalColors, standardPalette,
                                standardPaletteDict, svgPalette,
                                getPalette, paletteQColor, 
                                qcolor, get_name_color, 
                                standardQColor, svgQColor,
                                qtGlobalColors, mplColors, ColorPalette)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# NOTE: 2021-05-19 10:00:27
# Iterate through the types INSIDE this union with BrushStyleType._subs_tree()[1:]
# _subs_tree() returns a tuple of types where the first element is always
# typing.Union, so we leave it out.

# NOTE: 2021-06-08 11:39:33
# Python sip may apply the following mappings:
# QtCore.Qt.BrushStyle -> int, 
# QtGui.QBitmap -> QtGui.QPixmap,
# QtCore.Qt.PenStyle -> int
#
# The consequences are that the _subs_tree method returns as follows:
#
# BrushStyleType._subs_tree():
# (typing.Union, 
#  int,
#  PyQt5.QtGui.QGradient,
#  PyQt5.QtGui.QPixmap,
#  PyQt5.QtGui.QImage)
#
# PenStyleType._subs_tree():
#  (typing.Union, tuple, list, int)

BrushStyleType = typing.Union[int, QtCore.Qt.BrushStyle, QtGui.QGradient,
                              QtGui.QBitmap, QtGui.QPixmap, QtGui.QImage]

PenStyleType = typing.Union[tuple, list, QtCore.Qt.PenStyle, int]

FontStyleType = typing.Union[int, QtGui.QFont.Style]

FontWeightType = typing.Union[int, QtGui.QFont.Weight]

standardQtFontStyles = Bunch(sorted(((name, val) for name, val in vars(QtGui.QFont).items() if isinstance(val, QtGui.QFont.Style)), key = lambda x: x[1]))

standardQtFontWeights = Bunch(sorted(((name, val) for name, val in vars(QtGui.QFont).items() if isinstance(val, QtGui.QFont.Weight)), key = lambda x: x[1]))


standardQtPenStyles = Bunch(sorted(((name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenStyle) and val < 10),
                           key = lambda x: x[1]))

standardQtPenJoinStyles = Bunch(sorted(((name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenJoinStyle) and val <= 256),
                           key = lambda x: x[1]))

standardQtPenCapStyles = Bunch(sorted(((name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenCapStyle) and val <= 32),
                           key = lambda x: x[1]))

customDashStyles = {"Custom": [10., 5., 10., 5., 10., 5., 1., 5., 1., 5., 1., 5.]}

standardQtGradientPresets = Bunch(sorted(( (name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Preset) and name != "NumPresets")))

standardQtGradientSpreads = Bunch(sorted(( (name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Spread) )))

standardQtGradientTypes = Bunch(sorted(( (name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Type)),
                                      key = lambda x: x[1]))
validQtGradientTypes = Bunch(sorted(((name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Type) and value < 3),
                                      key = lambda x: x[1]))

standardQtBrushStyles = Bunch(sorted(((name, value) for name, value in vars(QtCore.Qt).items() if isinstance(value, QtCore.Qt.BrushStyle)),
                                           key = lambda x: x[1]))

standardQtBrushPatterns = Bunch(sorted(((name, value) for name, value in standardQtBrushStyles.items() if all((s not in name for s in ("Gradient", "Texture")))),
                                           key = lambda x: x[1]))

standardQtBrushGradients = Bunch(sorted(((name, value) for name, value in standardQtBrushStyles.items() if "Gradient" in name),
                                           key = lambda x: x[1]))

standardQtBrushTextures = Bunch(sorted(((name, value) for name, value in standardQtBrushStyles.items() if "Texture" in name),
                                           key = lambda x: x[1]))

qPainterCompositionModes = Bunch(sorted(((name, value) for name, value in vars(QtGui.QPainter).items() if isinstance(value, QtGui.QPainter.CompositionMode)), 
                                        key = lambda x: x[1]))

def populateMimeData(mimeData:QtCore.QMimeData, color:typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]):
    #from core.utilities import reverse_dict
    mimeData.setColorData(color)
    
    if isinstance(color, QtCore.Qt.GlobalColor):
        color = QtGui.QColor(color)
    mimeData.setText(color.name())
    # NOTE: 2021-05-14 23:27:20
    # The code below doesn't do what is intended: it should pass a color string
    # (format '#rrggbb) to mimeData's text attribute
    # However, DO NOT DELETE: this is an example of key lookup by value in enumerations
    # in the Qt namespace
    #if isinstance(color, QtCore.Qt.GlobalColor):
        #name = reverse_dict(qtGlobalColors)[color]
    #else:
        #name = color.name()
        
    #mimeData.setText(name)
    
def bound_point(point:QtCore.QPointF, bounds:QtCore.QRectF, lock:int) -> QtCore.QPointF:
    p = point
    
    left    = bounds.left()
    right   = bounds.right()
    top     = bounds.top()
    bottom  = bounds.bottom()
    
    if p.x() < left or (lock & HoverPoints.LockType.LockToLeft):
        p.setX(left)
        
    elif p.x() > right or (lock & HoverPoints.LockType.LockToRight):
        p.setX(right)
        
    if p.y() < top or (lock & HoverPoints.LockType.LockToTop):
        p.setY(top)
        
    elif p.y() > bottom or (lock & HoverPoints.LockType.LockToBottom):
        p.setY(bottom)
        
    return p

def restrict_point(p, w, h):
    x = min((max((0., p.x())),w))
    y = min((max((0., p.y())), h))
    return QtCore.QPointF(x, y)
    
    
def canDecode(mimeData:QtCore.QMimeData) -> bool:
    if mimeData.hasColor():
        return True
    
    if mimeData.hasText():
        colorName = mimeData.text()
        if len(colorName) >= 4 and colorName.startswith("#"):
            return True
        
    return False

@no_sip_autoconversion(QtCore.QVariant)
def fromMimeData(mimeData:QtCore.QMimeData) -> QtGui.QColor:
    if mimeData.hasColor():
        # NOTE: 2021-05-14 21:26:16 ATTENTION
        #return mimeData.colorData().value() 
        # sip "autoconverts" QVariant<QColor> to an int, therefore constructing
        # a QColor from that results in an unintended color!
        # Therefore we temporarily suppress autoconversion of QVariant here
        # NOTE: 2021-05-15 14:06:57 temporary sip diabling by means of the 
        # decorator core.prog.no_sip_autoconversion
        #import sip
        #sip.enableautoconversion(QtCore.QVariant, False)
        ret = mimeData.colorData().value() # This is a python-wrapped QVariant<QColor>
        #sip.enableautoconversion(QtCore.QVariant, True)
        return ret
    if canDecode(mimeData):
        return QtGui.QColor(mimeData.text())
    return QtGui.QColor()


@safeWrapper
def createDrag(color:QtGui.QColor, dragSource:QtCore.QObject) -> QtGui.QDrag:
    drag = QtGui.QDrag(dragSource)
    mime = QtCore.QMimeData()
    populateMimeData(mime, color)
    colorPix = QtGui.QPixmap(25, 20)
    colorPix.fill(color)
    painter = QtGui.QPainter(colorPix)
    painter.setPen(QtCore.Qt.black)
    painter.drawRect(0, 0, 24, 19)
    painter.end()
    drag.setMimeData(mime)
    drag.setPixmap(colorPix)
    drag.setHotSpot(QtCore.QPoint(-5, -7))
    return drag

def make_transparent_bg(strong:bool=False, size:int=16) -> QtGui.QPixmap:
    #ret = QtGui.QPixmap(size, size)
    #patternPainter = QtGui.QPainter(ret)
    if strong:
        color0 = QtCore.Qt.black
        color1 = QtCore.Qt.white
    else:
        color0 = QtCore.Qt.darkGray
        color1 = QtCore.Qt.lightGray

    return make_checkers(color0, color1, size)

def make_checkers(color0:typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor], 
                  color1:typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor],
                  size:int=16) -> QtGui.QPixmap:
    """Makes square checkers pattern as background for transparent graphics.
    
    The checkers pattern is: ▄▀  with color0 at the top left. The color roles
    can be inverted by swapping color0 and color1: ▀▄
    
    Parameters:
    ===========
    color0, color1: Qt colors (either QColor objects or Qt.GlobalColor enum values)
        They should be distinct from each other, not necessarily black & white.
        However, when they are Qt.color0 and Qt.color1, respectively, the function
        generates a bitmap (1-depth pixmap, made of 0s and 1s).
        NOTE that a QBitmap is a specialization of QPixmap.
        
        Otherwise, the function generates a pixmap.
        
        NOTE: color0 is used for the top-left square of the pixmap
        
    size: int - the length & width of the generated pixmap
    
    """
    if all ([c in (QtCore.Qt.color0, QtCore.Qt.color1) for c in (color0, color1)]): # make bitmap
        ret = QtGui.QBitmap(size, size)
        
    else:
        ret = QtGui.QPixmap(size, size)

    patternPainter = QtGui.QPainter(ret)
    
    patternPainter.fillRect(0,          0,          size//2,    size//2, color0)
    patternPainter.fillRect(size//2,    size//2,    size//2,    size//2, color0)
    patternPainter.fillRect(0,          size//2,    size//2,    size//2, color1)
    patternPainter.fillRect(size//2,    0,          size//2,    size//2, color1)
    patternPainter.end()
    
    return ret

def x_less_than(p1:QtCore.QPointF, p2:QtCore.QPointF) -> bool:
    return p1.x() < p2.x()

@safeWrapper
def makeCustomPathStroke(path:QtGui.QPainterPath,
                     dashes:list, width:numbers.Real=1.,
                     join:QtCore.Qt.PenJoinStyle=QtCore.Qt.MiterJoin,
                     cap:QtCore.Qt.PenCapStyle=QtCore.Qt.FlatCap,
                     ) -> QtGui.QPainterPath:
    
    if isinstance(dashes, (tuple, list)) and len(dashes):
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(width)
        stroker.setJoinStyle(join)
        stroker.setCapStyle(cap)
    
        stroker.setDashPattern(dashes)
        
        return stroker.createStroke(path)
    
    return path

@safeWrapper
def gradient2radial(gradient:QtGui.QGradient, 
                   centerRadius:float = 1., 
                   focalRadius:float = 0.,
                   distance:float= 1.) -> QtGui.QRadialGradient:
    if isinstance(gradient, QtGui.QRadialGradient):
        return gradient
    
    if isinstance(gradient, QtGui.QLinearGradient):
        center = gradient.start()
        focalPoint = gradient.finalStop()
        ret = QtGui.QRadialGradient(center, centerRadius, focalPoint, focalRadius)
    
    elif isinstance(gradient, QtGui.QConicalGradient):
        center = gradient.center()
        l = QtCore.QLineF.fromPolar(distance, gradient.angle())
        focalPoint = l.p2()
        ret = QtGui.QRadialGradient(center, centerRadius, focalPoint, focalRadius)

    elif isinstance(gradient, QtGui.QGradient):
        # see NOTE: 2021-09-16 17:55:08
        if gradient.type() == QtGui.QGradient.RadialGradient:
            ret = sip.cast(gradient, QtGui.QRadialGradient)
            ret.setCenterRadius(centerRadius)
            ret.setFocalRadius(focalRadius)
        
        if gradient.type() == QtGui.QGradient.LinearGradient:
            g = sip.cast(gradient, QtGui.QLinearGradient)
            
            center = g.start()
            focalPoint = g.finalStop()
            ret = QtGui.QRadialGradient(center, centerRadius, focalPoint, focalRadius)
            #l = QtGui.QLineF(QtCore.QPointF(0,0), QtCore.QPointF(0,10))
            #l.setLength(distance)
            #l.setAngle(0)
            #ret = QtGui.QRadialGradient(l.p1(), centerRadius, l.p2(), focalRadius)
            
        elif gradient.type() == QtGui.QGradient.ConicalGradient:
            g = sip.cast(gradient, QtGui.QConicalGradient)
            
            center = gradient.center()
            l = QtCore.QLineF.fromPolar(distance, g.angle())
            focalPoint = l.p2()
            ret = QtGui.QRadialGradient(center, centerRadius, focalPoint, focalRadius)

        else:
            ret = QtGui.QRadialGradient()
            
    else:
        ret = QtGui.QRadialGradient()
            
    ret.setStops(gradient.stops())
    ret.setSpread(gradient.spread())
            
    return ret

g2r = gradient2radial
    
@safeWrapper
def gradient2linear(gradient:QtGui.QGradient) -> QtGui.QLinearGradient:
    if isinstance(gradient, QtGui.QLinearGradient):
        return gradient
    
    if isinstance(gradient, QtGui.QRadialGradient):
        ret = QtGui.QLinearGradient(gradient.center(), gradient.focalPoint())
        
    elif isinstance(gradient, QtGui.QConicalGradient):
        l = QtCore.QLineF.fromPolar(distance, gradient.angle())
        l.setP1(gradient.center())
        ret = QtGui.QLinearGradient(l.p1(), l.p2())

    elif isinstance(gradient, QtGui.QGradient):
        # NOTE: 2021-09-16 17:55:08
        # type() for a generic QGradient by default returns QtGui.QGradient.LinearGradient
        if gradient.type() == QtGui.QGradient.LinearGradient:
            return sip.cast(gradient, QtGui.QLinearGradient)
        
        if gradient.type() == QtGui.QGradient.RadialGradient:
            g = sip.cast(gradient, QtGui.QRadialGradient)
            ret = QtGui.QLinearGradient(g.center(), g.focalPoint())
            
            
        elif gradient.type() == QtGui.QGradient.ConicalGradient:
            g = sip.cast(gradient, QtGui.QConicalGradient)
            l = QtCore.QLineF.fromPolar(distance, g.angle())
            l.setP1(g.center())
            ret = QtGui.QLinearGradient(l.p1(), l.p2())
            
        else:
            ret = QtGui.QLinearGradient()
            
    else:
        ret = QtGui.QLinearGradient()
            
    ret.setStops(gradient.stops())
    ret.setSpread(gradient.spread())
    
    return ret
    
g2l = gradient2linear

@safeWrapper
def gradient2conical(gradient:QtGui.QGradient) -> QtGui.QConicalGradient:
    if isinstance(gradient, QtGui.QConicalGradient):
        return gradient
    
    if isinstance(gradient, QtGui.QLinearGradient):
        l = QtCore.QLineF(gradient.start(), gradient.finalStop())
        ret = QtGui.QConicalGradient(l.p1(), l.angle())
        
    elif isinstance(gradient, QtGui.QRadialGradient):
        l = QtCore.QLineF(gradient.center(), gradient.focalPoint())
        ret = QtGui.QConicalGradient(l.p1(), l.angle())
        
    elif isinstance(gradient, QtGui.QGradient):
        # see NOTE: 2021-09-16 17:55:08
        if gradient.type() == QtGui.QGradient.ConicalGradient:
            return sip.cast(gradient, QtGui.QConicalGradient)
        
        if gradient.type() == QtGui.QGradient.LinearGradient:
            g = QtGui.QLinearGradient
            g = sip.cast(gradient, QtGui.QLinearGradient)
            l = QtCore.QLineF(g.start(), g.finalStop())
            ret = QtGui.QConicalGradient(l.p1(), l.angle())
            
        elif gradient.type() == QtGui.QGradient.RadialGradient:
            g = sip.cast(gradient, QtGui.QRadialGradient)
            l = QtCore.QLineF(g.center(), g.focalPoint())
            ret = QtGui.QConicalGradient(l.p1(), l.angle())
        
        else:
            ret = QtGui.QConicalGradient()
        
    else:
        ret = QtGui.QConicalGradient()
        
    ret.setStops(gradient.stops())
    ret.setSpread(gradient.spread())
    
    return ret

g2c = gradient2conical

def linearcoords(x:QtGui.QLinearGradient, precision:typing.Optional[int]=None) -> tuple:
    ret = (x.start().x(), x.start().y(), x.finalStop().x(), x.finalStop().y())
    if precision is not None:
        return tuple(np.around(v,precision) for v in ret)
    
    return ret
    
def radialcoords(x:QtGui.QRadialGradient, precision:typing.Optional[int]=None) -> tuple:
    
    ret = (x.center().x(),     x.center().y(),     x.centerRadius(), 
           x.focalPoint().x(), x.focalPoint().y(), x.focalRadius())
    
    if precision is not None:
        return tuple(np.around(v,precision) for v in ret)
    
    return ret
    
def conicalcoords(x:QtGui.QConicalGradient, precision:typing.Optional[int]=None) -> tuple:
    ret = (x.center().x(), x.center().y(), x.angle())
    
    if precision is not None:
        return tuple(np.around(v,precision) for v in ret)
    
    return ret
    
def gradientCoordinates(x:QtGui.QGradient, precision:typing.Optional[int]=None) -> tuple:
    if isinstance(x, QtGui.QLinearGradient):
        return linearcoords(x, precision)
    elif isinstance(x, QtGui.QRadialGradient):
        return radialcoords(x, precision)
    elif isinstance(x, QtGui.QConicalGradient):
        return conicalcoords(x, precision)
    
    elif isinstance(x, QtGui.QGradient):
        if x.type() & QtGui.QGradient.LinearGradient:
            x_ = sip.cast(x, QtGui.QLinearGradient)
            return linearcoords(x_, precision)
        elif x.type() & QtGui.QGradient.RadialGradient:
            x_ = sip.cast(x, QtGui.QRadialGradient)
            return radialcoords(x_, precision)
        elif x.type() & QtGui.QGradient.ConicalGradient:
            x_ = sip.cast(x, QtGui.QConicalGradient)
            return conicalcoords(x_, precision)
        
    return (0., 0., 0., 0.)

def gradientLine(gradient:typing.Union[QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient],
                    rect:typing.Union[QtCore.QRect, QtCore.QRectF], 
                    points:typing.Optional[typing.Union[QtGui.QPolygonF, tuple, list]]=None)-> QtGui.QPolygonF:
    if isinstance(gradient, QtGui.QLinearGradient):
        ret = QtCore.QLineF(gradient.start(), gradient.finalStop())

    elif isinstance(gradient, QtGui.QRadialGradient):
        ret = QtCore.QLineF(gradient.center(), gradient.focalPoint())

    elif isinstance(gradient, QtGui.QConicalGradient):
        # NOTE: 2021-05-27 15:31:42 
        # this is in logical coordinates i.e.
        # normalized to whatever size the paint device (widget/pimap, etc) has
        # NOTE: 2021-06-09 21:23:57 Not necessarily!!!
        gradCenter = gradient.center() 
        
        #print(f"gradientLine(conical): coordinates {gradientCoordinates(gradient)}")
        
        if isinstance(points, (QtGui.QPolygonF, tuple, list)) and len(points) >= 2:
            p0 = points[0]
            p1 = points[-1]
            
            dp = p1-p0
            length = np.sqrt(sum((dp.x()**2, dp.y()**2)))
            
            ret = QtCore.QLineF.fromPolar(p0, length)
            
        else:
            # NOTE: make the length of the line the radius of the circle inscribed in
            # rect (this radius is by definition the minimum of the x, y coordinates
            # rect's centre)
            #print(f"rect centre {(rect.center().x(), rect.center().y())}")
            #translate = gradient.center() - rect.center()
            #ret = QtCore.QLineF.fromPolar(min((rect.center().x(), rect.center().y())), gradient.angle())
            ret = QtCore.QLineF.fromPolar(min([gradCenter.x(), gradCenter.y()]), gradient.angle())
            #translate = rect.center() - ret.center()
            translate = ret.center() - rect.center()
            ret.translate(translate)
            
        #print(f"\t ret: {ret}, length: {ret.length()}; angle: {ret.angle()}")

        # NOTE: 2021-06-09 22:07:06 places the center mapped to real coordinates
        #mappedCenter = QtGui.QTransform.fromScale(rect.width(), rect.height()).map(gradient.center())

        # NOTE: 2021-05-27 09:28:27
        # this paints the hover point symmetrically around the renderer's centre
        #l = QtCore.QLineF(self.rect().topLeft(), self.rect().topRight())
        #mappedCenter = self.rect().center()
        #ret = QtCore.QLineF.fromPolar(l.length(), gradient.angle())
        #ret.translate(mappedCenter)
        # NOTE: 2021-05-27 09:28:33
        # radius of an inscribed circle is the min orthogonal distance from
        # center to the rect sides
        #ret = QtCore.QLineF.fromPolar(min([mappedCenter.x(), mappedCenter.y()]), gradient.angle())
        #ret.translate(ret.center() - mappedCenter)
        ## this should keep the gradient's centre where is meant to be ?
        #l = QtCore.QLineF(mappedCenter, self.rect().topRight())
        #ret = QtCore.QLineF.fromPolar(l.length(), gradient.angle())
        #return ret
        
    else:
        ret = QtCore.QLineF(QtCore.QPointF(0,0), QtCore.QPointF(rect.width(), rect.height()))
        
    return ret

def rescaleGradient(gradient:QtGui.QGradient, src_rect:typing.Union[QtCore.QRect, QtCore.QRectF],
                    dest_rect:typing.Union[QtCore.QRect, QtCore.QRectF]) -> QtGui.QGradient:
    g = normalizeGradient(gradient, src_rect)
    return scaleGradient(g, dest_rect)
        
def scaleGradient(gradient:QtGui.QGradient, rect:typing.Union[QtCore.QRect, QtCore.QRectF]) -> QtGui.QGradient:
    """ATTENTION/WARNING gradient must have normalized coordinates!
    
    """
    x = rect.x()
    y = rect.y()
    w = rect.width()
    h = rect.height()
    coords = gradientCoordinates(gradient)
    #print(f"scaleGradient input gradient coords {coords}")
    if isinstance(gradient, QtGui.QLinearGradient):
        # x0, y0, x1, y1
        x0 = coords[0] * w + x
        y0 = coords[1] * h + y
        x1 = coords[2] * w + x
        y1 = coords[3] * h + y
        g = QtGui.QLinearGradient(x0,y0,x1,y1)
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
    
    elif isinstance(gradient, QtGui.QRadialGradient):
        # x0, y0, r0, x1, y1, r1
        x0 = coords[0] * w + x
        y0 = coords[1] * h + y
        r0 = coords[2] * min([w/2, h/2])
        x1 = coords[3] * w + x
        y1 = coords[4] * h + y
        r1 = coords[5] * min([w/2, h/2])
        g = QtGui.QRadialGradient(x0, y0, r0, x1, y1, r1)
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
        
    elif isinstance(gradient, QtGui.QConicalGradient):
        # x0, y0, alpha
        x0 = coords[0] * w + x
        y0 = coords[1] * h + y
        g = QtGui.QConicalGradient(x0, y0, gradient.angle())
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
        
    else:
        x0 = coords[0] * w + x
        y0 = coords[1] * h + y
        x1 = coords[2] * w + x
        y1 = coords[3] * h + y
        g = QtGui.QLinearGradient(x0,y0,x1,y1)
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
        # generate a Linear gradieht based o the generic and the rect
        
        #raise TypeError("Expecting a concrete QGradient subtype; got %s instead" % type(g).__name__)

def normalizeGradient(gradient:QtGui.QGradient, rect:typing.Union[QtCore.QRect, QtCore.QRectF]) -> QtGui.QGradient:
    """
    """
    x = rect.x()
    y = rect.y()
    w = rect.width()
    h = rect.height()
    coords = gradientCoordinates(gradient)
    #print(f"painting_shared.normalizeGradient {coords}")
    if isinstance(gradient, QtGui.QLinearGradient):
        # x0, y0, x1, y1
        x0 = (coords[0]-x)/w
        y0 = (coords[1]-y)/h
        x1 = (coords[2]-x)/w
        y1 = (coords[3]-y)/h
        g = QtGui.QLinearGradient(x0,y0,x1,y1)
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
    
    elif isinstance(gradient, QtGui.QRadialGradient):
        # x0, y0, r0, x1, y1, r1
        x0 = (coords[0]-x)/w
        y0 = (coords[1]-y)/h
        r0 =  coords[2] / min([w/2, h/2])
        x1 = (coords[3]-x)/w
        y1 = (coords[4]-y)/h
        r1 =  coords[5] / min([w/2, h/2])
        g = QtGui.QRadialGradient(x0, y0, r0, x1, y1, r1)
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
    
    elif isinstance(gradient, QtGui.QConicalGradient):
        # x0, y0, alpha
        x0 = (coords[0]-x)/w
        y0 = (coords[1]-y)/h
        g = QtGui.QConicalGradient(x0, y0, gradient.angle())
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
        
    else:
        raise TypeError("Expecting a concrete QGradient subtype; got %s instead" % type(g).__name__)
        
@no_sip_autoconversion(QtCore.QVariant)
def comboDelegateBrush(index:QtCore.QModelIndex, role:int) -> QtGui.QBrush:
    brush = QtGui.QBrush()
    v = QtCore.QVariant(index.data(role))
    if v.type() == QtCore.QVariant.Brush:
        brush = v.value()
        
    elif v.type() == QtCore.QVariant.Color:
        brush = QtGui.QBrush(v.value())
    return brush

def y_less_than(p1:QtCore.QPointF, p2:QtCore.QPointF) -> bool:
    return p1.y() < p2.y()

class HoverPoints(QtCore.QObject):
    pointsChanged = pyqtSignal(QtGui.QPolygonF, name = "pointsChanged")
    
    class PointShape(IntEnum):
        CircleShape=auto()
        RectangleShape=auto()
    
    
    class LockType(IntEnum):
        NoLock = 0x00
        LockToLeft = 0x01
        LockToRight = 0x02
        LockToTop = 0x04
        LockToBottom = 0x08
        
    class SortType(IntEnum):
        NoSort = auto()
        XSort = auto()
        YSort = auto()
        
    class ConnectionType(IntEnum):
        NoConnection = auto()
        LineConnection = auto()
        CurveConnection = auto()
        
    def __init__(self, widget:QtWidgets.QWidget, shape:PointShape=PointShape.CircleShape,
                 size:typing.Union[int, typing.Tuple[int]]=11,
                 compositionMode:typing.Optional[typing.Union[QtGui.QPainter.CompositionMode, str, int]] = None):
        """HoverPoints constructor
        
        Parameters:
        -----------
        widgets: QWidget = the widgets where the hover points are drawn
        shape: HoverPoints.PointShape enum value = the shape of the hover point.
            Either:
                HoverPoints.PointShape.CircleShape (default)
                HoverPoints.Pointshape.RectangleShape
            
        size: int or a pair (tuple, list) of int (default: 11) = Size (in pixels)
            of the hover point.
            When an int: 
                CircleShape points use this as their diameter;
                RectangleShape points use this as the width and height (i.e. squares)
                
            When a tuple of int, the values are the width and height of the shaped point
            (if unequal, they will be drawn as ellipse or rectangles, depending on
            the PointShape)
        """
        super().__init__(widget)
        
        self._widget = widget
        widget.installEventFilter(self)
        
        # NOTE 2021-05-21 21:29:33 touchscreens
        # I don't think is needed
        widget.setAttribute(QtCore.Qt.WA_AcceptTouchEvents) 
        
        self._connectionType = HoverPoints.ConnectionType.CurveConnection
        self._sortType = HoverPoints.SortType.NoSort
        self._shape = shape
        self._pointPen = QtGui.QPen(QtGui.QColor(255, 255, 255, 191), 1)
        self._connectionPen = QtGui.QPen(QtGui.QColor(255, 255, 255, 127), 2)
        self._pointBrush = QtGui.QBrush(QtGui.QColor(191, 191, 191, 127))
        if isinstance(size, (tuple, list)) and len(size) == 2 and all([isinstance(v, int) for v in size]):
            self._pointSize = QtCore.QSize(*size)
        elif isinstance(size, int):
            self._pointSize = QtCore.QSize(size, size)
        else:
            self._pointSize = QtCore.QSize(11, 11)
        self._currentIndex = -1
        self._editable = True
        self._enabled = True
        self._points = QtGui.QPolygonF()
        self._bounds = QtCore.QRectF()
        self._locks = list() # of QPoint/QPointF
        self._labels = None
        
        self._compositionMode = None
        
        if isinstance(compositionMode, QtGui.QPainter.CompositionMode):
            self._compositionMode = compositionMode
            
        elif isinstance(compositionMode, str):
            self._compositionMode = qPainterCompositionModes[compositionMode]
            
        elif isinstance(compositionMode, int) and compositionMode in qPainterCompositionModes.values():
            self._compositionMode = compositionMode
            
        
        #self._fingerPointMapping = dict() # see NOTE 2021-05-21 21:29:33 touchscreens
        
        self.pointsChanged.connect(self._widget.update)
        
    def __repr__(self):
        ret = list()
        ret.append(f"{self.__class__.__name__} with {len(self)} points:")
        for k, p in enumerate(self.points):
            ret.append(f"\tpoint {k}: x = {p.x()}; y = {p.y()}")
            
        return "\n".join(ret)
    
    def __str__(self):
        return "\n".join([v for v in itertools.chain((f"{p.x(), p.y()}" for p in points))])
        
    def __len__(self):
        return len(self.points)
        
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value:bool) -> None:
        if self._enabled != value:
            self._enabled = value
            self._widget.update()
            
    @property
    def compositionMode(self) -> QtGui.QPainter.CompositionMode:
        return self._compositionMode
    
    @compositionMode.setter
    def compositionMode(self, val:typing.Union[QtGui.QPainter.CompositionMode, str, int, type(None)]):
        if isinstance(val, str):
            self._compositionMode = qPainterCompositionModes[val]
            
        elif isinstance(val, (int, QtGui.QPainter.CompositionMode)):
            self._compositionMode = val
            
        else:
            self._compositionMode = None # revert to platform's defaults
            
    @property
    def labels(self) -> typing.Union[str, tuple, list, bool]:
        return self._labels
    
    @labels.setter
    def labels(self, val:typing.Union[str, tuple, list, bool]) -> None:
        self._labels = val
        
    @pyqtSlot(bool)
    def setEnabled(self, value:bool) -> None:
        self.enabled = value
        #if self._enabled != value:
            #self._enabled = enabled
            #self._widget.update()
            
    @pyqtSlot(bool)
    def setDisabled(self, value:bool) -> None:
        self.enabled = not value
        #self.setEnabled(not value)
        
    def _pointBoundingRect(self, i:typing.Union[int, QtCore.QPointF]) -> QtCore.QRectF:
        if isinstance(i, int):
            p = self._points.at(i)
        elif isinstance(i, QtCore.QPointF) and i in self._points:
            p = i
        else:
            return
        
        w = self._pointSize.width()
        h = self._pointSize.height()
        # NOTE: 2021-06-21 08:52:20
        # a hover point's (x,y) are at the CENTER of the shape, i.e. it is at w/2 and h/2
        x = p.x() - w/2 
        y = p.y() - h/2
        return QtCore.QRectF(x, y, w, h)
    
    def boundingRect(self) -> QtCore.QRectF:
        if self._bounds.isNull() or self._bounds.isEmpty() or not self._bounds.isValid():
            return QtCore.QRectF(self._widget.rect())
        else:
            return self._bounds
        
    def setBoundingRect(self, boundingRect:QtCore.QRectF) -> None:
        self._bounds = boundingRect
        
    @property
    def points(self) -> QtGui.QPolygonF:
        return self._points
    
    @points.setter
    def points(self, points:QtGui.QPolygonF) -> None:
        # NOTE: 2021-05-23 20:57:59
        # QPolygonF has API compatible with list() (on C++ side is a QVector<QPointF>)
        self._points.clear() # just so that refs to QPointF are garbage-collected
        self._points = QtGui.QPolygonF([bound_point(p, self.boundingRect(), 0) for p in points])
        self._locks.clear()
        
        if len(self._points):
            self._locks = [0] * len(self._points)
            
    @property
    def pointSize(self) -> QtCore.QSize:
        return self._pointSize
        
    @pointSize.setter
    def pointSize(self, size:typing.Union[QtCore.QSize, QtCore.QSizeF, typing.Tuple[numbers.Real, numbers.Real]]) -> None:
        if isinstance(size, (QtCore.QSize, QtCore.QSizeF)):
            self._pointSize = size
        else:
            self._pointSize = QtCore.QSizeF(*size)
            
        
    @property
    def sortType(self) -> SortType:
        return self._sortType
    
    @sortType.setter
    def sortType(self, sortType:SortType) -> None:
        self._sortType = sortType
        
    @property
    def connectionType(self) -> ConnectionType:
        return self._connectionType
    
    @connectionType.setter
    def connectionType(self, connectionType:ConnectionType) -> None:
        self._connectionType = connectionType
        
    @property
    def connectionPen(self) -> QtGui.QPen:
        return self._connectionPen
    
    @connectionPen.setter
    def connectionPen(self, pen:QtGui.QPen) -> None:
        self._connectionPen = pen
        
    @property
    def shapePen(self) -> QtGui.QPen:
        return self._pointPen
    
    @shapePen.setter
    def shapePen(self, pen: QtGui.QPen) -> None:
        self._pointPen = pen
        
    @property
    def shapeBrush(self) -> QtGui.QBrush:
        return self._pointBrush
    
    @shapeBrush.setter
    def shapeBrush(self, brush:QtGui.QBrush) -> None:
        self._pointBrush = brush_label
        
    @property
    def editable(self) -> bool:
        return self._editable
    
    @editable.setter
    def editable(self, value:bool) -> None:
        self._editable = value
    
    def setPointLock(self, pos:int, lock:LockType) -> None:
        self._locks[pos] = lock
       
    @safeWrapper
    def eventFilter(self, obj:QtCore.QObject, ev:QtCore.QEvent) -> bool:
        try:
            if obj == self._widget and self._enabled:
                if ev.type() == QtCore.QEvent.MouseButtonPress:
                    #if len(self._fingerPointMapping) == 0: # see # NOTE 2021-05-21 21:29:33 touchscreens
                        #return True
                    
                    me = sip.cast(ev, QtGui.QMouseEvent)
                    
                    clickPos = me.pos()
                    
                    index = -1
                    
                    # NOTE: 2021-05-24 10:50:53
                    # check if event is is on a point => select that point
                    #for i in range(self._points.size(
                    # NOTE: 2021-05-24 10:44:48
                    # Use Python list API for QPolygon/QPolygonF
                    for i in range(len(self._points)):
                        path = QtGui.QPainterPath()
                        if self._shape == HoverPoints.PointShape.CircleShape:
                            path.addEllipse(self._pointBoundingRect(i))
                        else:
                            path.addRect(self._pointBoundingRect(i))

                        if path.contains(clickPos):
                            # NOTE: 2021-05-24 10:51:46 if clicked on a point then
                            # set indes to that point's index; else leave index -1
                            index = i
                            break
                        
                    # NOTE: 2021-06-21 08:53:59
                    # index stays at -1 if no point bounding rect containing 
                    # clickPos is found
                    
                    if me.button() == QtCore.Qt.LeftButton: 
                        # add new point or select clicked one & filter event
                        if index == -1: 
                            # new point added (index is left as -1 because 
                            # clickPos was not any points - see  NOTE: 2021-05-24 10:50:53)
                            if not self._editable: # non-editable => don't block (filter) event
                                return False
                            
                            pos = 0
                            
                            # figure out where to insert the new point
                            if self._sortType == HoverPoints.SortType.XSort:
                                #for i in range(self._points.size()):
                                # see  NOTE: 2021-05-24 10:44:48
                                for k, p in enumerate(self._points):
                                    if p.x() > clickPos.x():
                                        pos = k
                                        break
                                    
                            elif self._sortType == HoverPoints.SortType.YSort:
                                #for i in range(self._points.size()):
                                # see  NOTE: 2021-05-24 10:44:48
                                for k, p in enumerate(self._points):
                                    if p.y() > clickPos.y():
                                        pos = k
                                        break
                                    
                            self._points.insert(pos, clickPos)
                            self._locks.insert(pos, 0) # inserts a NoLock at point index pos
                            
                            # NOTE: 2021-06-26 22:48:21
                            # when part of a gradient editor this ensures points
                            # are added in all shade widgets (hence consistent
                            # with a new gradient stop)
                            if hasattr(self._widget, "pointInserted"):
                                self._widget.pointInserted.emit(pos, clickPos)
                            
                            self._currentIndex = pos
                            self.firePointChange()
                        
                        else:
                            self._currentIndex = index
                            
                        return True # propagate event
                    
                    elif me.button() == QtCore.Qt.RightButton: # remove point if editable & propagate event
                        if index >= 0 and self._editable: 
                            if self._locks[index] == 0:
                                self._locks.pop(index)
                                self._points.remove(index)
                                
                            # NOTE: 2021-06-26 22:49:20
                            # when part of a gradient editor this ensures
                            # corrsponding points in the other shade widgets are
                            # also removed, consistent with the rempval of the
                            # corresponding gradient stop
                            if hasattr(self._widget, "pointRemoved"):
                                self._widget.pointRemoved.emit(index)
                            
                            self.firePointChange()
                            return True # propagate event
                        
                        return False # block event
                        
                elif ev.type() == QtCore.QEvent.MouseButtonRelease:
                    #if len(self._fingerPointMapping):
                        #return True
                    self._currentIndex = -1
                    
                    return False
                    
                elif ev.type() == QtCore.QEvent.MouseMove:
                    #if len(self._fingerPointMapping):
                        #return True
                    pos = QtCore.QPointF(ev.pos())
                    
                    me = sip.cast(ev, QtGui.QMouseEvent)
                    if self._currentIndex >= 0:
                        if me.modifiers() == QtCore.Qt.ShiftModifier:
                            # SHIFT: constrain vertical move
                            pos.setX(self._points[self._currentIndex].x())
                            
                        elif me.modifiers() == QtCore.Qt.ControlModifier:
                            pos.setY(self._points[self._currentIndex].y())
                            # CTRL: constrain horizontal move
                            
                        elif me.modifiers() == (QtCore.Qt.ShiftModifier | QtCore.Qt.ControlModifier):
                            pos0 = self._points[self._currentIndex]
                            l = QtCore.QLineF(pos0, pos)
                            if not l.isNull():
                                angle = l.angle()
                                if angle >=0. and angle < 22.5:
                                    l.setAngle(0.0)
                                    
                                elif angle >= 22.5 and angle < 67.5:
                                    l.setAngle(45.)
                                    
                                elif angle >= 67.5 and angle < 112.5:
                                    l.setAngle(90.)
                                    
                                elif angle >= 112.5 and angle < 157.5:
                                    l.setAngle(135.)
                                    
                                elif angle >= 157.5 and angle < 202.5:
                                    l.setAngle(180.)
                                    
                                elif angle >= 202.5 and angle < 247.5:
                                    l.setAngle(225.)
                                    
                                else:
                                    l.setAngle(270.)
                                    
                                pos = l.p2()
                                    
                        # NOTE: 2021-06-26 22:46:39
                        # synchronize X-coordinate of corresponding hover points
                        # when part of gradient editor (see NOTE: 2021-06-26 22:21:21
                        # in gui.gradientwidgets)
                        if hasattr(self._widget, "pointMovedX"):
                            self._widget.pointMovedX.emit(self._currentIndex, pos.x())
                            
                        self._movePoint(self._currentIndex, pos, True)
                        #self._movePoint(self._currentIndex, ev.pos(), True)
                        
                    return False # block event
                    
                #elif ev.type() == QtCore.QEvent.TouchBegin:
                    #pass # see NOTE 2021-05-21 21:29:33 skipped code for touchscreens
                
                #elif ev.type() == QtCore.QEvent.TouchUpdate:
                    #pass # see NOTE 2021-05-21 21:29:33 skipped code for touchscreens
                    
                #elif ev.type() == QtCore.QEvent.TouchEnd:
                    #pass # see NOTE 2021-05-21 21:29:33 skipped code for touchscreens
                    
                elif ev.type() == QtCore.QEvent.Resize:
                    e = sip.cast(ev, QtGui.QResizeEvent)
                    if e.oldSize().width() != 0 and e.oldSize().height() != 0:
                        stretch_x = e.size().width()  / e.oldSize().width()
                        stretch_y = e.size().height() / e.oldSize().height()
                        for i,p in enumerate(self._points):
                            self._movePoint(i, QtCore.QPointF(p.x() * stretch_x, p.y() * stretch_y), False)
                            
                        self.firePointChange(True)
                            
                    return False
                    
                elif ev.type() == QtCore.QEvent.Paint:
                    that_widget = self._widget
                    self._widget = None
                    QtCore.QCoreApplication.sendEvent(obj, ev)
                    self._widget = that_widget
                    self._paintPoints()
                    return True
                
            return False
        
        except:
            traceback.print_exc()
            return False
        
    @safeWrapper
    def _paintPoints(self) -> None:
        p = QtGui.QPainter()
        p.begin(self._widget)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        if self._connectionPen.style() != QtCore.Qt.NoPen and self._connectionType != HoverPoints.ConnectionType.NoConnection:
            p.setPen(self._connectionPen)
            
            if self._connectionType == HoverPoints.ConnectionType.CurveConnection:
                path = QtGui.QPainterPath()
                path.moveTo(self._points.at(0))
                for i in range(1,self._points.size()):
                    p1 = self._points.at(i-1)
                    p2 = self._points.at(i)
                    distance = p2.x() - p1.x()
                    path.cubicTo(p1.x() + distance/2, p1.y(),
                                 p1.x() + distance/2, p2.y(),
                                 p2.x(), p2.y())
                    
                p.drawPath(path)
            else:
                p.drawPolyline(self._points)
                
        p.setPen(self._pointPen)
        p.setBrush(self._pointBrush)
        
        #p.setCompositionMode(QtGui.QPainter.CompositionMode_Overlay)
        if isinstance(self._compositionMode, QtGui.QPainter.CompositionMode):
            p.setCompositionMode(self._compositionMode)
        
        #for point in self._points:
        for i, point in enumerate(self._points):
            # NOTE: 2021-09-17 11:48:06
            # the point's coordinates are at the CENTER of the bounding rect
            bounds = self._pointBoundingRect(point)
            
            if self._shape == HoverPoints.PointShape.CircleShape:
                p.drawEllipse(bounds)
            else:
                p.drawRect(bounds)
            
            if self._labels is not None:
                ctr = bounds.center()
                
                if ctr.x() < self._widget.width()/2: # paint to the RIGHT
                    if ctr.y() < self._widget.height()/2: # paint BELOW
                        pos = bounds.bottomRight()
                    else:
                        pos = bounds.topRight() # paint ABOVE
                        
                else:
                    if ctr.y() < self._widget.height()/2: # paint to the LEFT
                        pos = bounds.bottomLeft() # paint BELOW
                    else:
                        pos = bounds.topLeft() # paint ABOVE
                        
                if self._labels is True:
                    p.drawStaticText(pos, QtGui.QStaticText(f"{i}: {point.x()}, {point.y()}"))
                    #p.drawStaticText(pos, QtGui.QStaticText(f"{i}: {ctr.x()}, {ctr.y()}"))
                    
                elif isinstance(self._labels, str) and len(self._labels.strip()):
                    p.drawStaticText(pos, QtGui.QStaticText(f"self._labels {i}: {point.x()}, {point.y()}"))
                    #p.drawStaticText(pos, QtGui.QStaticText(f"self._labels {i}: {ctr.x()}, {ctr.y()}"))
                    
                elif isinstance(self._labels, (tuple, list)) and all((isinstance(l, str) for l in self.l_labels)):
                    if i < len(self._labels):
                        label = f"{self._labels[i]}: {point.x()}, {point.y()}"
                        #label = f"{self._labels[i]}: {ctr.x()}, {ctr.y()}"
                        
                    else:
                        label = f"{i}: {point.x()}, {point.y()}"
                        #label = f"{i}: {ctr.x()}, {ctr.y()}"
                        
                    p.drawStaticText(pos, QtGui.QStaticText(f"{label}"))
                
    def setPoints(self, points:QtGui.QPolygonF) -> None:
        self.points = points
            
    def _movePoint(self, index:int, point:QtCore.QPointF, emitUpdate:typing.Optional[bool]=False) -> None:
        self._points[index] = bound_point(point, self.boundingRect(), self._locks[index])
        if emitUpdate:
            self.firePointChange()
        
    
    def firePointChange(self, fromResize:bool=False):
        if self._sortType != HoverPoints.SortType.NoSort:
            oldCurrent = QtCore.QPointF()
            
            if self._currentIndex != -1:
                oldCurrent = self._points[self._currentIndex]
                
            if self._sortType == HoverPoints.SortType.XSort:
                sortedPoints = sorted([p for p in self._points], key = lambda x: x.x())
                
            elif self._sortType == HoverPoints.SortType.YSort:
                sortedPoints = sorted([p for p in self._points], key = lambda x: x.y())
                
            self._points = QtGui.QPolygonF(sortedPoints)
            
            if self._currentIndex != -1:
                for i, p in enumerate(self._points):
                    if p == oldCurrent:
                        self._currentIndex = i
                        break
        if not fromResize:
            self.pointsChanged.emit(self._points)

def printGradientStops(g:typing.Union[QtGui.QGradient, typing.Sequence[typing.Tuple[numbers.Real, QtGui.QColor]]], 
                       nTabs:int=0, out:bool=True, 
                       caller:typing.Optional[typing.Union[str, typing.Callable[..., typing.Any]]]=None,
                       prefix:str = "",
                       suffix:str = "") -> typing.Optional[str]:
    """Prints out gradient stops in an uniform fashion.
    Particularly helpful for debugging
    
    Parameters:
    ----------
    g: QtGui.QGradient, or a QGradientStops (sequence of (float,QColor) tuples)
    
        NOTE: in Qt, QGradientStops is an alias for QVector<QGradientStop>, 
                whereas QGradientStop is an alias for QPair<qreal, QColor>
                
        In Python (PyQt5), these types are "mapped" as follows:
        
        QVector -> list
        QPair   -> tuple with two elements
        
        This means that QGradientStops are represented, in Python, as a list of 
        two-element tuples (float, QColor). This function also accepts an 
        n-tuple (or any iterable) containing (float, QColor) tuples.
    
    nTabs:int; optional, default is 0
        How many tab characters to prepend to each line
        
    out:bool; optional, default True
        When True, the function prints to console and returns None; otherwise, 
        the function returns the string that would be printed, instead of 
        printing it.
        
    caller: a callable (function or method); optional (default is None)
        When given, the string representation of the caller will be prepended
        
    prefix, suffix: str (optional, default is the empty string "")
        Text to be prepended, repsectively, appended, to the output
    """
    
    if isinstance(g, QtGui.QGradient):
        stops = g.stops()
    elif isinstance(g, (tuple, list)) and all([isinstance(v, (tuple, list)) and len(v) == 2 and isinstance(v[0], numbers.Number) and isinstance(v[1], QtGui.QColor) for v in g]):
        stops = g
    else:
        if out:
            print("NOT A QGRADIENT")
        else:
            return "NOT A QGRADIENT"
        
    txt = list()
    
    tabtxt = "\t" * nTabs
    
    txt.append("%s%d stops:" % (tabtxt, len(stops)))
    
    if inspect.isfunction(caller) or inspect.ismethod(caller):
        txt.insert(0,"%s%s" % (tabtxt, caller.__qualname__))
        
    elif isinstance(caller, str):
        if caller.lower().strip() == "auto":
            stack = inspect.stack()
            if len(stack) > 1:
                caller = stack[1].function
            else:
                caller = ""
            
        txt.insert(0,"%s%s" % (tabtxt, caller))
        
        
    tabtxt = "\t" * (nTabs+1)
    
    for k, s in enumerate(stops):
        txt.append("%s%d: %s -> %s" % (tabtxt, k, s[0], s[1].name(QtGui.QColor.HexArgb)))
        
    if len(prefix.strip()):
        txt.insert(0, "%s%s" % ("\t" * (nTabs), prefix))

    if len(suffix.strip()):
        txt.appnd("%s%s" % ("\t" * (nTabs), suffix))
        
    ret = "\n".join(txt)

    if out:
        print(ret)
        
    else:
        return ret
        
def printPoints(points:typing.Union[QtGui.QPolygonF, QtGui.QPolygon, typing.Sequence[typing.TypeVar("point", QtCore.QPoint, QtCore.QPointF)]],
                nTabs:int=0, out:bool=True, 
                caller:typing.Optional[typing.Union[str, typing.Callable[..., typing.Any]]]=None,
                prefix:str="",
                suffix:str="") -> typing.Optional[str]:
    """Prints out the x,y coordinates of a sequence of QPoint or QPointF objects
    Particularly helpful for debugging.
    
    Parameters:
    ----------
    
    points: a QtGui.QPolygon, QtGui.QPolygonF, or an iterable (tuple, list)
        containing QtCore.QPoint and/or QtCore.QPointF objects
    
    nTabs:int; optional, default is 0
        How many tab characters to prepend to each line
        
    out:bool; optional, default True
        When True, the function prints to console and returns None; otherwise, 
        the function returns the string that would be printed, instead of 
        printing it.
        
    caller: a callable (function or method); optional (default is None)
        When given, the string representation of the caller will be prepended
        
    prefix, suffix: str (optional, default is the empty string "")
        Text to be prepended, repsectively, appended, to the output
    
    """
    
    txt = list()
    
    tabtxt = "\t" * nTabs
    
    txt.append("%s%d points:" % (tabtxt, len(points)))
    
    if inspect.isfunction(caller) or inspect.ismethod(caller):
        txt.insert(0,"%s%s" % (tabtxt, caller.__qualname__))
        
    elif isinstance(caller, str):
        if caller.lower().strip() == "auto":
            stack = inspect.stack()
            if len(stack) > 1:
                caller = stack[0].function
            else:
                caller = ""
            
        txt.insert(0,"%s%s" % (tabtxt, caller))
        
    tabtxt = "\t" * (nTabs+1)
    
    for k, p in enumerate(points):
        txt.append("%s%d: x = %s, y = %s" % (tabtxt, k, p.x(), p.y()))
        
    if len(prefix.strip()):
        txt.insert(0, "%s%s" % ("\t" * (nTabs), prefix))

    if len(suffix.strip()):
        txt.appnd("%s%s" % ("\t" * (nTabs), suffix))
        
    ret = "\n".join(txt)
    
    if out:
        print(ret)
        
    else:
        return ret
        
class ColorGradient():
    """Encapsulates the appearance of a conical, linear or radial Qt gradient.
    
    It is a callable, therefore it can be used as a factory for one of the Qt 
    gradient :classes:: QtGui.QConicalGradient, QtGui.QLinearGradient, and
    QtGui.QConicalGradient
    """
    _descriptors_ = ("preset") # in the generic case, this is a QtGui.QGradient.Preset enum value
    _gradient_type_ = QtGui.QGradient.NoGradient # QtGui.QGradient.Type enum value
    _required_attributes_ = ("_ID_","coordinates", "coordinateMode", "spreadMode", "stops", "type", )
    _qtclass_ = QtGui.QGradient
    
    @safeWrapper
    def _importQGradient_(self, g) -> typing.Union[QtGui.QLinearGradient,QtGui.QRadialGradient,QtGui.QConicalGradient]:
        # NOTE: 2021-06-24 12:05:00
        # below, if g is of a conforming type, no conversion occurs
        # ('conforming type' means a QLinearGradient passed to g2l, etc)
        # NOTE: 2021-09-16 18:23:09
        # for generic QGradient we convert automatically according to the
        # gradient's type() value
        if isinstance(self, LinearColorGradient):
            return g2l(g)
        
        if isinstance(self, ConicalColorGradient):
            return g2c(g)
        
        if isinstance(self, RadialColorGradient):
            return g2r(g)
        
        else:
            # NOTE: 2021-09-16 17:52:46
            # because a generic QGradient is not very useful (it only encapsulates
            # gradient stops) we convert anything here to to a more concrete type
            gtype = reverse_mapping_lookup(standardQtGradientTypes, g.type())
            if gtype == "RadialGradient":
                return g2r(g) # make this linear by default
            
            if gtype == "ConicalGradient":
                return g2c(g)
            
            return g2l(g)
            
    def _checkQtGradient_(self, x):
        return isinstance(x, (self._qtclass_, QtGui.QGradient.Preset)) # or (isinstance(x, QtGui.QGradient) and x.type() & self._gradient_type_)
    
    def _init_parametric_(self, *args, stops, spread, coordinateMode, name):
        if len(args):
            self._coordinates_ = DataBag(zip(self._descriptors_, args), use_mutable=True, use_casting=False, allow_none=True)
        else:
            self._coordinates_ = DataBag(use_mutable=True, use_casting=False, allow_none=True)
            
        self._stops_ = stops
        self._spread_ = spread
        self._coordinateMode_ = coordinateMode
        if len(name.strip()):
            self._ID_ = name
        else:
            self._ID_ = type(self).__name__
            
    def __init__(self, *args, **kwargs):
        """ColorGradient constructor:
        
        Variadic parameters:
        --------------------
        *args: unpacked sequence of objects, with the following alterntives:
        
            1) a sequence of floats with a number of coordinates as appropriate
                to the gradient type:
                Linear: x0, y0, x1, y1 (coordinates of start and final stop points,
                                        respectively)
                Radial: x0, y0, r0, x1, y1, r1 (coordinates and radius of the 
                                        center and focal points, respectively)
                Conical: x, y, alpha: coordinates of the center and the angle
                
            2) an instance of QtGui.QGradient (either generic or one of its concrete
            gradient subclasses: QtGui.QLinearGradient, QtGui.QConicalGradient,
            QtGui.QRadialGradient)
            
            3) a str, with the value being a valid QtGui.QGradient.Preset key
            (e.g. "AboveTheSky") -- see gui.painting_shared.standardQtGradientPresets
            for details
            
            4) a QtGui.QGradient.Preset (the value itself, not its 'key', as in (3))
               
            5) an int with the value being a valid QtGui.QGradient.Preset enum value
            WARNING if the value it NOT a value Preset enum value the constructor
            issues a warning and the gradient will have the defaults as below
            
        Varkeyword parameters:
        ---------------------
        stops: sequence of (float, QtGui.QColor) tuples = the gradient color stops
            (default: [(0.0, QtGui.QColor(QtCore.Qt.white)), (1.0, QtGui.QColor(QtCore.Qt.black))])
            
        spread: a QtGui.QGradient.Spread enum value or int (default: PadSpread)
        
        coordinateMode: a QtGui.QGradient.CoordinateMode enum value or int
            (default: QtGui.QGradient.PadSpread)
            
        name: str, default "" (empty str, which forces the "name" attribute to be the name of the gradient type)
        
        atol, rtol: floats, default 1e-3 for both: absolute and relative tolerances,
            respectively, for comparing x coordinates of the gradient stops 
            (these are always normalized in the closed interval [0., 1.])
        
        Returns:
        --------
        
        None (is a constructor)
        
        Behaviour:
        ---------
        
        The object is intialized according to the variadic parameters args as 
        follows:
        
        When called directly as a constructor for ColorGradient:
            a) When 'args' contain one concrete QtGui gradient object (i.e., one of
                QtGui.QLinearGradient, QtGui.QConicalGradient, QtGui,QRadialGradient):
                
                The constructor works like a factory function, e.g.:
                
                In: g = ColorGradient(q_lg)

                In: type(g)
                Out: gui.planargraphics.LinearColorGradient

                In this example, 'q_gl' is a QtGui.QLinearGradient object.
                
            b) When args contain a QtGui.QGradient object (i.e. a 'generic' Qt
                gradient) or a standard Qt gradient preset name, value 
                or int that resolves to an existing preset:
                
                The constructor initializes a concrete ColorGradient type
                based on the value returned by the QGradient object's type()
                method (default is a LinearColorGradient)
                
            c) When args contain a sequence of numeric values, or args ARE a 
                sequence of numeric values:
                
                The constructor works like a factory as in (a), but the :class:
                of the object being initalized is according to the number of 
                values in the sequence:
                3 => ConicalColorGradient
                4 => LinearColorGradient
                6 => RadialColorGradient
                
            ATTENTION: The upshot of this is that a ColorGradient object can 
            NEVER be initialized (i.e. the constructor ALWAYS returns an instance
            of a concrete ColorGradient :class:: LinearColorGradient, 
            RadialColorGradient, or ConicalColorGradient)
            
                
        """
        stops = kwargs.get("stops", [(0.0, QtGui.QColor(QtCore.Qt.white)),
                                     (1.0, QtGui.QColor(QtCore.Qt.black))])
        spread = kwargs.get("spread", QtGui.QGradient.PadSpread)
        coordinateMode = kwargs.get("coordinateMode", QtGui.QGradient.LogicalMode)
        name = kwargs.get("name", "")
        
        self.atol = kwargs.get("atol", 1e-3)
        self.rtol = kwargs.get("rtol", 1e-3)
        
        # CAUTION 2021-06-24 11:19:29
        # this is called by concrete subclasses, too (LinearColorGradient, ConicalColorGradient, RadialColorGradient)
        # 
        
        self._valid = False
        self._normalized = False
        self._stops_ = list()
        
        if len(args):
            #print("args", args)
            if len(args) == 1:
                if isinstance(args[0], (tuple, list)) and all([isinstance(v, numbers.Real) for v in args[0]]):
                    # construct from parameters (depends on the concrete subclass)
                    # then return
                    if isinstance(self, ColorGradient):
                        # kick in factory code to initalize concrete color gradient
                        if len(args[0]) == 3:
                            cls = ConicalColorGradient
                            qcls = QtGui.QConicalGradient
                        elif len(args[0]) == 4:
                            cls = LinearColorGradient
                            qcls = QtGui.QLinearGradient
                        elif len(args[0]) == 6:
                            cls = RadialColorGradient
                            qcls = QtGui.QRadialGradient
                        else:
                            raise RuntimeError("Expecting 3, 4 or 6 numeric parameters; got %s instead" % len(args[0]))
                        
                        self.__class__ = cls
                        self._qtclass_ = qcls
                        self._gradient_type_ = cls._gradient_type_
                        self._descriptors_ = cls._descriptors_
                        self._coordinates_ = DataBag(zip(cls._descriptors_, args[0]))
                        self._stops_ = g.stops()
                        self._spread_ = g.spread()
                        self._coordinateMode_ = g.coordinateMode()
                        self.name = name
                    else:
                        self._init_parametric_(args[0], 
                                            stops=stops, 
                                            spread=spread, 
                                            coordinateMode=coordinateMode, 
                                            name=name)
                    return
                
                if isinstance(args[0], str):
                    if args[0] not in standardQtGradientPresets.keys():
                        raise ValueError("Unknown gradient preset name %s" % args[0])
                    
                    # NOTE: 2021-06-24 10:18:05
                    # when a str, must it must be a valid QGradient.Preset enum key
                    # Qt only allows direct construction of a generic QGradient
                    # from a preset, and the result always has type() 0 (i.e.,
                    # QtGui.QGradient.LinearGradient)
                    
                    # NOTE: 2021-09-16 17:57:13 As of now, _importQGradient_
                    # returns a concrete gradient when a generic QGradient is 
                    # passed (by default, a LinearGradient unless the generic
                    # grandient's type() returns otherwise, EXCLUDING 'NoGradient')
                    qg = QtGui.QGradient(standardQtGradientPresets[args[0]])
                    
                    g = self._importQGradient_(qg)
                    
                    name = args[0] 
                    
                elif isinstance(args[0], (QtGui.QGradient.Preset, int)):
                    # see NOTE: 2021-09-16 17:57:13
                    qg = QtGui.QGradient(args[0])
                    g = self._importQGradient_(qg)
                    
                    if args[0] in standardQtGradientPresets.values():
                        # override 'name' parameter
                        name = reverse_mapping_lookup(standardQtGradientPresets, args[0])
                        
                    else: # shouldn't happen
                        warnings.warn("No standard Qt gradient preset %d exists" % args[0])
                    
                elif isinstance(args[0], QtGui.QGradient):
                    # see NOTE: 2021-09-16 17:57:13
                    g = self._importQGradient_(args[0])
                    
                    name = reverse_mapping_lookup(standardQtGradientTypes, args[0].type())

                elif isinstance(args[0], ColorGradient):
                    g = args[0]() # generate QGradient from args[0]
                    
                else:
                    raise TypeError("Unexpected argument type %s" % type(args[0]).__name__)
                    
                # NOTE: 2021-06-24 11:37:04 
                # OK, so now g is either a generic QGradient or a concrete 
                # QLinearGradient/QConicalGradient/QRadialGradient object
                #
                # The following possibilities exist:
                if not isinstance(self, (ConicalColorGradient, LinearColorGradient, RadialColorGradient)):
                    # a) self is a generic ColorGradient:
                    if isinstance(g, (QtGui.QConicalGradient, QtGui.QLinearGradient, QtGui.QRadialGradient)):
                        # a.1) BUT: g is an instance of a concrete QGradient subclass
                        # we "cast" 'self' to a concrete subclass (i.e one of ConicalColorGradient,
                        # LinearColorGradient, or RadialColorGradient), see
                        # NOTE: 2021-06-24 14:50:54 below
                        #
                        # this is sort of a factory method => cls is a concrete ColorGradient subclass
                        #
                        # and allows the following example code to run, where
                        # q_lg is a QtGui.QLinearGradient, for example:
                        #
                        # In: g = ColorGradient(q_lg)
                        # 
                        # In: type(g)
                        # Out: gui.planargraphics.LinearColorGradient
                        # 
                        if isinstance(g, QtGui.QConicalGradient):
                            cls = ConicalColorGradient
                            qcls = QtGui.QConicalGradient
                        elif isinstance(g, QtGui.QLinearGradient):
                            cls = LinearColorGradient
                            qcls = QtGui.QLinearGradient
                        elif isinstance(g, QtGui.QRadialGradient):
                            cls = RadialColorGradient
                            qcls = QtGui.QRadialGradient
                        else:
                            raise RuntimeError("Incorect use of %s as factory for ColorGradient subclass instance by passing a %s object; try using the 'gui.planargraphics.colorGradient' factory function instead" % (type(self).__name__, type(g).__name__))
                            
                        # NOTE: 2021-06-24 14:50:54
                        # this kind of "casting" of sorts might be frowned upon, 
                        # but will successfully inform the interpreter that self
                        # is now a Conical/Linear/RadialColorGradient object,
                        # and not just a (generic) ColorGradient object
                        self.__class__ = cls
                        self._qtclass_ = qcls
                        self._gradient_type_ = cls._gradient_type_
                        self._descriptors_ = cls._descriptors_
                        self._coordinates_ = DataBag(zip(cls._descriptors_, gradientCoordinates(g)))
                        self._stops_ = g.stops()
                        self._spread_ = g.spread()
                        self._coordinateMode_ = g.coordinateMode()
                        self.name = name
                    
                    else:
                        # NOTE: 2021-09-16 18:05:52
                        # not reaching here anymore, because _importQGradient_
                        # now returns a concrete gradient type it is fed a 
                        # generic QGradient
                        # a.2) self is generic ColorGradient AND 
                        # g is a generic QGradient
                        # OK - just import the other params
                        self._init_parametric_((name,), 
                                               stops=g.stops(),
                                               spread=g.spread(),
                                               coordinateMode=g.coordinateMode(),
                                               name=name)
                        
                    return
                
                # b) self is an instance of a ColorGradient subclass, and g is
                # an instance of a compatible QGradient subclass because it was
                # imported via _importQGradient_()
                self._init_parametric_(*gradientCoordinates(g),
                                    stops = g.stops(),
                                    spread = g.spread(),
                                    coordinateMode = g.coordinateMode(),
                                    name = name)
                
                    
            elif all([isinstance(v, numbers.Real) for v in args]):
                if isinstance(self, ColorGradient):
                    # kick in factory code
                    if len(args) == 3:
                        cls = ConicalColorGradient
                        qcls = QtGui.QConicalGradient
                    elif len(args) == 4:
                        cls = LinearColorGradient
                        qcls = QtGui.QLinearGradient
                    elif len(args) == 6:
                        cls = RadialColorGradient
                        qcls = QtGui.QRadialGradient
                    else:
                        raise RuntimeError("Expecting 3, 4 or 6 numeric parameters; got %s instead" % len(args))
                    
                    self.__class__ = cls
                    self._qtclass_ = qcls
                    self._gradient_type_ = cls._gradient_type_
                    self._descriptors_ = cls._descriptors_
                    self._coordinates_ = DataBag(zip(cls._descriptors_, args))
                    self._stops_ = g.stops()
                    self._spread_ = g.spread()
                    self._coordinateMode_ = g.coordinateMode()
                    self.name = name
                    
                else:
                    # initialize instance of concrete gradient type
                    self._init_parametric_(args, stops, spread, coordinateMode, name)
                
            else:
                raise RuntimeError("Expecting a sequence of floats")
            
        else:
            self._init_parametric_(stop=stops, spread=spread, coordinateMode=coordinateMode,name=name)
            
    def __getattr__(self, name):
        # attribute access to coordinates
        if name in self.__class__._descriptors_:
            return self._coordinates_[name]
        
        return object.__getattribute__(self, name)
    
    def __setattr__(self, name, value):
        # attribute access to coordinates
        if name in self.__class__._descriptors_:
            self._coordinates_[name] = value
            
        else:
            object.__setattr__(self, name, value)
            
    @property
    def name(self):
        return self._ID_
    
    @name.setter
    def name(self, val:str):
        if not isinstance(val, str) or len(val.strip()) == 0:
            self._ID_ = type(self).__name__
            
        else:
            self._ID_ = val
            
    @property
    def coordinates(self) -> DataBag:
        return self._coordinates_
    
    @coordinates.setter
    def coordinates(self, *args):
        if not isinstance(self, (ConicalColorGradient, LinearColorGradient, RadialColorGradient)):
            return
        
        if len(args) == 1 and isinstance(args[0], (tuple, list)) and all([isinstance(v, numbers.Real) for v in args[0]]):
            args = args[0]
        
        elif not all([isinstance(v, numbers.Real) for v in args]):
            raise TypeError("Expecting a sequence of real scalars")
        
        if isinstance(self, ConicalColorGradient):
            if len(args) != 3:
                raise RuntimeError("Expecting 3 parameters")
            
        elif isinstance(self, LinearColorGradient):
            if len(args) != 4:
                raise RuntimeError("Expecting 4 parameters")
            
        elif isinstance(self, RadialColorGradient):
            if len(args) != 6:
                raise RuntimeError("Expecting 6 parameters")
            
        for k,c in enumerate(self._descriptors_):
            self._coordinates_[c] = args[k]
            
    @property
    def coordinateMode(self) -> QtGui.QGradient.CoordinateMode:
        return self._coordinateMode_
    
    @coordinateMode.setter
    def coordinateMode(self, value:typing.Union[QtGui.QGradient.CoordinateMode, int]):
        self._coordinateMode_ = value
        
    @property
    def stops(self) -> list:
        return self._stops_
    
    @stops.setter
    def stops(self, value):
        if not isinstance(value, (tuple, list)):
            return
        
        if not all([isinstance(v, (tuple, list)) and len(v) == 2 and isinstance(v[0], numbers.Real) and isinstance(v[1], QtGui.QColor)]):
            return
        
        self._stops_[:] = sorted(list(value), key = lambda x: x[0])
        
    @property
    def spread(self) -> QtGui.QGradient.Spread:
        return self._spread_
        
    @spread.setter
    def spread(self, value:typing.Union[QtGui.QGradient.Spread, int]):
        self._spread_ = value
        
    def colorAt(self, k:int) -> QtGui.QColor:
        if k >= len(self.stops) or k < 0:
            return QtGui.QColor(QtCore.Qt.black)
        
        return self.stops[k][1]
    
    def setColorAt(self, x:typing.Union[int, float], color:QtGui.QColor):
        """Set the color at a gradient stop.
        
        Parameters:
        -----------
        x: int or float
            When an int, 'x' specifies the index of the gradient stop and can take
            values in the range(len(self.stops))
            
            When a float, 'x' can take any value in the closed interval [0., 1.]
            If 'x' is the x value of an existing gradient stop (or close enough
            to it at the relative and absolute tolerances given by self.atol and
            self.rtol (by default, 1e-3) then the color at that stop is assigned
            a new value; otherwise, a new stop is being added to the gradient, 
            with the specified color.
            
        color: QtGui.QColor: the new color
        """
        if isinstance(x, int):
            if x >= len(self.stops) or x < 0:
                raise ValueError("When an int, 'x' must be in the half-open interval [0, %d); got %d instead" % (len(self.stops), x))
            
            self.stops[x][1] = color
            
        elif isinstance(x, float):
            if x < 0 or x > 1:
                raise ValueError("When a float, 'x' must be in the closed interval [0., 1.]; got %s instead" % x)
            
            xx = sorted([s[0] for s in self.stops])
            
            found_stops = list(np.arange(len(xx))[np.isclose(xx, x, atol=self.atol, rtol=self.rtol)])
            
            if len(found_stops):
                self.stops[found_stops[0]] = color
                
            else:
                self.addStop(x, color)
            
    def addStop(self, x:float, color:QtGui.QColor):
        if x < 0 or x  > 1:
            raise ValueError("New value must be in the interval [0,1]")
        
        xx = sorted([s[0] for s in self.stops])
        
        i = np.searchsorted(xx, x)
        
        self.stops.insert(i, (x, color))
        
    def removeStop(self, x:typing.Union[int, float]):
        if isinstance(x, int):
            if x >= len(self.stops) or x < 0:
                raise ValueError("When an int, 'x' must be in the half-open interval [0, %d); got %d instead" % (len(self.stops), x))
        
            del self.stops[x]
            #self.stops.pop(x)
            
        elif isinstance(x, float):
            if x < 0 or x > 1:
                raise ValueError("When a float, 'x' must be in the closed interval [0., 1.]; got %s instead" % x)
        
            xx = sorted([s[0] for s in self.stops])
            
            found_stops = list(np.arange(len(xx))[np.isclose(xx, x, atol=self.atol, rtol=self.rtol)])
            
            if len(found_stops):
                del g.stops[found_stops[0]]
                #self.stops.pop(found_stops[0])
            
    def normalize(self, rect:typing.Union[QtCore.QRect, QtCore.QRectF]):
        if self._normalized:
            return
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()
        if isinstance(self, LinearColorGradient):
            x0 = (self.coordinates.x0-x)/w
            y0 = (self.coordinates.y0-y)/w
            x1 = (self.coordinates.x1-x)/w
            y1 = (self.coordinates.y1-y)/w
            self.coordinates.x0 = x0
            self.coordinates.y0 = y0
            self.coordinates.x1 = x1
            self.coordinates.y1 = y1
            
        elif isinstance(self, RadialColorGradient):
            x0 = (self.coordinates.x0-x)/w
            y0 = (self.coordinates.y0-y)/w
            r0 = self.coordinates.r0 / min([w/2, h/2])
            x1 = (self.coordinates.x1-x)/w
            y1 = (self.coordinates.y1-y)/w
            r1 = self.coordinates.r1 / min([w/2, h/2])
            self.coordinates.x0 = x0
            self.coordinates.y0 = y0
            self.coordinates.r0 = r0
            self.coordinates.x1 = x1
            self.coordinates.y1 = y1
            self.coordinates.r1 = r1
            
        elif isinstance(self, ConicalColorGradient):
            x0 = (self.coordinates.x0-x)/w
            y0 = (self.coordinates.y0-y)/w
            self.coordinates.x0 = x0
            self.coordinates.y0 = y0
        else: 
            #NOTE: 2021-06-09 13:27:28
            # by default, when constructed from a preset this is a linear gradient
            # see NOTE: 2021-06-09 13:27:41
            return
        
        self._normalized = True
        
    def scale(self, rect:typing.Union[QtCore.QRect, QtCore.QRectF]):
        if not self._normalized:
            return
        
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()
        
        if isinstance(self, LinearColorGradient):
            x0 = self.coordinates.x0 * w + x
            y0 = self.coordinates.y0 * h + y
            x1 = self.coordinates.x1 * w + x
            y1 = self.coordinates.y1 * h + y
            self.coordinates.x0 = x0
            self.coordinates.y0 = y0
            self.coordinates.x1 = x1
            self.coordinates.y1 = y1
            
        elif isinstance(self, RadialColorGradient):
            x0 = self.coordinates.x0 * w + x
            y0 = self.coordinates.y0 * h + y
            r0 = self.coordinates.r0 * min([w/2, h/2])
            x1 = self.coordinates.x1 * w + x
            y1 = self.coordinates.y1 * h + y
            r1 = self.coordinates.r1 * min([w/2, h/2])
            self.coordinates.x0 = x0
            self.coordinates.y0 = y0
            self.coordinates.r0 = r0
            self.coordinates.x1 = x1
            self.coordinates.y1 = y1
            self.coordinates.r1 = r1
            
        elif isinstance(self, ConicalColorGradient):
            x0 = self.coordinates.x0 * w + x
            y0 = self.coordinates.y0 * h + y
            self.coordinates.x0 = x0
            self.coordinates.y0 = y0
        else:
            return
        
        self._normalized = False
        
    def rescale(self, src_rect, dest_rect):
        if self._normalized:
            self.normalize(src_rect)
            
        self.scale(dest_rect)
            
    def __call__(self) -> typing.Union[QtGui.QGradient, QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient]:
        """Factory for a concrete QGradient object based on this object's attributes
        
        A 'concrete' QGradient is a QLinearGradient, QRadialGradient, or a 
        QConicalGradient object.
        """
        coords = (v for v in self.coordinates.values())
        ret = self._qtclass_(*coords)
        ret.setStops(self._stops_)
        ret.setSpread(self._spread_)
        ret.setCoordinateMode(self._coordinateMode_)
        return ret
    
    @property
    def valid(self):
        """Read-only.
        This is always False for ColorGradient objects and True for ColorGradient
        subclass instances (LinearColorGradient, RadialColorGradient, ConicalColorGradient)
        """
        return self._valid
    
class LinearColorGradient(ColorGradient):
    _descriptors_ = ("x0", "y0", "x1", "y1", )
    _gradient_type_ = QtGui.QGradient.LinearGradient
    _qtclass_ = QtGui.QLinearGradient
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._valid = True
                
class RadialColorGradient(ColorGradient):
    _descriptors_ = ("x0", "y0", "r0", "x1", "y1", "r1")
    _gradient_type_ = QtGui.QGradient.RadialGradient
    _qtclass_ = QtGui.QRadialGradient
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._valid = True
                

class ConicalColorGradient(ColorGradient):
    _descriptors_ = ("x0", "y0", "angle")
    _gradient_type_ = QtGui.QGradient.ConicalGradient
    _qtclass_ = QtGui.QConicalGradient
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._valid = True

def colorGradient(*args, **kwargs) -> ColorGradient:
    """Factory for Linear, Radial and Conical color gradient objects
    
    Originally indended to be used in order to avoid generating instances of the 
    more generic ColorGradient :class:.
    
    NOTE: 2021-09-16 18:33:52
    
    As of now, this function is superceded by the constructor for ColorGradient,
    which now makes it (nearly) impossible to generate an instance of 
    ColorGradient directly.
    
    However, it is kept here for the benefit of code still using it (notably,
    GradientDialog, BrushLnF, etc)
    
    Variadic parameters (*args):
    ============================
    Either a QtGui.QGradient, or a sequence of float values (gradient coordinates)
    When a QGradient, it must be a QGradient subclass (QLinearGradient, 
    QRadialGradient, QConicalGradient) or a QGradient with type() != QGradient.NoGradient
    
    When a sequence of floats, these can be packed as a tuple or list in the first
    argument, or can be unpacked (as comma-separated arguements)
    
    Varkeyword parameters: - see ColorGradient.__init__
    ======================
    stop
    spread
    coordinateMode
    name
    
    Returns
    ========
    An object which is either a subclass of ColorGradient (LinearColorGradient,
    RadialColorGradient or ConicalColorGradient), based on the QGradient subclass
    in args[0] or on the number of float values in args.
    When neither parameters in args make sense, returns a generic ColorGradient object.
    """
    if len(args):
        if len(args)==1:
            if isinstance(args[0], QtGui.QGradient):
                if isinstance(args[0], QtGui.QLinearGradient) or args[0].type() == QtGui.QGradient.LinearGradient:
                    return LinearColorGradient(*args)
                elif isinstance(args[0], QtGui.QRadialGradient) or args[0].type() == QtGui.QGradient.RadialGradient:
                    return RadialColorGradient(*args)
                elif isinstance(args[0], QtGui.QConicalGradient) or args[0].type() == QtGui.QGradient.ConicalGradient:
                    return ConicalColorGradient(*args)
                else:
                    raise TypeError(f"Unsupported gradient type {type(args[0]).__name__} ({reverse_mapping_lookup(standardQtGradientTypes, args[0].type())})")
                
            elif isinstance(args[0], str):
                if args[0] not in standardQtGradientPresets:
                    raise ValueError(f"Unknown gradient preset {args[0]}")
                
                return LinearColorGradient(args[0])
            
            elif isinstance(args[0], (QtGui.QGradient.Preset, int)):
                if isinstance(args[0], int) and args[0] not in standardQtGradientPresets.values():
                    raise ValueError(f"Unknown gradient preset {args[0]}")
                    
                return LinearColorGradient(args[0])
                
            elif isinstance(args[0], (tuple, list) and all([isinstance(v, numbers.Real) for v in args])):
                if len(args[0]) == 3:
                    return ConicalColorGradient(*args[0], **kwargs)
                elif len(args[0]) == 4:
                    return LinearColorGradient(*args[0],  **kwargs)
                elif len(args[0]) == 6:
                    return RadialColorGradient(*args[0],  **kwargs)
                else:
                    raise ValueError(f"Unexpected number of coordinates {len(args[0])}")
                    
        elif all([isinstance(v, numbers.Real) for v in args]):
            if len(args) == 3:
                return ConicalColorGradient(*args, **kwargs)
            elif len(args) == 4:
                return LinearColorGradient(*args, **kwargs)
            elif len(args) == 6:
                return RadialColorGradient(*args, **kwargs)
            else:
                raise ValueError(f"Unexpected number of coordinates {len(args[0])}")
            
    return ColorGradient(**kwargs)

class Brush(Bunch):
    """Encapsulates the appearance atribute of a QtGui.QBrush.
    
    It is a callable, therefore it can be used as a QBrush factory.
    
    All members are expected to be str, with the following exceptions:
    
    gradient: can also be a sequence of numbers, an int (standard gradient) or a
        ColorGradient
        
    pixmap, texture: str , bytes
    
    In addition, when image, pixmap or texture are a str this is supposed to
    be the qualified name of a file containing the image or pixmap data.
    
    """
    def __init__(self, color:str="white", style:str="SolidPattern", 
                 gradient:typing.Optional[typing.Union[str, tuple, list, ColorGradient, int]]=None, 
                 texture:typing.Optional[typing.Union[str, bytes]]=None,
                 image:typing.Optional[str]=None,
                 pixmap:typing.Optional[typing.Union[str, bytes]]=None,
                 name:typing.Optional[str]=None) -> None:
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = self.__class__.__name__
        super().__init__(color=color, style=style, gradient=gradient,
                         texture=texture, image=image, pixmap=pixmap,
                         name=name)
        
    def __call__(self):
        if isinstance(self.gradient, (str, tuple, list, int)):
            grad = colorGradient(gradient)
            return QtGui.QBrush(grad)
        
        if isinstance(self.gradient, ColorGradient):
            return QtGui.QBrush(gradient())
        
        if isinstance(self.pixmap, str) and os.path.isfile(self.pixmap):
            pixmap = QtGui.QPixmap(self.pixmap)
            
            return QtGui.QBrush(pixmap)
        
        if isinstance(self.pixmap, bytes):
            try:
                pixmap = QtGui.QPixmap(self.pixmap.decode())
                return QtGui.QBrush(self.pixmap)
            except:
                raise
            
        if isinstance(self.texture, str) and os.path.isfile(self.texture):
            texture = QtGui.QPixmap(self.texture)
            return QtGui.QBrush(qcolor(self.color), self.texture)
        
        if isinstance(self.texture, bytes):
            try:
                texture = QtGui.QPixmap(self.texture.decode())
                return QtGui.QBrush(qcolor(self.color), self.texture)
            except:
                raise
            
        if isinstance(self.image, str) and os.path.isfile(self.image):
            image = QtGui.QImage(self.image)
            return QtGui.QBrush(self.image)
        
        return QtGui.QBrush(qcolor(self.color), self.style)
        
class Pen(Bunch):
    """Encapsulatesthe appearance attribute of a QtGui.QPen.
    
    It is a callable, therefore it can be used as a QPen factory.
    
    All member attributes are :str: with the exception of 'brush' (Brush) and
    'cosmetic' (bool)
    """
    def __init__(self, width:float=1., color:str="black", style:str="SolidLine", 
                 cap:str="SquareCap", join:str="BevelJoin", cosmetic:bool=True,
                 brush:typing.Optional[typing.Optional[Brush]]=None,
                 name:typing.Optional[str]=None) -> None:
        """Default constructor mimics the default behaviour of the QtGui.QPen
        constructor
        """
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = self.__class__.__name__
            
        super().__init__(width=width, color=color, style=style, cap=cap, 
                         join=join, brush=brush, cosmetic=cosmetic, name=name)
        
    def __call__(self):
        style = standardQtPenStyles.get(self.style, QtCore.Qt.SolidLine)
        cap = standardQtPenCapStyles.get(self.cap, QtCore.Qt.SquareCap)
        join = standardQtPenJoinStyles.get(self.join, QtCore.Qt.BevelJoin)
        
        if isinstance(self.brush, Brush):
            brush = self.brush()
            pen = QtGui.QPen(brush, self.width, style=style, cap=cap, join=join)
        
        else:
            pen = QtGui.QPen(style)
            pen.setColor(qcolor(self.color))
            
        pen.setCosmetic(self.cosmetic)
        return pen
        
        
        
        

