import array, os, typing, numbers
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

standardQtPenStyles = dict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenStyle) and val < 10],
                           key = lambda x: x[1]))

standardQtPenJoinStyles = dict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenJoinStyle) and val <= 256],
                           key = lambda x: x[1]))

standardQtPenCapStyles = dict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenJoinStyle) and val <= 32],
                           key = lambda x: x[1]))

customDashStyles = {"Custom": [10., 5., 10., 5., 10., 5., 1., 5., 1., 5., 1., 5.]}

@safeWrapper
def makeCustomPathStroke(path:QtGui.QPainterPath,
                     dashes:list, width:numbers.Real=1.,
                     join:QtCore.Qt.PenJoinStyle=QtCore.Qt.MiterJoin,
                     cap:QtCore.Qt.PenCapStyle=QtCore.Qt.FlatCap,
                     ) -> QtGui.QPainterPath:
    
    if isinstance(dashes, (tuple, list)) and len(dashes):
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(width)
        stroker.setJoinStyle(join)
        stroker.setCapStyle(cap)
    
        stroker.setDashPattern(dashes)
        
        return stroker.createStroke(path)
    
    return path
    

class PenStyleComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("StrokeRole", QtCore.Qt.UserRole +1)], 
                        module=__name__, qualname="PenStyleComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="PenStyleComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
        
    @no_sip_autoconversion(QtCore.QVariant)
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):
        #color = QtGui.QColor(QtCore.Qt.white)
        isSelected = (option.state and QtWidgets.QStyle.State_Selected)
        
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
        
        if isinstance(penStyle, (QtCore.Qt.PenStyle, tuple, list, int)):
            #paletteBrush = False
            tmpRenderHints = painter.renderHints()
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(innerColor)
            painter.drawRoundedRect(innerRect, 2, 2)
            path = QtGui.QPainterPath()
            path.moveTo(lineRect.x(), lineRect.y() + lineRect.height()//2)
            path.lineTo(lineRect.x()+lineRect.width(), lineRect.y() + lineRect.height()//2)
            
            if isinstance(penStyle, (tuple, list)):# custom stroke
                painter.fillPath(makeCustomPathStroke(path, penStyle, 2), penColor)
            else:
                painter.setPen(QtGui.QPen(penColor, 2, penStyle))
                painter.drawPath(path)
            
            painter.setRenderHints(tmpRenderHints)
            painter.setBrush(QtCore.Qt.NoBrush)

    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        return QtCore.QSize(100, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
class PenStyleComboBox(QtWidgets.QComboBox):
    # FIXME/TODO/ see qt examples/widgets/painting/pathstroke
    activated = pyqtSignal(object, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(object, name="highlighted")
    styleChanged = pyqtSignal(object, name="styleChanged")
    
    def __init__(self, style:typing.Optional[QtCore.Qt.PenStyle]=None,
                 customStyles:typing.Optional[dict]=customDashStyles,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        #QtWidgets.QComboBox._init__(self, parent=parent)
        #self._styleDict = standardQtPenStyles
        self._customStyles = {}
        self._internalStyle = QtCore.Qt.SolidLine
        self._customStyle = QtCore.Qt.NoPen
        #self._customStyleName = "Custom"

        if len(customStyles):
            self._customStyles.update(customStyles)
            
        self.setItemDelegate(PenStyleComboDelegate(self))
        
        self._addStyles()
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        self.setCurrentIndex(1)
        self._slotActivated(1)
        self.setMaxVisibleItems(13)
        #self._setCustomStyle("SolidLine", QtCore.Qt.SolidLine)
        
    @pyqtSlot(int)
    @safeWrapper
    def _slotActivated(self, index:int):
        if index == 0:
            from .quickdialog import (QuickDialog, OptionalStringInput)
            dlg  = QuickDialog(self, "Custom Dash Pattern")
            namePrompt = OptionalStringInput(dlg, "Name:")
            dashPrompt = OptionalStringInput(dlg, "Dash style:")
            if dlg.exec_():
                name = namePrompt.text()
                dash = dashPrompt.text()
                if len(dash.strip()):
                    dashes = [eval(x) for x in dash.strip().split(",") if len(x)]
                    
                    if all([isinstance(v, numbers.Real) for v in dashes]):
                        if len(name.strip()):
                            self._setCustomStyle(name, dashes, True)
                        else:
                            self._setCustomStyle("Custom...", dashes, False)
            return
        else:
            self._internalStyle = self.itemData(index, PenStyleComboDelegate.ItemRoles.StrokeRole)
            self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
            self.activated[object].emit(self._internalStyle)

    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == 0:
            self._internalStyle = self._customStyle
            self.setToolTip("Custom dashes")
        else:
            self._internalStyle = self.itemData(index, PenStyleComboDelegate.ItemRoles.StrokeRole)
            self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
    
    def _addStyles(self):
        self.addItem(self.tr("Custom dashes...", "@item:inlistbox Custom stroke style"))
        self.setItemData(0, "Custom dashes...", QtCore.Qt.ToolTipRole)
        
        styles = [(name, val) for name, val in standardQtPenStyles.items() if val > QtCore.Qt.NoPen and val < QtCore.Qt.CustomDashLine]
        
        styles += [("No Pen", QtCore.Qt.NoPen)]
        
        styles += [(name, val) for name, val in self._customStyles.items()]
        
        for k, (name, val) in enumerate(styles):
            self.addItem("")
            self.setItemData(k + 1, val, PenStyleComboDelegate.ItemRoles.StrokeRole)
            self.setItemData(k + 1, name, QtCore.Qt.ToolTipRole)
            
    def _setCustomStyle(self, name:str, value:typing.Union[list, tuple, QtCore.Qt.PenStyle], lookup:bool=True):
        if len(self._customStyles):
            if lookup:
                if name not in self._customStyles.keys():
                    self._customStyles[name] = value
                    self.clear()
                    self._addStyles()
                    self._customStyle = value
                    self._internalStyle = value
                    self.setCurrentIndex(self.count()-1)
                else:
                    i = [k for k in self._customStyles.keys()].index(name)
                    self._internalStyle = self._customStyles[name]
                    self._customStyle = self._internalStyle
                    self.setCurrentIndex(i+1)
                
                return
                
        self._internalStyle = value
        self._customStyle = value
        self.setItemData(0, name, QtCore.Qt.ToolTipRole)
        self.setItemData(0, self._internalStyle, PenStyleComboDelegate.ItemRoles.StrokeRole)
    
    def paintEvent(self, ev:QtGui.QPaintEvent):
        painter = QtWidgets.QStylePainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.Text))
        
        opt = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(opt) # inherited from QtWidgets.QComboBox
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, opt)
        
        frame = QtCore.QRect(self.style().subControlRect(QtWidgets.QStyle.CC_ComboBox, opt,
                                                         QtWidgets.QStyle.SC_ComboBoxEditField, self))
        
        lineRect = frame.adjusted(2, 2, -2, -2)
        
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        isSelected = (opt.state and QtWidgets.QStyle.State_Selected)
        
        #paletteBrush = comboDelegateBrush(index, QtCore.Qt.BackgroundRole).style() == QtCore.Qt.NoBrush
        
        if isSelected:
            innerColor = opt.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = opt.palette.color(QtGui.QPalette.Base)
            
        _, _, v, _ = innerColor.getHsv()
        
        if v > 128:
            penColor = QtGui.QColor(QtCore.Qt.black)
        else:
            penColor = QtGui.QColor(QtCore.Qt.white)

        path = QtGui.QPainterPath()
        path.moveTo(lineRect.x(), lineRect.y() + lineRect.height()//2)
        path.lineTo(lineRect.x()+lineRect.width(), lineRect.y() + lineRect.height()//2)
        
        penStyle = self._internalStyle

        if isinstance(penStyle, (tuple, list)):
            painter.fillPath(makeCustomPathStroke(path, penStyle, 2), penColor)
        else:
            painter.setPen(QtGui.QPen(penColor, 2, penStyle))
            painter.drawPath(path)
        #if self._internalColor.alpha() < 255 and isinstance(self._tPmap, QtGui.QPixmap):
            #painter.setBrush(QtCore.Qt.NoBrush)
            #painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
            #painter.fillRect(frame.adjusted(1, 1, -1, -1), QtGui.QBrush(self._tPmap))
            #painter.fillRect(frame.adjusted(1, 1, -1, -1), self._internalColor)
        #else:
            #painter.setBrush(QtGui.QBrush(self._internalColor))
            #painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
        painter.end()

class BrushComboDelegate(QtWidgets.QAbstractItemDelegate):
    pass

class BrushComboBox(QtWidgets.QComboBox):
    pass

