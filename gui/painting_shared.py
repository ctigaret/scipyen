import numbers, os, typing
from enum import IntEnum, auto
from collections import OrderedDict

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import sip # for sip.cast

from core.prog import (safeWrapper, no_sip_autoconversion)
from core.traitcontainers import DataBag

from .scipyen_colormaps import (qtGlobalColors, standardPalette,
                                standardPaletteDict, svgPalette,
                                getPalette, paletteQColors, paletteQColor, 
                                standardQColor, svgQColor,
                                qtGlobalColors, mplColors)

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

standardQtPenStyles = OrderedDict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenStyle) and val < 10],
                           key = lambda x: x[1]))

standardQtPenJoinStyles = OrderedDict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenJoinStyle) and val <= 256],
                           key = lambda x: x[1]))

standardQtPenCapStyles = OrderedDict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenCapStyle) and val <= 32],
                           key = lambda x: x[1]))

customDashStyles = {"Custom": [10., 5., 10., 5., 10., 5., 1., 5., 1., 5., 1., 5.]}

standardQtGradientPresets = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Preset) and name != "NumPresets"]))

standardQtGradientSpreads = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Spread)]))

standardQtGradientTypes = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Type)],
                                      key = lambda x: x[1]))
validQtGradientTypes = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Type) and value < 3],
                                      key = lambda x: x[1]))

standardQtBrushStyles = OrderedDict(sorted([(name, value) for name, value in vars(QtCore.Qt).items() if isinstance(value, QtCore.Qt.BrushStyle)],
                                           key = lambda x: x[1]))

standardQtBrushPatterns = OrderedDict(sorted([(name, value) for name, value in standardQtBrushStyles.items() if all([s not in name for s in ("Gradient", "Texture")])],
                                           key = lambda x: x[1]))

standardQtBrushGradients = OrderedDict(sorted([(name, value) for name, value in standardQtBrushStyles.items() if "Gradient" in name],
                                           key = lambda x: x[1]))

standardQtBrushTextures = OrderedDict(sorted([(name, value) for name, value in standardQtBrushStyles.items() if "Texture" in name],
                                           key = lambda x: x[1]))

def populateMimeData(mimeData:QtCore.QMimeData, color:typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]):
    from core.datatypes import reverse_dict
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
        if gradient.type() == QtGui.QGradient.ConicalGradient:
            return sip.cast(gradient, QtGui.QConicalGradient)
        
        if gradient.type() == QtGui.QGradient.LinearGradient:
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

def linearcoords(x):
    return (x.start().x(), x.start().y(), x.finalStop().x(), x.finalStop().y())
    
def radialcoords(x):
    return (x.center().x(),     x.center().y(),     x.centerRadius(), 
            x.focalPoint().x(), x.focalPoint().y(), x.focalRadius())
    
def conicalcoords(x):
    return (x.center().x(), x.center().y(), x.angle())
    
def gradientCoordinates(x:QtGui.QGradient) -> tuple:
    if isinstance(x, QtGui.QLinearGradient):
        return linearcoords(x)
    elif isinstance(x, QtGui.QRadialGradient):
        return radialcoords(x)
    elif isinstance(x, QtGui.QConicalGradient):
        return conicalcoords(x)
    
    elif isinstance(x, QtGui.QGradient):
        if x.type() & QtGui.QGradient.LinearGradient:
            x_ = sip.cast(x, QtGui.QLinearGradient)
            return linearcoords(x_)
        elif x.type() & QtGui.QGradient.RadialGradient:
            x_ = sip.cast(x, QtGui.QRadialGradient)
            return radialcoords(x_)
        elif x.type() & QtGui.QGradient.ConicalGradient:
            x_ = sip.cast(x, QtGui.QConicalGradient)
            return conicalcoords(x_)
        
    return (0., 0., 0., 0.)

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
        raise TypeError("Expecting a concrete QGradient subtype; got %s instead" % type(g).__name__)
        
def normalizeGradient(gradient:QtGui.QGradient, rect:typing.Union[QtCore.QRect, QtCore.QRectF]) -> QtGui.QGradient:
    x = rect.x()
    y = rect.y()
    w = rect.width()
    h = rect.height()
    coords = gradientCoordinates(gradient)
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
        r0 = coords[2] / min([w/2, h/2])
        x1 = (coords[3]-x)/w
        y1 = (coords[4]-y)/h
        r1 = coords[5] / min([w/2, h/2])
        g = QtGui.QRadialGradient(x0, y0, r0, x1, y1, r1)
        g.setStops(gradient.stops())
        g.setSpread(gradient.spread())
        g.setCoordinateMode(gradient.coordinateMode())
        return g
    
    elif isinstance(g, QtGui.QConicalGradient):
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
        
    def __init__(self, widget:QtWidgets.QWidget, shape:PointShape, debug:bool=False):
        super().__init__(widget)
        self._debug = debug
        
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
        self._pointSize = QtCore.QSize(11, 11)
        self._currentIndex = -1
        self._editable = True
        self._enabled = True
        self._points = QtGui.QPolygonF()
        self._bounds = QtCore.QRectF()
        self._locks = list() # of QPoint/QPointF
        
        #self._fingerPointMapping = dict() # see NOTE 2021-05-21 21:29:33 touchscreens
        
        self.pointsChanged.connect(self._widget.update)
        
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value:bool) -> None:
        if self._enabled != value:
            self._enabled = value
            self._widget.update()
            
        
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
        x = p.x() - w/2 
        y = p.y() - h/2
        return QtCore.QRectF(x, y, w, h)
    
    #@property
    def boundingRect(self) -> QtCore.QRectF:
        if self._bounds.isNull() or self._bounds.isEmpty() or not self._bounds.isValid():
            return QtCore.QRectF(self._widget.rect())
        else:
            return self._bounds
        
    #@boundingRect.setter
    #def boundingRect(self, boundingRect:QtCore.QRectF) -> None:
        #self._bounds = boundingRect
        
    def setBoundingRect(self, boundingRect:QtCore.QRectF) -> None:
        self._bounds = boundingRect
        
    @property
    def points(self) -> QtGui.QPolygonF:
        return self._points
    
    #def points(self, points:typing.Union[QtGui.QPolygonF,typing.Iterable[typing.Union[QtCore.QPointF, QtCore.QPoint]]]) -> None:
        #if isinstance(points, (list, tuple)) and len(points) and all([isinstance(v, (QtCore.QPoint, QtCore.QPointF)) for v in points]):
            #points = QtGui.QPolygonF(points)
        #elif not isinstance(points, QtGui.QPolygonF):
            #raise TypeError("points expected a QtGui.QPolygonF, or a sequence of QtCore.QPointF or QtCore.QPoint; got %s instead" % type(points).__name__)
    @points.setter
    def points(self, points:QtGui.QPolygonF) -> None:
        # NOTE: 2021-05-23 20:57:59
        # QPolygonF has API compatible with list() (on C++ side is a QVector<QPointF>)
        #if points.size() != self._points.size():
        #if len(points) != len(self._points):
            #self._fingerPointMapping.clear() # see NOTE 2021-05-21 21:29:33 touchscreens
        
        #print("HoverPoints.points =", self, [p for p in points])
        self._points.clear() # just so that refs to QPointF are garbage-collected
        self._points = QtGui.QPolygonF([bound_point(p, self.boundingRect(), 0) for p in points])
        if self._debug:
            print("HoverPoints._points =", self, [p for p in self._points])
        #self._points = QtGui.QPolygonF([bound_point(p, self.rect(), 0) for p in points])
        #boundedPoints = [bound_point(points.at(i), self.boundingRect(), 0) for i in range(points.size())]
        #print("HoverPoints._points", [p for p in self._points])
        
        self._locks.clear()
        
        #if self._points.size():
        if len(self._points):
            self._locks = [0] * len(self._points)
            #self._locks = [0] * self._points.size()
            
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
                    #me = QtGui.QMouseEvent(ev)
                    
                    clickPos = me.pos()
                    
                    index = -1
                    
                    # NOTE: 2021-05-24 10:50:53
                    # check if event os is on a point
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
                    
                    if me.button() == QtCore.Qt.LeftButton: 
                        # add new point or select clicked one & filter event
                        if index == -1: 
                            # new point added (index is unchanged from -1 because 
                            # clickPos is not any points - see  NOTE: 2021-05-24 10:50:53)
                            if not self._editable: # non-editable => don't block (filter) event
                                return False
                            
                            pos = 0
                            
                            if self._sortType == HoverPoints.SortType.XSort:
                                #for i in range(self._points.size()):
                                # see  NOTE: 2021-05-24 10:44:48
                                for k, p in enumerate(self._points):
                                    if p.x() > clickPos.x():
                                        pos = k
                                        break
                                #for i in range(len(self._points)):
                                    ##if self._points.at(i).x() > clickPos.x():
                                    #if self._points[i].x() > clickPos.x():
                                        #pos = i
                                        #break
                                    
                            elif self._sortType == HoverPoints.SortType.YSort:
                                #for i in range(self._points.size()):
                                # see  NOTE: 2021-05-24 10:44:48
                                for k, p in enumerate(self._points):
                                    if p.y() > clickPos.y():
                                        pos = k
                                        break
                                #for i in range(len(self._points)):
                                    ##if self._points.at(i).y() > clickPos.y():
                                    #if self._points[i].y() > clickPos.y():
                                        #pos = i
                                        #break
                                    
                            # add point at index pos
                            self._points.insert(pos, clickPos)
                            self._locks.insert(pos, 0)
                            self._currentIndex = pos
                            self.firePointChange()
                        
                        else:
                            self._currentIndex = index
                            
                        return True # stop (filter) event
                    
                    elif me.button() == QtCore.Qt.RightButton: # remove point if editable & propagate event
                        if index >= 0 and self._editable: 
                            if self._locks[index] == 0:
                                self._locks.pop(index)
                                self._points.remove(index)
                                
                            self.firePointChange()
                            return True
                        
                        return False
                        
                elif ev.type() == QtCore.QEvent.MouseButtonRelease:
                    #if len(self._fingerPointMapping):
                        #return True
                    self._currentIndex = -1
                    
                    return False
                    
                elif ev.type() == QtCore.QEvent.MouseMove:
                    #if len(self._fingerPointMapping):
                        #return True
                    
                    if self._currentIndex >= 0:
                        self._movePoint(self._currentIndex, ev.pos(), True)
                        
                    return False
                    
                #elif ev.type() == QtCore.QEvent.TouchBegin:
                    #pass # see NOTE 2021-05-21 21:29:33 touchscreens
                
                #elif ev.type() == QtCore.QEvent.TouchUpdate:
                    #pass # see NOTE 2021-05-21 21:29:33 touchscreens - skipped code
                #elif ev.type() == QtCore.QEvent.TouchEnd:
                    #pass # see NOTE 2021-05-21 21:29:33 touchscreens - skipped code
                elif ev.type() == QtCore.QEvent.Resize:
                    e = sip.cast(ev, QtGui.QResizeEvent)
                    if e.oldSize().width() != 0 and e.oldSize().height() != 0:
                        stretch_x = e.size().width()  / e.oldSize().width()
                        stretch_y = e.size().height() / e.oldSize().height()
                        for i,p in enumerate(self._points):
                            self._movePoint(i, QtCore.QPointF(p.x() * stretch_x, p.y() * stretch_y), False)
                            
                        self.firePointChange()
                        #for i in range(self._points.size()):
                            #p = self._points[i]
                            
                    return False
                    
                elif ev.type() == QtCore.QEvent.Paint:
                    #print("HoverPoints.eventFilter: paint event")
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
        
        #for i, p in enumerate(self._points):
        for point in self._points:
            bounds = self._pointBoundingRect(point)
            if self._shape == HoverPoints.PointShape.CircleShape:
                p.drawEllipse(bounds)
            else:
                p.drawRect(bounds)
                    
    def setPoints(self, points:QtGui.QPolygonF) -> None:
        self.points = points
            
    def _movePoint(self, index:int, point:QtCore.QPointF, emitUpdate:typing.Optional[bool]=False) -> None:
        self._points[index] = bound_point(point, self.boundingRect(), self._locks[index])
        if emitUpdate:
            self.firePointChange()
        
    
    def firePointChange(self):
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
                    
        self.pointsChanged.emit(self._points)

