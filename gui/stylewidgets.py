import array, os, typing, numbers
from collections import OrderedDict
import numpy as np
from enum import IntEnum

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, no_sip_autoconversion)

from .painting_shared import (make_transparent_bg,
                              standardQtPenStyles,
                              standardQtPenJoinStyles,
                              standardQtPenCapStyles,
                              PenStyleType,
                              BrushStyleType,
                              customDashStyles,
                              standardQtGradientPresets,
                              standardQtGradientSpreads,
                              standardQtGradientTypes,
                              validQtGradientTypes,
                              standardQtBrushStyles,
                              standardQtBrushPatterns,
                              standardQtBrushGradients,
                              standardQtBrushTextures,
                              standardPalette, standardPaletteDict, svgPalette,
                              getPalette, paletteQColors, paletteQColor, 
                              standardQColor, svgQColor, mplColors,
                              qtGlobalColors,
                              makeCustomPathStroke,
                              comboDelegateBrush,)

from .quickdialog import QuickDialog
from .gradientwidgets import GradientDialog

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class PenComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("PenRole", QtCore.Qt.UserRole +1),
                                                  ], 
                        module=__name__, qualname="PenComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="PenComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
        self._styling = "stroke"
        
    @property
    def styling(self) -> str:
        return self._styling
    
    @styling.setter
    def styling(self, value:str):
        if isinstance(value, str) and value.lower() in ("cap", "join", "stroke"):
            self._styling = value

    #@no_sip_autoconversion(QtCore.QVariant)
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):
        isSelected = (option.state and QtWidgets.QStyle.State_Selected)
        
        paletteBrush = comboDelegateBrush(index, QtCore.Qt.BackgroundRole).style() == QtCore.Qt.NoBrush
        
        if isSelected:
            innerColor = option.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = option.palette.color(QtGui.QPalette.Base)
            
        penColor = option.palette.color(QtGui.QPalette.WindowText)

        #_, _, v, _ = innerColor.getHsv()
        
        #if v > 128:
            #penColor = QtGui.QColor(QtCore.Qt.black)
        #else:
            #penColor = QtGui.QColor(QtCore.Qt.white)

        #### Draw item widget
        opt = QtWidgets.QStyleOptionViewItem(option)
        opt.showDecorationSelected=True
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)
        
        innerRect = option.rect.adjusted(self.LayoutMetrics.FrameMargin,
                                         self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin)
        
        tmpRenderHints = painter.renderHints()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        #### Draw stroke/cap/join
        lineRect = innerRect.adjusted(2, 2, -2, -2)

        style = index.data(self.ItemRoles.PenRole) # NOTE:2021-05-15 21:18:24Q QVariant
        
        path = QtGui.QPainterPath()
            
        if self._styling == "stroke":
            path.moveTo(lineRect.x(), lineRect.y() + lineRect.height()//2)
            path.lineTo(lineRect.x()+lineRect.width(), lineRect.y() + lineRect.height()//2)
            
            if style is None: # request custom stroke
                # revert painter & return
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(innerColor)
                painter.drawRoundedRect(innerRect, 2, 2)
                
                if paletteBrush:
                    if isSelected:
                        textColor = option.palette.color(QtGui.QPalette.HighlightedText)
                    else:
                        textColor = option.palette.color(QtGui.QPalette.Text)
                else:
                    _, _, v, _ = innerColor.getHsv()
                    if v > 128:
                        textColor = QtGui.QColor(QtCore.Qt.black)
                    else:
                        textColor = QtGui.QColor(QtCore.Qt.white)
                        
                if textColor.isValid():
                    painter.setPen(textColor)
                    painter.drawText(innerRect.adjusted(1, 1, -1, -1), QtCore.Qt.AlignCenter, "Customize ...")
    
                
                
                painter.setRenderHints(tmpRenderHints)
                painter.setBrush(QtCore.Qt.NoBrush)
                return
        
            elif isinstance(style, (tuple, list)):# custom stroke
                pen = QtGui.QPen(penColor, 2, style=QtCore.Qt.CustomDashLine)
                pen.setDashPattern(style)
                painter.setPen(pen)
                
            else:
                painter.setPen(QtGui.QPen(penColor, 2, style=style)) # avoid style = None
                
        
        elif self._styling == "cap":
            path.moveTo(lineRect.x() + lineRect.width()//4, 
                        lineRect.y() + lineRect.height()//2)
            
            path.lineTo(lineRect.x() + 3*lineRect.width()//4, 
                        lineRect.y() + lineRect.height()//2)

            painter.setPen(QtGui.QPen(penColor, 6, cap=style))
        
        elif self._styling == "join":
            path.moveTo(lineRect.x() + lineRect.width()//4,
                        lineRect.y() + 3*lineRect.height()//4)
            path.lineTo(lineRect.x() + lineRect.width()//2,
                        lineRect.y() + lineRect.height()//4)
            path.lineTo(lineRect.x() + 3*lineRect.width()//4,
                        lineRect.y() + 3*lineRect.height()//4)
            
            painter.setPen(QtGui.QPen(penColor, 4, join=style))
            
        else:
            # revert painter & return
            painter.setRenderHints(tmpRenderHints)
            painter.setBrush(QtCore.Qt.NoBrush)
            return
        
        #### draw specific path with custom pen
        painter.drawPath(path)
        if self._styling == "stroke" and style in (0, QtCore.Qt.NoPen):
            painter.setPen(penColor)
            painter.drawText(innerRect.adjusted(1, 1, -1, -1), QtCore.Qt.AlignCenter, "No Pen")
            
        painter.setRenderHints(tmpRenderHints)
        painter.setBrush(QtCore.Qt.NoBrush)

    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        if self._styling == "join":
            return QtCore.QSize(50, 3 * option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
        
        if self._styling == "cap":
            return QtCore.QSize(50, 2 * option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
            
        else:
            return QtCore.QSize(50, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
class PenComboBox(QtWidgets.QComboBox):
    # see 
    #   qt examples/widgets/painting/pathstroke
    #   qt examples/widgets/painting/pinterpaths
    
    activated = pyqtSignal(object, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(object, name="highlighted")
    styleChanged = pyqtSignal(object, name="styleChanged")
    
    def __init__(self, style:typing.Optional[QtCore.Qt.PenStyle]=None,
                 customStyles:typing.Optional[dict]=customDashStyles, # only for custom strokes
                 styling:str = "stroke",
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        
        self._customStyles = {}
        
        if isinstance(styling, str) and styling.lower() in ("cap", "join", "stroke"):
            self._styling = styling
        else:
            self._styling = "stroke" # other acceptable values are "cap" and "join"
        
        if self._styling == "cap":
            self._styles = standardQtPenCapStyles
            self._internalStyle = QtCore.Qt.FlatCap
            
        elif self._styling == "join":
            self._styles = standardQtPenJoinStyles
            self._internalStyle = QtCore.Qt.MiterJoin
            
        else:
            self._styles = standardQtPenStyles
            if len(customStyles) and all ([isinstance(v, PenStyleType._subs_tree()[1:]) for v in customStyles]):
                self._customStyles.update(customStyles)
            self._internalStyle = QtCore.Qt.SolidLine
            
        self._customStyle = QtCore.Qt.NoPen
        
        self.setItemDelegate(PenComboDelegate(self))
        self.itemDelegate().styling = self._styling
        
        self._addStyles()
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        self.setCurrentIndex(1)
        self._slotActivated(1)
        self.setMaxVisibleItems(13)
        
    @pyqtSlot(int)
    @safeWrapper
    def _slotActivated(self, index:int):
        if self.styling == "stroke" and index == 0:
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
                            
                    self.activated[object].emit(self._internalStyle)
                    
            return

        self._internalStyle = self.itemData(index, PenComboDelegate.ItemRoles.PenRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
        self.activated[object].emit(self._internalStyle)

    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == 0:
            self._internalStyle = self._customStyle
            self.setToolTip("Custom dashes")
            return

        self._internalStyle = self.itemData(index, PenComboDelegate.ItemRoles.PenRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
    
    def _addStyles(self):
        #if all([isinstance(v, QtCore.Qt.PenStyle) for v in self._styles.values()]):
        #elif all([isinstance(v, QtCore.Qt.PenCapStyle, QtCore.Qt.PenJoinStyle) for v in self._styles.values()]):
        styles =  [(name, val) for name, val in self._styles.items()]
        
        #if self._styling in ("cap", "join"):
            #styles =  [(name, val) for name, val in self._styles.items()]

        if self._styling == "stroke":
            styles =  [(name, val) for name, val in self._styles.items() if val > QtCore.Qt.NoPen and val < QtCore.Qt.CustomDashLine]
            #styles =  [(name, val) for name, val in standardQtPenStyles.items() if val > QtCore.Qt.NoPen and val < QtCore.Qt.CustomDashLine]
        
            styles += [("No Pen", QtCore.Qt.NoPen)]
        
            styles += [(name, val) for name, val in self._customStyles.items()]
        
            self.addItem(self.tr("Custom dashes...", "@item:inlistbox Custom stroke style"))
            self.setItemData(0, "Custom dashes...", QtCore.Qt.ToolTipRole)
        
        for k, (name, val) in enumerate(styles):
            self.addItem("")
            ndx = k + 1 if self._styling == "stroke" else k
            self.setItemData(ndx, val, PenComboDelegate.ItemRoles.PenRole)
            self.setItemData(ndx, name, QtCore.Qt.ToolTipRole)
            
    def _setCustomStyle(self, name:str, value:typing.Union[list, tuple], 
                        lookup:bool=True):
        if not isinstance(value, (list, tuple)) or self._styling in ("cap", "join"):
            return
        
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
        self.setItemData(0, self._internalStyle, PenComboDelegate.ItemRoles.PenRole)
    
    @no_sip_autoconversion(QtCore.QVariant)
    def paintEvent(self, ev:QtGui.QPaintEvent):
        painter = QtWidgets.QStylePainter(self) # CAUTION Must call end() before returning
        
        #### Draw styled widget
        painter.setPen(self.palette().color(QtGui.QPalette.Text))
        
        opt = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(opt) # inherited from QtWidgets.QComboBox
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, opt)
        
        #### Draw pen
        frame = QtCore.QRect(self.style().subControlRect(QtWidgets.QStyle.CC_ComboBox, opt,
                                                         QtWidgets.QStyle.SC_ComboBoxEditField, self))
        
        lineRect = frame.adjusted(2, 2, -2, -2)
        
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        isSelected = (opt.state and QtWidgets.QStyle.State_Selected)
        
        if isSelected:
            innerColor = opt.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = opt.palette.color(QtGui.QPalette.Base)
            
        #_, _, v, _ = innerColor.getHsv()
        
        #if v > 128:
            #penColor = QtGui.QColor(QtCore.Qt.black)
        #else:
            #penColor = QtGui.QColor(QtCore.Qt.white)
            
        penColor = opt.palette.color(QtGui.QPalette.WindowText)
            
        path = QtGui.QPainterPath()

        if self.styling == "stroke":
            path.moveTo(lineRect.x(), lineRect.y() + lineRect.height()//2)
            path.lineTo(lineRect.x()+lineRect.width(), lineRect.y() + lineRect.height()//2)
            
            if isinstance(self._internalStyle, (tuple, list)) and all([isinstance(v, numbers.Real) for v in self._internalStyle]):
                # NOTE: 2021-05-23 09:05:17 alternative also works; don't delete next line
                #painter.fillPath(makeCustomPathStroke(path, self._internalStyle, 2), penColor)
                pen = QtGui.QPen(penColor, 2, style=QtCore.Qt.CustomDashLine)
                pen.setDashPattern(self._internalStyle)
                painter.setPen(pen)
            else:
                painter.setPen(QtGui.QPen(penColor, 2, style=self._internalStyle))
                
        elif self.styling == "cap":
            path.moveTo(lineRect.x() + lineRect.width()//4, 
                        lineRect.y() + lineRect.height()//2)
            
            path.lineTo(lineRect.x() + 3*lineRect.width()//4, 
                        lineRect.y() + lineRect.height()//2)
            
            painter.setPen(QtGui.QPen(penColor, 6, cap=self._internalStyle))
            
        elif self.styling == "join":
            path.moveTo(lineRect.x() + lineRect.width()//4,
                        lineRect.y() + 3*lineRect.height()//4)
            path.lineTo(lineRect.x() + lineRect.width()//2,
                        lineRect.y() + lineRect.height()//4)
            path.lineTo(lineRect.x() + 3*lineRect.width()//4,
                        lineRect.y() + 3*lineRect.height()//4)
                
            painter.setPen(QtGui.QPen(penColor, 4, join=self._internalStyle))
            
        else:
            painter.end()
            return
            
        painter.drawPath(path)
        
        if self.styling == "stroke" and self._internalStyle in (0, QtCore.Qt.NoPen):
            painter.setPen(penColor)
            painter.drawText(frame.adjusted(1, 1, -1, -1), QtCore.Qt.AlignCenter, "No Pen")
            
        painter.end()

    @property
    def styling(self) -> str:
        return self._styling
    
    @styling.setter
    def styling(self, value:str):
        if isinstance(value, str) and value.lower() in ("cap", "join", "stroke"):
            self._styling = value
            self.itemDelegate().styling = value
        
class BrushComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("BrushRole", QtCore.Qt.UserRole +1)], 
                        module=__name__, qualname="BrushComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="BrushComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
        
    #@no_sip_autoconversion(QtCore.QVariant)
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):

        isSelected = (option.state and QtWidgets.QStyle.State_Selected)
        
        paletteBrush = comboDelegateBrush(index, QtCore.Qt.BackgroundRole).style() == QtCore.Qt.NoBrush

        if isSelected:
            innerColor = option.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = option.palette.color(QtGui.QPalette.Base)
            
        penColor = option.palette.color(QtGui.QPalette.WindowText)

        #_, _, v, _ = innerColor.getHsv()
        
        #if v > 128:
            #penColor = QtGui.QColor(QtCore.Qt.black)
        #else:
            #penColor = QtGui.QColor(QtCore.Qt.white)

        #### Draw item widget
        opt = QtWidgets.QStyleOptionViewItem(option)
        opt.showDecorationSelected=True
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)
        
        innerRect = option.rect.adjusted(self.LayoutMetrics.FrameMargin,
                                         self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin)
        
        tmpRenderHints = painter.renderHints()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        #painter.setPen(penColor)
        #painter.setPen(QtCore.Qt.NoPen)
        #painter.setBrush(innerColor)
        #painter.drawRoundedRect(innerRect, 2, 2)
        
        #### Draw brush
        brushStyle = index.data(self.ItemRoles.BrushRole)
        print("BrushComboDelegate.paint brushStyle", brushStyle, "(type %s)" % type(brushStyle))
        painter.setPen(QtCore.Qt.transparent)
        if isinstance(brushStyle, BrushStyleType._subs_tree()[1:]):
            #print("brushSyle", brushStyle)
            if brushStyle in standardQtBrushPatterns.values():
                brush = QtGui.QBrush(brushStyle)
                brush.setColor(penColor) 
            elif brushStyle in standardQtBrushGradients.values():
                brush = QtGui.QBrush(QtGui.QGradient(standardQtGradientPresets["AboveTheSky"]))
                #if brushStyle QtCore.Qt.LinearGradientPattern:
                    #gradient = QtGui.QLinearGradient()
                # TODO: 2021-05-20 13:17:00
                # set a default preset & call GUI to choose one and/or edit gradient
                # then construct a QGradient on that and construct the brush on that
                #return
            elif brushStyle in standardQtBrushTextures.values():
                brush = QtGui.QBrush(make_transparent_bg(strong=True))
                # TODO: 2021-05-20 13:17:55
                # set a default texture & call GUI to choose an image or pixmap
                # then create a brush on that!
                #return
            else:
                brush = QtGui.QBrush(QtCore.Qt.NoBrush)
                
            painter.setBrush(brush)
        elif isinstance(brushStyle, (QtGui.QPixmap, QtGui.QImage, QtGui.QGradient, QtGui.QBrush)):
            brush = QtGui.QBrush(brushStyle)
            
        else:
            painter.setBrush(QtCore.Qt.NoBrush)
            
        painter.drawRoundedRect(innerRect, 2, 2)
          
        #### Reset painter
        painter.setRenderHints(tmpRenderHints)
        painter.setBrush(QtCore.Qt.NoBrush)

    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        return QtCore.QSize(50, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
class BrushComboBox(QtWidgets.QComboBox):
    # NOTE: 2021-05-20 21:22:12
    # brush gradients: see 
    #   qt examples/widgets/painting/gradients
    #   qt examples/widgets/painting/pathstroke
    #   qt examples/widgets/painting/painterpaths
    activated = pyqtSignal(object, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(object, name="highlighted")
    styleChanged = pyqtSignal(object, name="styleChanged")
    
    def __init__(self, style:typing.Optional[typing.Union[BrushStyleType, QtGui.QPixmap,QtGui.QImage, QtGui.QGradient]]=None,
                  customStyles:typing.Optional[dict]=None,
                  restrict:typing.Optional[str]=None,
                  parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._customStyles = {}
        self._brushes = OrderedDict([(name, val) for name, val in standardQtBrushPatterns.items() if val > 0])
        #if isinstance(style, BrushStyleType._subs_tree()[1:]):
        if isinstance(style, BrushStyleType._subs_tree()):
            self._customStyle = style
        elif isinstance(style, (QtGui.QPixmap, QtGui.QImage, QtGui.QGradient)):
            self._customStyle = brush(style)
        else:
            self._customStyle = QtCore.Qt.NoBrush
        
        self._internalStyle = self._customStyle
        
        if self._customStyle is not QtCore.Qt.NoBrush:
            self._brushes["Custom"] = self._customStyle
            
        self._brushes.update(standardQtBrushPatterns)
        
        brushTypes = tuple(list(BrushStyleType._subs_tree()[1:]) + [QtGui.QPixmap, QtGui.QImage, QtGui.QGradient])
        
        if isinstance(customStyles, dict) and len(customStyles) and all([isinstance(v, brushTypes) for v in customStyles.values()]):
            self._brushes.update(customStyles)
               
        self.setItemDelegate(BrushComboDelegate(self))
        
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        self.setMaxVisibleItems(13)
        self._gradient_brush_item_index = -1
        self._n_brush_styles = 0
        self._addStyles()
        self.setCurrentIndex(0)
        self._slotActivated(0)

    def paintEvent(self, ev:QtGui.QPaintEvent):
        print("BrushComboBox.paintEvent internal style", self._internalStyle, "(type %s)" % type(self._internalStyle))
        painter = QtWidgets.QStylePainter(self)

        #### Draw styled widget
        painter.setPen(self.palette().color(QtGui.QPalette.Text))
        
        opt = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(opt) # inherited from QtWidgets.QComboBox
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, opt)
        
        #### Draw brush
        frame = QtCore.QRect(self.style().subControlRect(QtWidgets.QStyle.CC_ComboBox, opt,
                                                         QtWidgets.QStyle.SC_ComboBoxEditField, self))
        
        isSelected = (opt.state and QtWidgets.QStyle.State_Selected)
        
        if isSelected:
            innerColor = opt.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = opt.palette.color(QtGui.QPalette.Base)
            
        penColor =  opt.palette.color(QtGui.QPalette.WindowText)
        #_, _, v, _ = innerColor.getHsv()
        
        #if v > 128:
        #else:
            #penColor = QtGui.QColor(QtCore.Qt.white)
            
        #_, _, v, _ = innerColor.getHsv()
        
        #if v > 128:
            #penColor = QtGui.QColor(QtCore.Qt.black)
        #else:
            #penColor = QtGui.QColor(QtCore.Qt.white)
            
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.transparent)
        #painter.setPen(penColor)
        if isinstance(self._internalStyle, BrushStyleType._subs_tree()[1:]):
            brush = QtGui.QBrush(self._internalStyle)
            #brush.setColor(QtCore.Qt.black) 
            brush.setColor(penColor) 
            painter.setBrush(brush)
            
        elif isinstance(self._internalStyle, (QtGui.QPixmap, QtGui.QImage, QtGui.QGradient, QtGui.QBrush)):
            brush = QtGui.QBrush(self._internalStyle)
            #brush.setColor(penColor)
            painter.setBrush(brush)
        else:
            #painter.setPen(QtCore.Qt.transparent)
            painter.setBrush(QtCore.Qt.NoBrush)
            
        painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
        painter.end()
        
    @pyqtSlot(int)
    @safeWrapper
    def _slotActivated(self, index:int):
        #print("BrushComboBox._slotActivated: index =", index)
        #print("BrushComboBox._slotActivated: _n_brush_styles =", self._n_brush_styles)
        #print("BrushComboBox._slotActivated: _gradient_brush_item_index =", self._gradient_brush_item_index)
        if self.count() == 0:
            return
        #if index == 0:
        #if index == self.count()-1:
        if index == self._n_brush_styles:
            filePathName, _ = QtWidgets.QFileDialog.getOpenFileName(self, caption="Open image or pixmap file",
                                                             filter="Images (*.png *.xpm *.jpg *.jpeg *.gif *.tif *.tiff);;Vector drawing (*.svg);; All files (*.*)")
            if len(filePathName) == 0:
                return
            
            _, fileName = os.path.split(filePathName)

            if len(fileName) == 0:
                return
            
            name, ext = os.path.splitext(fileName)
            val = None
            # FIXME: 2021-05-19 11:15:43 TODO
            # automatically recognize bitmaps and set val to a QBitmap
            if len(ext):
                if ext in (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".gif"):
                    #load image
                    img = QtGui.QImage(filePathName)
                    if img.isNull():
                        return
                    
                    val = QtGui.QBrush(img)
                    
                elif ext in (".xmp", ".bpm"):
                    #load pixmap
                    pix = QtGui.QPixmap(filePathName)
                    if pix.isNull():
                        return
                    val = QtGui.QBrush(pix)
                    
                elif ext in (".svg"):
                    # load svg
                    renderer = QtSvg.QSvgRenderer()
                    image = QtGui.QImage()
                    painter = QtGui.QPainter(image)
                    renderer.render(painter)
                    if not image.isNull():
                        pix = QtGui.QPixmap.fromImage(image)
                        if pix.isNull():
                            return
                        val = QtGui.QBrush(pix)
                else:
                    return
            else:
                return # FIXME 2021-05-19 11:14:48 what to do with extension-less files?
                
            if val is not None:
                self._setCustomStyle(name, val, True)
                self.activated[object].emit(self._internalStyle)
                
            return
        
        elif index == self._gradient_brush_item_index:
            dlg = GradientDialog(parent=self)
            dlg.finished[int].connect(self._slotUpdateGradientBrush)
            dlg.open()
            #gw = GradientWidget()
            #gw.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            #gdlg.addWidget(gw)
            #gdlg.finished[int].connect(self._slotUpdateGradientBrush)
            #gdlg.open()
            
        
        self._internalStyle = self.itemData(index, BrushComboDelegate.ItemRoles.BrushRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
        self.activated[object].emit(self._internalStyle)
            
    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == self._n_brush_styles:
            self._internalStyle = self._customStyle
            self.setToolTip("Custom image")
            return
        
        if index == self._gradient_brush_item_index:
            self._internalStyle = self._customStyle
            self.setToolTip("Gradient")
            return
        
        self._internalStyle = self.itemData(index, BrushComboDelegate.ItemRoles.BrushRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
        
    @pyqtSlot(int)
    @safeWrapper
    def _slotUpdateGradientBrush(self, value:typing.Union[int, QtWidgets.QDialog.DialogCode]):
        dlg = self.sender()
        if isinstance(dlg, GradientDialog) and value == QtWidgets.QDialog.Accepted:
            gradient = dlg.gw.gradient
            
            if len(gradient.stops()) > 1:
                brush = QtGui.QBrush(gradient)
                self._setCustomStyle("Gradient", brush, True)
                self.update()
                self.activated[object].emit(self._internalStyle)
        
    def _addStyles(self):
        styles =  [(name, val) for name, val in standardQtBrushPatterns.items() if val > 0]
        styles += [("No Brush", QtCore.Qt.NoBrush)]
        styles += [("Gradient ...", QtCore.Qt.NoBrush)]
        self._gradient_brush_item_index = len(styles)-1
        styles += [(name, val) for name , val in self._customStyles.items()]
        self._n_brush_styles = len(styles)
        
        #ndx = 0
        for k, (name, val) in enumerate(styles):
            self.addItem("")
            self.setItemData(k, val, BrushComboDelegate.ItemRoles.BrushRole)
            self.setItemData(k, name, QtCore.Qt.ToolTipRole)
            #ndx = k
        
        self.addItem(self.tr("Custom pixmap...", "@item:inlistbox Custom pixmap brush"))
        #ndx += 1
        self.setItemData(len(styles), "Custom pixmap...", QtCore.Qt.ToolTipRole)
        
        #self.addItem(self.tr("Custom brush...", "@item:inlistbox Custom brush style"))
        #self.setItemData(0, "Custom brush...", QtCore.Qt.ToolTipRole)
        
        #styles =  [(name, val) for name, val in standardQtBrushPatterns.items() if val > 0]
        #styles += [("No Brush", QtCore.Qt.NoBrush)]
        #styles += [("Gradient ...", QtCore.Qt.NoBrush)]
        #styles += [(name, val) for name , val in self._customStyles.items()]
        
        #for k, (name, val) in enumerate(styles):
            #self.addItem("")
            #self.setItemData(k+1, val, BrushComboDelegate.ItemRoles.BrushRole)
            #self.setItemData(k+1, name, QtCore.Qt.ToolTipRole)
        

    def _setCustomStyle(self, name:str, value:typing.Union[BrushStyleType, QtGui.QPixmap, QtGui.QImage, QtGui.QGradient], lookup:bool=True):
        if not isinstance(value, BrushStyleType._subs_tree()[1:]) and not isinstance(value, (QtGui.QPixmap, QtGui.QImage, QtGui.QGradient)):
            return
        
        if len(self._customStyles):
            if lookup:
                if name not in self._customStyles.keys():
                    self._customStyles[name] = value
                    self.clear()
                    self._addStyles()
                    self._customStyle = value
                    self._internalStyle = value
                    self._setCurrentIndex(self.count()-1)
                else:
                    i = [k for k in self._customStyles.key()].index(name)
                    self._internalStyle = self._customStyles[name]
                    self._customStyle = self._internalStyle
                    self.setCurrentIndex(i+1)
                    
                return
            
        self._internalStyle = value
        self._customStyle = value
        self.setItemData(0, name, QtCore.Qt.ToolTipRole)
        self.setItemData(0, self._internalStyle, BrushComboDelegate.ItemRoles.BrushRole)
        #self.activated[object].emit(self._internalStyle)
        
            
        
