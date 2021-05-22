import numbers, typing
from enum import IntEnum, auto

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

import sip

def x_less_than(p1:QtCore.QPointF, p2:QtCore.QPointF) -> bool:
    return p1.x() < p2.x()

def y_less_than(p1:QtCore.QpointF, p2:QtCore.QPointF) -> bool:
    return p1.y() < p2.y()

class HoverPoints(QtCore.QObject):
    pointsChanged = pyqtSignal(QtGui.QPolygonF, named = "pointsChanged")
    
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
        
    @staticmethod
    def bound_point(point:QtCore.QPointF, bounds:QtCore.QRectF, lock:int) -> QtCore.QPointF:
        p = point
        
        left = bounds.left()
        right = bounds.right()
        top = bounds.top()
        bottom= bountds.bottom()
        
        if p.x() < left or (lock & HoverPoints.LockType.LockToLeft):
            p.setX(left)
            
        elif p.x() > right or (lock & HoverPoints.LockType.LockToRight):
            p.setX(right)
            
        if p.y() < top or (lock & HoverPoints.LockType.LockToTop):
            p.setY(top)
            
        elif p.y() > bottom or (lock & HoverPoints.LockType.LockToBottom):
            p.setY(bottom)
            
        return p
        
        
    def __init__(widget:QtWidgets.QWidget, shape:HoverPoints.PointShape):
        super().__init__(widget)
        
        self._widget = widget
        widget.installEventFilter(self)
        
        # NOTE 2021-05-21 21:29:33 touchscreens
        # I don't think is needed
        widget.setAttribute(QtCore.Qt.WA_AcceptTouchgEvents) 
        
        self._connectionType = HoverPoints.ConnectionType.CurveConnection
        self._sortType = HoverPoints.SortType.NoSort
        self._shape = shape
        self._pointPen = QtGui.QPen(QtGui.QCOlor(255, 255, 255, 191), 1)
        self._connectionPen = QtGui.QPen(QtGui.QCOlor(255, 255, 255, 127), 2)
        self._pointBrush = QtGui.QBrush(QtGui.QColor(191, 191, 191, 127))
        self._pointSize = QtCore.QSize(11, 11)
        self._currentIndex = -1
        self._editable = True
        self._enabled = True
        self._points = QtGui.QPolygonF()
        self._bounds = QtCore.QRectF()
        self._locks = list()
        
        self._fingerPointMapping = dict() # see NOTE 2021-05-21 21:29:33 touchscreens
        
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
    def points(self) -> QtCore.QPolygonF:
        return self._points
    
    @points.setter
    def points(self, points:typing.Union[QtGui.QPolygonF,typing.Iterable[typing.Union[QtCore.QPointF, QtCore.QPoint]]]) -> None:
        if isinstance(points, (list, tuple)):
            self._points = QtGui.QPolygonF(*points)
        else:
            self._points = points
        
    #def setPoints(self, points:QtGui.QPolygonF):
        #self._points = points
        
    @property
    def pointSize(self) -> QtCore.QSize:
        return self._pointSize
        
    @pointSize.setter
    def pointSize(self, size:typing.Union[QtCore.QSizeF, typing.Tuple[numbers.Real, numbers.Real]]) -> None:
        if isinstance(size, (QtCore.Qt.QSize, QtCore.Qt.QSizeF)):
            self._pointSize = size
        else:
            self._pointSize = QtCoreQt.QSizeF(*size)
            
        
    @property
    def sortType(self) -> HoverPoints.SortType:
        return self._sortType
    
    @sortType.setter
    def sortType(self, sortType:HoverPoints.SortType) -> None:
        self._sortType = sortType
        
    @property
    def connectionType(self) -> HoverPoints.ConnectionType:
        return self._connectionType
    
    @connectionType.setter
    def connectionType(self, connectionType:HoverPoints.ConnectionType) -> None:
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
    
    def setPointLock(self, pos:int, lock:HoverPoints.LockType) -> None:
        self._lock[pos] = lock
        
        
    def eventFilter(self, obj:QtCore.QObject, ev:QtCore.QEvent) -> bool:
        if obj == self._widget and self._enabled:
            if ev.type() == QtCore.QEvent.MouseButtonPress:
                if len(self._fingerPointMapping) == 0: # see # NOTE 2021-05-21 21:29:33 touchscreens
                    return True
                
                me = sip.cast(ev, QtGui.QMouseEvent)
                #me = QtGui.QMouseEvent(ev)
                
                clickPos = me.pos()
                
                index = -1
                
                for i in range(self._points.size()):
                    path = QtGui.QPainterPath()
                    if self._shape == HoverPoints.PointShape.CircleShape:
                        path.addEllipse(self._pointBoundingRect(i))
                    else:
                        path.addRect(self._pointBoundingRect(i))

                    if path.contains(clickPos):
                        index = i
                        break
                
                if me.button() == QtCore.Qt.LeftButton: # add new point or select clicked one & propagate event
                    if index == -1: # new point added (index is unchanged from -1 because clickPos is not on path)
                        if not self._editable: # non-editable => don't propagate event
                            return False
                        
                        pos = 0
                        
                        if self._sortType == HoverPoints.SortType.XSort:
                            for i in range(self._points.size()):
                                if self._points.at(i).x() > clickPos.x():
                                    pos = i
                                    break
                                
                        elif self._sortType == HoverPoints.SortType.YSort:
                            for i in range(self._points.size()):
                                if self._points.at(i).y() > clickPos.y():
                                    pos = i
                                    break
                                
                        self._points.insert(pos, clickPos)
                        self._locks.insert(pos, 0)
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
                            
                        self.firePointChange()
                        return True
                    
            elif ev.type() == QtCore.QEvent.MouseButtonRelease:
                if len(self._fingerPointMapping):
                    return True
                self._currentIndex = -1
                
            elif ev.type() == QtCore.QEvent.MouseMove:
                if len(self._fingerPointMapping):
                    return True
                
                if self._currentIndex >= 0:
                    self._movePoint(self._currentIndex, event.pos())
                
            elif ev.type() == QtCore.QEvent.TouchBegin:
                pass # see NOTE 2021-05-21 21:29:33 touchscreens
            
            elif ev.type() == QtCore.QEvent.TouchUpdate:
                pass # see NOTE 2021-05-21 21:29:33 touchscreens - skipped code
            elif ev.type() == QtCore.QEvent.TouchEnd:
                pass # see NOTE 2021-05-21 21:29:33 touchscreens - skipped code
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
                
            elif ev.type() == QtCore.QEvent.Paint:
                that_widget = self._widget
                self._widget = NOne
                QtCore.QCoreApplication.sendEvent(obj, ev)
                self._widget = that_widget
                self._paintPoints()
                return True
            
        return False
    
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
        for in self._points:
            bounds = self._pointBoundingRect(p)
            if self._shape == HoverPoints.PointShape.CircleShape:
                p.drawEllipse(bounds)
            else:
                p.drawRect(bounds)
                    
    def setPoints(points:QtGui.QPolygonF) -> None:
        if points.size() != self._points.size():
            self._fingerPointMapping.clear()
            
        self._points.clear()
        
        for p in points:
            self._points.append(self.bound_point(p, self.boundingRect(), 0))
            
        self._locks.clear()
        if self._points.size():
            self._locks = [0] * self._points.size()
            
    def _movePoint(index:int, point:QtCore.QPointF, emitUpdate:bool) -> None:
        self._points[index] = self.bound_point(point, self.boundingRect(), self._locks[index])
        if emitUpdate:
            self.firePointChange()
        
    
    def firePointChange(self):
        if self._sortType != HoverPoints.SortType.noSort:
            oldCurrent = QtCore.QPointF()
            if self._currentIndex != -1:
                oldCurrent = self._points[self._currentIndex]
                
            if self._sortType == HoverPoints.SortType.XSort:
                self._points = QtCore.QPolygonF(sortedPoints = sorted([p for p in self._points], key = x_less_than))
            elif self._sortType == HoverPoints.SortType.YSort:
                self._points = QtCore.QPolygonF(sortedPoints = sorted([p for p in self._points], key = y_less_than))
                
            if self._currentIndex != -1:
                for i, p in enumerate(self._points):
                    if p == oldCurrent:
                        self._currentIndex = i
                        break
                    
        self.pointsChanged.emit(self._points)

