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

from core.prog import (safeWrapper, no_sip_autoconversion)

from .scipyen_colormaps import (qtGlobalColors, standardPalette,
                                standardPaletteDict, svgPalette,
                                getPalette, paletteQColors, paletteQColor, 
                                standardQColor, svgQColor,
                                qtGlobalColors, mplColors)

from .colorwidgets import (transparent_painting_bg, make_checkers,
                           comboDelegateBrush)

from .painting_shared import (HoverPoints, x_less_than, y_less_than,)

class ShadeWidget(QtWidgets.QWidget):
    colorsChanged = pyqtSignal(QtGui.QPolygonF, name="colorsChanged")
    
    class ShadeType(IntEnum):
        RedShade = auto()
        GreenShade = auto()
        Blueshade = auto()
        ARGBShade = auto()
        
    def __init__(self, shadeType:ShadeWidget.ShadeType, 
                 parent:typing.Optional[QtWidgets.QWidget]=None) -> None:
        
        super().__init__(parent=parent)
        
        self._shadeType = shadeType
        
        self._alphaGradient = QtGui.QLinearGradient(0, 0, 0, 0)
        
        if self._shadeType == Shadewidget.ShadeType.ARGBShade:
            # create checkers background for Alpha channel display
            pm = make_checkers(QtCore.Qt.lightGray, QtCore.Qt.darkGray, 20)
            pal = QtGui.QPalette()
            pal.setBrush(self.backgroundRole(), QtGui.QBrush(pm))
            self.setAutoFillBackground(True)
            self.setPalette(pal)
            
        else:
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
            
        points = QtGui.QPolygonF([QtCore.QPointF(0, self.sizeHint().height()),
                                  QtCore.QPointF(self.sizeHint().width(), 0)])
        
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape)
        self._hoverPoints.points = points
        self._hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
        self._hoverPoints.setPointLock(1, HoverPoints.LockType.LockToRight)
        self._hoverPoints.sortType = HoverPoints.SortType.XSort
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed) # horizontal, vertical
        
        self._hoverPoints.pointsChanged[QtGui.QPolygonF].connect(self.colorsChanged)
        
    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(150,40)
    
    @property
    def hoverPoints(self) -> HoverPoints:
        return self._hoverPoints
        
    @property
    def points(self) -> QtGui.QPolygonF:
        return self._hoverPoints.points
        
    def colorAt(x:int) -> int:
        self._generateShade()
        
        pts = QtGui.QPolygonF(self._hoverPoints.points)
        for i in range(1, pts.size()):
            if pts.at(i-1).x() <= x and pts.at(i).x() >= x:
                l = QtCore.QLineF(pts.at(i-1), pts.at(i))
                l.setLength(l.length() * ((x - l.x1()) / l.dx()))
                return self._shade.pixel(round(min([l.x2(), float(self._shade.width()  - 1)])),
                                         round(min([l.y2(), float(self._shade.height() - 1)])))
        return 0
    
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        if self._shadeType == ShadeWidget.ShadeType.ARGBShade:
            self._alphaGradient = QtGui.QLinearGradient(0, 0, self.width(), 0)
            
            for stop in stops:
                c = QtGui.QColor(stop[1])
                self._alphaGradient.setColorAt(stop[0], QColor(c.red(), c.green(), c.blue()))
                
            self._shade = QtGui.GImage()
            self._generateShade()
            self.update()
            
    def paintEvent(self, ev:QtGui.QPaintEvent) -> None:
        self._generateShade()
        
        p = QtGui.QPainter(self)
        
        p.drawImage(0,0,self._shade)
        p.setPen(QtGui.QColor(146, 146, 146))
        p.drawRect(0,0, self.width() - 1, self.height() - 1)
        
    def _generateShade(self) -> None:
        if self._shade.isNull() or self.shade.size() != self.size():
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
    
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        pts_red = list() #QtGui.QPolygonF()
        pts_green = list() # QtGui.QPolygonF()
        pts_blue = list() # QtGui.QPolygonF()
        pts_alpha = list() # QtGui.QPolygonF()
        
        h_red = float(self._redShade.height())
        h_green = float(self._greenShade.height())
        h_blue = float(self._blueShade.height())
        h_alpha = float(self._alphaShade.height())
        
        for i in range(len(stops)):
            pos = float(stops[i][0])
            qrgb = QtGui.QColor(stops[i][1]).rgba()
            
            pts_red.append(QtCore.QpointF(pos * self._redShade.width(),
                                          h_red - QtGui.qRed(qrgb) * h_red / 255))
    
            pts_green.append(QtCore.QpointF(pos * self._greenShade.width(),
                                          h_green - QtGui.qGreen(qrgb) * h_green / 255))
    
            pts_blue.append(QtCore.QpointF(pos * self._blueShade.width(),
                                          h_blue - QtGui.qBlue(qrgb) * h_blue / 255))
    
            pts_alpha.append(QtCore.QpointF(pos * self._alphaShade.width(),
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

        sortedPoints = sorted(p for p in points, key = x_less_than)
        
        for i in range(points.size()):
            x = int(points.at(i).x())
            if i + 1 < points.size() and x == int(points.at(i+1).x()):
                continue
            
            color = QtGui.QColor((0x00ff0000 & self._redShade.colorAt(x)) >> 16,
                                 (0x0000ff00 & self._greenShade.colorAt(x)) >> 8,
                                 (0x000000ff & self._blueShade.colorAt(x)),
                                 (0xff000000 & self._alphaShade.colorAt(x)) >> 24)
            
            if x / w > 1:
                return
            
        stops.append((x/w, color))
        
        self._alphaShade.setGradientStops(stops)
        
        self.gradientStopsChanged.emit(stops)
        
class GradientRenderer(QtWidgets.QWidget):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None) -> None:
        super().__init__(parent=parent)
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape)
        self._hoverPoints.pointSize = QtCore.QSize(20,20)
        self._hoverPoints.connectionType = HoverPoints.ConnectionType.NoConnection
        self._hoverPoints.editable = False
        
        points = [QtCore.QPointF(100, 100), QPointF(200,200)]
        self._hoverPoints.points = points
        
        self._stops = list()
        
        self._spread = QtGui.QGradient.PadSpread
        self._gradientType = QtCore.Qt.LinearGradientPattern # this is a Qt.BrushStyle enum value
        
    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400,400) # contemplate smaller sizes
    
    def mousePressEvent(self, ev:QtGui.QMouseEvent) -> None:
        self.setDescriptionEnabled(False)
        
    @property
    def hoverPoints(self) -> HoverPoints:
        return self._hoverPoints
    
    def setPadSpread(self) -> None:
        self._spread = QtGui.QGradient.PadSpread
        self.update()
        
    def setRepeatSpread(self) -> None:
        self._spread = QtGui.QGradient.RepeatSpread
        self.update()
        
    def setReflectSpread(self) -> None:
        self._spread = QtGui.QGradient.ReflectSpread
        self.update()
        
    def setLinearGradient(self) -> None:
        self._gradientType = QtCore.Qt.LinearGradientPattern
        self.update()
        
    def setRadialGradient(self) -> None:
        self._gradientType = QtCore.Qt.RadialGradientPattern
        self.update()
        
    def setConicalGradient(self) -> None:
        self._gradientType = Qtcore.Qt.ConicalGradientPattern
        self.update()
        
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        self._stops[:] = stops
        self.update()
        
    def paint(self, p:QtGui.QPainter) -> None:
        pts = QtGui.QPolygonF(self._hoverPoints.points)
        
        g = QtGui.QGradient()
        
        if self._gradientType == QtCore.Qt.LinearGradientPattern:
            g = QtGui.QLinearGradient(pts.at(0), pts.at(1))
            
        elif self._gradientType == QtCore.Qt..RadialGradientPattern:
            g = QtGui.QRadialGradient(pts.at(0), min([self.width(), self.height()] / 3.0, pts.at(1)))
            
        else:
            l = QtCore.QLineF(pta.at(0), pts.at(1))
            angle = QtCore.QLinef(0,0,1,0).angleTo(l)
            g = QtGui.QConicalGradient(pts.at(0), angle)
            
        for stop in self._stops:
            g.setColorAt(stop[0], QtGui.QColor(stop[1]))
            
        g.setSpread(self._spread)
        
        p.setBrush(g)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(self.rect())
        
    
        
class GradientWidget(QtWidgets.QWidget):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)

    self._renderer = GradientRenderer(self)
    
    self.mainContentWidget = QtWidgets.QWidget()
    self.mainGroup = QtWidgets.QGroupBox(self.mainContentWidget)
    self.mainGroup.setTitle("Gradients")
    
    self.editorGroup = QtWidgets.QGroupBox(self.mainGroup)
    self.editorGroup.setTitle("Color Editor")
    
    self._editor = GradientEditor(self.editorGroup)
    
    typeGroup = QtWidgets.QGroupBox(self.mainGroup)
    self.typeGroup.setTitle("Gradient Type")
    
    self._linearButton = QtWidgets.QRadioButton("Linear Gradient", self.typeGroup)
    self._radialButton = QtWidgets.QRadioButton("Radial Gradient", self.typeGroup)
    self._conicalButton = QtWidgets.QRadioButton("Conical Gradient", self.typeGroup)
    
    self.spreadGroup = QtWidgets.QGroupBox(mainGroup)
    self.spreadGroup.setTitle("Spread Method")
    self._padSpreadButton = QtWidgets.QRadioButton("Pad Spread", self.spreadGroup)
    self._reflectSpreadButton = QtWidgets.QRadioButton("Reflect Spread", self.spreadGroup)
    self._repeatSpreadButton = QtWidgets.QRadioButton("Repeat Spread", self.spreadGroup)
    
    self.presetsGroup = QtWidgets.QGroupBox(mainGroup)
    self.presetsGroup.setTitle("Presets")
    self.prevPresetButton = QtWidgets.QPushButton("<", self.presetsGroup)
    self._presetButton = QtWidgets.QPushButton("(unset)", self.presetsGroup)
    self.nextPresetButton = QtWidgets.QPushButton(">", self.presetsGroup)
    self.updatePresetName()
    
    self.mainGroup.setFixedWidth(200)
    
    self.mainGroupLayout = QtWidgets.QVBoxLayout(self.mainGroup)
    self.mainGroupLayout.addWidget(self.editorGroup)
    self.mainGroupLayout.addWidget(self.typeGroup)
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
    
    # TODO/FIXME to continue

def set_shade_points(points:typing.Union[QtGui.QPolygonF, list], shade:ShadeWidget) -> None:
    shade.hoverPoints.points = QtGui.QPolygonF(points)
    shade.hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
    shade.hoverPoints.setPointLock(points.size() - 1, HoverPoints.LockType.LockToRight)
    shade.update()
