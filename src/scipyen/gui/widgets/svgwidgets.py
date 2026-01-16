# -*- coding: utf-8 -*-
# $Id: svgwidgets.py $
# SPDX-FileCopyrightText: 2022 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widgets for rendering SVG
"""
import sys, os, traceback, typing, types
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
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

class SimpleSVGWidget(QtWidgets.QWidget):
    # from qtsvg SVGViewer example
    def __init__(self, svg:typing.Optional[str]=None, parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent)
        self._scale:float = 1.0
        self._renderer:QtSvg.QSvgRenderer = QtSvg.QSvgRenderer()
        self._renderer.repaintNeeded.connect(self.update)
        if isinstance(svg, str) and len(svg.strip()):
            if not self._renderer.load(QtCore.QByteArray(bytes(svg.encode()))):
                raise ValueError("Invalid svg string")
        
    def paintEvent(self, event:QtGui.QPaintEvent):
        svgSize = self._renderer.defaultSize() * self._scale
        pw = self.parentWidget()
        widgetSize = QtCore.QSize(pw.width(), pw.height()) if isinstance(pw, QtWidgets.QWidget) else  QtCore.QSize(self.width(), self.height())
        self.setFixedSize(svgSize.expandedTo(widgetSize))
        
        painter = QtGui.QPainter(self)
        # painter.fillRect(0, 0, self.width(), self.height(), QtCore.Qt.transparent)
        painter.save()
        bounds = QtCore.QRectF((widgetSize.width() - svgSize.width()) / 2,
                              (widgetSize.height() - svgSize.height()) / 2,
                              svgSize.width(), svgSize.height())
        painter.setClipRect(bounds)
        
        self._renderer.render(painter, bounds)
        painter.restore()
        painter.end()
        
    def renderAsImage(self, imageSize:QtCore.QSize) -> QtGui.QImage:
        image = QtGui.QImage(imageSize, QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(image)
        self._renderer.render(painter, QtCore.QRectF(QtCore.QPointF(), QtCore.QSizeF(imageSize)))
        return image
    
    def setSvg(self, svg:str):
        if not self._renderer.load(QtCore.QByteArray(bytes(svg.encode()))):
            raise ValueError("Invalid svg string")
        self.update()

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
        return self._renderer.defaultSize() * self._scale if self._renderer.isValid() else QtCore.QSize(1, 1)

    def fileSize(self) -> QtCore.QSize:
        return self._renderer.defaultSize() if self._renderer.isValid() else QtCore.QSize()
