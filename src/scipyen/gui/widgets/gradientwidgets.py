""" see qt examples/widgets/painting/gradients
"""
import array, os, typing, numbers, inspect, traceback
from collections import OrderedDict
import numpy as np
from enum import IntEnum, auto
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty

import sip

from core.prog import (safeWrapper, no_sip_autoconversion)

from core.utilities import (counter_suffix, reverse_dict, reverse_mapping_lookup)

from gui.painting_shared import (HoverPoints, x_less_than, y_less_than,
                              qtGlobalColors, standardPalette, standardPaletteDict, 
                              svgPalette, getPalette, paletteQColor, 
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
                              gradientLine,
                              scaleGradient,
                              rescaleGradient,
                              ColorPalette,
                              ColorGradient, 
                              colorGradient,
                              restrict_point, 
                              printPoints)

from gui import quickdialog as qd

class ShadeWidget(QtWidgets.QWidget):
    colorsChanged   = pyqtSignal(QtGui.QPolygonF, name="colorsChanged")
    pointMovedX     = pyqtSignal(int, float, name="pointMovedX")
    pointInserted   = pyqtSignal(int, QtCore.QPointF, name="pointInserted")
    pointRemoved    = pyqtSignal(int, name="pointRemoved")
    
    class ShadeType(IntEnum):
        RedShade = auto()
        GreenShade = auto()
        BlueShade = auto()
        ARGBShade = auto()
        
    def __init__(self, shadeType:ShadeType, 
                 parent:typing.Optional[QtWidgets.QWidget]=None,
                 size:typing.Union[int, typing.Tuple[int]]=11) -> None:
        
        super().__init__(parent=parent)
        
        if isinstance(size, (tuple, list)) and len(size) == 2 and all([isinstance(v, int) for v in size]):
            self._pointSize = QtCore.QSize(*size)
        elif isinstance(size, int):
            self._pointSize = QtCore.QSize(size, size)
        else:
            self._pointSize = QtCore.QSize(11, 11)

        self._shade = QtGui.QImage()
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
        
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape, size = self._pointSize)
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
    
    @pyqtSlot(int, float)
    def slot_syncPointX(self, index, x):
        if index >= 0 and index < len(self.points):
            self.points[index].setX(x)
            self.update()
            
    @pyqtSlot(int, QtCore.QPointF)
    def slot_pointInserted(self, index, p):
        if index >= 0:
            if index == 0:
                y = self._hoverPoints._points[0].y()
            elif index >= len(self._hoverPoints._points):
                y = self._hoverPoints._points[-1].y()
            else:
                p0 = self._hoverPoints._points[index-1]
                p1 = self._hoverPoints._points[index]
                l = QtCore.QLineF(p0, p1)
                if l.dx() > 0:
                    y = l.dy()*(p.x()-p0.x())/l.dx() + p0.y() 
                
                
            self._hoverPoints._points.insert(index,QtCore.QPointF(p.x(), y))
            self._hoverPoints._locks.insert(index, 0) # inserts a NoLock at point index
            self.update()
        
    @pyqtSlot(int)
    def slot_pointRemoved(self, index):
        if index >= 0:
            self._hoverPoints._locks.pop(index)
            self._hoverPoints._points.remove(index)
            self.update()
        
        
    @property
    def hoverPoints(self) -> HoverPoints:
        return self._hoverPoints
        
    @property
    def points(self) -> QtGui.QPolygonF:
        return self._hoverPoints.points
    
    def colorAt(self, x:int) -> int:
        """Returns the color of the pixel in the shade's image at index 'x'.
        'x' is an integer 'x' coordinate in shade's image.
        
        """
        # NOTE: 2021-06-23 22:21:09
        # QImage.pixel(x,y) returns the color of the pixel at (x,y) as a Qrgb
        # (an unsigned int)
        self._generateShade()
        
        pts = self._hoverPoints.points
        
        for k in range(1, len(pts)):
            # check between which pair of points 'x' is located
            if x >= pts[k-1].x() and x <= pts[k].x():
                # NOTE: 2021-06-23 22:08:18
                # 'x' is between the x coordinates of two successive hover points
                # pts[k-1] and pts[k];
                # calculate the interpolating line between the first hover point
                # and the virtual point at x
                
                # first generate the line interpolating the two successive hover
                # points
                l = QtCore.QLineF(pts[k-1], pts[k])
                
                if l.dx() > 0: # points at k-1 and k don't overlap
                    # there is a finite horizontal distance dx between the ends of
                    # the hover points line 'l', then scale this line by the fraction
                    # of the horizontal distance from line start to x, to dx
                    l.setLength(l.length() * (x - l.x1()) / l.dx())
                    # Now, x coordinate of the second point of the line is the
                    # same as 'x'
                    # we take the pixel at the coordinates of this new end point
                    # (making sure they don't fall beyond the image boundaries)
                    return self._shade.pixel(round(min([l.x2(), float(self._shade.width()  - 1)])),
                                             round(min([l.y2(), float(self._shade.height() - 1)])))
        # otherwise return black
        return 0
    
    def setGradientStops(self, stops:typing.Iterable[typing.Tuple[float, typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]]]) -> None:
        if self._shadeType == ShadeWidget.ShadeType.ARGBShade:
            self._alphaGradient = QtGui.QLinearGradient(0, 0, self.width(), 0)
            
            for stop in stops:
                c = QtGui.QColor(stop[1])
                self._alphaGradient.setColorAt(stop[0], QtGui.QColor(c.red(), c.green(), c.blue()))
            
            self._shade = QtGui.QImage() # make this image null - why? another bug which creates a color gradient
            # in the alpha shade; we don't need to show the color there!
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
                
                # to overlay the color
                p.setCompositionMode(QtGui.QPainter.CompositionMode_DestinationIn)
                fade = QtGui.QLinearGradient(0,0,0,self.height())
                fade.setColorAt(0, QtGui.QColor(0,0,0,255))
                fade.setColorAt(1, QtGui.QColor(0,0,0,0))
                p.fillRect(self.rect(), fade)
                
            else:
                self._shade = QtGui.QImage(self.size(), QtGui.QImage.Format_RGB32)
                fade = QtGui.QLinearGradient(0,0,0,self.height())
                fade.setColorAt(1, QtCore.Qt.black)
                if self._shadeType == ShadeWidget.ShadeType.RedShade:
                    fade.setColorAt(0, QtCore.Qt.red)
                elif self._shadeType == ShadeWidget.ShadeType.GreenShade:
                    fade.setColorAt(0, QtCore.Qt.green)
                else:
                    fade.setColorAt(0, QtCore.Qt.blue)
                    
                p = QtGui.QPainter(self._shade)
                p.fillRect(self.rect(), fade)
                
        
class GradientEditor(QtWidgets.QWidget):
    gradientStopsChanged = pyqtSignal(object, name="gradientStopsChanged")
    
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 size:typing.Union[int, typing.Tuple[int]]=11) -> None:
        super().__init__(parent=parent)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(1)
        vbox.setContentsMargins(1, 1, 1, 1)
        
        if isinstance(size, (tuple, list)) and len(size) == 2 and all([isinstance(v, int) for v in size]):
            self._pointSize = QtCore.QSize(*size)
        elif isinstance(size, int):
            self._pointSize = QtCore.QSize(size, size)
        else:
            self._pointSize = QtCore.QSize(11, 11)
            
        self._redShade = ShadeWidget(ShadeWidget.ShadeType.RedShade, self, size = self.pointSize)
        self._greenShade = ShadeWidget(ShadeWidget.ShadeType.GreenShade, self, size = self.pointSize)
        self._blueShade = ShadeWidget(ShadeWidget.ShadeType.BlueShade, self, size = self.pointSize)
        self._alphaShade = ShadeWidget(ShadeWidget.ShadeType.ARGBShade, self, size = self.pointSize)
        
        vbox.addWidget(self._redShade)
        vbox.addWidget(self._greenShade)
        vbox.addWidget(self._blueShade)
        vbox.addWidget(self._alphaShade)
        
        self._redShade.colorsChanged.connect(self.pointsUpdated)
        self._greenShade.colorsChanged.connect(self.pointsUpdated)
        self._blueShade.colorsChanged.connect(self.pointsUpdated)
        self._alphaShade.colorsChanged.connect(self.pointsUpdated)
        
        for shade in (self._redShade, self._greenShade, self._blueShade, self._alphaShade):
            for s in (self._redShade, self._greenShade, self._blueShade, self._alphaShade):
                if shade is not s:
                    shade.pointMovedX.connect(s.slot_syncPointX)
                    shade.pointInserted.connect(s.slot_pointInserted)
                    shade.pointRemoved.connect(s.slot_pointRemoved)
    
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
        
        self._alphaShade.setGradientStops(stops) # this is essential for painting the background of the _alphaShade
        
    @pyqtSlot(QtGui.QPolygonF)
    def pointsUpdated(self, points:QtGui.QPolygonF):
        stops = self._generateStops(self._redShade.points, self._greenShade.points, self._blueShade.points, self._alphaShade.points)
        if stops:
            self._alphaShade.setGradientStops(stops)
            self.gradientStopsChanged.emit(stops)
        
    def _generateStops(self, r, g, b, a):
        w = float(self._alphaShade.width())
        
        stops = list()

        allpoints = QtGui.QPolygonF()
        allpoints += QtGui.QPolygonF(r)
        allpoints += QtGui.QPolygonF(g)
        allpoints += QtGui.QPolygonF(b)
        allpoints += QtGui.QPolygonF(a)

        sortedPoints = sorted([p for p in allpoints], key = lambda x: x.x())
        
        # NOTE: 2021-06-26 22:21:21
        # Code in gui.painting_shared.HoverPoints.eventFilter() and a few PyQt
        # signals/slots here solves the problem described at NOTE: 2021-06-25 11:10:51
        #
        # This new code ensures that the following GUI operations are correctly 
        # represented by the hover points in the shade widgets:
        #
        # 1) adding a hover point in a shade triggers the insertion of a new 
        #   hover point at the same X coordinate in the other shade widgets and
        #   generates a new gradient stop; 
        #   the new hover points inserted in the other shade widgets get their Y 
        #   coordinate from the interpolation line between the points that bracket
        #   the inserted point.
        #
        # 2) removing a hover point in a shade removes the corresponding hover
        #   points in the other shade widgets, and the corresponding gradient stop
        #
        # 3) movement of a hover point along the X axis in a shade widget is now
        #   reflected in the the corresponding hover point in the other shade 
        #   widgets (these 'other' points keep their Y coordinate);
        #   this avoids the unintended generation of new gradient stoop after a
        #   hover point was moved - an unintended feature in the Qt example code
        #   
        # see also NOTE: 2021-06-26 22:46:39 in gui.painting_shared.HoverPoints.eventFilter()
        
        # NOTE: 2021-06-25 11:10:51
        # the problem with this approach is the unintended addition of gradient stops:
        # when a point being dragged in one of the shades changes its 'x' coordinate, 
        # this will result in the addition of a new gradient stop for the new 'x' 
        # coordinate, since the 'old' position will still generate a color stop 
        
        # NOTE: 2021-06-25 13:27:16
        # on second thoughts, this might be the intended behaviour: for each 
        # point moved on the 'x' axis, generate two stops instead of the previous
        # stop; the new stops are :
        #
        # 1) at the new 'x' coordinate of the moved point
        # 2) at the old 'x' coordinate of the points that have not moved
        #
        # NOTE, however, this wil result in new stops being added over and over
        # which can become a nuisance (the Qt example "gradients" is not interested
        # is storing the new gradient after edit so this bug is not apparent there)
        #
        # The question is:
        # if one shade point changes its 'x' position, but the corresponding
        # points in the other shades do not, should this generate two gradient
        # stop, or just alter the original stop?
        
        for i, point in enumerate(sortedPoints):
            k = int(point.x())
            
            #if i + 1 < len(sortedPoints) and k == int(sortedPoints[i+1].x()):
                #continue
            
            if i + 1 < len(sortedPoints) and np.isclose(point.x(), sortedPoints[i+1].x()):#, atol = self.pointSize.width()/20., rtol = self.pointSize.width()/20.):
                continue
            
            color = QtGui.QColor((0x00ff0000 & self._redShade.colorAt(k))   >> 16, # red
                                 (0x0000ff00 & self._greenShade.colorAt(k)) >>  8, # green
                                 (0x000000ff & self._blueShade.colorAt(k)),        # blue
                                 (0xff000000 & self._alphaShade.colorAt(k)) >> 24) # transparent
            
            if k / w > 1:
                return
            
            stops.append((k/w, color))
        
        return stops
    
    @property
    def pointSize(self):
        return self._pointSize
    
    @pointSize.setter
    def pointSize(self, val):
        for shade in (self._redShade, self._greenShade, self._blueShade, self._alphaShade):
            if isinstance(val, int):
                shade._hoverPoints._pointSize = QtCore.QSize(val, val)
                
            elif isinstance(val, (tuple, list)) and len(val)==2 and all([isinstance(v, int) for v in val]):
                shade._hoverPoints._pointSize = QtCore.QSize(*val)
                
            else:
                return
            
            shade.update()
            
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
        # related to on-screen help/description - not needed here (for now)
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
        
        self.scaleX = 1.
        self.scaleY = 1.
        
        self._hoverPoints = HoverPoints(self, HoverPoints.PointShape.CircleShape)
        self._hoverPoints.pointSize = QtCore.QSize(20,20)
        self._hoverPoints.connectionType = HoverPoints.ConnectionType.NoConnection
        self._hoverPoints.editable = False
        
        if not isinstance(hoverPoints, QtGui.QPolygonF) or hoverPoints.size() == 0:
            self._hoverPoints.points = QtGui.QPolygonF([QtCore.QPointF(100, 100), QtCore.QPointF(200,200)])
        else:
            self._hoverPoints.points = hoverPoints
            
        # NOTE: 2021-09-21 12:54:28
        # use for debugging - do NOT remove; just comment-out for release
        #self._hoverPoints.compositionMode = QtGui.QPainter.CompositionMode_Xor
        #self._hoverPoints.labels = True
        
        self._gradient = None
        
        self._stops = gradientStops
        self._spread = gradientSpread
        self._coordinateMode = coordinateMode
        self._gradientBrushType = QtCore.Qt.LinearGradientPattern # this is a Qt.BrushStyle enum value
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
            gline = gradientLine(g, self._renderer.rect())
            self.hoverPoints.points = QtGui.QPolygonF((gline.p1(), gline.p2()))
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
        return gradientLine(gradient, self.rect())

    def _restrictPoint(self, p:QtCore.QPointF) -> QtCore.QPointF:
        return restrict_point(p, self.width(), self.height())
            
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
    def _getGradient(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str, int,  ColorGradient]) -> QtGui.QGradient:
        if isinstance(val, QGui.QGradient):
            return val
        
        if isinstance(val, QtGui.QGradient.Preset):
            return QtGui.QGradient(val)
        
        if isinstance(val, ColorGradient):
            return val()
        
        if isinstance(val, int) and val in range(-len(self._gradients),len(self._gradients)):
            return QtGui.QGradient([v for v in self._gradients.values()][val])
        
        if isinstance(val, str) and val in self._gradients.keys():
            return QtGui.QGradient(self._gradients[val])
        
        return QtGui.QGradient() # black to white linear gradient
        
    # TODO: 2021-05-27 15:40:49
    # make a gradient combobox to choose from the list of gradients
    # instead of the current "Preset" group
    def __init__(self, gradient:typing.Optional[typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str, int, ColorGradient]]=None,
                 customGradients:dict=dict(),
                 parent:typing.Optional[QtWidgets.QWidget] = None, 
                 title:typing.Optional[str]="Scipyen Gradient Editor") -> None:
        
        # NOTE: no need to call self._showGradient anywhere inside the constructor
        # or functions called by the constructor (e.g. self._configureUI_());
        # a gradient will be shown once the widget has become visible, and this
        # is taken care of self.showEvent()
        
        super().__init__(parent=parent)
        self._rendererGradient = None # calculated by the renderer!
         # when a QLineF use it to check if gradient was modified
        self._gradientLine = None
        
        self._gradientIndex = 0
        self._defaultGradient = gradient
        
        self._gradients = OrderedDict()
        
        self._customGradients = customGradients
        
        self._setupGradients()
        
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
        
        self._updatePresetsCombo()
        
    def _setupGradients(self):
        self._gradients.clear()
        
        if len(self._customGradients):
            self._gradients.update(dict(sorted([(name, val) for name, val in self._customGradients.items()], key = lambda x: x[0])))
            
        self._gradients.update(standardQtGradientPresets)
        
        if isinstance(self._defaultGradient, (QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient)):
            self._gradients["Default"] = gradient
            self._gradients.move_to_end("Default", last=False)
        
        
    def showEvent(self, ev):
        """Executed when the widget becomes visible.
        """
        #print("GradientWidget.showEvent self._rendererGradient", self._rendererGradient)
        if self._rendererGradient is None:
            self._showGradient(list(self._gradients.values())[self._gradientIndex])
        ev.accept()
        
    def _configureUI_(self):
        self._renderer = GradientRenderer(self)
        
        self.mainContentWidget = QtWidgets.QWidget()
        self.mainGroup = QtWidgets.QGroupBox(self.mainContentWidget)
        self.mainGroup.setTitle("Gradients")
        
        # ### BEGIN Gradient editor swatches
        self.swatchesGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.swatchesGroup.setTitle("Stops")
        
        self._editor = GradientEditor(self.swatchesGroup)
        # ### END Gradient editor swatches
        
        # ### BEGIN Gradient type radial buttons group
        self.typeGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.typeGroup.setTitle("Type")
        
        self._linearButton = QtWidgets.QRadioButton("Linear", self.typeGroup)
        self._radialButton = QtWidgets.QRadioButton("Radial", self.typeGroup)
        self._conicalButton = QtWidgets.QRadioButton("Conical", self.typeGroup)
        
        # ### END Gradient type radial buttons group
        
        # ### BEGIN Radial gradient options GUI
        self.radialParamsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.radialParamsGroup.setTitle("Radii")
        
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
        
        # ### END Radial gradient options GUI
        
        # ### BEGIN Gradient spread radial buttons group
        self.spreadGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.spreadGroup.setTitle("Spread")
        self._padSpreadButton = QtWidgets.QRadioButton("Pad", self.spreadGroup)
        self._padSpreadButton.setToolTip("Fill area with closest stop color")
        self._reflectSpreadButton = QtWidgets.QRadioButton("Reflect", self.spreadGroup)
        self._reflectSpreadButton.setToolTip("Reflect gradient outside its area")
        self._repeatSpreadButton = QtWidgets.QRadioButton("Repeat", self.spreadGroup)
        self._repeatSpreadButton.setToolTip("Repeat gradient outside its area")
        
        # ### END Gradient spread radial buttons group
        
        # ### BEGIN Gradient coordinate mode group
        #self.coordinateModeGroup = QtWidgets.QGroupBox(self.mainGroup)
        #self.coordinateModeGroup.setTitle("Coordinate Mode")
        #self._logicalCoordinateButton = QtWidgets.QRadioButton("Logical", self.coordinateModeGroup)
        #self._logicalCoordinateButton.setToolTip("Logical")
        #self._logicalCoordinateButton.clicked.connect(self._renderer.setLogicalCoordinateMode)
        #self._deviceCoordinateButton = QtWidgets.QRadioButton("Device", self.coordinateModeGroup)
        #self._deviceCoordinateButton.setToolTip("Stretch to Device")
        #self._deviceCoordinateButton.clicked.connect(self._renderer.setDeviceCoordinateMode)
        #self._objectCoordinateButton = QtWidgets.QRadioButton("Object", self.coordinateModeGroup)
        #self._objectCoordinateButton.setToolTip("Object")
        #self._objectCoordinateButton.clicked.connect(self._renderer.setObjectCoordinateMode)
        
        #self.coordinateModeLayout = QtWidgets.QHBoxLayout(self.coordinateModeGroup)
        #self.coordinateModeLayout.addWidget(self._logicalCoordinateButton)
        #self.coordinateModeLayout.addWidget(self._deviceCoordinateButton)
        #self.coordinateModeLayout.addWidget(self._objectCoordinateButton)
        
        # ### END Gradient coordinate mode group
        
        # ### BEGIN Gradient presets group
        
        self.presetsGroup = QtWidgets.QGroupBox(self.mainGroup)
        self.presetsGroup.setTitle("Presets")
        self.presetsGroup.setToolTip("Available Gradients (including Qt's presets)")
        self.presetsGroup.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.prevPresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.prevPresetButton.setIcon(QtGui.QIcon.fromTheme("go-previous"))
        self.prevPresetButton.setToolTip("Go back")
        self.prevPresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        #self._presetButton = QtWidgets.QPushButton("(unset)", self.presetsGroup)
        #self._presetButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         #QtWidgets.QSizePolicy.Fixed)
        
        self._presetComboBox = QtWidgets.QComboBox(self.presetsGroup)
        self._presetComboBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Fixed)
        self._presetComboBox.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        
        self._presetComboBox.setEditable(True)
        self._presetComboBox.lineEdit().undoAvailable = True
        self._presetComboBox.lineEdit().redoAvailable = True
        self._presetComboBox.lineEdit().setClearButtonEnabled(True)
        
        self.nextPresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.nextPresetButton.setIcon(QtGui.QIcon.fromTheme("go-next"))
        self.nextPresetButton.setToolTip("Go forward")
        self.nextPresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        #self._updatePresetName()
        
        self.addPresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.addPresetButton.setIcon(QtGui.QIcon.fromTheme("list-add"))
        self.addPresetButton.setToolTip("Remember this gradient")
        self.addPresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        self.removePresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.removePresetButton.setIcon(QtGui.QIcon.fromTheme("list-remove"))
        self.removePresetButton.setToolTip("Forget this gradient")
        self.removePresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        self.restorePresetButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.restorePresetButton.setIcon(QtGui.QIcon.fromTheme("edit-reset"))
        self.restorePresetButton.setToolTip("Reset gradient")
        self.restorePresetButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        self.editPresetButtonAccept = QtWidgets.QPushButton("", self.presetsGroup)
        self.editPresetButtonAccept.setIcon(QtGui.QIcon.fromTheme("dialog-ok-apply"))
        self.editPresetButtonAccept.setToolTip("Apply changes")
        self.editPresetButtonAccept.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        self.editPresetButtonReject = QtWidgets.QPushButton("", self.presetsGroup)
        self.editPresetButtonReject.setIcon(QtGui.QIcon.fromTheme("dialog-cancel"))
        self.editPresetButtonReject.setToolTip("Forget changes")
        self.editPresetButtonReject.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        self.reloadPresetsButton = QtWidgets.QPushButton("", self.presetsGroup)
        self.reloadPresetsButton.setIcon(QtGui.QIcon.fromTheme("view-refresh"))
        self.reloadPresetsButton.setToolTip("Reload gradients database")
        self.reloadPresetsButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
        
        # ### END Gradient presets group
        
        # ### BEGIN type and spread group
        self.typeSpreadGroup = QtWidgets.QGroupBox(self.mainGroup)
        
        self.typeSpreadLayout = QtWidgets.QHBoxLayout(self.typeSpreadGroup)
        self.typeSpreadLayout.addWidget(self.typeGroup)
        self.typeSpreadLayout.addWidget(self.spreadGroup)
        
        # ### END type and spread group
        
        #self.toolBox = QtWidgets.QToolBox(self.mainGroup)
        #self.toolBox.addItem(self.swatchesGroup, "Stops")
        #self.toolBox.addItem(self.typeSpreadGroup, "Type and Spread")
        #self.toolBox.addItem(self.radialParamsGroup, "Radii")
        
        self.mainGroupLayout = QtWidgets.QVBoxLayout(self.mainGroup)
        self.mainGroupLayout.addWidget(self.presetsGroup)
        #self.mainGroupLayout.addWidget(self.toolBox)
        
        self.mainGroupLayout.addWidget(self.swatchesGroup)
        self.mainGroupLayout.addWidget(self.typeSpreadGroup)
        #self.mainGroupLayout.addWidget(self.coordinateModeGroup)
        #self.mainGroupLayout.addWidget(self.typeGroup)
        #self.mainGroupLayout.addWidget(self.spreadGroup)
        
        self.mainGroupLayout.addWidget(self.radialParamsGroup)

        self.editorGroupLayout = QtWidgets.QVBoxLayout(self.swatchesGroup)
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
        #self._logicalCoordinateButton.setChecked(True)

        self.presetsGroupLayout = QtWidgets.QVBoxLayout(self.presetsGroup)
        self.presetsBrowseLayout = QtWidgets.QHBoxLayout()
        self.presetsBrowseLayout.addWidget(self.prevPresetButton)
        #self.presetsGroupLayout.addWidget(self._presetButton, 1)
        self.presetsBrowseLayout.addWidget(self._presetComboBox, 1)
        self.presetsBrowseLayout.addWidget(self.nextPresetButton)
        
        self.presetActionsLayout = QtWidgets.QHBoxLayout()
        self.presetActionsLayout.addWidget(self.editPresetButtonAccept)
        self.presetActionsLayout.addWidget(self.editPresetButtonReject)
        self.presetActionsLayout.addWidget(self.restorePresetButton)
        self.presetActionsLayout.addWidget(self.addPresetButton)
        self.presetActionsLayout.addWidget(self.removePresetButton)
        self.presetActionsLayout.addWidget(self.reloadPresetsButton)
        
        
        self.presetsGroupLayout.addItem(self.presetsBrowseLayout)
        self.presetsGroupLayout.addItem(self.presetActionsLayout)
        
        #self.presetsGroup.setLayout(self.)
        
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
        self._editor.gradientStopsChanged.connect(self.slot_gradientModified)
        
        self._linearButton.clicked.connect(self._renderer.setLinearGradient)
        self._linearButton.clicked.connect(self.slot_gradientModified)
        self._radialButton.clicked.connect(self._renderer.setRadialGradient)
        self._radialButton.clicked.connect(self.slot_gradientModified)
        self._conicalButton.clicked.connect(self._renderer.setConicalGradient)
        self._conicalButton.clicked.connect(self.slot_gradientModified)
        
        self._padSpreadButton.clicked.connect(self._renderer.setPadSpread)
        self._reflectSpreadButton.clicked.connect(self._renderer.setReflectSpread)
        self._repeatSpreadButton.clicked.connect(self._renderer.setRepeatSpread)
        
        self.prevPresetButton.clicked.connect(self.setPrevPreset)
        self._presetComboBox.activated[int].connect(self.slot_presetActivated)
        self._presetComboBox.lineEdit().editingFinished.connect(self.slot_gradientNameChanged)
        self.nextPresetButton.clicked.connect(self.setNextPreset)
        self.addPresetButton.clicked.connect(self.slot_addGradientToPresets)
        self.removePresetButton.clicked.connect(self.slot_removeGradientFromPresets)
        self.restorePresetButton.clicked.connect(self.slot_restoreGradientFromPresets)
        self.editPresetButtonAccept.clicked.connect(self.slot_acceptGradientChange)
        self.editPresetButtonReject.clicked.connect(self.slot_rejectGradientChange)
        self.reloadPresetsButton.clicked.connect(self.reloadPresets)
        
        if isinstance(self._title, str) and len(self._title.strip()):
            self.setWindowTitle(self._title)
            
        self.radialParamsGroup.setEnabled(self._radialButton.isChecked())
            
        
    @property
    def defaultGradient(self) -> typing.Optional[QtGui.QGradient]:
        return self._defaultGradient
    
    @defaultGradient.setter
    def defaultGradient(self, val:typing.Optional[QtGui.QGradient]=None) -> None:
        self._setDefaultGradient(val)
        
    @pyqtSlot()
    def setPreset(self) -> None:
        self._changePresetBy(0)
        self._resetTitle()
        
    @pyqtSlot(int)
    def slot_presetActivated(self, index):
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        self._gradientIndex = index
        namedgrad = list(self._gradients.items())[self._gradientIndex]
        self._presetComboBox.setToolTip(namedgrad[0])
        self._showGradient(namedgrad[1])
        self._resetTitle()
        
    @pyqtSlot()
    def setPrevPreset(self) -> None:
        self._changePresetBy(-1)
        self._resetTitle()
        
    @pyqtSlot()
    def setNextPreset(self) -> None:
        self._changePresetBy(1)
        self._resetTitle()
        
    @pyqtSlot()
    def slot_gradientModified(self) -> None:
        if isinstance(self._title, str) and len(self._title.strip()):
            self.setWindowTitle("%s *" % self._title)
        else:
            self.setWindowTitle("%s *" % QtWidgets.QApplication.applicationDisplayName())
            
        self.radialParamsGroup.setEnabled(self._radialButton.isChecked())
        
    def _resetTitle(self):
        if isinstance(self._title, str) and len(self._title.strip()):
            self.setWindowTitle(self._title)
        else:
            self.setWindowTitle(QtWidgets.QApplication.applicationDisplayName())
        
    def _updatePresetsCombo(self):
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        self._presetComboBox.clear()
        self._presetComboBox.addItems(list(self._gradients.keys()))
        namedgrad = list(self._gradients.items())[self._gradientIndex]
        cbIndex = list(self._gradients.keys()).index(namedgrad[0])
        self._presetComboBox.setCurrentIndex(cbIndex)
        self._presetComboBox.setToolTip(namedgrad[0])
        
    def _changePresetBy(self, indexOffset:int) -> None:
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        if len(self._gradients) == 0:
            return
        
        # NOTE: 2021-05-25 13:16:27
        #### BEGIN enable circular browsing (round-robin)
        self._gradientIndex += indexOffset
        
        if self._gradientIndex >= len(self._gradients):
            self._gradientIndex = (self._gradientIndex - 1) % len(self._gradients)
            
        elif self._gradientIndex < -1 * len(self._gradients):
            self._gradientIndex = self._gradientIndex % len(self._gradients)
        
        #### END enable circular browsing

        # NOTE: use this in for non-circular navigation 
        #self._gradientIndex = max([0, min([self._gradientIndex + indexOffset, len(slf._gradients)-1])])
        
        namedgrad = list(self._gradients.items())[self._gradientIndex] 
        
        cbIndex = [n for n in self._gradients.keys()].index(namedgrad[0])
        self._presetComboBox.setCurrentIndex(cbIndex)
        
        self._showGradient(namedgrad[1]) 
        
    def _showGradient(self, 
                      gradient:typing.Union[QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient, QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient],
                      gradientType:typing.Optional[typing.Union[QtGui.QGradient.Type, str]]=QtGui.QGradient.LinearGradient,
                      points:typing.Optional[QtGui.QPolygonF] = None) -> None:
        """Displays gradient.
        
        If gradient is generic (QtGui.QGradient) then the concrete gradient type
        must be specified in the parameter 'gradientType'
        
        Parameters:
        ===========
        
        gradient: Either:
            QtGui.QGradient (generic) or one of its subclasses: 
                QLinearGradient, QRadialGradient, QConicalGradient,
                
            QtGui.QGradient.Preset enum value
            
            str: name of a gradient (either a preset name, or a name in the internal
                mapping of gradients which includes the Qt presets and any custom
                gradient(s) passed to the constructor)
            
            a planargraphics.ColorGradient object
            
        gradientType: optional, default: QtGui.QGradient.LinearGradient
            A QtGui.QGradient.Type enum value, or a str indicating the type.
            
            Valid strings are those that contain "linear". "radial", and "conical"
            as substrings (case-insensitive).
        
        """
        #print("GradientWidget._showGradient traceback")
        #traceback.print_stack()
        #print("\tgradient:", gradient)
        if not isinstance(gradient, (QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient)):
            return
        
        if isinstance(gradient, str) and len(gradient.strip()):
            # NOTE 2021-09-21 09:21:27: 
            # initialize a generic gradient from a preset name
            #print("GradientWidget._showGradient: from str")
            if gradient in self._gradients.keys():
                gradient = self._gradients[gradient]
                
            elif gradient in standardQtGradientPresets.keys():
                gradient = QtGui.QGradient(standardQtGradientPresets[gradient])
                
            else:
                return
            
        elif isinstance(gradient, QtGui.QGradient.Preset):
            # NOTE 2021-09-21 09:21:36: 
            # initialize a generic gradient from a preset
            #print("GradientWidget._showGradient: from preset")
            gradient = QtGui.QGradient(gradient)
            
        elif isinstance(gradient, ColorGradient):
            # NOTE 2021-09-21 09:21:54:
            # initialize a generic gradient from a ColorGradient
            #print("GradientWidget._showGradient: from ColorGradient")
            gradient = gradient()
            
        stops = gradient.stops()
        
        # NOTE: 2021-09-21 09:24:23
        # Determine the gradient type - useful especially when a generic gradient
        # is passed here.
        if not isinstance(gradient, (QtGui.QLinearGradient, QtGui.QRadialGradient, QtGui.QConicalGradient)):
            # NOTE: 2021-06-10 15:57:28
            # when gradient is a generic QGradient, (see NOTE 2021-09-21 09:21:27,
            # and NOTE 2021-09-21 09:21:36) use the specified gradientType to
            # determine how this is rendered:
            # NOTE 2021-09-21 09:23:08:
            # a) when gradientType is a str, convert it to the corresponding 
            #   QtGui.QGradient.Type enum value, if possible, else raise error
            # b) when gradientType is neither a str, nor a QtGui.QGradient.Type 
            #   value then use the radial buttons state in the 'Type' group.
            if isinstance(gradientType, str):
                if "linear" in gradientType.lower():
                    gradientType = QtGui.QGradient.LinearGradient
                elif "radial" in gradientType.lower():
                    gradientType = QtGui.QGradient.RadialGradient
                elif "conical" in gradientType.lower():
                    gradientType = QtGui.QGradient.ConicalGradient
                else:
                    raise ValueError("Unknown gradient type %s" % gradientType)
                
            elif not isinstance(gradientType, QtGui.QGradient.Type):
                if self._linearButton.isChecked():
                    gradientType = QtGui.QGradient.LinearGradient
                elif self._radialButton.isChecked():
                    gradientType = QtGui.QGradient.RadialGradient
                elif self._conicalButton.isChecked():
                    gradientType = QtGui.QGradient.ConicalGradient
                    
                else:# shouldn't get here
                    gradientType = QtGui.QGradient.LinearGradient # default
                
            if gradientType == QtGui.QGradient.LinearGradient:
                g = g2l(gradient)
                #gradient = sip.cast(gradient, QtGui.QLinearGradient)
                
            elif gradientType == QtGui.QGradient.RadialGradient:
                g = g2r(gradient)
                #gradient = sip.cast(gradient, QtGui.QRadialGradient)
                
            elif gradientType == QtGui.QGradient.ConicalGradient:
                g = g2c(gradient)
                #gradient = sip.cast(gradient, QtGui.QConicalGradient)
                
            else:
                return
            
            gradient = g
            
        #print("GradientWidget._showGradient gradient:", gradient)
        #print("\tresolved to:", reverse_mapping_lookup(standardQtGradientTypes, gradient.type()))
        #stops = gradient.stops()
        
        #print(f"GradientWidget._showGradient, points: {points}")
        
        if isinstance(points, (QtGui.QPolygonF, QtGui.QPolygon)) and len(points)==2:
            hoverStops = QtGui.QPolygonF(points)
        else:
            g = scaleGradient(gradient, self._renderer.rect())
            gline = gradientLine(g, self._renderer.rect()) 
            hoverStops = QtGui.QPolygonF((gline.p1(), gline.p2()))
        # NOTE: 2021-06-21 08:33:39
        # renderer doesn't know about the editor, and editor doesn't know about
        # renderer; therefore, the gradient stops must be sent to both
        self._editor.setGradientStops(stops)
        self._renderer.gradientStops = stops
        self._renderer.hoverPoints.points = hoverStops
        #printPoints(self._renderer.hoverPoints.points)
        self._renderer.update()
        
        if isinstance(gradient, QtGui.QLinearGradient):
            if not self._linearButton.isChecked():
                self._linearButton.setChecked(True)
            self._renderer.gradientBrushType = QtCore.Qt.LinearGradientPattern
            
        elif isinstance(gradient, QtGui.QRadialGradient):
            if not self._radialButton.isChecked():
                self._radialButton.setChecked(True)
            self._renderer.gradientBrushType = QtCore.Qt.RadialGradientPattern
            
        elif isinstance(gradient, QtGui.QConicalGradient):
            if not self._conicalButton.isChecked():
                self._conicalButton.setChecked(True)
            self._renderer.gradientBrushType = QtCore.Qt.ConicalGradientPattern
            
        if gradient.spread() == QtGui.QGradient.RepeatSpread:
            if not self._repeatSpreadButton.isChecked():
                self._repeatSpreadButton.setChecked(True)
            self._renderer.spread = QtGui.QGradient.RepeatSpread
            
        elif gradient.spread() == QtGui.QGradient.ReflectSpread:
            if not self._reflectSpreadButton.isChecked():
                self._reflectSpreadButton.setChecked(True)
            self._renderer.spread = QtGui.QGradient.ReflectSpread
            
        else:
            if not self._padSpreadButton.isChecked():
                self._padSpreadButton.setChecked(True)
            self._renderer.spread = QtGui.QGradient.PadSpread
            
        self.radialParamsGroup.setEnabled(self._radialButton.isChecked())
            
        if "*" in self.windowTitle():
            if isinstance(self._title, str) and len(self._title.strip()):
                self.setWindowTitle(self._title)
            else:
                self.setWindowTitle("")
        
        self._renderer.update()
        
        self._rendererGradient = self._renderer.gradient
            
    @pyqtSlot()
    def slot_addGradientToPresets(self):
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        name = self._presetComboBox.currentText()
        
        value = self.gradient # this is the current gradient, edited or not
        
        self.addGradient(value, name)
        
    def addGradient(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient],
                    name:str="") -> None:
        """Qt slot for adding a custom gradient
        """
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        
        if not isinstance(val, (QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient)):
            return
        
        if not isinstance(name, str) or len(name.strip()) == 0:
            gradname = counter_suffix("Custom", list(self._gradients.keys()), sep = " ")
            
        else:
            gradname = counter_suffix(name, list(self._gradients.keys()), sep = " ")
            
        self._customGradients[gradname] = val
        self._setupGradients()
        self._gradientIndex = list(self._gradients.keys()).index(gradname)
        self._updatePresetsCombo()
        self._showGradient(val) # this one might be shown already
        self._resetTitle()
        
    @pyqtSlot()
    def slot_removeGradientFromPresets(self):
        self.removeGradient(self._presetComboBox.currentText())
        
    def removeGradient(self, name:str):
        """Remove a gradient from the list by name.
        Standard Qt gradient presets are not affected (they are read-only).
        The 'Default' gradient can be removed.
        
        Once removed, the displayed gradient will be the next in the list 
        (round-robin) or, if the list is empty, a bog-standard gradient 
        linear, black-white) which will be set as the new 'Default'.
        
        Does nothing if a gradient with the specified names is not found in the
        internal list of gradients.
        
        """
        if name not in self._gradients.keys():
            return
        
        ndx = list(self._gradients.keys()).index(name)
        
        show = False
        
        if self._gradientIndex == ndx:
            show = True
        
        if name == "Default":
            # this is a special case, as it is the one passed at the c'tor
            # we simply set this to None
            self._defaultGradient = None
            
        elif name in self._customGradients.keys(): # these are read-only
            self._customGradients.pop(name, None)
            
        self._setupGradients()
        
        if self._gradientIndex == ndx:
            if ndx >= len(self._gradients):
                self._gradientIndex = len(self._gradients) - ndx
            
        self._updatePresetsCombo()
        
        if show:
            self._showGradient(list(self._gradients.values())[self._gradientIndex])
        
        self._resetTitle()
        
    @pyqtSlot()
    def slot_restoreGradientFromPresets(self):
        name = self._presetComboBox.currentText()
        if name in self._gradients.keys():
            self._showGradient(self._gradients[name])
            
        self._resetTitle()
        
    @pyqtSlot()
    def slot_acceptGradientChange(self):
        name = self._presetComboBox.currentText()
        
        if name not in self._gradients.keys() or name in standardQtGradientPresets.keys():
            self.addGradient(self.gradient, name)
            return
        
        if name in self._customGradients.keys():# change this in-place
            self._customGradients[name] = self.gradient
            
        elif name == "Default":
            self._defaultGradient = self.gradient
            
        self._setupGradients()
        self._gradientIndex = list(self._gradients.keys()).index(name)
        self._updatePresetsCombo()
        self._showGradient(self._gradients[name])
        self._resetTitle()
        
    @pyqtSlot()
    def slot_rejectGradientChange(self):
        self.slot_restoreGradientFromPresets()
        self._resetTitle()
        
    @pyqtSlot()
    def reloadPresets(self):
        self._setupGradients()
        self._changePresetBy(0)
        self._resetTitle()
        
    @pyqtSlot()
    def slot_gradientNameChanged(self):
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        val = self._presetComboBox.lineEdit().text()
        
        if len(self._gradients) == 0:
            return
        
        if val in self._gradients.keys():
            # existing name: show it
            gradient = self._gradients[val]
            newIndex = list(self._gradients.keys()).index(val)
            self._presetComboBox.setCurrentIndex(newIndex)
            self._gradientIndex = newIndex
            self._showGradient(gradient)
            self._resetTitle()
            return
        
        # NOTE: 2021-06-13 20:04:15
        # edited text indicates new name for the currently displayed gradient 
        # (at _gradientIndex) - indicates user wants to rename it
        # this is possible ONLY when the current gradient is NOT one of the
        # standard Qt gradient presets
        currentGradName = list(self._gradients.keys())[self._gradientIndex]
        
        if currentGradName in standardQtGradientPresets.keys():
            # cannot change a preset name! therefore look for a name starting with val
            # and add that gradient under the new name
            newName = counter_suffix(val, self._gradients.keys())
            self.addGradient(self._gradients[currentGradName], newName)
            
        else:
            self.renameGradient(self._gradientIndex, val)

    def renameGradient(self, index, newname):
        if len(self._gradients) == 0:
            return
        
        if index >= len(self._gradients):
            index = (index - 1) % len(self._gradients)
            
        elif index < -1 * len(self._gradients):
            index = index % len(self._gradients)
            
        namedgrad = list(self._gradients.items())[index]
        
        if namedgrad[0] in standardQtGradientPresets.keys() or namedgrad[0] not in self._customGradients.keys():
            # cannot recycle a standard preset name
            newname = counter_suffix(newname, self._gradients.keys())
            
            self.addGradient(namedgrad[1], newname)
            
            return
            
        elif namedgrad[0] in self._customGradients.keys():
            self._customGradients.pop(namedgrad[0], None)
            self._customGradients[newname] = namedgrad[1]
        
        else:
            return 
        
        self._setupGradients()
        self._gradientIndex = list(self._gradients.keys()).index(newname)
        self._updatePresetsCombo()
        
        self._showGradient(list(self._gradients.values())[self._gradientIndex])
        self.slot_gradientModified()
            
    def renameCurrentGradient(self, newname:str) -> None:
        sigBlocker = QtCore.QSignalBlocker(self._presetComboBox)
        if len(newname.strip()) == 0:
            return
        
        self.renameGradient(self._gradientIndex, newname )
        
        newname = counter_suffix(newname, self._gradients.keys())
        
        currentName = [n for n in self._gradients.keys()][self._gradientIndex]
        gradient = self._gradients.pop(currentName, None)
        self._gradients[newname] = gradient
        self._updatePresetsCombo()
        self.slot_gradientModified()
        
    def removeCurrentGradient(self):
        name = [n for n in self._gradients.keys()][self._gradientIndex]
        self._gradients.pop(name, None)
        self._changePresetBy(0)
        self._resetTitle()
            
    def _getRendererGradientLine(self) -> QtCore.QLineF:
        """ Returns the QLineF through the renderer's hoverpoints"""
        g = self._renderer.gradient # always one of QLinearGradient, QRadialGradient, QConicalGradient
        hoverStopsLine = QtCore.QLineF(*(p for p in self._renderer.hoverPoints.points))
        return hoverStopsLine
        
    #@property
    #def normalizedGradient_old(self) -> QtGui.QGradient:
        #g = self._renderer.gradient # always one of QLinearGradient, QRadialGradient, QConicalGradient
        #line = self._getRendererGradientLine()
        #if isinstance(g, QtGui.QLinearGradient):
            #ret = QtGui.QLinearGradient(line.p1(), line.p2())
            
        #elif isinstance(g, QtGui.QRadialGradient):
            #radiusScale = 1/min([self._renderer.width(), self._renderer.height()])
            #ret = QtGui.QRadialGradient(line.p1(), g.centerRadius() * radiusScale,
                                        #line.p2(), g.focalRadius()  * radiusScale)
            
        #else: # conical gradient
            #ret = QtGui.QConicalGradient(line.p1(), g.angle())
            
        #ret.setStops(g.stops())
        #ret.setSpread(g.spread())
        #ret.setCoordinateMode(g.coordinateMode())
        
        #return ret
        
    @property
    def normalizedGradient(self) -> QtGui.QGradient:
        """The currently displayed gradient normalized to the renderer's size
        """
        #return normalizeGradient(self.gradient, self._renderer.sizeHint())
        return normalizeGradient(self._renderer.gradient, self._renderer.rect())
    
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
        return self.normalizedGradient
    
    @property
    def gradientWithPoints(self) -> typing.Tuple[QtGui.QGradient, QtGui.QPolygonF]:
        return (self.normalizedGradient, self._renderer.hoverPoints.points)
    
    @property
    def customGradients(self):
        ret = OrderedDict(sorted(list(self._customGradients.items()), key = lambda x: x[0]))
        if isinstance(self._defaultGradient, QtGui.QGradient):
            ret["Default"] = self._defaultGradient
            ret.move_to_end("Default", last=False)
            
        return ret
            
    
    def scaledGradient(self, rect):
        return scaleGradient(self.normalizedGradient, rect)
    
    def setGradient(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str],
                    gradientType:typing.Optional[typing.Union[QtGui.QGradient.Type, str]]=None,
                    points:typing.Optional[QtGui.QPolygonF] = None) -> None:
        """Sets the display to show a gradient.
        
        The gradient is NOT added to the internal list of gradients.
        
        """
        if not isinstance(val, (QtGui.QGradient, QtGui.QGradient.Preset, str, ColorGradient)):
            return
        #print("GradientWidget.setGradient", val)
        self._showGradient(val, gradientType, points=points)
        self.slot_gradientModified()
        
    #def setGradientWithPoints(self, val:typing.Union[QtGui.QGradient, QtGui.QGradient.Preset, str],
                              #gradientType:typing.Optional[typing.Union[QtGui.QGradient.Type, str]]=None,
                              #points:typing.)
            
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
    def qGradient(self) -> QtGui.QGradient:
        return self.gw.gradient
    
    @property
    def qGradientWithPoints(self) -> typing.Tuple[QtGui.QGradient, QtGui.QPolygonF]:
        return self.gw.gradientWithPoints
        
    @property
    def gradient(self) -> ColorGradient:
        return colorGradient(self.gw.gradient)
    
    @property
    def gradientWithPoints(self) -> ColorGradient:
        grad, points = self.gw.gradientWithPoints
        return colorGradient(self.gw.gradient), points
    
    @property
    def colorGradient(self) -> ColorGradient:
        return self.gradient
    
    @property
    def colorGradientWithPoints(self) -> ColorGradient:
        return self.gradientWithPoints
    
        
def set_shade_points(points:typing.Union[QtGui.QPolygonF, list], shade:ShadeWidget) -> None:
    shade.hoverPoints.points = QtGui.QPolygonF(points)
    shade.hoverPoints.setPointLock(0, HoverPoints.LockType.LockToLeft)
    shade.hoverPoints.setPointLock(-1, HoverPoints.LockType.LockToRight)
    shade.update()
