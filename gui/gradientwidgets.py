""" see qt examples/widgets/painting/gradients
"""
import array, os, typing, numbers
import numpy as np
from collections import OrderedDict
from enum import IntEnum, auto
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import sip

from core.prog import (safeWrapper, no_sip_autoconversion)

from core.datatypes import (reverse_dict, reverse_mapping_lookup)

from .painting_shared import (HoverPoints, x_less_than, y_less_than,
                              qtGlobalColors, standardPalette, standardPaletteDict, 
                              svgPalette, getPalette, paletteQColors, paletteQColor, 
                              standardQColor, svgQColor, qtGlobalColors, mplColors,
                              make_transparent_bg, make_checkers,
                              comboDelegateBrush,
                              standardQtGradientPresets,
                              standardQtGradientSpreads,
                              standardQtGradientTypes,
                              validQtGradientTypes,
                              standardQtBrushGradients,
                              g2l, g2c, g2r,
                              gradientCoordinates,
                              normalizeGradient, 
                              scaleGradient,
                              rescaleGradient,
                              )

from .planargraphics import (ColorGradient, colorGradient,)

from . import quickdialog as qd

class ShadeWidget(QtWidgets.QWidget):
    colorsChanged = pyqtSignal(QtGui.QPolygonF, name="colorsChanged")
    
    class ShadeType(IntEnum):
        RedShade = auto()
        GreenShade = auto()
        BlueShade = auto()
        ARGBShade = auto()
        
    def __init__(self, shadeType:ShadeType, 
                 parent:typing.Optional[QtWidgets.QWidget]=None) -> None:
        
        super().__init__(parent=parent)
        
        self._shade = QtGui.QImage()
        
        #print("ShadeWidget.__init__ shadeType", shadeType)
        self._shadeType = shadeType
        
        self._alphaGradient = QtGui.QLinearGradient(0, 0, 0, 0)
        
        if self._shadeType == ShadeWidget.ShadeType.ARGBShade:
            # create checkers background for Alpha channel display
            pm = make_checkers(QtCore.Qt.lightGray, QtCore.Qt.darkGray, 20)
            pal = QtGui.QPalette()
            pal.setBrush(self.backgroundRole(), QtGui.QBrush(pm))
            self.setAutoFillBackground(True)
            self.setPalette(pal)
            
        else:
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
            
        # NOTE: 2021-05-23 20:59:37
        # QPolygon and QPolygonF are API-compatible with list()
        points = QtGui.QPolygonF([QtCore.QPointF(0, self.sizeHint().height()),
                                  QtCore.QPointF(self.sizeHint().width(), 0)])
        
        #print("ShadeWidget.__init__ polygon", [p for p in points])
        
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape)
        self._hoverPoints.points = points
        self._hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
        self._hoverPoints.setPointLock(1, HoverPoints.LockType.LockToRight)
        self._hoverPoints.sortType = HoverPoints.SortType.XSort
        
        #self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed) # horizontal, vertical
        #self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed) # horizontal, vertical
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding) # horizontal, vertical
        
        self._hoverPoints.pointsChanged[QtGui.QPolygonF].connect(self.colorsChanged)
        
    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(150,40)
    
    @property
    def hoverPoints(self) -> HoverPoints:
        return self._hoverPoints
        
    @property
    def points(self) -> QtGui.QPolygonF:
        return self._hoverPoints.points
        
    def colorAt(self, x:int) -> int:
        self._generateShade()
        
        pts = self._hoverPoints.points
        for k in range(1, len(pts)):
            #print("ShadeWidget.colorAt x %s: point at %d, %s, at %d, %s" % (x, i-1, pts.at(i-1).x(), i, pts.at(i).x()))
            if pts[k-1].x() <= x and pts[k].x() >= x:
                l = QtCore.QLineF(pts[k-1], pts[k])
                if l.dx() > 0:
                    l.setLength(l.length() * ((x - l.x1()) / l.dx()))
                    return self._shade.pixel(round(min([l.x2(), float(self._shade.width()  - 1)])),
                                            round(min([l.y2(), float(self._shade.height() - 1)])))
                return 0
        return 0
    
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        if self._shadeType == ShadeWidget.ShadeType.ARGBShade:
            self._alphaGradient = QtGui.QLinearGradient(0, 0, self.width(), 0)
            
            for stop in stops:
                c = QtGui.QColor(stop[1])
                self._alphaGradient.setColorAt(stop[0], QtGui.QColor(c.red(), c.green(), c.blue()))
                
            self._shade = QtGui.QImage()
            self._generateShade()
            self.update()
            
    def paintEvent(self, ev:QtGui.QPaintEvent) -> None:
        self._generateShade()
        
        p = QtGui.QPainter(self)
        
        p.drawImage(0,0,self._shade)
        p.setPen(QtGui.QColor(146, 146, 146))
        p.drawRect(0,0, self.width() - 1, self.height() - 1)
        
    def resizeEvent(self, e:QtGui.QResizeEvent) -> None:
        self._generateShade
        super().resizeEvent(e)
        
    def _generateShade(self) -> None:
        if self._shade.isNull() or self._shade.size() != self.size():
            if self._shadeType == ShadeWidget.ShadeType.ARGBShade:
                self._shade = QtGui.QImage(self.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
                self._shade.fill(0)
                
                p = QtGui.QPainter(self._shade)
                p.fillRect(self.rect(), self._alphaGradient)
                
                p.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
                fade = QtGui.QLinearGradient(0,0,0,self.height())
                fade.setColorAt(0, QtGui.QColor(0,0,0,255))
                fade.setColorAt(1, QtGui.QColor(0,0,0,0))
                p.fillRect(self.rect(), fade)
                
            else:
                self._shade = QtGui.QImage(self.size(), QtGui.QImage.Format_RGB32)
                shade = QtGui.QLinearGradient(0,0,0,self.height())
                shade.setColorAt(1, QtCore.Qt.black)
                if self._shadeType == ShadeWidget.ShadeType.RedShade:
                    shade.setColorAt(0, QtCore.Qt.red)
                elif self._shadeType == ShadeWidget.ShadeType.GreenShade:
                    shade.setColorAt(0, QtCore.Qt.green)
                else:
                    shade.setColorAt(0, QtCore.Qt.blue)
                    
                p = QtGui.QPainter(self._shade)
                p.fillRect(self.rect(), shade)
                
        
class GradientEditor(QtWidgets.QWidget):
    gradientStopsChanged = pyqtSignal(object, name="gradientStopsChanged")
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(1)
        vbox.setContentsMargins(1, 1, 1, 1)
        
        self._redShade = ShadeWidget(ShadeWidget.ShadeType.RedShade, self)
        self._greenShade = ShadeWidget(ShadeWidget.ShadeType.GreenShade, self)
        self._blueShade = ShadeWidget(ShadeWidget.ShadeType.BlueShade, self)
        self._alphaShade = ShadeWidget(ShadeWidget.ShadeType.ARGBShade, self)
        
        vbox.addWidget(self._redShade)
        vbox.addWidget(self._greenShade)
        vbox.addWidget(self._blueShade)
        vbox.addWidget(self._alphaShade)

        self._redShade.colorsChanged.connect(self.pointsUpdated)
        self._greenShade.colorsChanged.connect(self.pointsUpdated)
        self._blueShade.colorsChanged.connect(self.pointsUpdated)
        self._alphaShade.colorsChanged.connect(self.pointsUpdated)
    
    @pyqtSlot(object)
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        pts_red = list() 
        pts_green = list() 
        pts_blue = list() 
        pts_alpha = list() 
        
        h_red = float(self._redShade.height())
        h_green = float(self._greenShade.height())
        h_blue = float(self._blueShade.height())
        h_alpha = float(self._alphaShade.height())
        
        for i in range(len(stops)):
            pos = float(stops[i][0])
            
            qrgb = QtGui.QColor(stops[i][1]).rgba()
            
            pts_red.append(QtCore.QPointF(pos * self._redShade.width(),
                                          h_red - QtGui.qRed(qrgb) * h_red / 255))
    
            pts_green.append(QtCore.QPointF(pos * self._greenShade.width(),
                                          h_green - QtGui.qGreen(qrgb) * h_green / 255))
    
            pts_blue.append(QtCore.QPointF(pos * self._blueShade.width(),
                                          h_blue - QtGui.qBlue(qrgb) * h_blue / 255))
    
            pts_alpha.append(QtCore.QPointF(pos * self._alphaShade.width(),
                                          h_alpha - QtGui.qAlpha(qrgb) * h_alpha / 255))
            
        set_shade_points(QtGui.QPolygonF(pts_red), self._redShade)
        set_shade_points(QtGui.QPolygonF(pts_green), self._greenShade)
        set_shade_points(QtGui.QPolygonF(pts_blue), self._blueShade)
        set_shade_points(QtGui.QPolygonF(pts_alpha), self._alphaShade)
    
    @pyqtSlot(QtGui.QPolygonF)
    def pointsUpdated(self, points:QtGui.QPolygonF):
        w = float(self._alphaShade.width())
        
        stops = list()
        
        points = QtGui.QPolygonF()
        points += self._redShade.points
        points += self._greenShade.points
        points += self._blueShade.points
        points += self._alphaShade.points

        sortedPoints = sorted([p for p in points], key = lambda x: x.x())
        #sortedPoints = sorted([p for p in points], key = x_less_than)
        
        #print("GradientEditor.pointsUpdated: " len(sortedPoints))
        
        for i, point in enumerate(sortedPoints):
            k = int(point.x())
            #k = int(sortedPoints.at(i).x())
            if i + 1 < len(sortedPoints) and k == int(sortedPoints[i+1].x()):
                continue
            
            color = QtGui.QColor((0x00ff0000 & self._redShade.colorAt(k)) >> 16,   # red
                                 (0x0000ff00 & self._greenShade.colorAt(k)) >> 8,  # green
                                 (0x000000ff & self._blueShade.colorAt(k)),        # blue
                                 (0xff000000 & self._alphaShade.colorAt(k)) >> 24) # transparent
            
            if k / w > 1:
                return
            
            stops.append((k/w, color))
        
        self._alphaShade.setGradientStops(stops)
        
        self.gradientStopsChanged.emit(stops)
        
class GradientRenderer(QtWidgets.QWidget):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None,
                 autoCenterRadius:bool=True, relativeCenterRadius:bool=False,
                 autoFocalRadius:bool=True, relativeFocalRadius:bool=False,
                 centerRadius:typing.Optional[float]=None,
                 focalRadius:typing.Optional[float]=None, 
                 hoverPoints:typing.Optional[QtGui.QPolygonF]=QtGui.QPolygonF(), 
                 gradientStops:list = list(),
                 gradientSpread:typing.Union[QtGui.QGradient.Spread, int] = QtGui.QGradient.PadSpread,
                 coordinateMode:typing.Union[QtGui.QGradient.CoordinateMode, int] = QtGui.QGradient.LogicalMode,
                 ) -> None:
        super().__init__(parent=parent)
        
        # NOTE: 2021-05-23 22:18:35 ArthurFrame FIXME/TODO factor out
        # NOTE: NOT using OpenGL
        #self._prefer_image = False
        #### BEGIN
        # related to on-ascreen help/description - not needed here
        #self._document = None
        #self._show_doc = False
        # NOTE 2021-05-23 22:23:16 use make_checkers instead
        #self._tile = QtGui.QPixmap(128,128)
        ##self._tile.fill(QtCore.Qt.white)
        #self._tile.fill(QtCore.Qt.lightGray)
        #pt = QtGui.QPainter(self._tile)
        #color = QtGui.QColor(30,230,230)
        #color = QtGui.QColor(QtCore.Qt.darkGray)
        #pt.fillRect(0,0,64,64, color)
        #pt.fillRect(64,64,64,64, color)
        #pt.end()
        #### END
        
        self._tile = make_checkers(QtCore.Qt.lightGray,
                                   QtCore.Qt.darkGray,
                                   128)
        
        
        self._def_width = self._def_height = 400
        
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape)
        #self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape,
                                        #debug=True)
        #print("GradientRenderer.__init__ hoverPoints", self._hoverPoints)
        self._hoverPoints.pointSize = QtCore.QSize(20,20)
        self._hoverPoints.connectionType = HoverPoints.ConnectionType.NoConnection
        self._hoverPoints.editable = False
        
        if not isinstance(hoverPoints, QtGui.QPolygonF) or hoverPoints.size() == 0:
            self._hoverPoints.points = QtGui.QPolygonF([QtCore.QPointF(100, 100), QtCore.QPointF(200,200)])
        else:
            self._hoverPoints.points = hoverPoints
            
        self._gradient = None
        
        #self._stops = list()
        
        self._stops = gradientStops
        #self._spread = QtGui.QGradient.PadSpread
        self._spread = gradientSpread
        self._coordinateMode = coordinateMode
        self._gradientBrushType = QtCore.Qt.LinearGradientPattern # this is a Qt.BrushStyle enum value
        #self._gradient = None # NOTE: 2021-05-24 13:15:41 Cezar Tigaret
        self._centerRadius = centerRadius
        self._useAutoCenterRadius = autoCenterRadius
        self._useRelativeCenterRadius = relativeCenterRadius
        self._focalRadius = focalRadius
        self._useAutoFocalRadius = autoFocalRadius
        self._useRelativeFocalRadius = relativeFocalRadius
        
    @property
    def focalRadius(self) -> numbers.Real:
        return self._focalRadius
    
    @focalRadius.setter
    def focalRadius(self, value:numbers.Real) -> None:
        self._focalRadius = value
        #self.update()
        
    @property
    def centerRadius(self) -> numbers.Real:
        if self._centerRadius is None or self._useAutoCenterRadius:
            self._centerRadius = min([self.width(), self.height()]) / 3.0
            
        return self._centerRadius
    
    @centerRadius.setter
    def centerRadius(self, val:numbers.Real) -> None:
        self._centerRadius = val
        #self.update()
        
    @property
    def autoCenterRadius(self) -> bool:
        return self._useAutoCenterRadius
    
    @autoCenterRadius.setter
    def autoCenterRadius(self, val:bool) -> None:
        self._useAutoCenterRadius = val
        #self.update()
        
    @property
    def autoFocalRadius(self) -> bool:
        return self._useAutoFocalRadius
    
    @autoFocalRadius.setter
    def autoFocalRadius(self, val:bool) -> None:
        self._useAutoFocalRadius = val
        
    @property
    def relativeCenterRadius(self) -> bool:
        return self._useRelativeCenterRadius
    
    @relativeCenterRadius.setter
    def relativeCenterRadius(self, val:bool) -> None:
        self._useRelativeCenterRadius = val
        #self.update()
        
    @property
    def relativeFocalRadius(self) -> bool:
        return self._useRelativeFocalRadius
    
    @relativeFocalRadius.setter
    def relativeFocalRadius(self, val:bool) -> None:
        self._useRelativeFocalRadius = val
        
    #@property
    #def preferImage(self) -> bool:
        ## NOTE: 2021-05-24 08:26:56 ArthurWidget
        #return self._prefer_image
    
    #@preferImage.setter
    #def preferImage(self, val:bool) -> None:
        ## NOTE: 2021-05-24 08:26:56 ArthurWidget
        #self._prefer_image = val
        ##self.update()
        
    @property
    def gradientBrushType(self) -> typing.Union[QtCore.Qt.BrushStyle, int]:
        return self._gradientBrushType
    
    @gradientBrushType.setter
    def gradientBrushType(self, val:typing.Union[QtCore.Qt.BrushStyle, int]) -> None:
        #print("renderer.gradientBrushType val=",val)
        if val not in standardQtBrushGradients.values():
            return
        
        self._gradientBrushType = val
        #self.update()
        
    @property
    def gradient(self) -> QtGui.QGradient:
        return self._gradient
    
    @gradient.setter
    def gradient(self, g:typing.Union[QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient]) -> None:
        if isinstance(g, (QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient)):
            self._gradient = g
            self.hoverPoints.points = self._getLogicalStops(g)
            self._stops[:] = g.stops()

            if isinstance(g, QtGui.QRadialGradient):
                self._gradientBrushType = QtCore.Qt.RadialGradientPattern

            elif isinstance(g, QtGui.QConicalGradient):
                self._gradientBrushType = QtCore.Qt.ConicalGradientPattern

            else:
                self._gradientBrushType = QtCore.Qt.LinearGradientPattern
                
            self.update()
            
    @property
    def spread(self) -> typing.Union[QtGui.QGradient.Spread, int]:
        return self._spread
    
    @spread.setter
    def spread(self, val:typing.Union[QtGui.QGradient.Spread, int]) -> None:
        self._spread = val
        #self.update()
        
    @property
    def coordinateMode(self) -> typing.Union[QtGui.QGradient.CoordinateMode, int]:
        return self._coordinateMode
    
    @coordinateMode.setter
    def coordinateMode(self, val:typing.Union[QtGui.QGradient.CoordinateMode, int]) -> None:
        self._coordinateMode = val

    @property
    def gradientStops(self) -> typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]:
        return self._stops
    
    @gradientStops.setter
    def gradientStops(self, val:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        if not isinstance(val, (tuple, list)) or not all([self._checkStop(s) for s in val]):
            return
        self._stops[:] = val
        #self.update()
    
    @pyqtSlot(float)
    def setFocalRadius(self, val:float) -> None:
        self.focalRadius = val
        self.update()
        
    @pyqtSlot(float)
    def setCenterRadius(self, val:float) -> None:
        self.centerRadius = val
        self.update()

    @pyqtSlot()
    def setAutoCenterRadius(self) -> None:
        self.autoCenterRadius = True
        self.relativeCenterRadius = False
        self.update()
        
    @pyqtSlot()
    def setRelativeCenterRadius(self) -> None:
        self.autoCenterRadius = False
        self.relativeCenterRadius = True
        self.update()

    @pyqtSlot()
    def setAbsoluteCenterRadius(self) -> None:
        self.autoCenterRadius = False
        self.relativeCenterRadius = False
        self.update()
        
    @pyqtSlot()
    def setAutoFocalRadius(self) -> None:
        self._useAutoFocalRadius = True
        self._useRelativeFocalRadius = False
        self.update()
        
    @pyqtSlot()
    def setRelativeFocalRadius(self) -> None:
        self._useAutoFocalRadius=False
        self._useRelativeFocalRadius = True
        self.update()
        
    @pyqtSlot()
    def setAbsoluteFocalRadius(self) -> None:
        self._useAutoFocalRadius = False
        self._useRelativeFocalRadius = False
        self.update()
    
    @safeWrapper
    def paintEvent(self, e:QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setClipRect(e.rect())
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.save()
        painter.drawTiledPixmap(self.rect(), self._tile)
        self.paint(painter)
        painter.restore()
        
    def resizeEvent(self, e:QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        
    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self._def_width, self._def_height) # contemplate smaller sizes
    
    @property
    def hoverPoints(self) -> HoverPoints:
        return self._hoverPoints
    
    @pyqtSlot()
    def setPadSpread(self) -> None:
        self.spread = QtGui.QGradient.PadSpread
        self.update()
        
    @pyqtSlot()
    def setRepeatSpread(self) -> None:
        self.spread = QtGui.QGradient.RepeatSpread
        self.update()
        
    @pyqtSlot()
    def setReflectSpread(self) -> None:
        self.spread = QtGui.QGradient.ReflectSpread
        self.update()
        
    @pyqtSlot()
    def setLogicalCoordinateMode(self) -> None:
        self.coordinateMode = QtGui.QGradient.LogicalMode
        self.update()
        
    @pyqtSlot()
    def setDeviceCoordinateMode(self) -> None:
        self.coordinateMode = QtGui.QGradient.StretchToDeviceMode
        self.update()
        
    @pyqtSlot()
    def setObjectCoordinateMode(self) -> None:
        self.coordinateMode = QtGui.QGradient.ObjectMode
        self.update()
        
    @pyqtSlot()
    def setLinearGradient(self) -> None:
        self.gradientBrushType = QtCore.Qt.LinearGradientPattern
        self.update()
        
    @pyqtSlot()
    def setRadialGradient(self) -> None:
        self.gradientBrushType = QtCore.Qt.RadialGradientPattern
        self.update()
        
    @pyqtSlot()
    def setConicalGradient(self) -> None:
        self.gradientBrushType = QtCore.Qt.ConicalGradientPattern
        self.update()
        
    @pyqtSlot(object)
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        self.gradientStops = stops
        self.update()
        
    def _checkStop(self, val) -> bool:
        return isinstance(val, (tuple, list)) and len(val) == 2 and isinstance(val[0], numbers.Real) and isinstance(val[1], (QtGui.QColor, QtCore.Qt.GlobalColor))
        
    def _getStopsLine(self, gradient:typing.Union[QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient])-> QtGui.QPolygonF:
        if isinstance(gradient, QtGui.QLinearGradient):
            return QtCore.QLineF(gradient.start(), gradient.finalStop())

        elif isinstance(gradient, QtGui.QRadialGradient):
            return QtCore.QLineF(gradient.center(), gradient.focalPoint())

        elif isinstance(gradient, QtGui.QConicalGradient):
            # NOTE: 2021-05-27 15:31:42 
            # this is in logical coordinates i.e.
            # normalized to whatever size the paint device (widget/pimap, etc) has
            # NOTE: 2021-06-09 21:23:57 Not necessarily!!!
            gradCenter = gradient.center() 
            # NOTE: 2021-06-09 22:07:06 places the center mapped to real coordinates
            centerPoint = QtGui.QTransform.fromScale(self.width(), self.height()).map(gradient.center())
            #centerPoint = QtCore.QPointF(gradCenter.x() * self.rect().width(),
                                         #gradCenter.y() * self.rect().height())
            # NOTE: 2021-05-27 09:28:27
            # this paints the hover point symmetrically around the renderer's centre
            #l = QtCore.QLineF(self.rect().topLeft(), self.rect().topRight())
            #centerPoint = self.rect().center()
            #ret = QtCore.QLineF.fromPolar(l.length(), gradient.angle())
            #ret.translate(centerPoint)
            # NOTE: 2021-05-27 09:28:33
            # radius of an inscribed circle is the min orthogonal distance from
            # center to the rect sides
            ret = QtCore.QLineF.fromPolar(min([centerPoint.x(), centerPoint.y()]), gradient.angle())
            ret.translate(centerPoint)
            ## this should keep the gradient's centre where is meant to be ?
            #l = QtCore.QLineF(centerPoint, self.rect().topRight())
            #ret = QtCore.QLineF.fromPolar(l.length(), gradient.angle())
            return ret

        return QtCore.QLineF(QtCore.QPointF(0,0), QtCore.QPointF(self.width(), self.height()))
            
    def _getLogicalStops(self, gradient:typing.Union[QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient]):
        objectStopsLine = self._getStopsLine(gradient)
        
        # NOTE: 2021-06-09 21:40:36
        # this is why this works with both "normalized" and "unormalized" gradients.
        #scaleX = 1. if np.isclose(objectStopsLine.dx(), 0.) else 0.8 * self.width()  / abs(objectStopsLine.dx())
        #scaleY = 1. if np.isclose(objectStopsLine.dy(), 0.) else 0.8 * self.height() / abs(objectStopsLine.dy())
        
        scaleX = 1. if np.isclose(objectStopsLine.dx(), 0.) else self.width()  / abs(objectStopsLine.dx())
        scaleY = 1. if np.isclose(objectStopsLine.dy(), 0.) else self.height() / abs(objectStopsLine.dy())
        
        logicalStopsLine = QtGui.QTransform.fromScale(scaleX, scaleY).map(objectStopsLine)
        logicalStopsLine.translate(self.rect().center() - logicalStopsLine.center())
        
        return QtGui.QPolygonF((logicalStopsLine.p1(), logicalStopsLine.p2()))

    @safeWrapper
    def paint(self, p:QtGui.QPainter) -> None:
        # NOTE: 2021-05-27 08:17:19
        # not sure why, but if setting the painter brush to a gradient stored as
        # attribute to the renderer will crash this (SegmentationFault)
        # This is a problem, because it appears I cannot set the default gradient
        # to be displayed by passing a gradient object!
        # Therefore, the gradient displayed by the renderer MUST be dynamically
        # constructed here, in the paint() method, using:
        # 1. the stored gradient stops
        # 2. the logical stops for the hover points
        # 3. the stored type of the gradient (linear, radial or conical)
        # 4. the size of the widget.
        
        # The type of the gradient is decided by reading the gradient brush type
        # which will then paint a gradient accorindgly.
        
        # Similarly, the spread type and, for a radial gradient, the radii of the
        # central and focal points, need also to be stored in the renderer, as
        # separate attributes.
        
        g = QtGui.QGradient()
        pts = self._hoverPoints.points
    
        if self._gradientBrushType == QtCore.Qt.LinearGradientPattern:
            g = QtGui.QLinearGradient(pts[0], pts[1])
            
        elif self._gradientBrushType == QtCore.Qt.RadialGradientPattern:
            # NOTE: 2021-05-27 15:32:23
            # center is the first hover point (hover point [0])
            # center radius is 1/3 of minimal side (width or height)
            # focal point is 2nd hover point 
            # focal radius is 0 in the original code
            
            if self._centerRadius is None or self._useAutoCenterRadius:
                centerRadius = min([self.width(), self.height()]) / 3.0
                
            elif self._useRelativeCenterRadius:
                centerRadius = self._centerRadius * min([self.width(), self.height()])
                
            else:
                centerRadius = self._centerRadius
            
            if self._focalRadius is None or self._useAutoFocalRadius:
                focalRadius = 0.
                
            elif self._useRelativeFocalRadius:
                focalRadius = self._focalRadius * min([self.width(), self.height()])
                
            else:
                focalRadius = self._focalRadius
            
            g = QtGui.QRadialGradient(pts[0], centerRadius, pts[1], focalRadius)
            
        else: # conical gradient pattern
            l = QtCore.QLineF(pts[0], pts[1])
            
            # NOTE: 2021-05-24 14:18:59
            # line (0,0,1,0) = horizontal line
            # line.angleTo(l) = angle from horizontal line to line 'l'
            angle = QtCore.QLineF(0,0,1,0).angleTo(l)
            g = QtGui.QConicalGradient(pts[0], angle)
            
        for stop in self._stops:
            g.setColorAt(stop[0], QtGui.QColor(stop[1]))
            
        g.setSpread(self._spread)
        g.setCoordinateMode(self._coordinateMode)
        
        p.setBrush(g)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(self.rect())
        
        self._gradient = g # so it can be returned
        
class GradientWidget(QtWidgets.QWidget):
    # TODO: 2021-05-27 15:40:49
    # make a gradient combobox to choose from the list of gradients
    # instead of the current "Preset" group
    def __init__(self, gradient:typing.Optional[QtGui.QGradient]=None,
                 customGradients:dict=dict(),
                 parent:typing.Optional[QtWidgets.QWidget] = None, 
                 title:typing.Optional[str]="Scipyen Gradient Editor") -> None:
        super().__init__(parent=parent)
        
        self._title = title
        
        self._useRelativeCenterRadius = False
        self._useRelativeFocalRadius = False
        self._useAutoCenterRadius = True
        self._useAutoFocalRadius = True
        
        self._configureUI_()
        
        if self._useAutoCenterRadius:
            self._autoCenterRadiusButton.setChecked(True)
            self._centerRadiusSpinBox.setEnabled(False)
            
        elif self._useRelativeCenterRadius:
            self._relativeCenterRadiusButton.setChecked(True)
            self._centerRadiusSpinBox.setEnabled(True)
            self._centerRadiusSpinBox.setMinimum(0.)
            self._centerRadiusSpinBox.setMaximum(1.)
            
        else:
            self._absoluteCenterRadiusButton.setChecked(True)
            self._centerRadiusSpinBox.setEnabled(True)
            self._centerRadiusSpinBox.setMinimum(0.)
            self._centerRadiusSpinBox.setMaximum(min([self._renderer.width(), self._renderer.height()]))
        
        if self._useAutoFocalRadius:
            self._autoFocalRadiusButton.setChecked(True)
            self._focalRadiusSpinBox.setEnabled(False)
            
        elif self._useRelativeFocalRadius:
            self._relativeFocalRadiusButton.setChecked(True)
            self._focalRadiusSpinBox.setEnabled(True)
            
        else:
            self._absoluteFocalRadiusButton.setChecked(True)
            self._focalRadiusSpinBox.setEnabled(True)
        
        
        self._gradientIndex = 0
        self._defaultGradient = None
        self._gradients = dict()
        if len(customGradients):
            self._gradients = dict([(name, val) for name, val in customGradients.items()] + 
                                   [(name, val) for name, val in standardQtGradientPresets.items()])
        else:
            self._gradients.update(standardQtGradientPresets)
            
        self._setDefaultGradient(gradient)
        
        self._updatePresetName()
        self._changePresetBy(0)
            
            
        #self._autoFocalRadiusButton.animateClick()
        #self._autoCenterRadiusButton.animateClick()
        #QtCore.QTimer.singleShot(50, self._showDefault)
        
    def showEvent(self, ev):
        self._showGradient(self._defaultGradient)
        #self.update()
        ev.accept()
        
    def _configureUI_(self):
        self._renderer = GradientRenderer(self)
        
        self.mainContentWidget = QtWidgets.QWidget()
        self.mainGroup = QtWidgets.QGroupBox(self.mainContentWidget)
        self.mainGroup.setTitle("Gradients")
        
        self.editorGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.editorGroup.setTitle("Color Editor")
        
        self._editor = GradientEditor(self.editorGroup)
        
        self.typeGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.typeGroup.setTitle("Type")
        #self.typeGroup.setTitle("Gradient Type")
        
        self._linearButton = QtWidgets.QRadioButton("Linear", self.typeGroup)
        self._radialButton = QtWidgets.QRadioButton("Radial", self.typeGroup)
        self._conicalButton = QtWidgets.QRadioButton("Conical", self.typeGroup)
        
        self.radialParamsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.radialParamsGroup.setTitle("Radial Gradient Options")
        #self.radialParamsGroup.setTitle("Radial Gradients")
        
        self.gradientCenterRadiusGroup = QtWidgets.QGroupBox(self.radialParamsGroup)
        self.gradientCenterRadiusGroup.setTitle("Center Radius")
        
        self._autoCenterRadiusButton = QtWidgets.QRadioButton("Automatic", 
                                                        self.gradientCenterRadiusGroup)
        self._autoCenterRadiusButton.clicked.connect(self.setAutoCenterRadius)
        
        self._relativeCenterRadiusButton = QtWidgets.QRadioButton("Relative",
                                                            self.gradientCenterRadiusGroup)
        
        self._relativeCenterRadiusButton.clicked.connect(self.setRelativeCenterRadius)
        
        self._absoluteCenterRadiusButton = QtWidgets.QRadioButton("Absolute", 
                                                            self.gradientCenterRadiusGroup)
        
        self._absoluteCenterRadiusButton.clicked.connect(self.setAbsoluteCenterRadius)
        
        self._centerRadiusSpinBox = QtWidgets.QDoubleSpinBox(self.gradientCenterRadiusGroup)
        self._centerRadiusSpinBox.setMinimum(0)
        self._centerRadiusSpinBox.setMaximum(1)
        self._centerRadiusSpinBox.setStepType(QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        self._centerRadiusSpinBox.setSingleStep(0.01)
        self._centerRadiusSpinBox.valueChanged[float].connect(self.setCenterRadius)
        
        self.gradientFocalRadiusGroup = QtWidgets.QGroupBox(self.radialParamsGroup)
        self.gradientFocalRadiusGroup.setTitle("Focal Radius")
        
        self._autoFocalRadiusButton = QtWidgets.QRadioButton("Automatic", 
                                                        self.gradientFocalRadiusGroup)
        
        self._autoFocalRadiusButton.clicked.connect(self.setAutoFocalRadius)
        
        self._relativeFocalRadiusButton = QtWidgets.QRadioButton("Relative",
                                                            self.gradientFocalRadiusGroup)
        
        self._relativeFocalRadiusButton.clicked.connect(self.setRelativeFocalRadius)
        
        self._absoluteFocalRadiusButton = QtWidgets.QRadioButton("Absolute", 
                                                            self.gradientFocalRadiusGroup)
        
        self._absoluteFocalRadiusButton.clicked.connect(self.setAbsoluteFocalRadius)
        
        self._focalRadiusSpinBox = QtWidgets.QDoubleSpinBox(self.gradientFocalRadiusGroup)
        self._focalRadiusSpinBox.setMinimum(0)
        self._focalRadiusSpinBox.setMaximum(1)
        self._focalRadiusSpinBox.setStepType(QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        self._focalRadiusSpinBox.setSingleStep(0.01)
        self._focalRadiusSpinBox.valueChanged[float].connect(self.setFocalRadius)
        
        self.gradientCenterRadiusGroupLayout = QtWidgets.QVBoxLayout(self.gradientCenterRadiusGroup)
        self.gradientCenterRadiusGroupLayout.addWidget(self._autoCenterRadiusButton)
        self.gradientCenterRadiusGroupLayout.addWidget(self._relativeCenterRadiusButton)
        self.gradientCenterRadiusGroupLayout.addWidget(self._absoluteCenterRadiusButton)
        self.gradientCenterRadiusGroupLayout.addWidget(self._centerRadiusSpinBox)
        
        self.gradientFocalRadiusGroupLayout = QtWidgets.QVBoxLayout(self.gradientFocalRadiusGroup)
        self.gradientFocalRadiusGroupLayout.addWidget(self._autoFocalRadiusButton)
        self.gradientFocalRadiusGroupLayout.addWidget(self._relativeFocalRadiusButton)
        self.gradientFocalRadiusGroupLayout.addWidget(self._absoluteFocalRadiusButton)
        self.gradientFocalRadiusGroupLayout.addWidget(self._focalRadiusSpinBox)
        
        self.radialParamsLayout = QtWidgets.QHBoxLayout(self.radialParamsGroup)
        #self.radialParamsLayout = QtWidgets.QVBoxLayout(self.radialParamsGroup)
        self.radialParamsLayout.addWidget(self.gradientCenterRadiusGroup)
        self.radialParamsLayout.addWidget(self.gradientFocalRadiusGroup)
        
        self.spreadGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.spreadGroup.setTitle("Spread")
        #self.spreadGroup.setTitle("Spread Method")
        self._padSpreadButton = QtWidgets.QRadioButton("Pad", self.spreadGroup)
        self._padSpreadButton.setToolTip("Fill area with closest stop color")
        self._reflectSpreadButton = QtWidgets.QRadioButton("Reflect", self.spreadGroup)
        self._reflectSpreadButton.setToolTip("Reflect gradient outside its area")
        self._repeatSpreadButton = QtWidgets.QRadioButton("Repeat", self.spreadGroup)
        self._repeatSpreadButton.setToolTip("Repeat gradient outside its area")
        
        self.coordinateModeGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.coordinateModeGroup.setTitle("Coordinate Mode")
        self._logicalCoordinateButton = QtWidgets.QRadioButton("Logical", self.coordinateModeGroup)
        self._logicalCoordinateButton.setToolTip("Logical")
        self._logicalCoordinateButton.clicked.connect(self._renderer.setLogicalCoordinateMode)
        self._deviceCoordinateButton = QtWidgets.QRadioButton("Device", self.coordinateModeGroup)
        self._deviceCoordinateButton.setToolTip("Stretch to Device")
        self._deviceCoordinateButton.clicked.connect(self._renderer.setDeviceCoordinateMode)
        self._objectCoordinateButton = QtWidgets.QRadioButton("Object", self.coordinateModeGroup)
        self._objectCoordinateButton.setToolTip("Object")
        self._objectCoordinateButton.clicked.connect(self._renderer.setObjectCoordinateMode)
        
        self.coordinateModeLayout = QtWidgets.QHBoxLayout(self.coordinateModeGroup)
        self.coordinateModeLayout.addWidget(self._logicalCoordinateButton)
        self.coordinateModeLayout.addWidget(self._deviceCoordinateButton)
        self.coordinateModeLayout.addWidget(self._objectCoordinateButton)
        
        
        self.presetsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.presetsGroup.setTitle("Gradients")
        self.presetsGroup.setToolTip("Available Gradients (including Qt's presets)")
        self.prevPresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.prevPresetButton.setIcon(QtGui.QIcon.fromTheme("go-previous"))
        self.prevPresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        self._presetButton = QtWidgets.QPushButton("(unset)", self.presetsGroup)
        self._presetButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Fixed)
        self.nextPresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.nextPresetButton.setIcon(QtGui.QIcon.fromTheme("go-next"))
        self.nextPresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        #self._updatePresetName()
        
        self.mainGroupLayout = QtWidgets.QVBoxLayout(self.mainGroup)
        self.mainGroupLayout.addWidget(self.editorGroup)
        self.typeSpreadGroup = QtWidgets.QGroupBox(self.mainGroup)
        
        self.typeSpreadLayout = QtWidgets.QHBoxLayout(self.typeSpreadGroup)
        self.typeSpreadLayout.addWidget(self.typeGroup)
        self.typeSpreadLayout.addWidget(self.spreadGroup)
        self.mainGroupLayout.addWidget(self.typeSpreadGroup)
        self.mainGroupLayout.addWidget(self.coordinateModeGroup)
        #self.mainGroupLayout.addWidget(self.typeGroup)
        #self.mainGroupLayout.addWidget(self.spreadGroup)
        
        self.mainGroupLayout.addWidget(self.radialParamsGroup)

        self.mainGroupLayout.addWidget(self.presetsGroup)
        
        self.editorGroupLayout = QtWidgets.QVBoxLayout(self.editorGroup)
        self.editorGroupLayout.addWidget(self._editor)
        
        self.typeGroupLayout = QtWidgets.QVBoxLayout(self.typeGroup)
        self.typeGroupLayout.addWidget(self._linearButton)
        self.typeGroupLayout.addWidget(self._radialButton)
        self.typeGroupLayout.addWidget(self._conicalButton)

        self.spreadGroupLayout = QtWidgets.QVBoxLayout(self.spreadGroup)
        self.spreadGroupLayout.addWidget(self._padSpreadButton)
        self.spreadGroupLayout.addWidget(self._reflectSpreadButton)
        self.spreadGroupLayout.addWidget(self._repeatSpreadButton)
        
        
        self._linearButton.setChecked(True)
        self._padSpreadButton.setChecked(True)
        self._logicalCoordinateButton.setChecked(True)

        self.presetsGroupLayout = QtWidgets.QHBoxLayout(self.presetsGroup)
        self.presetsGroupLayout.addWidget(self.prevPresetButton)
        self.presetsGroupLayout.addWidget(self._presetButton, 1)
        self.presetsGroupLayout.addWidget(self.nextPresetButton)
        
        self.mainGroup.setLayout(self.mainGroupLayout)
        
        self.mainContentLayout = QtWidgets.QVBoxLayout()
        self.mainContentLayout.addWidget(self.mainGroup)
        self.mainContentWidget.setLayout(self.mainContentLayout)
        
        self.mainScrollArea = QtWidgets.QScrollArea()
        self.mainScrollArea.setWidget(self.mainContentWidget)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Preferred, 
                                        QtWidgets.QSizePolicy.Preferred)

        self.vSplitter = QtWidgets.QSplitter(self)
        self.vSplitter.addWidget(self._renderer)
        self.vSplitter.addWidget(self.mainScrollArea)
        self.mainLayout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.addWidget(self.vSplitter)
        
        self._editor.gradientStopsChanged.connect(self._renderer.setGradientStops)
        self._linearButton.clicked.connect(self._renderer.setLinearGradient)
        self._radialButton.clicked.connect(self._renderer.setRadialGradient)
        self._conicalButton.clicked.connect(self._renderer.setConicalGradient)
        
        self._padSpreadButton.clicked.connect(self._renderer.setPadSpread)
        self._reflectSpreadButton.clicked.connect(self._renderer.setReflectSpread)
        self._repeatSpreadButton.clicked.connect(self._renderer.setRepeatSpread)
        
        self.prevPresetButton.clicked.connect(self.setPrevPreset)
        self._presetButton.clicked.connect(self.setPreset)
        self.nextPresetButton.clicked.connect(self.setNextPreset)
        
        if isinstance(self._title, str) and len(self._title.strip()):
            self.setWindowTitle(self._title)
        
    @property
    def defaultGradient(self) -> typing.Optional[QtGui.QGradient]:
        return self._defaultGradient
    
    @defaultGradient.setter
    def defaultGradient(self, val:typing.Optional[QtGui.QGradient]=None) -> None:
        self._setDefaultGradient(val)
        
    def _setDefaultGradient(self, val:typing.Optional[typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str]]=None) -> None:
        if not isinstance(val, (QtGui.QGradient, QtGui.QGradient.Preset, str)):
            return 
        
        if isinstance(val, str):
            if val not in self._gradients.keys():
                return
            
            self._defaultGradient = self._gradients[val]
            #gradient = self._gradients[val]
            
        else:
            self._defaultGradient = val
            #gradient = val
            
        self._gradients["Default"] = self._defaultGradient
        
        self._gradientIndex = [n for n in self._gradients.keys()].index("Default")
        
    @pyqtSlot()
    def _showDefault(self,) -> None:
        if isinstance(self._defaultGradient, (QtGui.QGradient, QtGui.QGradient.Preset)):
            self._showGradient(self._defaultGradient)
            
        else:
            return
        
    @pyqtSlot()
    def setPreset(self) -> None:
        self._changePresetBy(0)
        
    @pyqtSlot()
    def setPrevPreset(self) -> None:
        self._changePresetBy(-1)
        
    @pyqtSlot()
    def setNextPreset(self) -> None:
        self._changePresetBy(1)
        
    def _updatePresetName(self) -> None:
        currentPreset = [(name, val) for name, val in self._gradients.items()][self._gradientIndex]
        self._presetButton.setText(currentPreset[0])
        self._presetButton.setToolTip(currentPreset[0])
        
    def _changePresetBy(self, indexOffset:int) -> None:
        if len(self._gradients) == 0:
            return
        
        # NOTE: enable circular browsing
        self._gradientIndex += indexOffset
        
        if self._gradientIndex >= len(self._gradients):
            self._gradientIndex = 0
            
        elif self._gradientIndex < -1 * len(self._gradients):
            self._gradientIndex = len(self._gradients) - 1
            
        
        # NOTE: 2021-05-24 12:48:43
        # leave this in for strict browsing between min & max preset
        #self._gradientIndex = max([0, min([self._gradientIndex + indexOffset, len(standardQtGradientPresets)-1])])

        # NOTE: 2021-05-25 13:16:27
        # the presets should apply to all types gradients; choosing a the preset should NOT
        # enforce linear gradient display
        #preset = [(name, val) for name, val in standardQtGradientPresets.items()][self._gradientIndex][1]
        preset = [(name, val) for name, val in self._gradients.items()][self._gradientIndex]
        
        if preset[0] in standardQtGradientPresets.keys():
            gradient = QtGui.QGradient(preset[1])
            
        else:
            gradient = preset[1]
            if not isinstance(gradient, QtGui.QGradient):
                if isinstance(gradient, QtGui.QGradient.Preset):
                    gradient = QtGui.QGradient(gradient)
                else:
                    return
        
        if self._radialButton.isChecked():
            g = g2r(gradient) # points radii taken into account in _showGradient
            
        elif self._conicalButton.isChecked():
            g = g2c(gradient)
            
        else:
            g = g2l(gradient)
        
        # NOTE: 2021-05-27 22:18:59
        # this will also take care of radial gradient points radii when gradient
        # is a generic one or a preset object
        self._showGradient(g) 
        
        self._updatePresetName()
        
        
    def _showGradient(self, 
                      gradient:typing.Union[QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient, QtGui.QGradient, QtGui.QGradient.Preset, str],
                      gradientType:typing.Optional[typing.Union[QtGui.QGradient.Type, str]]=QtGui.QGradient.LinearGradient) -> None:
        """Displays gradient.
        
        If gradient is generic (QtGui.QGradient) then the parameter gradientType
        specifies the concrete gradient type for display purpose.
        
        Parameters:
        ===========
        
        gradient: Either:
            QtGui.QGradient (generic) or one of its subclasses: 
                QLinearGradient, QRadialGradient, QConicalGradient,
                
            QtGui.QGradient.Preset enum value
            
            str: name of a gradient
        
        """
        if not isinstance(gradient, (QtGui.QGradient, QtGui.QGradient.Preset, str)):
            return
        
        if isinstance(gradient, str):
            if gradient in self._gradients.keys():
                gradient = self._gradients[gradient]
            else:
                return
            
        if isinstance(gradient, QtGui.QGradient.Preset):
            gradient = QtGui.QGradient(gradient)
        
        if not isinstance(gradient, (QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient)):
            if isinstance(gradientType, str):
                if "linear" in gradientType.lower():
                    gradientType = QtGui.QGradient.LinearGradient
                elif "radial" in gradientType.lower():
                    gradientType = QtGui.QGradient.RadialGradient
                elif "conical" in gradientType.lower():
                    gradientType = QtGui.QGradient.ConicalGradient
                else:
                    return 
                
            if not isinstance(gradientType, QtGui.QGradient.Type):
                return
            
            if gradientType == QtGui.QGradient.LinearGradient:
                gradient = g2l(gradient)
                
            elif gradientType == QtGui.QGradient.RadialGradient:
                self._renderer.autoCenterRadius=self._useAutoCenterRadius
                self._renderer.relativeCenterRadius=self._useRelativeCenterRadius
                self._renderer.autoFocalRadius=self._useAutoFocalRadius
                self._renderer.relativeFocalRadius=self._useRelativeFocalRadius
                    
                gradient = g2l(gradient, centerRadius = self._centerRadiusSpinBox.value(),
                               focalRadius = self._focalRadiusSpinBox.value())
                
            elif gradientType == QtGui.QGradient.ConicalGradient:
                gradient = g2c(gradient)
                
            else:
                return
            
        stops = gradient.stops()
        logicalStops = self._renderer._getLogicalStops(gradient)
        self._editor.setGradientStops(stops)
        self._renderer.hoverPoints.points = logicalStops

        self._renderer.gradientStops = stops
        
        if isinstance(gradient, QtGui.QLinearGradient):
            self._linearButton.setChecked(True)
            self._renderer.gradientBrushType = QtCore.Qt.LinearGradientPattern
            
        elif isinstance(gradient, QtGui.QRadialGradient):
            self._radialButton.setChecked(True)
            self._renderer.gradientBrushType = QtCore.Qt.RadialGradientPattern
            
        elif isinstance(gradient, QtGui.QConicalGradient):
            self._conicalButton.setChecked(True)
            self._renderer.gradientBrushType = QtCore.Qt.ConicalGradientPattern
            
        if gradient.spread() == QtGui.QGradient.RepeatSpread:
            self._repeatSpreadButton.setChecked(True)
            self._renderer.spread = QtGui.QGradient.RepeatSpread
            
        elif gradient.spread() == QtGui.QGradient.ReflectSpread:
            self._reflectSpreadButton.setChecked(True)
            self._renderer.spread = QtGui.QGradient.ReflectSpread
            
        else:
            self._padSpreadButton.setChecked(True)
            self._renderer.spread = QtGui.QGradient.PadSpread
            
        self._renderer.update()
            
    @pyqtSlot(object)
    def setGradient(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient]) -> None:
        """Qt slot for setting a custom gradient; 
        Sets a new value to the 'gradient' property
        """
        if isinstance(val, (QtGui.QGradient, QtGui.QGradient.Preset, str,)):
            self.gradient = val

        elif isinstance(val, ColorGradient):
            self.gradient = val()
        
        
    @pyqtSlot(object)
    def addGradient(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset]) -> None:
        """Qt slot for adding a custom gradient
        """
        if not isinstance(val, (QtGui.QGradient, QtGui.QGradient.Preset)):
            return
        
        customGradientNames = [n for n in self._gradients.keys() if n.lower().startswith("custom")]
        
        name = "Custom %d" % len(customGradientNames)
        
        self._gradients[name] = val
        
        self._gradientIndex = [n for n in self._gradients.keys()].index(name)
        
        self._updatePresetName()
        
        self.gradient=val
        
    def renameCurrentGradient(self, name:str) -> None:
        if len(name.strip()) == 0:
            return
        
        names = [n for n in self._gradients.keys() if n.startswith(name)]
        if len(names):
            name ="%s %d" % (name, len(names))
            
        currentName = [n for n in self._gradients.keys()][self._gradientIndex]
        
        gradient = self._gradients.pop(currentName, None)
        
        self._gradients[name] = gradient
        
        self._updatePresetName
        
    def removeCurrentGradient(self):
        name = [n for n in self._gradients.keys()][self._gradientIndex]
        
        self._gradients.pop(name, None)
        
        self._changePresetBy(0)
            
    @property
    def normalizedGradient(self) -> QtGui.QGradient:
        """The currently displayed gradient normalized to the renderer's size
        """
        #return normalizeGradient(self.gradient, self._renderer.sizeHint())
        return normalizeGradient(self.gradient, self._renderer.rect())
        
    @property
    def gradient(self) -> QtGui.QGradient:
        """Accessor to the currently displayed gradient (a QGradient).
        NOTE: This is dynamically generated by the renderer.
        The setter for this method uses the QGradient object passsed as argument
        to instruct the rendering of a new gradient which can be accesses by this
        property.
        
        Hence, setting this property to a gradient will NOT store a reference to
        the gradient object argument, but will generate a new one.
        
        Furthermore, the gradient is not processed in any particular way: its
        coordinates, coordinate mode and spread are left unchanged 
        """
        return self._renderer.gradient
    
    def scaledGradient(self, rect):
        return scaleGradient(self.normalizedGradient, rect)
    
    @gradient.setter
    def gradient(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str]) -> None:
        if not isinstance(val, (QtGui.QGradient, QtGui.QGradient.Preset, str)):
            return
        self._showGradient(val)
            
    @pyqtSlot()
    def setAutoCenterRadius(self)-> None:
        self._centerRadiusSpinBox.setEnabled(False)
        self._renderer.setAutoCenterRadius()
        self._useAutoCenterRadius = True
    
    @pyqtSlot()
    def setRelativeCenterRadius(self) -> None:
        self._centerRadiusSpinBox.setEnabled(True)
        val = self._centerRadiusSpinBox.value()
        self._centerRadiusSpinBox.setMinimum(0.)
        self._centerRadiusSpinBox.setMaximum(1.)
        if self._useAutoCenterRadius:
            if isinstance(self.gradient, QtGui.QRadialGradient):
                val = self.gradient.centerRadius() 
                val /= min([self._renderer.width(), self._renderer.height()])
                self._centerRadiusSpinBox.setValue(val)
        elif not self._useRelativeCenterRadius:
            if val < 0. or val > 1.:
                val /= min([self._renderer.width(), self._renderer.height()])
                self._centerRadiusSpinBox.setValue(val)
                
        self._useRelativeCenterRadius = True
        self._useAutoCenterRadius = False
        self._renderer.setRelativeCenterRadius()
    
    @pyqtSlot()
    def setAbsoluteCenterRadius(self) -> None:
        self._centerRadiusSpinBox.setEnabled(True)
        val = self._centerRadiusSpinBox.value()
        self._centerRadiusSpinBox.setMinimum(0.)
        self._centerRadiusSpinBox.setMaximum(min([self._renderer.width(), self._renderer.height()]))
        if self._useAutoCenterRadius:
            if isinstance(self.gradient, QtGui.QRadialGradient):
                val = self.gradient.centerRadius()
                self._centerRadiusSpinBox.setValue(val)
            
        elif self._useRelativeCenterRadius:
            if val < 1.:
                if val < 0.:
                    val = 0
                else:
                    val *= min([self._renderer.width(), self._renderer.height()])
                self._centerRadiusSpinBox.setValue(val)
        self._useRelativeCenterRadius = False
        self._useAutoCenterRadius = False
        self._renderer.setAbsoluteCenterRadius()
    
    @pyqtSlot()
    def setAutoFocalRadius(self) -> None:
        self._focalRadiusSpinBox.setEnabled(False)
        self._renderer.setAutoFocalRadius()
        self._useAutoFocalRadius = True
    
    @pyqtSlot()
    def setRelativeFocalRadius(self) -> None:
        self._focalRadiusSpinBox.setEnabled(True)
        val = self._focalRadiusSpinBox.value()
        self._focalRadiusSpinBox.setMinimum(0.)
        self._focalRadiusSpinBox.setMaximum(1.)
        if self._useAutoFocalRadius:
            if isinstance(self.gradient, QtGui.QRadialGradient):
                val = self.gradient.focalRadius() 
                val /= min([self._renderer.width(), self._renderer.height()])
                self._focalRadiusSpinBox.setValue(val)
        elif not self._useRelativeFocalRadius:
            if val < 0. or val > 1.:
                val /= min([self._renderer.width(), self._renderer.height()])
                self._focalRadiusSpinBox.setValue(val)
        self._useRelativeFocalRadius = True
        self._useAutoFocalRadius = False
        self._renderer.setRelativeFocalRadius()
    
    @pyqtSlot()
    def setAbsoluteFocalRadius(self) -> None:
        self._focalRadiusSpinBox.setEnabled(True)
        val = self._focalRadiusSpinBox.value()
        self._focalRadiusSpinBox.setMinimum(0.)
        self._focalRadiusSpinBox.setMaximum(min([self._renderer.width(), self._renderer.height()]))
        if self._useAutoFocalRadius:
            if isinstance(self.gradient, QtGui.QRadialGradient):
                val = self.gradient.focalRadius()
                self._focalRadiusSpinBox.setValue(val)
        elif self._useRelativeFocalRadius:
            if val < 1.:
                if val < 0.:
                    val = 0
                else:
                    val *= min([self._renderer.width(), self._renderer.height()])
                self._focalRadiusSpinBox.setValue(val)
        
        self._useRelativeFocalRadius = False
        self._useAutoFocalRadius = False
        self._renderer.setAbsoluteFocalRadius()
        
    @pyqtSlot(float)
    def setCenterRadius(self, val:float) -> None:
        if not self._autoCenterRadiusButton.isChecked():
            self._renderer.setCenterRadius(val)
        
    @pyqtSlot(float)
    def setFocalRadius(self, val:float) -> None:
        if not self._autoFocalRadiusButton.isChecked():
            self._renderer.setFocalRadius(val)
            
class GradientDialog(QtWidgets.QDialog):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None,
                 title:str="Select/Edit Gradient"):
        super().__init__(parent=parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.gw = GradientWidget()
        self.gw.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.layout.addWidget(self.gw)
        self.insertButtons()
        if not isinstance(title, str) or len(title.strip()) == 0:
            title = "Select/Edit Gradient"
            
        self.setWindowTitle(title)
        
    def insertButtons(self):
        self.buttons = QtWidgets.QFrame(self)
        self.buttons.OK = QtWidgets.QPushButton("OK", self.buttons)
        self.buttons.Cancel = QtWidgets.QPushButton("Cancel", self.buttons)
        self.buttons.OK.setDefault(1)
        self.buttons.Cancel.clicked.connect(self.reject)
        self.buttons.OK.clicked.connect(self.accept)
        
        self.buttons.layout = QtWidgets.QHBoxLayout(self.buttons)
        self.buttons.layout.addStretch(5)
        self.buttons.layout.addWidget(self.buttons.OK)
        self.buttons.layout.addWidget(self.buttons.Cancel)
        self.layout.addWidget(self.buttons)
        
    @property
    def colorGradient(self) -> ColorGradient:
        return colorGradient(self.gradient)
        
        
            
def set_shade_points(points:typing.Union[QtGui.QPolygonF, list], shade:ShadeWidget) -> None:
    shade.hoverPoints.points = QtGui.QPolygonF(points)
    shade.hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
    shade.hoverPoints.setPointLock(points.size() - 1, HoverPoints.LockType.LockToRight)
    shade.update()
