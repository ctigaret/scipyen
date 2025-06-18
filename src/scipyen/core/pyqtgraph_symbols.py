# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os
__has_PySide6__=False
if os.environ["QT_API"] == "pyside6":
    import PySide6
    from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
    from PySide6.QtCore import Signal, Slot
    from PySide6.QtUiTools import loadUiType as __loadUiType__
    import qtpy
    qtpy.API = os.environ["QT_API"]
    os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"
    os.environ["FORCE_QT_API"] = "1"
    __has_PySide6__=True
elif os.environ["QT_API"] == "pyqt6":
    import qtpy
    qtpy.API = os.environ["QT_API"]
    os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
    os.environ["FORCE_QT_API"] = "1"
    from qtpy import QtCore, QtGui, QtWidgets, QtSvg
    from qtpy.QtCore import Signal, Slot
    from qtpy.uic import loadUiType as __loadUiType__
else:
    import qtpy
    qtpy.API = os.environ["QT_API"]
    from qtpy import QtCore, QtGui, QtWidgets, QtSvg
    from qtpy.QtCore import Signal, Slot
    from qtpy.uic import loadUiType as __loadUiType__

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



