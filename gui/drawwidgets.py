import typing
from enum import IntEnum, auto

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

class HoverPoints(QtCore.QObject):
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
        
    pointsChanged = pyqtSignal(QtGui.QPolygonF, named = "pointsChanged")
        
    def __init_(widget:QtWidgets.QWidget, shape:HoverPoints.PointShape):
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
        
    @pyqtSlot(bool)
    def setEnabled(self, value:bool) -> None:
        if self._enabled != value:
            self._enabled = enabled
            self._widget.update()
            
    @pyqtSlot(bool)
    def setDisabled(self, value:bool) -> None:
        self.setEnabled(not value)
        
    def pointBoundingRect(self, i:int) -> QtCore.QRectF:
        p = self._points.at(i)
        w = self._pointSize.width()
        h = self._pointSize.height()
        x = p.x() - w/2 
        y = p.y() - h/2
        return QtCore.QRectF(x, y, w, h)
    
    def boundingRect(self) -> QtCore.QRectF:
        if self._bounds.isNull() or self._bounds.isEmpty() or not self._bounds.isValid():
            return QtCore.QRectF(self._widget.rect())
        else:
            return self._bounds
        
    def eventFilter(self, obj:QtCore.QObject, ev:QtCore.QEvent) -> bool:
        if obj == self._widget and self._enabled:
            if ev.type() == QtCore.QEvent.MouseButtonPress:
                if len(self._fingerPointMapping) == 0: # see # NOTE 2021-05-21 21:29:33 touchscreens
                    return True
                
                me = QtGui.QMouseEvent(ev)
                
                clickPos = me.pos()
                
                index = -1
                
                for i in range(self._points.size()):
                    path = QtGui.QPainterPath()
                    if self._shape == HoverPoints.PointShape.CircleShape:
                        path.addEllipse(self.pointBoundingRect(i))
                    else:
                        path.addRect(self.pointBoundingRect(i))

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
                    self.movePoint(self._currentIndex, event.pos())
                
            elif ev.type() == QtCore.QEvent.TouchBegin:
                pass # see NOTE 2021-05-21 21:29:33 touchscreens
            
            elif ev.type() == QtCore.QEvent.TouchUpdate:
                pass # see NOTE 2021-05-21 21:29:33 touchscreens - skipped code
            elif ev.type() == QtCore.QEvent.TouchEnd:
                pass # see NOTE 2021-05-21 21:29:33 touchscreens - skipped code
            elif ev.type() == QtCore.QEvent.Resize:
                pass # TODO / FIXME
                
                        
                
        
    



