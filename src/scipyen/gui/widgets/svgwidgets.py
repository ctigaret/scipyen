# -*- coding: utf-8 -*-
# $Id: svgwidgets.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widgets for rendering SVG
"""
import sys, os, traceback, typing, types, xml
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork,)
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True
    
from core.prog import scipywarn
from core.strutils import is_svg

class SimpleSVGWidget(QtWidgets.QWidget):
    # from qtsvg SVGViewer example
    default_render_size = QtCore.QSize(64,64)
    def __init__(self, svg:typing.Optional[str]=None, 
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
        self._scale:float = 1.0
        self._renderer:QtSvg.QSvgRenderer = QtSvg.QSvgRenderer()
        self._renderer.repaintNeeded.connect(self.update)
        self.setSvg(svg)
        
    def paintEvent(self, event:QtGui.QPaintEvent):
        if self._renderer.isValid():
            defSize = self._renderer.defaultSize()
            if defSize.isNull():
                defSize = self.default_render_size
            if isinstance(self._scale, float):
                renderSize = defSize * self._scale
            elif isinstance(self._scale, typing.Sequence) and all([isinstance(v, (float, int)) for v in self._scale]):
                renderSize = QtCore.QSize(int(defSize.width() * self._scale[0]), int(defSize.height() * self._scale[1]))
            self.setBaseSize(renderSize)
            # pw = self.parentWidget()
            widgetSize = QtCore.QSize(self.width(), self.height())
            # widgetSize = QtCore.QSize(pw.width(), pw.height()) if isinstance(pw, QtWidgets.QWidget) else  QtCore.QSize(self.width(), self.height())
            # self.setFixedSize(renderSize.expandedTo(widgetSize))

        else:
            widgetSize = QtCore.QSize(self.width(), self.height())#super(QtWidgets.QWidget, self).size()# QtCore.QSize(128,128)
            # widgetSize = QtCore.QSize(128,128)
            renderSize = widgetSize
            self.setBaseSize(widgetSize)

        painter = QtGui.QPainter(self)
        # painter.fillRect(0, 0, self.width(), self.height(), QtCore.Qt.transparent)
        if self._renderer.isValid():
            painter.save()
            bounds = QtCore.QRectF((widgetSize.width() - renderSize.width()) / 2,
                                (widgetSize.height() - renderSize.height()) / 2,
                                renderSize.width(), renderSize.height())
            painter.setClipRect(bounds)
            self._renderer.render(painter, bounds)
            painter.restore()
        painter.end()

    def setSvg(self, svg:typing.Optional[typing.Union[str, xml.dom.minidom.Element]]):
        # print(f"{self.__class__.__name__}.setSvg(svg={type(svg).__name__})")
        if isinstance(svg, str) and is_svg(svg):
            if not self._renderer.load(QtCore.QByteArray(bytes(svg.encode()))):
                scipywarn(f"Could not render {svg}")
            self.update()
            self.resizeEvent()
        elif isinstance(svg, xml.dom.minidom.Element):
            if not self._renderer.load(QtCore.QByteArray(bytes(svg.toprettyxml().encode()))):
                scipywarn(f"Could not render {svg}")

            self.update()
            self.resizeEvent()

        else:
            self._renderer = QtSvg.QSvgRenderer()
            self.update()

    def resizeEvent(self, event:typing.Optional[QtCore.QEvent]=None):
        if not self._renderer.isValid():
            return
        renderSize = self._renderer.defaultSize()
        if renderSize.isNull():
            renderSize = self.default_render_size
        # print(f"{self.__class__.__name__}.resizeEvent: renderSize = {renderSize}")
        # pw = self.parentWidget()
        widgetSize = QtCore.QSize(self.width(), self.height())
        # widgetSize = QtCore.QSize(pw.width(), pw.height()) if isinstance(pw, QtWidgets.QWidget) else  QtCore.QSize(self.width(), self.height())
        newSize = renderSize.scaled(widgetSize, QtCore.Qt.KeepAspectRatio)
        scaleX = newSize.width() / renderSize.width()
        scaleY = newSize.height() / renderSize.height()
        self._scale =  (newSize.width() / renderSize.width(), newSize.height() / renderSize.height())
        
        self.update()
        
    def renderAsImage(self, imageSize:QtCore.QSize) -> QtGui.QImage:
        image = QtGui.QImage(imageSize, QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(image)
        self._renderer.render(painter, QtCore.QRectF(QtCore.QPointF(), QtCore.QSizeF(imageSize)))
        return image
    
    def reload(self):
        if not self._renderer.isValid():
            return
        
        self.update()
        
    def setScale(self, scale:float):
        if self._scale == scale:
            return
        
        self._scale = scale
        self.update()
        
    def sizeHint(self) -> QtCore.QSize:
        if self._renderer.isValid():
            defSize = self._renderer.defaultSize()
            if isinstance(self._scale, (float, int)):
                return defSize * self._scale
            elif isinstance(self._scale, typing.Sequence) and all([isinstance(v, (float, int)) for v in self._scale]):
                return QtCore.QSize(int(defSize.width() * self._scale[0]), int(defSize.height()* self._scale[1]))
        else:
            return QtCore.QSize(1, 1)

    def svgSize(self) -> QtCore.QSize:
        return self._renderer.defaultSize() if self._renderer.isValid() else QtCore.QSize()
