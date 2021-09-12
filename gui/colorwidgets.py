"""KColorButton and KColorCombo from KWidgetsAddons framework 'translated' here.

Translation and additional code (C) 2021 Cezar M. Tigaret <cezar.tigaret@gmail.com>

What is new/different from the KWidgetsAddons classes:
    1) ColorToolButton - is the QToolButton version of ColorPushButton
    2) Both ColorPushButton and ColorToolButton inherit their functionality from
       ColorButtonMixin (which does all the work)
    3) alpha channel optional in color chooser dialog
    4) option to keep alpha value when a color is dropped or pasted onto the widget
    5) option to have a light chequered pattern for transparent colors
    6) Qt::GlobalColors enum in the Qt's Core module (wrapped as a sip.enumtype
       in PyQt5) is represented as the 'qtGlobalColors' dictionary in this 
       module's namespace.
       
       This allows a reverse lookup of a global color enum key (as a str) based 
       on its int value.
       
       Useful to retrieve the Qt enum object as a symbol given its int value.
       For example, given PyQt5.QtCore imported as QtCore:
       reverse_dict(qtGlobalColors)[7] -> 'QtCore.Qt.red'
       
       and 
       
       eval(reverse_dict(qtGlobalColors)[7]) -> 7
       
       Furthermore this can be used to populate a combo box (see ColorCombo); to
       retrieve the actual color name, use (following the example above):
       
       reverse_dict(qtGlobalColors)[7].split('.')[-1] -> 'red'
    
    NOTE: 2021-05-17 14:00:51
    Color palettes moves to gui.scipyen_colormaps module
"""
import os, typing
from pprint import pprint
import numpy as np

from enum import IntEnum
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, no_sip_autoconversion)
from core.utilities import reverse_mapping_lookup
from .painting_shared import (standardPalette, standardPaletteDict, svgPalette,
                              getPalette, paletteQColor, 
                              standardQColor, svgQColor, mplColors, qtGlobalColors, 
                              canDecode, populateMimeData, fromMimeData,
                              createDrag, make_transparent_bg, make_checkers,
                              comboDelegateBrush,ColorPalette)

from .scipyen_colormaps import qcolor, get_name_color


__module_path__ = os.path.abspath(os.path.dirname(__file__))


class ColorPushButton(QtWidgets.QPushButton):
    """Blunt port (read "almost verbatim code translation") of KColorButton
    
    What is new:
        option to keep alpha value when a color is dropped or pasted onto the widget
        option to have a light chequered pattern for transparent colors
    """
    changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    
    def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 alphaChannelEnabled:bool = True, useDefaultColor=True,
                 transparentPixmap:typing.Optional[QtGui.QPixmap]=None, 
                 keepAlphaOnDropPaste=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        
        self._color = color
        self._defaultColor = defaultColor
        self._changed = False
        self._alphaChannelEnabled = alphaChannelEnabled
        self._useDefaultColor = useDefaultColor
        self._mPos = QtCore.QPoint()
        self._tPmap = transparentPixmap
        if not self._tPmap:
            self._tPmap = make_transparent_bg()
        self._alpha = 255
        self._keepAlpha = keepAlphaOnDropPaste
        self._dialog = None
        
        self.setAcceptDrops(True)
        self.clicked.connect(self._chooseColor)
        
    @safeWrapper
    def initStyleOption(self, opt:QtWidgets.QStyleOptionButton):
        """Required in all concrete subclasses of QWidget
        """
        opt.initFrom(self)
        opt.state = QtWidgets.QStyle.State_Sunken if self.isDown() else QtWidgets.QStyle.State_Raised
        #  NOTE: 2021-05-14 21:52:32
        if isinstance(self, QtWidgets.QPushButton) and self.isDefault():
            opt.features |= QtWidgets.QStyleOptionButton.DefaultButton
        opt.text=""
        opt.icon = QtGui.QIcon()
        
    @property
    def strongTransparentPattern(self) -> bool:
        return self._strongTransparentPattern
        
    @strongTransparentPattern.setter
    def strongTransparentPattern(self, value:bool):
        self._strongTransparentPattern = value
        self.update()
        
    @property
    def changed(self) -> bool:
        return self._changed
    
    @property
    def keepAlphaOnDropPaste(self) -> bool:
        return self._keepAlpha
    
    @keepAlphaOnDropPaste.setter
    def keepAlphaOnDropPaste(self, value:bool):
        self._keepAlpha = value
        
    @property
    def color(self) -> QtGui.QColor:
        return QtGui.QColor(self._color)
    
    @color.setter
    def color(self, qcolor:QtGui.QColor):
        self._color = QtGui.QColor(qcolor)
        self._alpha = self._color.alpha()
        self.update()
        self.changedColor.emit(self._color)
        
    @property
    def defaultColor(self) -> QtGui.QColor:
        return self._defaultColor
    
    @defaultColor.setter
    def defaultColor(self, qcolor:QtGui.QColor):
        self._defaultColor = qcolor
        
    @property
    def alphaChannelEnabled(self) -> bool:
        return self._alphaChannelEnabled
    
    @alphaChannelEnabled.setter
    def alphaChannelEnabled(self, value:bool):
        self._alphaChannelEnabled = value
        
    @pyqtSlot(QtGui.QColor)
    def slot_setColor(self, value):
        if isinstance(value, QtGui.QColor) and value.isValid():
            sigblock = QtCore.QSignalBlocker(self)
            self.color = value
    
    @safeWrapper
    def paintEvent(self, ev:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        style = self.style()
        opt = QtWidgets.QStyleOptionButton()
        self.initStyleOption(opt)
        # draw bevel
        style.drawControl(QtWidgets.QStyle.CE_PushButtonBevel, opt, painter, self)
        
        labelRect = style.subElementRect(QtWidgets.QStyle.SE_PushButtonContents, opt, self)
        # draw color rectangle
        shift = style.pixelMetric(QtWidgets.QStyle.PM_ButtonMargin, opt, self) / 2
        labelRect.adjust(shift, shift, -shift, -shift)
        x, y, w, h = labelRect.getRect()
        
        if self.isChecked() | self.isDown():
            x += style.pixelMetric(QtWidgets.QStyle.PM_ButtonShiftHorizontal, opt, self)
            y += style.pixelMetric(QtWidgets.QStyle.PM_ButtonShiftVertical, opt, self)
            
        fillColor = QtGui.QColor(self.color) if self.isEnabled() else self.palette().color(self.backgroundRole())
        
        QtWidgets.qDrawShadePanel(painter, x, y, w, h, self.palette(), True, 1, None)
        
        if fillColor.isValid():
            rect = QtCore.QRect(x+1, y+1, w-2, h-2)
            if fillColor.alpha() < 255 and isinstance(self._tPmap, QtGui.QPixmap):
                painter.fillRect(rect, QtGui.QBrush(self._tPmap))
            painter.fillRect(rect, fillColor)
            
        if self.hasFocus():
            focusRect = style.subElementRect(QtWidgets.QStyle.SE_PushButtonFocusRect, opt, self)
            focusOpt = QtWidgets.QStyleOptionFocusRect()
            focusOpt.initFrom(self)
            focusOpt.rect = focusRect
            focusOpt.backgroundColor = self.palette().window().color()
            style.drawPrimitive(QtWidgets.QStyle.PE_FrameFocusRect, focusOpt, painter, self)
        
    @safeWrapper
    def sizeHint(self) -> QtCore.QSize:
        opt = QtWidgets.QStyleOptionButton()
        self.initStyleOption(opt)
        return self.style().sizeFromContents(QtWidgets.QStyle.CT_PushButton, opt, QtCore.QSize(16,16), self)

    @safeWrapper
    def minimumSizeHint(self) -> QtCore.QSize:
        opt = QtWidgets.QStyleOptionButton()
        self.initStyleOption(opt)
        return self.style().sizeFromContents(QtWidgets.QStyle.CT_PushButton, opt, QtCore.QSize(8,8), self)
    
    @safeWrapper
    def dragEnterEvent(self, ev:QtGui.QDragEnterEvent):
        ev.setAccepted(canDecode(ev.mimeData()) and self.isEnabled())
    
    @safeWrapper
    def dropEvent(self, ev:QtGui.QDropEvent):
        # NOTE: 2021-05-14 21:39:47
        # is mimeData.hasColor() is a QVariant<QColor> which is converted by
        # Qt into a QColor argument for the constructor below
        # ATTENTION:  DO NOT use sip-converted QVariant here
        # (see also NOTE: 2021-05-14 21:26:16)
        c = QtGui.QColor(fromMimeData(ev.mimeData()))
        if c.isValid():
            if self._keepAlpha:
                c.setAlpha(self._alpha)
            self.color = c
    
    @safeWrapper
    def keyPressEvent(self, ev:QtGui.QKeyEvent):
        key = ev.key() | int(ev.modifiers())
        
        if key in QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Copy):
            mime = QtCore.QMimeData()
            populateMimeData(mime, self.color)
            QtWidgets.QApplication.clipboard().setMimeData(mime, QtGui.QClipboard.Clipboard)
            
        elif key in  QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Paste):
            color = fromMimeData(QtWidgets.QApplication.clipboard().mimeData(QtGui.QClipboard.Clipboard))
            if self._keepAlpha:
                color.setAlpha(self._alpha)
            self.color = color
            
        else:
            super().keyPressEvent(ev)
    
    @safeWrapper
    def mousePressEvent(self, ev:QtGui.QMouseEvent):
        self._mPos = ev.pos()
        super().mousePressEvent(ev)
    
    @safeWrapper
    def mouseMoveEvent(self, ev:QtGui.QMouseEvent):
        if ev.buttons() & QtCore.Qt.LeftButton and \
            (ev.pos() - self._mPos).manhattanLength() > QtWidgets.QApplication.startDragDistance():
            createDrag(self.color, self).exec_()
            self.setDown(False)
            
    @pyqtSlot()
    def _chooseColor(self):
        if self._dialog:
            self._dialog.show()
            self._dialog.raise_()
            self._dialog.activateWindow()
            return
        
        self._dialog = QtWidgets.QColorDialog(self)
        self._dialog.setCurrentColor(self.color)
        self._dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, self._alphaChannelEnabled)
        #self._dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._dialog.accepted.connect(self._colorChosen)
        self._dialog.show()
        
    @pyqtSlot()
    def _colorChosen(self):
        if not self._dialog:
            return
        
        if self._dialog.selectedColor().isValid():
            self.color = self._dialog.selectedColor()
        elif self._useDefaultColor:
            self.color = self._defaultColor
        
        
class ColorComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("ColorRole", QtCore.Qt.UserRole +1)], 
                        module=__name__, qualname="ColorComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="ColorComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None, 
                 transparentPixmap:typing.Optional[QtGui.QPixmap] = None):
        super().__init__(parent)
        self._tPmap = transparentPixmap
    
    #@no_sip_autoconversion(QtCore.QVariant)
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):
        innerColor = QtGui.QColor(QtCore.Qt.white)
        isSelected = (option.state and QtWidgets.QStyle.State_Selected)
        paletteBrush = comboDelegateBrush(index, QtCore.Qt.BackgroundRole).style() == QtCore.Qt.NoBrush
        
        if isSelected:
            innerColor = option.palette.color(QtGui.QPalette.Highlight)
        else:
            innerColor = option.palette.color(QtGui.QPalette.Base)
            
        # highlight selected item
        opt = QtWidgets.QStyleOptionViewItem(option)
        opt.showDecorationSelected=True
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)
        innerRect = option.rect.adjusted(self.LayoutMetrics.FrameMargin,
                                         self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin,
                                         -self.LayoutMetrics.FrameMargin)

        # inner color
        cv = index.data(self.ItemRoles.ColorRole) # NOTE:2021-05-15 21:18:24Q QVariant
        #print(cv)
        if isinstance(cv, QtGui.QColor):
            if cv.isValid():
                #print("ColorComboDelegate paint: %s" % cv.name(QtGui.QColor.HexArgb))
                innerColor = cv
                paletteBrush = False
                tmpRenderHints = painter.renderHints()
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setPen(QtCore.Qt.transparent)
                if innerColor.alpha() < 255 and isinstance(self._tPmap, QtGui.QPixmap):
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.drawRoundedRect(innerRect, 2, 2)
                    painter.fillRect(innerRect, QtGui.QBrush(self._tPmap))
                    painter.fillRect(innerRect, innerColor)
                else:
                    painter.setBrush(innerColor)
                    painter.drawRoundedRect(innerRect, 2, 2)
                painter.setRenderHints(tmpRenderHints)
                painter.setBrush(QtCore.Qt.NoBrush)
                
        tv = index.data(QtCore.Qt.DisplayRole)
        if isinstance(tv, str) and len(tv.strip()):
            textColor = QtGui.QColor()
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
                painter.drawText(innerRect.adjusted(1, 1, -1, -1), QtCore.Qt.AlignCenter, tv)
    
    def sizeHint(self, option:QtWidgets.QStyleOptionViewItem, 
                 index:QtCore.QModelIndex) -> QtCore.QSize:
        return QtCore.QSize(100, option.fontMetrics.height() + 2 * self.LayoutMetrics.FrameMargin)
    
        
class ColorComboBox(QtWidgets.QComboBox):
    activated = pyqtSignal(QtGui.QColor, name="activated") # overloads QComboBox.activated[int] signal
    highlighted = pyqtSignal(QtGui.QColor, name="highlighted")
    colorChanged = pyqtSignal(QtGui.QColor, name="colorChanged")

    def __init__(self, color:typing.Optional[typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor, str]]=None, 
                 palette:typing.Optional[typing.Union[list, tuple, dict, str, ColorPalette]]=standardPalette,
                 alphaChannelEnabled:bool=True,
                 transparentPixmap:typing.Optional[QtGui.QPixmap]=None,
                 keepAlphaOnDropPaste=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        
        colorList = []
        self._colorDict = {}
        
        self._customColor = None
        self._customColorName = None
        
        if isinstance(palette, ColorPalette):
            self._palette = palette
            
        elif isinstance(palette, str):
            self._palette = ColorPalette(collection_name=palette)
                
        elif isinstance(palette, (tuple, list)):
            self._palette = ColorPalette(None,
                                         palette=dict(map(lambda c: get_name_color(c,"all"), palette)))
        
        elif isinstance(palette, dict):
            self._palette = ColorPalette(None, {"palette": palette})
            
        else:
            self._palette = ColorPalette(None, {"standard":standardPaletteDict})
            
        if color is not None:
            self._customColorName, self._customColor = get_name_color(color, "all")
        
        #self._customColor = QtGui.QColor(QtCore.Qt.white)
        self._internalColor = QtGui.QColor() if self._customColor is None else self._customColor
        self._internalColorName = self._customColorName

        self._tPmap = transparentPixmap
        
        if not self._tPmap:
            self._tPmap = make_transparent_bg()
            
        self._keepAlpha = keepAlphaOnDropPaste
        
        self._alpha = 255
        
        self._alphaChannelEnabled = alphaChannelEnabled
        
        ndx = 1
                
        if len(self._colorDict) and self._internalColorName in self._colorDict:
            nn,cc = zip(*self._colorDict.items())
            ndx = cc.index(self._internalColorName)
            
        elif self._internalColorName:
            ndx = 0
            
        # ### BEGIN initialization of Qt part
        super().__init__(parent=parent)
        
        self.setItemDelegate(ColorComboDelegate(self, self._tPmap))
        
        self._addColors()
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        print("\tset to %i" % ndx)
        self.setCurrentIndex(ndx)
        if ndx > 0:
            self._slotActivated(ndx)
            
        self.setMaxVisibleItems(13)
        self.setAcceptDrops(True)
        if self._internalColorName:
            self.setToolTip(self._internalColorName)
        
        # ### END initialization of Qt part
        
    @safeWrapper
    def dragEnterEvent(self, ev:QtGui.QDragEnterEvent):
        ev.setAccepted(canDecode(ev.mimeData()) and self.isEnabled())
    
    @safeWrapper
    def dropEvent(self, ev:QtGui.QDropEvent):
        # NOTE: 2021-05-14 21:39:47
        # is mimeData.hasColor() is a QVariant<QColor> which is converted by
        # Qt into a QColor argument for the constructor below
        # ATTENTION:  DO NOT use sip-converted QVariant here
        # (see also NOTE: 2021-05-14 21:26:16)
        c = QtGui.QColor(fromMimeData(ev.mimeData()))
        if c.isValid():
            if self._keepAlpha:
                c.setAlpha(self._alpha)
            self.color = c
    
    @safeWrapper
    def mousePressEvent(self, ev:QtGui.QMouseEvent):
        self._mPos = ev.pos()
        super().mousePressEvent(ev)
    
    @safeWrapper
    def mouseMoveEvent(self, ev:QtGui.QMouseEvent):
        if ev.buttons() & QtCore.Qt.LeftButton and \
            (ev.pos() - self._mPos).manhattanLength() > QtWidgets.QApplication.startDragDistance():
            createDrag(self.color, self).exec_()
            self.setDown(False)
            
    @safeWrapper
    def keyPressEvent(self, ev:QtGui.QKeyEvent):
        key = ev.key() | int(ev.modifiers())
        
        if key in QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Copy):
            mime = QtCore.QMimeData()
            populateMimeData(mime, self.color)
            QtWidgets.QApplication.clipboard().setMimeData(mime, QtGui.QClipboard.Clipboard)
            
        elif key in  QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Paste):
            color = fromMimeData(QtWidgets.QApplication.clipboard().mimeData(QtGui.QClipboard.Clipboard))
            if self._keepAlpha:
                color.setAlpha(self._alpha)
            self.color = color
            
        else:
            super().keyPressEvent(ev)
    
    def _addColors(self):
        self.addItem(self.tr("Custom...", "@item:inlistbox Custom color"))
        
        if isinstance(self._internalColor, QtGui.QColor) and self._internalColor.isValid():
            self.setItemData(0, self._internalColor, ColorComboDelegate.ItemRoles.ColorRole)
        
        #if len(self._colorDict):
            #for k, (name, c) in enumerate(self._colorDict.items()):
                #if c.isValid():
                    #self.addItem(name)
                    #self.setItemData(k + 1, self._colorDict[name], 
                                     #ColorComboDelegate.ItemRoles.ColorRole)
                    #self.setItemData(k + 1, self._colorDict[name], 
                                     #QtCore.Qt.ToolTipRole)
                
        if len(self._palette):
            for k, named_c[0], named_c[1] in enumerate(self._palette.named_qcolors):
                if named_c[1].isValid():
                    self.addItem(named_c[0])
                    self.setItemData(k + 1, named_c[1], 
                                     ColorComboDelegate.ItemRoles.ColorRole)
                    self.setItemData(k + 1, named_c[0], 
                                     QtCore.Qt.ToolTipRole)
                
        else:
            for k in range(len(standardPalette)):
                c = standardQColor(k)
                if c.isValid():
                    self.addItem("")
                    self.setItemData(k + 1, c, ColorComboDelegate.ItemRoles.ColorRole)
                    self.setItemData(k + 1, c.name(QtGui.QColor.HexArgb), QtCore.Qt.ToolTipRole)
    
    def _setCustomColor(self, color:QtGui.QColor, lookupInPresets:bool=True):
        from core.utilities import reverse_mapping_lookup
        if not color.isValid():
            return 
        
        self._alpha = color.alpha()
        
        if lookupInPresets:
            if len(self._colorDict) and color in self._colorDict.values():
                name = reverse_mapping_lookup(self._colorDict, color)
                if isinstance(name, tuple) and len(name):
                    name = name[0]
                i  = [k for k in self._colorDict.keys()].index(name)
                self.setCurrentIndex(i+1)
                self._internalColor = color
                self.setToolTip("%s (%s)" % (name, color.name(QtGui.QColor.HexArgb)))
                return
                
            else:
                for i in range(len(standardPalette)):
                    if standardQColor(i) == color:
                        self.setCurrentIndex(i+1)
                        self._internalColor = color
                        self.setToolTip(color.name(QtGui.QColor.HexArgb))
                        return
                    
        self._internalColor = color
        self._customColor = color
        self.setItemData(0, self._customColor, ColorComboDelegate.ItemRoles.ColorRole)
        self.setItemData(0, self._customColor.name(QtGui.QColor.HexArgb), QtCore.Qt.ToolTipRole)
        self.setToolTip(color.name(QtGui.QColor.HexArgb))
        #self.colorChanged.emit(color)
        #self.activated[QtGui.QColor].emit(color)
        
    @pyqtSlot(QtGui.QColor)
    def slot_setColor(self, value:QtGui.QColor):
        if isinstance(value, QtGui.QColor) and value.isValid():
            sigblock = QtCore.QSignalBlocker(self)
            self._setCustomColor(value)
            self.update()
    
    @pyqtSlot(int)
    @safeWrapper
    def _slotActivated(self, index:int):
        if index == 0:
            if self._alphaChannelEnabled:
                c = QtWidgets.QColorDialog.getColor(initial=self._customColor, 
                                                    options=QtWidgets.QColorDialog.ShowAlphaChannel,
                                                    parent=self)
            else:
                c = QtWidgets.QColorDialog.getColor(initial=self._customColor, 
                                                    parent=self)
                
            if c.isValid():
                self._customColor = c
                self._setCustomColor(self._customColor, False)
                
        elif len(self._colorDict) and index <= len(self._colorDict):
            c = [v for v in self._colorDict.values()][index - 1]
            if c.isValid():
                self._internalColor = c
                
        elif index <= len(standardPalette):
            c = standardQColor(index-1)
            if c.isValid():
                self._internalColor = c
            
        else:
            return
        
        self.activated[QtGui.QColor].emit(self._internalColor)
    
    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == 0:
            self._internalColor = self._customColor
                
        elif len(self._colorDict) and index <= len(self._colorDict):
            c = [v for v in self._colorDict.values()][index - 1]
            if c.isValid():
                self._internalColor = c
            
        elif index <= len(standardPalette):
            c = standardQColor(index - 1)
            if c.isValid():
                self._internalColor = c
                
        else:
            return
        
        self.highlighted[QtGui.QColor].emit(self._internalColor)
    
    @property
    def isCustomColor(self):
        return self._internalColor == self._customColor
    
    @property
    def color(self) -> QtGui.QColor:
        return self._internalColor
    
    @color.setter
    def color(self, color: QtGui.QColor):
        if not color.isValid():
            return
        
        if self.count() == 0:
            self._addColors()
            
        self._setCustomColor(color, True)
    
    @property
    def colors(self) -> typing.List[QtGui.QColor]:
        """The list of currently displayed colors (beginning with the custom one)
        """
        if len(self._colorDict):
            if self.color.isValid():
                return [self.color] + [c for c in self._colorDict.values()]
            return [c for c in self._colorDict.values()]
        else:
            if self.color.isValid():
                return [self.color] + [QtGui.QColor(*c) for c in standardPalette]
            return [QtGui.QColor(*c) for c in standardPalette]
    
    @colors.setter
    def colors(self, value:typing.Union[dict,list, str]):
        """WARNING: Does NOT check the contents of value!
        """
        if isinstance(value, str):
            value = getPalette(value)
            
        if isinstance(value, (tuple, list)):
            colorList = [paletteQColor(value, k) for k in range(len(value))]
            self._colorDict = dict(((c.name(QtGui.QColor.HexArgb), c) for c in colorList))
        elif isinstance(value, dict):
            self._colorDict = dict([(k, paletteQColor(value, k)) for k in value.keys()])
        else:
            return
        
        self.clear()
        self._addColors()
        
    @property
    def keepAlphaOnDropPaste(self) -> bool:
        return self._keepAlpha
    
    @keepAlphaOnDropPaste.setter
    def keepAlphaOnDropPaste(self, value:bool):
        self._keepAlpha = value
        
    @property
    def colorNames(self) -> typing.List[str]:
        """The list of color names in "#rrggbb" format
        """
        if len(self._colorDict):
            if self.color.isValid():
                return [self.color.name(QtGui.QColor.HexArgb)] + [c.name(QtGui.QColor.HexArgb) for c in self._colorDict.values()]
            return [c.name(QtGui.QColor.HexArgb) for c in self._colorDict.values()]
        
        else:
            if self.color.valid():
                return p[self.color.name(QtGui.QColor.HexArgb)] + [QtGui.QColor(*c).name(QtGui.QColor.HexArgb) for c in standardPalette]
            
    @property
    def qualifiedColorNames(self) -> typing.List[str]:
        """the list of qualified color names (if they exist), else #rgb names
        """
        if len(self._colorDict):
            if self.color().isValid():
                return [self.color.name(QtGui.QColor.HexArgb)] + [name for name in self._colorDict.keys()]
            
            return [name for name in self._colorDict.keys()]
        
        else:
            return self.colorNames
    
    def showEmptyList(self):
        self.clear()
    
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
        
        #print("ColorComboBox.paintEvent _internalColor %s (is valid: %s)" % (self._internalColor.name(), self._internalColor.isValid()))
        
        if self._internalColor.alpha() < 255 and isinstance(self._tPmap, QtGui.QPixmap):
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
            painter.fillRect(frame.adjusted(1, 1, -1, -1), QtGui.QBrush(self._tPmap))
            painter.fillRect(frame.adjusted(1, 1, -1, -1), self._internalColor)
        else:
            painter.setBrush(QtGui.QBrush(self._internalColor))
            painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
            
        painter.end()
