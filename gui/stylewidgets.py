import array, os, typing
import numpy as np

from enum import IntEnum
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, no_sip_autoconversion)

from .scipyen_colormaps import (qtGlobalColors, standardPalette,
                                standardPaletteDict, svgPalette,
                                getPalette, paletteQColors, paletteQColor, 
                                standardQColor, svgQColor,
                                qtGlobalColors, mplColors)

from .colorwidgets import (make_transparent_pattern, comboDelegateBrush)

__module_path__ = os.path.abspath(os.path.dirname(__file__))



class PenComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("StrokeRole", QtCore.Qt.UserRole +1)], 
                        module=__name__, qualname="PenComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="PenComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
        
    @no_sip_autoconversion
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):
        #color = QtGui.QColor(QtCore.Qt.white)
        isSelected - (option.state and QtWidgets.QStyle.State_Selected)
        
        paletteBrush = comboDelegateBrush(index, QtCore.Qt.BackgroundRole).style() == QtCore.Qt.NoBrush
        
        if isSelected:
            innerColor = option.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = option.palette.color(QtGui.QPalette.Base)
            
        _, _, v, _ = innerColor.getHsv()
        
        if v > 128:
            penColor = QtGui.QColor(QtCore.Qt.black)
        else:
            penColor = QtGui.QColor(QtCore.Qt.white)

        opt = QtWidgets.QStyleOptionViewItem(option)
        opt.showDecorationSelected=True
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)
        innerRect = option.rect.adjusted(self.LayoutMetrics.FrameMargin,
                                         self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin)
        
        lineRect = innerRect.adjusted(2, 2, -2, -2)

        penStyle = index.data(self.ItemRoles.StrokeRole) # NOTE:2021-05-15 21:18:24Q QVariant
        #if isinstance(cv, QtGui.QColor):
        if isinstance(cv, QtCore.Qt.PenStyle):
            #if cv.isValid():
            #innerColor = cv
            paletteBrush = False
            tmpRenderHints = painter.renderHints()
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setBrush(innerColor)
            painter.drawRoundedRect(innerRect, 2, 2)
            painter.setPen(QtGui.QPen(penColor, 2, penStyle))
            painter.drawLine(lineRect.x(), 
                             lineRect.y()//2, 
                             lineRect.x()+lineRect.width(),
                             lineRect.y()//2)
            
            #painter.setPen(QtCore.Qt.transparent)
            #if innerColor.alpha() < 255 and isinstance(self._tPmap, QtGui.QPixmap):
                #painter.setBrush(QtCore.Qt.NoBrush)
                #painter.drawRoundedRect(innerRect, 2, 2)
                #painter.fillRect(innerRect, QtGui.QBrush(self._tPmap))
                #painter.fillRect(innerRect, innerColor)
            #else:
                #painter.setBrush(innerColor)
                #painter.drawRoundedRect(innerRect, 2, 2)
            painter.setRenderHints(tmpRenderHints)
            painter.setBrush(QtCore.Qt.NoBrush)
                
    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        return QtCore.QSize(100, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
class PenComboBox(QtWidgets.QComboBox):
    activated = pyqtSignal(QtCore.Qt.PenStyle, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(QtCore.Qt.PenStyle, name="highlighted")
    styleChanged = pyqtSignal(QtCore.Qt.PenStyle, name="styleChanged")
    
    def __init__(self, style:typing.Optional[QtCore.Qt.PenStyle]=None,
                 palette:typing.Optional[typing.Union[list, tuple, dict, str]]=None,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(self, parent=parent)
        self._styleList = []
        self._styleDict = {}
        
        if isinstance(palette, (tuple, list)):
            self._styleList = [palettePenStyle(palette, k) for k in range(len(palette))]
            
        if isinstance(palette, dict):
            self._styleDict = dict([(k, palettePenStyle(palette, k)) for k in palette.keys()])
            
        self._customStyle = None
        
        # FIXME/TODO/ see qt examples/widgets/painting/pathstroke

class BrushComboDelegate(QtWidgets.QAbstractItemDelegate):
    pass

class BrushComboBox(QtWidgets.QComboBox):
    pass

