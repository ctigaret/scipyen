import array, os, typing, numbers
import numpy as np
from collections import OrderedDict
from enum import IntEnum
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg
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

standardQtPenStyles = OrderedDict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenStyle) and val < 10],
                           key = lambda x: x[1]))

standardQtPenJoinStyles = OrderedDict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenJoinStyle) and val <= 256],
                           key = lambda x: x[1]))

standardQtPenCapStyles = OrderedDict(sorted([(name,val) for name, val in vars(QtCore.Qt).items() if isinstance(val, QtCore.Qt.PenCapStyle) and val <= 32],
                           key = lambda x: x[1]))

PenStyleType = typing.Union[tuple, list, QtCore.Qt.PenStyle]

customDashStyles = {"Custom": [10., 5., 10., 5., 10., 5., 1., 5., 1., 5., 1., 5.]}

standardQtGradientPresets = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Preset)]))

standardQtGradientSpreads = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Spread)]))

standardQtGradientTypes = OrderedDict(sorted([(name, value) for name, value in vars(QtGui.QGradient).items() if isinstance(value, QtGui.QGradient.Type) and value < 3],
                                      key = lambda x: x[1]))

standardQtBrushStyles = OrderedDict(sorted([(name, value) for name, value in vars(QtCore.Qt).items() if isinstance(value, QtCore.Qt.BrushStyle)],
                                           key = lambda x: x[1]))

standardQtBrushPatterns = OrderedDict(sorted([(name, value) for name, value in standardQtBrushStyles.items() if all([s not in name for s in ("Gradient", "Texture")])],
                                           key = lambda x: x[1]))

standardQtBrushGradients = OrderedDict(sorted([(name, value) for name, value in standardQtBrushStyles.items() if "Gradient" in name],
                                           key = lambda x: x[1]))

standardQtBrushTextures = OrderedDict(sorted([(name, value) for name, value in standardQtBrushStyles.items() if "Texture" in name],
                                           key = lambda x: x[1]))


# NOTE: 2021-05-19 10:00:27
# Iterate through the types INSIDE this union with BrushStyleType._subs_tree()[1:]
# _subs_tree() returns a tuple of types where the first element is always
# typing.Union, so we leave it out.
BrushStyleType = typing.Union[QtCore.Qt.BrushStyle, QtGui.QGradient,
                              QtGui.QBitmap, QtGui.QPixmap, QtGui.QImage]

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
    ItemRoles = IntEnum(value="ItemRoles", names=[("PenRole", QtCore.Qt.UserRole +1),
                                                  ], 
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

        style = index.data(self.ItemRoles.PenRole) # NOTE:2021-05-15 21:18:24Q QVariant
        
        path = QtGui.QPainterPath()
        
        if isinstance(style, (QtCore.Qt.PenStyle, tuple, list, QtCore.Qt.PenCapStyle, QtCore.Qt.PenJoinStyle)):
            #paletteBrush = False
            tmpRenderHints = painter.renderHints()
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(innerColor)
            painter.drawRoundedRect(innerRect, 2, 2)
            if isinstance(style, (QtCore.Qt.PenStyle, tuple, list)):
                path.moveTo(lineRect.x(), lineRect.y() + lineRect.height()//2)
                path.lineTo(lineRect.x()+lineRect.width(), lineRect.y() + lineRect.height()//2)
            
                if isinstance(style, (tuple, list)):# custom stroke
                    pen = QtGui.QPen(penColor, 2, style=QtCore.Qt.CustomDashLine)
                    pen.setDashPattern(style)
                    
                    #painter.fillPath(makeCustomPathStroke(path, style, 2), penColor)
                else:
                    painter.setPen(QtGui.QPen(penColor, 2, style=style))
                    #painter.drawPath(path)
            
            elif isinstance(style, QtCore.Qt.PenCapStyle):
                path.moveTo(lineRect.x() + lineRect.width()//4, 
                            lineRect.y() + lineRect.height()//2)
                
                path.lineTo(lineRect.x() + 3*lineRect.width()//4, 
                            lineRect.y() + lineRect.height()//2)

                painter.setPen(QtGui.QPen(penColor, 2, cap=style))
            
            elif isinstance(style, QtCore.Qt.PenJoinStyle):
                path.moveTo(lineRect.x() + lineRect.width()//4,
                            lineRect.y() + 3*lineRect.height()//4)
                path.lineTo(lineRect.x() + lineRect.width()//2,
                            lineRect.y() + lineRect.height()//4)
                path.lineTo(lineRect.x() + 3*lineRect.width()//4,
                            lineRect.y() + 3*lineRect.height()//4)
                
                painter.setPen(QtGui.QPen(penColor, 2, join=style))
            
            painter.drawPath(path)
            painter.setRenderHints(tmpRenderHints)
            painter.setBrush(QtCore.Qt.NoBrush)

    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        return QtCore.QSize(50, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
class PenStyleComboBox(QtWidgets.QComboBox):
    # FIXME/TODO/ see qt examples/widgets/painting/pathstroke
    activated = pyqtSignal(object, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(object, name="highlighted")
    styleChanged = pyqtSignal(object, name="styleChanged")
    
    def __init__(self, styles:dict=standardQtPenStyles,
                 customStyles:typing.Optional[dict]=customDashStyles,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._styles = styles
        self._customStyles = {}
        #if isinstance(styling, str) and styling.lower() in ("cap", "join", "stroke"):
            #self._styling = styling
        #else:
            #self._styling = "stroke" # other acceptable values are "cap" and "join"
        
        #if isinstance(style, QtCore.Qt.PenStyle):
            #self._internalStyle = style
            #self._customStyle = style
        #else:
        self._internalStyle = QtCore.Qt.SolidLine
        self._customStyle = QtCore.Qt.NoPen
        
        if all([isinstance(v, QtCore.Qt.PenStyle) for v in self._styles.values()]):
            if len(customStyles) and all ([isinstance(v, PenStyleType._subs_tree()[1:]) for v in customStyles]):
                self._customStyles.update(customStyles)
            
        self.setItemDelegate(PenStyleComboDelegate(self))
        #self.itemDelegate().styling = self._styling
        
        self._addStyles()
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        self.setCurrentIndex(1)
        self._slotActivated(1)
        self.setMaxVisibleItems(13)
        
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
                            
                    self.activated[object].emit(self._internalStyle)
                    
            return

        self._internalStyle = self.itemData(index, PenStyleComboDelegate.ItemRoles.PenRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
        self.activated[object].emit(self._internalStyle)

    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == 0:
            self._internalStyle = self._customStyle
            self.setToolTip("Custom dashes")
            return

        self._internalStyle = self.itemData(index, PenStyleComboDelegate.ItemRoles.PenRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
    
    def _addStyles(self):
        if all([isinstance(v, QtCore.Qt.PenStyle) for v in self._styles.values()]):
            self.addItem(self.tr("Custom dashes...", "@item:inlistbox Custom stroke style"))
            self.setItemData(0, "Custom dashes...", QtCore.Qt.ToolTipRole)
        
            styles =  [(name, val) for name, val in self._styles.items() if val > QtCore.Qt.NoPen and val < QtCore.Qt.CustomDashLine]
            #styles =  [(name, val) for name, val in standardQtPenStyles.items() if val > QtCore.Qt.NoPen and val < QtCore.Qt.CustomDashLine]
        
            styles += [("No Pen", QtCore.Qt.NoPen)]
        
            styles += [(name, val) for name, val in self._customStyles.items()]
            
        elif all([isinstance(v, QtCore.Qt.PenCapStyle, QtCore.Qt.PenJoinStyle) for v in self._styles.values()]):
            styles =  [(name, val) for name, val in self._styles.items()]

        else:
            return
        
        for k, (name, val) in enumerate(styles):
            self.addItem("")
            self.setItemData(k + 1, val, PenStyleComboDelegate.ItemRoles.PenRole)
            self.setItemData(k + 1, name, QtCore.Qt.ToolTipRole)
            
    def _setCustomStyle(self, name:str, value:typing.Union[list, tuple, QtCore.Qt.PenStyle], 
                        lookup:bool=True):
        if not isinstance(value, (list, tuple, QtCore.Qt.PenStyle)):
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
                
                #self.activated[object].emit(self._internalStyle)
                
                return
                
        self._internalStyle = value
        self._customStyle = value
        self.setItemData(0, name, QtCore.Qt.ToolTipRole)
        self.setItemData(0, self._internalStyle, PenStyleComboDelegate.ItemRoles.PenRole)
        #self.activated[object].emit(self._internalStyle)
    
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

        #if self._styling == "stroke":
        print(type(self._internalStyle))
        if isinstance(self._internalStyle, (QtCore.Qt.PenStyle, tuple, list)):
            path.moveTo(lineRect.x(), lineRect.y() + lineRect.height()//2)
            path.lineTo(lineRect.x()+lineRect.width(), lineRect.y() + lineRect.height()//2)
            
            #penStyle = self._internalStyle
            
            if isinstance(self._internalStyle, (tuple, list)) and all([isinstance(v, numbers.Real) for v in penStyle]):
                #painter.fillPath(makeCustomPathStroke(path, self._internalStyle, 2), penColor)
                pen = QtGui.QPen(penColor, 2, style=QtCore.Qt.CustomDashLine)
                pen.setDashPattern(self._internalStyle)
                painter.setPen(pen)
            else:
                painter.setPen(QtGui.QPen(penColor, 2, style=self._internalStyle))
                #painter.drawPath(path)

            #if isinstance(penStyle, (tuple, list)):
                #painter.fillPath(makeCustomPathStroke(path, penStyle, 2), penColor)
            #else:
                #painter.setPen(QtGui.QPen(penColor, 2, style=penStyle))
                #painter.drawPath(path)
                
        #elif self.styling == "cap":
        elif isinstance(self._internalStyle, QtCore.Qt.PenCapStyle):# self.styling == "cap":
            path.moveTo(lineRect.x() + lineRect.width()//4, 
                        lineRect.y() + lineRect.height()//2)
            
            path.lineTo(lineRect.x() + 3*lineRect.width()//4, 
                        lineRect.y() + lineRect.height()//2)
            
            #capStyle = self._internalStyle

            painter.setPen(QtGui.QPen(penColor, 2, cap=self._internalStyle))
            #painter.drawPath(path)
            
        elif isinstance(self._internalStyle, QtCore.Qt.PenJoinStyle):
            path.moveTo(lineRect.x() + lineRect.width()//4,
                        lineRect.y() + 3*lineRect.height()//4)
            path.lineTo(lineRect.x() + lineRect.width()//2,
                        lineRect.y() + lineRect.height()//4)
            path.lineTo(lineRect.x() + 3*lineRect.width()//4,
                        lineRect.y() + 3*lineRect.height()//4)
                
            #joinStyle = self._internalStyle

            painter.setPen(QtGui.QPen(penColor, 2, join=self._internalStyle))
            
        painter.drawPath(path)
            
        painter.end()

    #@property
    #def styling(self) -> str:
        #return self._styling
    
    #@styling.setter
    #def styling(self, value:str):
        #if isinstance(value, str) and value.lower() in ("cap", "join", "stroke"):
            #self._styling = value
            #self.itemDelegate().styling = value
        
class BrushStyleComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("BrushRole", QtCore.Qt.UserRole +1)], 
                        module=__name__, qualname="BrushStyleComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="BrushStyleComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
        
    @no_sip_autoconversion(QtCore.QVariant)
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):

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
        
        brushStyle = index.data(self.ItemRoles.BrushRole)
        tmpRenderHints = painter.renderHints()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.transparent)
        if isinstance(brushStyle, BrushStyleType._subs_tree()[1:]):
            brush = QtGui.QBrush(brushStyle)
            brush.setColor(QtCore.Qt.black) # makes a difference only for patterns and bitmaps
            painter.setBrush(brush)
        else:
            painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(innerRect, 2, 2)
            
        painter.setRenderHints(tmpRenderHints)
        painter.setBrush(QtCore.Qt.NoBrush)

    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        return QtCore.QSize(50, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
class BrushStyleComboBox(QtWidgets.QComboBox):
    activated = pyqtSignal(object, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(object, name="highlighted")
    styleChanged = pyqtSignal(object, name="styleChanged")
    
    def __init__(self, style:typing.Optional[BrushStyleType]=None,
                  customStyles:typing.Optional[dict]=None,
                  restrict:typing.Optional[str]=None,
                  parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._customStyles = {}
        if isinstance(style, BrushStyleType._subs_tree()[1:]):
            self._internalStyle = style
            self._customStyle = style
        else:
            self._internalStyle = QtCore.Qt.NoBrush
            self._customStyle = QtCore.Qt.NoBrush
        
        if len(customStyles) and all([isinstance(v, BrushStyleType._subs_tree()[1:]) for v in customStyles.values()]):
            self._customStyles.update(customStyles)
        
        self.setItemDelegate(BrushStyleComboDelegate(self))

    def paintEvent(self, ev:QtGui.QPaintEvent):
        painter = QtWidgets.QStylePainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.Text))
        
        opt = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(opt) # inherited from QtWidgets.QComboBox
        painter.drawComplexControl(QtWidgets.QStyle.CC_ComboBox, opt)
        
        frame = QtCore.QRect(self.style().subControlRect(QtWidgets.QStyle.CC_ComboBox, opt,
                                                         QtWidgets.QStyle.SC_ComboBoxEditField, self))
        
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.transparent)
        if isinstance(self._internalStyle, BrushStyleType._subs_tree()[1:]):
            brush = QtGui.QBrush(self._internalStyle)
            brush.setColor(QtCore.Qt.black) 
            painter.setBrush(brush)
        else:
            painter.setBrush(QtCore.Qt.NoBrush)
            
        painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
        painter.end()
        
    @pyqtSlot(int)
    @safeWrapper
    def _slotActivated(slf, index:int):
        if index == 0:
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
                    val = QtGui.QImage(filePathName)
                    if val.isNull():
                        return
                elif ext in (".xmp", ".bpm"):
                    #load pixmap
                    val = QtGui.QPixmap(filePathName)
                    if val.isNull():
                        return
                elif ext in (".svg"):
                    # load svg
                    renderer = QtSvg.QSvgRenderer()
                    image = QtGui.QImage()
                    painter = QtGui.QPainter(image)
                    renderer.render(painter)
                    if not image.isNull():
                        val = QtGui.QPixmap.fromImage(image)
                        if val.isNull():
                            return
                else:
                    return
            else:
                return # FIXME 2021-05-19 11:14:48 what to do with extension-less files?
                
            if val is not None:
                self._setCustomStyle(name, val, True)
                self.activated[object].emit(self._internalStyle)
                
            return
        
        self._internalStyle = self.itemData(index, BrushStyleComboDelegate.ItemRoles.BrushRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
        self.activated[object].emit(self._internalStyle)
            
    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == 0:
            self._intenalStyle = self._customStyle
            self.setToolTip("Custom brush")
            return
        
        self._internalStyle = self.itemData(index, BrushStyleComboDelegate.ItemRoles.BrushRole)
        self.setToolTip(self.itemData(index, QtCore.Qt.ToolTipRole))
        
    def _addStyles(self):
        self.addItem(self.tr("Custom brush...", "@item:inlistbox Custom brush style"))
        self.setItemData(0, "Custom brush...", QtCore.Qt.ToolTipRole)
        
        styles =  [(name, val) for name, val in standardQtBrushStyles.items() if value > 0]
        styles += ["No Brush", QtCore.Qt.NoBrush]
        styles += [(name, val) for name , val in self._customStyles.items()]
        
        for k, (name, val) in enumerate(styles):
            self.addItem("")
            self.setItemData(k+1, val, BrushStyleComboDelegate.ItemRoles.BrushRole)
            self.setItemData(k+1, name, QtCore.Qt.ToolTipRole)
        

    def _setCustomStyle(self, name:str, value:BrushStyleType, lookup:bool=True):
        if not isinstance(value, BrushStyleType._subs_tree()[1:]):
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
                    
                #self.activated[object].emit(self._internalStyle)
                    
                return
            
        self._internalStyle = value
        self._customStyle = value
        self.setItemData(0, name, QtCore.Qt.ToolTipRole)
        self.setItemData(0, self._internalStyle, BrushStyleComboDelegate.ItemRoles.BrushRole)
        #self.activated[object].emit(self._internalStyle)
        
            
        
