# $Id: mplfigurewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os
import sys
import typing
import traceback

import matplotlib as mpl


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

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.figure import Figure

from core.prog import (scipywarn, timefunc, timemethod)

class MplFigureWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self._canvas_ = FigureCanvas(Figure())

        layout.addWidget(NavigationToolbar(self._canvas_, self))
        layout.addWidget(self._canvas_)

        self._ax_ = self._canvas_.figure.subplots()

    @property
    def figure(self):
        return self._canvas_.figure

    @property
    def canvas(self):
        return self._canvas_

    @property
    def axes(self):
        return self._ax_

    def subplots(self, *args, **kwargs):
        self._ax_ = self.figure.subplots(*args, **kwargs)
        self.canvas.draw_idle()

    def plot(self, *args, **kwargs):
        if self.axes is None:
            self.subplots()
        self.axes.plot(*args, **kwargs)
        self.canvas.draw_idle()

    def stem(self, *args, **kwargs):
        if self.axes is None:
            self.subplots()
        self.axes.stem(*args, **kwargs)
        self.canvas.draw_idle()

    def removeAxes(self):
        self.figure.delaxes()
        self._ax_= None
        self.canvas.draw_idle()

    def clearLegend(self):
        if self.figure and self.canvas:
            self.figure.legends.clear()
            self.canvas.draw_idle()

    def clear(self, full: bool=False):
        if full is True:
            self.figure.clear()
            self.removeAxes()
        else:
            self.axes.clear()

        if len(self.figure.legends):
            self.clearLegend()
        self.canvas.draw_idle()





