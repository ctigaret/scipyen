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
from itertools import (cycle, repeat)
from traitlets import Bunch

from enum import IntEnum
from functools import partial

import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, no_sip_autoconversion)
from core.utilities import reverse_mapping_lookup
from gui.painting_shared import (standardPalette, standardPaletteDict, svgPalette,
                              getPalette, paletteQColor, qcolor,
                              standardQColor, svgQColor, mplColors, qtGlobalColors, 
                              canDecode, populateMimeData, fromMimeData,
                              createDrag, make_transparent_bg, make_checkers,
                              comboDelegateBrush,get_name_color, ColorPalette,
                              )

from gui.scipyen_colormaps import (qcolor, get_name_color,ColorPalette)
from gui import quickdialog

from .stylewidgets import PenComboBox


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
        
        #print(f"ColorPushButton.__init__: color.name() = {color.name()}")
        
        self._color = qcolor(color)
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
        
        #if fillColor.isValid():
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

    def __init__(self, color:typing.Optional[typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor, int, str, typing.Sequence[typing.Union[int, float]]]]=None, 
                 palette:typing.Optional[typing.Union[list, tuple, dict, str, ColorPalette]]=standardPalette,
                 alphaChannelEnabled:bool=True,
                 transparentPixmap:typing.Optional[QtGui.QPixmap]=None,
                 keepAlphaOnDropPaste=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        
        #colorList = []
        self._color_palette = None
        
        if isinstance(palette, ColorPalette):
            self._color_palette = palette
            
        elif isinstance(palette, str):
            self._color_palette = ColorPalette(palette = getPalette(palette))
            #self._color_palette = ColorPalette(collection_name=palette)
                
        elif isinstance(palette, (tuple, list)):
            self._color_palette = ColorPalette(palette = dict(map(lambda c: get_name_color(c), palette)))
        
        elif isinstance(palette, dict):
            self._color_palette = ColorPalette(palette = palette)
            
        else:
            self._color_palette = ColorPalette() # the default: same contents as colormaps.defaultPalette
            
        self._customColor = Bunch(name="black", qcolor=QtGui.QColor("black"))
        
        if color is not None:
            #color = qcolor(color)
            self._customColor.name, self._customColor.qcolor = get_name_color(color)
            if isinstance(self._customColor.name, (tuple, list)):
                self._customColor.name = self._customColor.name[0]
        
        #print(f"ColorComboBox.__init__ self._customColor: {self._customColor}")
        
        #self._customColor = QtGui.QColor(QtCore.Qt.white)
        self._internalColor = self._customColor

        self._tPmap = transparentPixmap
        
        if not self._tPmap:
            self._tPmap = make_transparent_bg()
            
        self._keepAlpha = keepAlphaOnDropPaste
        
        self._alpha = 255
        
        self._alphaChannelEnabled = alphaChannelEnabled
        
        ndx = 1
                
        if len(self._color_palette):
            if self._internalColor.name in self._color_palette:
                ndx = self._color_palette.name_index(self._internalColor.name) + 1
                
            else:
                ndx = 0

        # ### BEGIN initialization of Qt part
        super().__init__(parent=parent)
        
        self.setItemDelegate(ColorComboDelegate(self, self._tPmap))
        
        self._addColors()
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        #print("\tset to %i" % ndx)
        self.setCurrentIndex(ndx)
        
        if ndx > 0:
            self._slotActivated(ndx)
            
        self.setMaxVisibleItems(13)
        self.setAcceptDrops(True)
        self.setToolTip(self._internalColor.name)
        
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
        
        if isinstance(self._internalColor.qcolor, QtGui.QColor) and self._internalColor.qcolor.isValid():
            self.setItemData(0, self._internalColor.qcolor, ColorComboDelegate.ItemRoles.ColorRole)
        
                
        if len(self._color_palette):
            for k, named_c in enumerate(self._color_palette.named_qcolors):
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
        if not color.isValid():
            return 
        
        self._alpha = color.alpha()
        
        if lookupInPresets:
            if self._color_palette.has_color(color):
                name = self._color_palette.colorname(color)
                if isinstance(name, (tuple, list)):
                    name = name[0]
                self._internalColor.name = name
                self._internalColor.qcolor = color
                #print(f"ColorComboBox._setCustomColor name {name}")
                ndx = self._color_palette.name_index(name)
                if ndx is None:
                    self.setCurrentIndex(0)
                else:
                    self.setCurrentIndex(ndx+1)
                
            else:
                for i in range(len(standardPalette)):
                    if standardQColor(i) == color:
                        self.setCurrentIndex(i+1)
                        name, _ = get_name_color(color)
                        if isinstance(name, (tuple, list)):
                            name = name[0]
                        self._internalColor.name = name
                        self._internalColor.qcolor = color
                        break
        else:
            name, _ = get_name_color(color)
            if isinstance(name, (tuple, list)):
                name = name[0]
            self._internalColor.name = name
            self._internalColor.qcolor = color
            self.setCurrentIndex(0)
            
            
        ttip = f"{self._internalColor.name}, ({self._internalColor.qcolor.name(QtGui.QColor.HexArgb)})"
        self.setToolTip(ttip)

        self.setItemData(0, self._internalColor.qcolor, ColorComboDelegate.ItemRoles.ColorRole)
        self.setItemData(0, ttip, QtCore.Qt.ToolTipRole)
        self._customColor = self._internalColor

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
                c = QtWidgets.QColorDialog.getColor(initial=self._customColor.qcolor, 
                                                    options=QtWidgets.QColorDialog.ShowAlphaChannel,
                                                    parent=self)
            else:
                c = QtWidgets.QColorDialog.getColor(initial=self._customColor.qcolor, 
                                                    parent=self)
                
            if c.isValid():
                name, color = get_name_color(c)
                if isinstance(name, (tuple, list)):
                    name = name[0]
                #self._customColor.qcolor = color
                #self._customColor.name = name
                self._setCustomColor(color, False)
                
        elif index <= len(self._color_palette):
            nc = [i for i in self._color_palette.named_qcolors][index - 1]
            #print(f"ColorComboBox._slotActivated {index} {nc}")
            if nc[1].isValid():
                self._internalColor.name = nc[0]
                self._internalColor.qcolor = nc[1]
                
            #print(f"ColorComboBox._slotActivated self._internalColor:\n{self._internalColor}")
            
        elif index <= len(standardPalette):
            c = standardQColor(index-1)
            if c.isValid():
                name, color = get_name_color(c)
                if isinstance(name, (tuple, list)):
                    name = name[0]
                self._internalColor.name = name
                self._internalColor.qcolor = color
            
        else:
            return
        
        self.activated[QtGui.QColor].emit(self._internalColor.qcolor)
    
    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        if index == 0:
            self._internalColor = self._customColor
                
        elif index <= len(self._color_palette):
            nc = [v for v in self._color_palette.named_qcolors][index - 1]
            if nc[1].isValid():
                self._internalColor.name = nc[0]
                self._internalColor.qcolor = nc[1]
            
        elif index <= len(standardPalette):
            name, color = get_name_color(standardQColor(index - 1))
            if nc[1].isValid():
                if isinstance(name, (tuple, list)):
                    name = name[0]
                self._internalColor.name = name
                self._internalColor.qcolor = color
                
        else:
            return
        
        self.highlighted[QtGui.QColor].emit(self._internalColor.qcolor)
    
    @property
    def isCustomColor(self):
        return self._internalColor == self._customColor
    
    @property
    def color(self) -> QtGui.QColor:
        return self._internalColor.qcolor
    
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
        ret = list()
        if self.color.isValid():
            ret.append(self.color)
        if len(self._color_palette):
            ret.append([c for c in self._color_palette.qcolors])
            
        return ret
    
    @colors.setter
    def colors(self, palette:typing.Union[dict,tuple, list, str, ColorPalette]):
        """WARNING: Does NOT check the contents of value!
        """
        if isinstance(palette, ColorPalette):
            self._color_palette = palette
            
        elif isinstance(palette, str):
            self._color_palette = ColorPalette(collection_name=palette)
                
        elif isinstance(palette, (tuple, list)):
            self._color_palette = ColorPalette(palette=dict(map(lambda c: get_name_color(c,"all"), palette)))
        
        elif isinstance(palette, dict):
            self._color_palette = ColorPalette(palette = palette)
            
        else:
            self._color_palette = ColorPalette(palette = standardPaletteDict)
            
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
        ret = [name for name in self._color_palette.keys()]
        if self.color.isValid():
            ret.insert(0, self._customColor.name)
            
        return ret
            
    @property
    def qualifiedColorNames(self) -> typing.List[str]:
        """the list of qualified color names (if they exist), else #rgb names
        """
        if len(self._color_palette):
            if self.color().isValid():
                return [self.color.name(QtGui.QColor.HexArgb)] + [name for name in self._color_palette.keys()]
            
            return [name for name in self._color_palette.keys()]
        
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
        
        if self._internalColor.qcolor.alpha() < 255 and isinstance(self._tPmap, QtGui.QPixmap):
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
            painter.fillRect(frame.adjusted(1, 1, -1, -1), QtGui.QBrush(self._tPmap))
            painter.fillRect(frame.adjusted(1, 1, -1, -1), self._internalColor.qcolor)
        else:
            painter.setBrush(QtGui.QBrush(self._internalColor.qcolor))
            painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
            
        painter.end()

class ColorSelectionWidget(QtWidgets.QWidget):
    """Combines a ColorComboBox and a ColorPushButton in the same widget
    """
    colorChanged = pyqtSignal(QtGui.QColor, name="colorChanged")
    
    def __init__(self, color:typing.Optional[QtGui.QColor]=None,
                 defaultColor:typing.Optional[QtGui.QColor]=None,
                 palette:typing.Optional[typing.Union[dict,list, tuple, str, ColorPalette]]=None,
                 useDefaultColor:bool=True,
                 alphaChannelEnabled:bool = True, 
                 transparentPixmap:typing.Optional[QtGui.QPixmap]=None,
                 keepAlphaOnDropPaste:bool=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._color = qcolor(color)

        self._colorComboBox = ColorComboBox(self._color,
                                            palette=palette,
                                            alphaChannelEnabled=alphaChannelEnabled,
                                            transparentPixmap=transparentPixmap,
                                            parent=self)
        
        self._colorPushButton = ColorPushButton(self._color, 
                                                defaultColor=defaultColor,
                                                alphaChannelEnabled=alphaChannelEnabled,
                                                useDefaultColor=useDefaultColor,
                                                keepAlphaOnDropPaste=keepAlphaOnDropPaste,
                                                transparentPixmap=transparentPixmap,
                                                parent=self)
        
        self._configureUI_()
        
    def _configureUI_(self):
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(0)
        for w in (self._colorComboBox, self._colorPushButton):
            self._layout.addWidget(w)
            
        # NOTE: required when self._color is None
        if not self._color:
            sigblock = QtCore.QSignalBlocker(self._colorPushButton)
            self._colorPushButton.color = self._colorComboBox.color
            self._color = self._colorComboBox.color

        self._colorComboBox.activated.connect(self.slot_setColor)
        self._colorPushButton.changedColor.connect(self.slot_setColor)
        
    @pyqtSlot(QtGui.QColor)
    def slot_setColor(self, color):
        self.color = color
        
    @property
    def color(self):
        return QtGui.QColor(self._color)
    
    @color.setter
    def color(self, color:QtGui.QColor):
        if isinstance(color, QtGui.QColor) and color.isValid():
            #print(f"ColorSelectionWidget color.setter {color}")
            self._color = color
            n,c = get_name_color(self._color)
            #print(f"ColorSelectionWidget color.setter {n}, {c}")
            sigblock = QtCore.QSignalBlocker(self._colorPushButton)
            if self.sender() is self._colorComboBox:
                self._colorPushButton.color = color
            else:
                self._colorComboBox._setCustomColor(color)
            self.colorChanged.emit(self._color)
            
    @property
    def palette(self):
        return self._colorComboBox.colors
    
    @palette.setter
    def palette(self, value):
        self._colorComboBox.colors = palette
        
    def validate(self):
        return True
        
def quickColorDialog(parent:typing.Optional[QtWidgets.QWidget]=None, 
                     title:typing.Optional[str]=None,
                     labels:typing.Optional[typing.Union[dict, typing.List[str]]]=None,
                     colors:typing.Optional[typing.List[typing.Union[str, QtGui.QColor]]] = None,
                     palette:typing.Optional[typing.Union[dict,list, tuple, str]]=None) -> dict:
    
    dlg = quickdialog.QuickDialog(parent=parent, title=title)
    
    if isinstance(labels, (tuple, list)):
        if len(labels) == 0:
            if isinstance(colors, (tuple, list)) and len(colors):
                lbl_col = dict(("Color%i" % k, color) for k, color in enumerate(colors))
                
            else:
                lbl_col = {"Select color": QtGui.QColor()}
                
        else:
            if isinstance(colors, (tuple, list)) and len(colors):
                if  len(labels) < len(colors):
                    lbl = list(labels)
                    lbl.extend("color%i" % k for k in range(len(labels), len(colors)))
                    lbl_col = dict(zip(lbl, colors))
                    
                elif len(labels) > len(colors):
                    clr = list(colors)
                    cc = cycle(cl)
                    clr.extend(next(cc) for k in range(len(colors), len(labels)))
                    lbl_col = dict(zip(labels, clr))
                else:
                    lbl_col = dict(zip(labels, colors))
                    
            else:
                lbl_col = dict(zip(labels, repeat(QtGui.QColor(), len(labels))))
                
    elif isinstance(labels, dict):
        lbl_col = labels
        
    else:
        lbl_col = {"Select color": QtGui.QColor()}
    
    group = quickdialog.HDialogGroup(dlg)
        
    colorselwidgets = dict()
    
    for label, color in lbl_col.items():
        vgroup = quickdialog.VDialogGroup(group)
        vgroup.layout.setSpacing(0)
        #vgroup.defaultAlignment = QtCore.Qt.AlignHCenter
        #print(f"quickColorDialog set up selection widget for {label}")
        colorselwidgets[label] = ColorSelectionWidget(color=color, parent=vgroup, palette=palette)
        vgroup.addWidget(QtWidgets.QLabel(label, vgroup), alignment=QtCore.Qt.AlignHCenter)
        vgroup.addWidget(colorselwidgets[label], alignment=QtCore.Qt.AlignHCenter)
        group.addWidget(vgroup)
        
    dlg.addWidget(group)
    
    dlg.resize(-1, -1)
        
    dlgret = dlg.exec()
    
    ret = Bunch()
    
    if dlgret:
        f = lambda x: Bunch(name=x[0], color=x[1])
        ret = Bunch((lbl, f(get_name_color(w.color))) for lbl, w in colorselwidgets.items())
        
    return ret
        
    
