from gui.pyqtgraph_patch import pyqtgraph as pg
from PyQt5 import (QtCore, QtWidgets, QtGui)

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



