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

from .painting_shared import (HoverPoints, x_less_than, y_less_than,
                              qtGlobalColors, standardPalette, standardPaletteDict, 
                              svgPalette, getPalette, paletteQColors, paletteQColor, 
                              standardQColor, svgQColor, qtGlobalColors, mplColors,
                              transparent_painting_bg, make_checkers,
                              comboDelegateBrush,
                              standardQtGradientPresets,
                              standardQtGradientSpreads,
                              standardQtGradientTypes,)

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
    
        #pts = QtGui.QPolygonF(self._hoverPoints.points)
        #for pt in pts:
            #print("ShadeWidget.colorAt x %s:" % x, pt.x(), pt.y())
            
        #for i in range(1, pts.size()):
            ##print("ShadeWidget.colorAt x %s: point at %d, %s, at %d, %s" % (x, i-1, pts.at(i-1).x(), i, pts.at(i).x()))
            #if pts.at(i-1).x() <= x and pts.at(i).x() >= x:
                #l = QtCore.QLineF(pts.at(i-1), pts.at(i))
                #if l.dx() > 0:
                    #l.setLength(l.length() * ((x - l.x1()) / l.dx()))
                    #return self._shade.pixel(round(min([l.x2(), float(self._shade.width()  - 1)])),
                                            #round(min([l.y2(), float(self._shade.height() - 1)])))
                #return 0
        #return 0
    
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
                 focalRadius:typing.Optional[float]=None) -> None:
        super().__init__(parent=parent)
        
        # NOTE: 2021-05-23 22:18:35 ArthurFrame FIXME/TODO factor out
        # NOTE: NOT using OpenGL
        self._prefer_image = False
        #### BEGIN
        # related to on-ascreen help/description - not needed here
        #self._document = None
        #self._show_doc = False
        # FIXME/TODO 2021-05-23 22:23:16 use make_checkers instead
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
        self._hoverPoints.pointSize = QtCore.QSize(20,20)
        self._hoverPoints.connectionType = HoverPoints.ConnectionType.NoConnection
        self._hoverPoints.editable = False
        
        points = [QtCore.QPointF(100, 100), QtCore.QPointF(200,200)]
        self._hoverPoints.points = points
        
        self._stops = list()
        
        self._spread = QtGui.QGradient.PadSpread
        self._gradientType = QtCore.Qt.LinearGradientPattern # this is a Qt.BrushStyle enum value
        self._gradient = None # NOTE: 2021-05-24 13:15:41 Cezar Tigaret
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
        
    @pyqtSlot(float)
    def setFocalRadius(self, val:float) -> None:
        self.focalRadius = val
        self.update()
        
    @pyqtSlot(float)
    def setCenterRadius(self, val:float) -> None:
        self.centerRadius = val
        self.update()

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
    
    def paintEvent(self, e:QtGui.QPaintEvent) -> None:
        # NOTE: 2021-05-24 08:24:10 ArthurWidget
        static_image = QtGui.QImage()
        painter = QtGui.QPainter()
        
        if self.preferImage:
            if static_image.isNull() or static_image.size() != self.size():
                static_image = QtGui.Qimage(self.size(), QtGui.QImage.Format_RGB32)
                
            painter.begin(static_image)
            
            o = 10
            # NOTE: 2021-05-24 08:57:00 TODO use make_checkers
            bg = self.palette().brush(QtGui.QPalette.Window)
            painter.fillRect(0,0, o, o, bg)
            painter.fillrect(self.width() - o, 0, o, o, bg)
            painter.fillRect(0, self.height() - o, o, o, bg)
            painter.fillRect(self.width() -o, self.height() - o, o, o, bg)
            
        else:
            painter.begin(self)
            
        painter.setClipRect(e.rect())
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        #clipPath = QtGui.QPainterPath()
        #r = self.rect() # QtCore.QRect
        #left = r.x() +1
        #top = r.y() + 1
        #right = r.right()
        #bottom = r.bottom()
        #radius2 = 8 *2
        
        #clipPath.moveTo(right - radius2, top)
        #clipPath.arcTo(right - radius2, top,                radius2, radius2,  90, -90)
        #clipPath.arcTo(right - radius2, bottom - radius2,   radius2, radius2,  90, -90)
        #clipPath.arcTo(left,            bottom - radius2,   radius2, radius2, 270, -90)
        #clipPath.arcTo(left,            top,                radius2, radius2, 180, -90)
        
        #clipPath.closeSubpath()
        painter.save()
        #painter.setClipPath(clipPath, QtCore.Qt.IntersectClip)
        
        painter.drawTiledPixmap(self.rect(), self._tile)
        
        self.paint(painter)
        
        painter.restore()
        
        #level = 180
        #painter.setPen(QtGui.QPen(QtGui.QColor(level, level, level), 2))
        #painter.setBrush(QtCore.Qt.NoBrush)
        #painter.drawPath(clipPath)
        
        if self.preferImage:
            painter.end()
            painter.begin(self)
            painter.drawImage(e.rect(), static_image, e.rect())
            #painter.end()
        
    def resizeEvent(self, e:QtGui.QResizeEvent) -> None:
        # NOTE: 2021-05-24 10:21:13 ArthurWidget
        # modified in ArthurWidget for open gl case - not needed here?
        #self._centerRadius = min([self.width(), self.height()]) / 3.0
        super().resizeEvent(e)
        
    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self._def_width, self._def_height) # contemplate smaller sizes
        #return QtCore.QSize(400,400) # contemplate smaller sizes
    
    @property
    def preferImage(self) -> bool:
        # NOTE: 2021-05-24 08:26:56 ArthurWidget
        return self._prefer_image
    
    @preferImage.setter
    def preferImage(self, val:bool) -> None:
        # NOTE: 2021-05-24 08:26:56 ArthurWidget
        self._prefer_image = val
        self.update()
        
    @property
    def hoverPoints(self) -> HoverPoints:
        return self._hoverPoints
    
    @pyqtSlot()
    def setPadSpread(self) -> None:
        self._spread = QtGui.QGradient.PadSpread
        self.update()
        
    @pyqtSlot()
    def setRepeatSpread(self) -> None:
        self._spread = QtGui.QGradient.RepeatSpread
        self.update()
        
    @pyqtSlot()
    def setReflectSpread(self) -> None:
        self._spread = QtGui.QGradient.ReflectSpread
        self.update()
        
    @pyqtSlot()
    def setLinearGradient(self) -> None:
        self._gradientType = QtCore.Qt.LinearGradientPattern
        self.update()
        
    @pyqtSlot()
    def setRadialGradient(self) -> None:
        self._gradientType = QtCore.Qt.RadialGradientPattern
        self.update()
        
    @pyqtSlot()
    def setConicalGradient(self) -> None:
        self._gradientType = QtCore.Qt.ConicalGradientPattern
        self.update()
        
    @pyqtSlot(object)
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        self._stops[:] = stops
        self.update()
        
    def paint(self, p:QtGui.QPainter) -> None:
        pts = self._hoverPoints.points
        #pts = QtGui.QPolygonF(self._hoverPoints.points)
        
        #g = QtGui.QGradient()
        self._gradient = QtGui.QGradient()
        
        if self._gradientType == QtCore.Qt.LinearGradientPattern:
            #g = QtGui.QLinearGradient(pts[0], pts[1])
            self._gradient = QtGui.QLinearGradient(pts[0], pts[1])
            
        elif self._gradientType == QtCore.Qt.RadialGradientPattern:
            #g = QtGui.QRadialGradient(pts[0], min([self.width(), self.height()]) / 3.0, pts[1])
            #QRadialGradient(const QPointF &center, qreal centerRadius, const QPointF &focalPoint, qreal focalRadius)
            # center is the first hover point (hover point [0])
            # center radiius is 1/3 of minimal side (width or height)
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
            
            self._gradient = QtGui.QRadialGradient(pts[0], centerRadius, pts[1], focalRadius)
            
        else: # conical gradient
            l = QtCore.QLineF(pts[0], pts[1])
            
            # NOTE: 2021-05-24 14:18:59
            # line (0,0,1,0) = horizontal line
            # line.angleTo(l) = angle from horizontal line to line 'l'
            angle = QtCore.QLineF(0,0,1,0).angleTo(l)
            #g = QtGui.QConicalGradient(pts[0], angle)
            #QConicalGradient(const QPointF &center, qreal angle)
            self._gradient = QtGui.QConicalGradient(pts[0], angle)
            
        for stop in self._stops:
            #g.setColorAt(stop[0], QtGui.QColor(stop[1]))
            self._gradient.setColorAt(stop[0], QtGui.QColor(stop[1]))
            
        #g.setSpread(self._spread)
        self._gradient.setSpread(self._spread)
        
        #p.setBrush(g)
        p.setBrush(self._gradient)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(self.rect())
        
class GradientWidget(QtWidgets.QWidget):
    def __init__(self, gradient:typing.Optional[QtGui.QGradient]=None,
                 parent:typing.Optional[QtWidgets.QWidget] = None, 
                 title:typing.Optional[str]="Scipyen Gradient Editor") -> None:
        super().__init__(parent=parent)
        
        self._presetIndex = 0
        self._defaultGradient = None
        self._setDefaultGradient(gradient)
        

        self._renderer = GradientRenderer(self)
        
        self.mainContentWidget = QtWidgets.QWidget()
        self.mainGroup = QtWidgets.QGroupBox(self.mainContentWidget)
        self.mainGroup.setTitle("Gradients")
        
        self.editorGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.editorGroup.setTitle("Color Editor")
        
        self._editor = GradientEditor(self.editorGroup)
        
        self.typeGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.typeGroup.setTitle("Gradient Type")
        
        self._linearButton = QtWidgets.QRadioButton("Linear", self.typeGroup)
        self._radialButton = QtWidgets.QRadioButton("Radial", self.typeGroup)
        self._conicalButton = QtWidgets.QRadioButton("Conical", self.typeGroup)
        
        self.radialParamsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.radialParamsGroup.setTitle("Radial Gradients")
        
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
        
        self.radialParamsLayout = QtWidgets.QVBoxLayout(self.radialParamsGroup)
        self.radialParamsLayout.addWidget(self.gradientCenterRadiusGroup)
        self.radialParamsLayout.addWidget(self.gradientFocalRadiusGroup)
        
        self.spreadGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.spreadGroup.setTitle("Spread Method")
        self._padSpreadButton = QtWidgets.QRadioButton("Pad", self.spreadGroup)
        self._reflectSpreadButton = QtWidgets.QRadioButton("Reflect", self.spreadGroup)
        self._repeatSpreadButton = QtWidgets.QRadioButton("Repeat", self.spreadGroup)
        
        self.presetsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.presetsGroup.setTitle("Presets")
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
        
        self._updatePresetName()
        
        #self.mainGroup.setFixedWidth(200)
        
        self.mainGroupLayout = QtWidgets.QVBoxLayout(self.mainGroup)
        self.mainGroupLayout.addWidget(self.editorGroup)
        self.mainGroupLayout.addWidget(self.typeGroup)
        self.mainGroupLayout.addWidget(self.radialParamsGroup)
        self.mainGroupLayout.addWidget(self.spreadGroup)
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
        #self.mainScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Fixed, 
                                        #QtWidgets.QSizePolicy.Preferred)

        self.vSplitter = QtWidgets.QSplitter(self)
        self.vSplitter.addWidget(self._renderer)
        self.vSplitter.addWidget(self.mainScrollArea)
        self.mainLayout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.addWidget(self.vSplitter)
        #self.mainLayout.addWidget(self._renderer)
        #self.mainLayout.addWidget(self.mainScrollArea)
        
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
        
        if isinstance(title, str) and len(title.strip()):
            self.setWindowTitle(title)
            
        self._autoFocalRadiusButton.animateClick()
        self._autoCenterRadiusButton.animateClick()
            
        QtCore.QTimer.singleShot(50, self._showDefault)
        
    @property
    def defaultGradient(self) -> typing.Optional[QtGui.QGradient]:
        return self._defaultGradient
    
    @defaultGradient.setter
    def defaultGradient(self, val:typing.Optional[QtGui.QGradient]=None) -> None:
        self._setDefaultGradient(val)
        
    def _setDefaultGradient(self, val:typing.Optional[QtGui.QGradient]=None) -> None:
        # FIXME: 2021-05-24 16:23:17 TODO
        if isinstance(val, QtGui.QLinearGradient):
            self._defaultGradient = val
            #self._setLinearGradient(self._defaultGradient)
            #self._linearButton.animateClick()
            #self._padSpreadButton.animateClick()
            
        #elif isinstance(val, QtGui.QRadialGradient):
        #elif isinstance(val, QtGui.QConicalGradient):
        elif isinstance(val, QtGui.QGradient):
            self._defaultGradient = sip.cast(val, QtGui.QLinearGradient)
            
        if self.isVisible():
            self._showDefault()
            
        #else:
            #self._changePresetBy(0)
            
        
        
    @pyqtSlot()
    def _showDefault(self,) -> None:
        if not isinstance(self._defaultGradient, QtGui.QGradient):
            self._changePresetBy(0)
        elif not isinstance(self._defaultGradient, QtGui.QLinearGradient):
            self._setLinearGradient(gradient)
            
        self._linearButton.animateClick()
        self._padSpreadButton.animateClick()
            
        self.update()
        
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
        currentPreset = [(name, val) for name, val in standardQtGradientPresets.items()][self._presetIndex]
        self._presetButton.setText(currentPreset[0])
        self._presetButton.setToolTip(currentPreset[0])
        
    def _changePresetBy(self, indexOffset:int) -> None:
        # NOTE: enable circular browsing
        self._presetIndex += indexOffset
        
        # NOTE: 2021-05-24 12:48:43
        # leave this in for strict browing between min & max preset
        #self._presetIndex = max([0, min([self._presetIndex + indexOffset, len(standardQtGradientPresets)-1])])
        
        preset = [(name, val) for name, val in standardQtGradientPresets.items()][self._presetIndex][1]
        
        gradient = QtGui.QGradient(preset)
        
        if gradient.type() != QtGui.QGradient.LinearGradient: # NOTE 2021-05-23 09:34:29 why?
            return
        
        linearGradient = sip.cast(gradient, QtGui.QLinearGradient)
        
        self._setLinearGradient(linearGradient)
        
        #objectStopsLine = QtCore.QLineF(linearGradient.start(), linearGradient.finalStop())
        
        #scaleX = 1. if np.isclose(objectStopsLine.dx(), 0.) else 0.8 * self._renderer.width()  / abs(objectStopsLine.dx())
        #scaleY = 1. if np.isclose(objectStopsLine.dy(), 0.) else 0.8 * self._renderer.height() / abs(objectStopsLine.dy())
        
        #logicalStopsLine = QtGui.QTransform.fromScale(scaleX, scaleY).map(objectStopsLine)
        #logicalStopsLine.translate(self._renderer.rect().center() - logicalStopsLine.center())
        #logicalStops = QtGui.QPolygonF((logicalStopsLine.p1(), logicalStopsLine.p2()))
        
        self._linearButton.animateClick()
        self._padSpreadButton.animateClick()
        #self._editor.setGradientStops(gradient.stops())
        #self._renderer.hoverPoints.points = logicalStops
        #self._renderer.setGradientStops(gradient.stops())
        
        self._updatePresetName()
        
    def _setLinearGradient(self, gradient) -> None:
        objectStopsLine = QtCore.QLineF(gradient.start(), gradient.finalStop())
        
        scaleX = 1. if np.isclose(objectStopsLine.dx(), 0.) else 0.8 * self._renderer.width()  / abs(objectStopsLine.dx())
        scaleY = 1. if np.isclose(objectStopsLine.dy(), 0.) else 0.8 * self._renderer.height() / abs(objectStopsLine.dy())
        
        logicalStopsLine = QtGui.QTransform.fromScale(scaleX, scaleY).map(objectStopsLine)
        logicalStopsLine.translate(self._renderer.rect().center() - logicalStopsLine.center())
        logicalStops = QtGui.QPolygonF((logicalStopsLine.p1(), logicalStopsLine.p2()))
        
        self._editor.setGradientStops(gradient.stops())
        self._renderer.hoverPoints.points = logicalStops
        self._renderer.setGradientStops(gradient.stops())
        
    def _setGradient(self, gradient:QtGui.QGradient) -> None:
        if isinstance(gradient, QtGui.QLinearGradient):
            objectStopsLine = QtCore.QLineF(gradient.start(), gradient.finalStop())
            
            scaleX = 1. if np.isclose(objectStopsLine.dx(), 0.) else 0.8 * self._renderer.width()  / abs(objectStopsLine.dx())
            scaleY = 1. if np.isclose(objectStopsLine.dy(), 0.) else 0.8 * self._renderer.height() / abs(objectStopsLine.dy())
            
            logicalStopsLine = QtGui.QTransform.fromScale(scaleX, scaleY).map(objectStopsLine)
            logicalStopsLine.translate(self._renderer.rect().center() - logicalStopsLine.center())
            logicalStops = QtGui.QPolygonF((logicalStopsLine.p1(), logicalStopsLine.p2()))
            
            self._editor.setGradientStops(gradient.stops())
            self._renderer.hoverPoints.points = logicalStops
            self._renderer.setGradientStops(gradient.stops())
            
        elif isinstance(gradient, QtGui.QRadialGradient):
            
            pass
        
        elif isinstance(gradient, QtGui.QConicalGradient):
            pass
    
        elif isinstance(gradient, QtGui.QGradient):
            objectStopsLine = QtCore.QLineF(gradient.stops()[0], gradient.stops()[-1])
            
            scaleX = 1. if np.isclose(objectStopsLine.dx(), 0.) else 0.8 * self._renderer.width()  / abs(objectStopsLine.dx())
            scaleY = 1. if np.isclose(objectStopsLine.dy(), 0.) else 0.8 * self._renderer.height() / abs(objectStopsLine.dy())
            
            logicalStopsLine = QtGui.QTransform.fromScale(scaleX, scaleY).map(objectStopsLine)
            logicalStopsLine.translate(self._renderer.rect().center() - logicalStopsLine.center())
            logicalStops = QtGui.QPolygonF((logicalStopsLine.p1(), logicalStopsLine.p2()))
            
            self._editor.setGradientStops(gradient.stops())
            self._renderer.hoverPoints.points = logicalStops
            self._renderer.setGradientStops(gradient.stops())
            
            
        else:
            return
            
        
    @pyqtSlot()
    def setAutoCenterRadius(self)-> None:
        self._centerRadiusSpinBox.setEnabled(False)
        #self._centerRadiusSpinBox.valueChanged[float].disconnect()
        self._renderer.setAutoCenterRadius()
    
    @pyqtSlot()
    def setRelativeCenterRadius(self) -> None:
        #self._centerRadiusSpinBox.valueChanged[float].disconnect()
        self._centerRadiusSpinBox.setEnabled(True)
        val = self._centerRadiusSpinBox.value()
        if val < 0. or val > 1.:
            val /= min([self._renderer.width(), self._renderer.height()])
            self._centerRadiusSpinBox.setValue(val)
        self._centerRadiusSpinBox.setMinimum(0.)
        self._centerRadiusSpinBox.setMaximum(1.)
        self._renderer.setRelativeCenterRadius()
        #self._centerRadiusSpinBox.valueChanged[float].connect(self._renderer.setCenterRadius)
    
    @pyqtSlot()
    def setAbsoluteCenterRadius(self) -> None:
        #self._centerRadiusSpinBox.valueChanged[float].disconnect()
        self._centerRadiusSpinBox.setEnabled(True)
        val = self._centerRadiusSpinBox.value()
        if val < 1.:
            if val < 0.:
                val = 0
            else:
                val *= min([self._renderer.width(), self._renderer.height()])
            self._centerRadiusSpinBox.setValue(val)
        self._centerRadiusSpinBox.setMinimum(0.)
        self._centerRadiusSpinBox.setMaximum(min([self._renderer.width(), self._renderer.height()]))
        self._renderer.setAbsoluteCenterRadius()
        #self._centerRadiusSpinBox.valueChanged[float].connect(self._renderer.setCenterRadius)
    
    @pyqtSlot()
    def setAutoFocalRadius(self) -> None:
        self._focalRadiusSpinBox.setEnabled(False)
        #self._focalRadiusSpinBox.valueChanged[float].disconnect()
        self._renderer.setAutoFocalRadius()
    
    @pyqtSlot()
    def setRelativeFocalRadius(self) -> None:
        #self._focalRadiusSpinBox.valueChanged[float].disconnect()
        self._focalRadiusSpinBox.setEnabled(True)
        val = self._focalRadiusSpinBox.value()
        if val < 0. or val > 1.:
            val /= min([self._renderer.width(), self._renderer.height()])
            self._focalRadiusSpinBox.setValue(val)
        self._focalRadiusSpinBox.setMinimum(0.)
        self._focalRadiusSpinBox.setMaximum(1.)
        self._renderer.setRelativeFocalRadius()
        #self._focalRadiusSpinBox.valueChanged[float].connect(self._renderer.setFocalRadius)
    
    @pyqtSlot()
    def setAbsoluteFocalRadius(self) -> None:
        #self._focalRadiusSpinBox.valueChanged[float].disconnect()
        self._focalRadiusSpinBox.setEnabled(True)
        val = self._focalRadiusSpinBox.value()
        if val < 1.:
            if val < 0.:
                val = 0
            else:
                val *= min([self._renderer.width(), self._renderer.height()])
            self._focalRadiusSpinBox.setValue(val)
        self._focalRadiusSpinBox.setMinimum(0.)
        self._focalRadiusSpinBox.setMaximum(min([self._renderer.width(), self._renderer.height()]))
        self._renderer.setAbsoluteFocalRadius()
        #self._focalRadiusSpinBox.valueChanged[float].connect(self._renderer.setFocalRadius)
        
    @pyqtSlot(float)
    def setCenterRadius(self, val:float) -> None:
        if not self._autoCenterRadiusButton.isChecked():
            self._renderer.setCenterRadius(val)
        
    @pyqtSlot(float)
    def setFocalRadius(self, val:float) -> None:
        if not self._autoFocalRadiusButton.isChecked():
            self._renderer.setFocalRadius(val)
        
        
def set_shade_points(points:typing.Union[QtGui.QPolygonF, list], shade:ShadeWidget) -> None:
    shade.hoverPoints.points = QtGui.QPolygonF(points)
    shade.hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
    shade.hoverPoints.setPointLock(points.size() - 1, HoverPoints.LockType.LockToRight)
    shade.update()
