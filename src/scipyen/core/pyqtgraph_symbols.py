# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os
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
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

from core.pyqtgraph_patch import pyqtgraph as pg

# each spike is a small vertical line centered at 0.0, height of 1
spike_Symbol = QtGui.QPainterPath(QtCore.QPointF(0.0, -0.5))
spike_Symbol.lineTo(QtCore.QPointF(0.0, 0.5))
spike_Symbol.closeSubpath()

event_Symbol = QtGui.QPainterPath(QtCore.QPointF(0.0, -0.5))
event_Symbol.lineTo(QtCore.QPointF(-0.1, 0.5))
event_Symbol.lineTo(QtCore.QPointF(0.1, 0.5))
event_Symbol.closeSubpath()

event_dn_Symbol = QtGui.QPainterPath(QtCore.QPointF(0.0, 0.5))
event_dn_Symbol.lineTo(QtCore.QPointF(-0.1, -0.5))
event_dn_Symbol.lineTo(QtCore.QPointF(0.1, -0.5))
event_dn_Symbol.closeSubpath()


event2_Symbol = QtGui.QPainterPath(QtCore.QPointF(0.0, 0.0))
event2_Symbol.lineTo(QtCore.QPointF(-0.1, -0.5))
event2_Symbol.lineTo(QtCore.QPointF(0.1, -0.5))
event2_Symbol.closeSubpath()

event2_dn_Symbol = QtGui.QPainterPath(QtCore.QPointF(0.0, 0.0))
event2_dn_Symbol.lineTo(QtCore.QPointF(-0.1, 0.5))
event2_dn_Symbol.lineTo(QtCore.QPointF(0.1,  0.5))
event2_dn_Symbol.closeSubpath()

if "spike" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    pg.graphicsItems.ScatterPlotItem.Symbols["spike"] = spike_Symbol

if "event" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    pg.graphicsItems.ScatterPlotItem.Symbols["event"] = event_Symbol
    
if "event_dn" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    pg.graphicsItems.ScatterPlotItem.Symbols["event_dn"] = event_dn_Symbol

if "event2" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    pg.graphicsItems.ScatterPlotItem.Symbols["event2"] = event2_Symbol
    
if "event2_dn" not in pg.graphicsItems.ScatterPlotItem.Symbols.keys():
    pg.graphicsItems.ScatterPlotItem.Symbols["event2_dn"] = event2_dn_Symbol



