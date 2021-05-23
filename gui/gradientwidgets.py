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
        
    def colorAt(self, x:int) -> int:
        self._generateShade()
        
        pts = self._hoverPoints.points
        for k in range(1, len(pts):
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
        
        print("GradientEditor.__init__ _redShade")
        self._redShade = ShadeWidget(ShadeWidget.ShadeType.RedShade, self)
        print("GradientEditor.__init__ _greenShade")
        self._greenShade = ShadeWidget(ShadeWidget.ShadeType.GreenShade, self)
        print("GradientEditor.__init__ _blueShade")
        self._blueShade = ShadeWidget(ShadeWidget.ShadeType.BlueShade, self)
        print("GradientEditor.__init__ _alphaShade")
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
        
        for i, point in enumerate(sortedPoints):
            k = int(point.x())
            #k = int(sortedPoints.at(i).x())
            if i + 1 < len(sortedPoints) and k == int(sortedPoints[i+1].x()):
                continue
            
            color = QtGui.QColor((0x00ff0000 & self._redShade.colorAt(k)) >> 16,
                                 (0x0000ff00 & self._greenShade.colorAt(k)) >> 8,
                                 (0x000000ff & self._blueShade.colorAt(k)),
                                 (0xff000000 & self._alphaShade.colorAt(k)) >> 24)
            
            if k / w > 1:
                return
            
        stops.append((k/w, color))
        
        self._alphaShade.setGradientStops(stops)
        
        self.gradientStopsChanged.emit(stops)
        
class GradientRenderer(QtWidgets.QWidget):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget]=None) -> None:
        super().__init__(parent=parent)
        
        # NOTE: 2021-05-23 22:18:35 ArthurFrame FIXME/TODO factor out
        # NOTE: NOT using OpenGL
        #### BEGIN
        self._prefer_image = False
        self._document = None
        self._show_doc = False
        # FIXME/TODO 2021-05-23 22:23:16 use make_checkers instead
        self._tile = QtGui.QPixmap(128,128)
        self._tile.fill(QtCore.Qt.white)
        pt = QtGui.QPainter(self._tile)
        color = QtGui.QColor(30,230,230)
        pt.fillRect(0,0,64,64, color)
        pt.fillRect(64,64,64,64, color)
        pt.end()
        #### END
        
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape)
        self._hoverPoints.pointSize = QtCore.QSize(20,20)
        self._hoverPoints.connectionType = HoverPoints.ConnectionType.NoConnection
        self._hoverPoints.editable = False
        
        points = [QtCore.QPointF(100, 100), QtCore.QPointF(200,200)]
        self._hoverPoints.points = points
        
        self._stops = list()
        
        self._spread = QtGui.QGradient.PadSpread
        self._gradientType = QtCore.Qt.LinearGradientPattern # this is a Qt.BrushStyle enum value
        
    def paintEvent(self, e:QtGui.QPaintEvent) -> None:
        pass # TODO
    
        
    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(400,400) # contemplate smaller sizes
    
    #def mousePressEvent(self, ev:QtGui.QMouseEvent) -> None:
        #self.setDescriptionEnabled(False)
        
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
        
        g = QtGui.QGradient()
        
        if self._gradientType == QtCore.Qt.LinearGradientPattern:
            g = QtGui.QLinearGradient(pts[0], pts[1])
            #g = QtGui.QLinearGradient(pts.at(0), pts.at(1))
            
        elif self._gradientType == QtCore.Qt.RadialGradientPattern:
            g = QtGui.QRadialGradient(pts[0], min([self.width(), self.height()] / 3.0, pts[1]))
            #g = QtGui.QRadialGradient(pts.at(0), min([self.width(), self.height()] / 3.0, pts.at(1)))
            
        else:
            l = QtCore.QLineF(pts[0], pts[1])
            #l = QtCore.QLineF(pts.at(0), pts.at(1))
            angle = QtCore.QLinef(0,0,1,0).angleTo(l)
            g = QtGui.QConicalGradient(pts[0], angle)
            #g = QtGui.QConicalGradient(pts.at(0), angle)
            
        for stop in self._stops:
            g.setColorAt(stop[0], QtGui.QColor(stop[1]))
            
        g.setSpread(self._spread)
        
        p.setBrush(g)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(self.rect())
        
class GradientWidget(QtWidgets.QWidget):
    def __init__(self, gradient:typing.Optional[QtGui.QGradient]=None,
                 parent:typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)
        
        self._presetIndex = 0
        self._defaultGradient = gradient

        self._renderer = GradientRenderer(self)
        
        self.mainContentWidget = QtWidgets.QWidget()
        self.mainGroup = QtWidgets.QGroupBox(self.mainContentWidget)
        self.mainGroup.setTitle("Gradients")
        
        self.editorGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.editorGroup.setTitle("Color Editor")
        
        self._editor = GradientEditor(self.editorGroup)
        
        self.typeGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.typeGroup.setTitle("Gradient Type")
        
        self._linearButton = QtWidgets.QRadioButton("Linear Gradient", self.typeGroup)
        self._radialButton = QtWidgets.QRadioButton("Radial Gradient", self.typeGroup)
        self._conicalButton = QtWidgets.QRadioButton("Conical Gradient", self.typeGroup)
        
        self.spreadGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.spreadGroup.setTitle("Spread Method")
        self._padSpreadButton = QtWidgets.QRadioButton("Pad Spread", self.spreadGroup)
        self._reflectSpreadButton = QtWidgets.QRadioButton("Reflect Spread", self.spreadGroup)
        self._repeatSpreadButton = QtWidgets.QRadioButton("Repeat Spread", self.spreadGroup)
        
        self.presetsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.presetsGroup.setTitle("Presets")
        self.prevPresetButton = QtWidgets.QPushButton("<", self.presetsGroup)
        self._presetButton = QtWidgets.QPushButton("(unset)", self.presetsGroup)
        self.nextPresetButton = QtWidgets.QPushButton(">", self.presetsGroup)
        
        self._updatePresetName()
        
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
        
        self.mainGroup.setLayout(self.mainGroupLayout)
        
        self.mainContentLayout = QtWidgets.QVBoxLayout()
        self.mainContentLayout.addWidget(self.mainGroup)
        self.mainContentWidget.setLayout(self.mainContentLayout)
        
        self.mainScrollArea = QtWidgets.QScrollArea()
        self.mainScrollArea.setWidget(self.mainContentWidget)
        self.mainScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Fixed, 
                                        QtWidgets.QSizePolicy.Preferred)


        self.mainLayout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.addWidget(self._renderer)
        self.mainLayout.addWidget(self.mainScrollArea)
        
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
        
        QtCore.QTimer.singleShot(50, self._setDefault)
        
    @pyqtSlot()
    def _setDefault(self,) -> None:
        if isinstance(self._defaultGradient, QtGui.QLinearGradient):
            self._setLinearGradient(gradient)
            self._linearButton.animateClick()
            self._padSpreadButton.animateClick()
        else:
            self._changePresetBy(0)
        
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
        
    def _changePresetBy(self, indexOffset:int) -> None:
        self._presetIndex = max([0, min([self._presetIndex + indexOffset, len(standardQtGradientPresets)-1])])
        
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
        
    

def set_shade_points(points:typing.Union[QtGui.QPolygonF, list], shade:ShadeWidget) -> None:
    shade.hoverPoints.points = QtGui.QPolygonF(points)
    shade.hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
    shade.hoverPoints.setPointLock(points.size() - 1, HoverPoints.LockType.LockToRight)
    shade.update()
