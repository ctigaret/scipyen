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
       reverse_dict(qtGLobalColors)[7] -> 'QtCore.Qt.red'
       
       and 
       
       eval(reverse_dict(qtGLobalColors)[7]) -> 7
       
       Furthermore this can be used to populate a combo box (see ColorCombo); to
       retrieve the actual color name, use (following the example above):
       
       reverse_dict(qtGlobalColors)[7].split('.')[-1] -> 'red'
    
        
"""
import array, os, typing
import numpy as np

from enum import IntEnum
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, no_sip_autoconversion)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

qtGlobalColors = dict(("QtCore.Qt.%s" % x,n) for x, n in vars(QtCore.Qt).items() if isinstance(n, QtCore.Qt.GlobalColor))

standardPalette = [
    [255, 255, 255], # white
    [192, 192, 192], # light gray
    [160, 160, 160], # gray
    [128, 128, 128], # dark gray
    [  0,   0,   0], # black
    [255, 128, 128], # light red
    [255, 192, 128], # light orange
    [255, 255, 128], # light yellow
    [128, 255, 128], # light green
    [128, 255, 255], # cyan blue
    [128, 128, 255], # light blue
    [255, 128, 255], # light violet
    [255,   0,   0], # red
    [255, 128,   0], # orange
    [255, 255,   0], # yellow
    [  0, 255,   0], # green
    [  0, 255, 255], # light blue
    [  0,   0, 255], # blue
    [255,   0, 255], # violet
    [128,   0,   0], # dark red
    [128,  64,   0], # dark orange
    [128, 128,   0], # dark yellow
    [  0, 128,   0], # dark green
    [  0, 128, 128], # dark light blue
    [  0,   0, 128], # dark blue
    [128,   0, 128] # dark violet
]

#standardPalette = np.array( 
#[
    #[255, 255, 255], # white
    #[192, 192, 192], # light gray
    #[160, 160, 160], # gray
    #[128, 128, 128], # dark gray
    #[0, 0, 0], # black

    #[255, 128, 128], # light red
    #[255, 192, 128], # light orange
    #[255, 255, 128], # light yellow
    #[128, 255, 128], # light green
    #[128, 255, 255], # cyan blue
    #[128, 128, 255], # light blue
    #[255, 128, 255], # light violet
    #[255, 0, 0], # red
    #[255, 128, 0], # orange
    #[255, 255, 0], # yellow
    #[0, 255, 0], # green
    #[0, 255, 255], # light blue
    #[0, 0, 255], # blue
    #[255, 0, 255], # violet
    #[128, 0, 0], # dark red
    #[128, 64, 0], # dark orange
    #[128, 128, 0], # dark yellow
    #[0, 128, 0], # dark green
    #[0, 128, 128], # dark light blue
    #[0, 0, 128], # dark blue
    #[128, 0, 128] # dark violet
#],
#dtype = np.dtype(int))
##dtype = np.dtype(bytes))

def standardColor(i:int) -> QtGui.QColor:
    return paletteColor(standardPalette, i)
    #if i < len(standardPalette):
        #entry = standardPalette[i]
        #return QtGui.QColor(entry[0], entry[1], entry[2])
    
    #return QtGui.QColor()

def paletteColor(palette:list, i:int) -> QtGui.QColor:
    if not isinstance(i, int):
        raise TypeError("expecting an int index; got %s instead" % type(i).__name__)
    
    if not isinstance(palette, (tuple, list)):
        raise TypeError("palette expected to be a sequence; got %s instead" % type(palette).__name__)
        
    if not all([isinstance(e, (tuple, list)) and len(e) in (3,4) and all([isinstance(v, int) and v >= 0 and v < 256 for v in e]) for e in palette]):
        raise ValueError("Palette must contain sequences of 3 or 4 int elements with values in [0 .. 256)")
        
    if i >=0 and i < len(palette):
        entry = palette[i]
        if not isinstance(entry, (tuple, list)) or not all([isinstance(v, int) for v in entry] or len(entry) not in (3,4)):
            raise TypeError("palette entries expected to be sequences of 3 or 4 int; insteasd, got %s for %dth entry" % (entry, i))
        return QtGui.QColor(*entry) # QColor(r,g,b a=255) - NOTE will raise appropriate Error if entry is wrong
    else:
        raise ValueError("index expected an int in the semi-open interval [0 .. %d); got %s instead" % (len(palette), i))
        
def populateMimeData(mimeData:QtCore.QMimeData, color:typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]):
    from core.datatypes import reverse_dict
    mimeData.setColorData(color)
    
    if isinstance(color, QtCore.Qt.GlobalColor):
        color = QtGui.QColor(color)
    mimeData.setText(color.name())
    # NOTE: 2021-05-14 23:27:20
    # The code below doesn't do what is intended: it should pass a color string
    # (format '#rrggbb) to mimeData's text attribute
    # However, DO NOT DELETE: this is an example of key lookup by value in enumerations
    # in the Qt namespace
    #if isinstance(color, QtCore.Qt.GlobalColor):
        #name = reverse_dict(qtGlobalColors)[color]
    #else:
        #name = color.name()
        
    #mimeData.setText(name)
    
def canDecode(mimeData:QtCore.QMimeData) -> bool:
    if mimeData.hasColor():
        return True
    
    if mimeData.hasText():
        colorName = mimeData.text()
        if len(colorName) >= 4 and colorName.startswith("#"):
            return True
        
    return False

@no_sip_autoconversion(QtCore.QVariant)
def fromMimeData(mimeData:QtCore.QMimeData) -> QtGui.QColor:
    if mimeData.hasColor():
        # NOTE: 2021-05-14 21:26:16 ATTENTION
        #return mimeData.colorData().value() 
        # sip "autoconverts" QVariant<QColor> to an int, therefore constructing
        # a QColor from that results in an unintended color!
        # Therefore we temporarily suppress autoconversion of QVariant here
        # NOTE: 2021-05-15 14:06:57 temporary sip diabling by means of the 
        # decorator core.prog.no_sip_autoconversion
        #import sip
        #sip.enableautoconversion(QtCore.QVariant, False)
        ret = mimeData.colorData().value() # This is a python-wrapped QVariant<QColor>
        #sip.enableautoconversion(QtCore.QVariant, True)
        return ret
    if canDecode(mimeData):
        return QtGui.QColor(mimeData.text())
    return QtGui.QColor()

@no_sip_autoconversion(QtCore.QVariant)
def colorComboDelegateBrush(index:QtCore.QModelIndex, role:int) -> QtGui.QBrush:
    #import sip
    #sip.enableautoconversion(QtCore.QVariant, False)
    brush = QtGui.QBrush()
    v = QtCore.QVariant(index.data(role))
    if v.type() == QtCore.QVariant.Brush:
        brush = v.value()
        
    elif v.type() == QtCore.QVariant.Color:
        brush = QtGui.QBrush(v.value())
    #sip.enableautoconversion(QtCore.QVariant, True)
    return brush

@safeWrapper
def createDrag(color:QtGui.QColor, dragSource:QtCore.QObject) -> QtGui.QDrag:
    drag = QtGui.QDrag(dragSource)
    mime = QtCore.QMimeData()
    populateMimeData(mime, color)
    colorPix = QtGui.QPixmap(25, 20)
    colorPix.fill(color)
    painter = QtGui.QPainter(colorPix)
    painter.setPen(QtCore.Qt.black)
    painter.drawRect(0, 0, 24, 19)
    painter.end()
    drag.setMimeData(mime)
    drag.setPixmap(colorPix)
    drag.setHotSpot(QtCore.QPoint(-5, -7))
    return drag


#class ColorButtonMixin(QtWidgets.QAbstractButton):
class ColorPushButton(QtWidgets.QPushButton):
    """Blunt port (read "almost verbatim code translation") of KColorButton
    
    What is new:
        option to keep alpha value when a color is dropped or pasted onto the widget
        option to have a light chequered pattern for transparent colors
    """
    changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    
    def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 alphaChannelEnabled:bool = True, useDefaultColor=True,
                 strongTransparentPattern:bool=False, keepAlphaOnDropPaste=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        
        self._color = color
        self._defaultColor = defaultColor
        self._changed = False
        self._alphaChannelEnabled = alphaChannelEnabled
        self._useDefaultColor = useDefaultColor
        self._mPos = QtCore.QPoint()
        self._strongTransparentPattern = strongTransparentPattern
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
        return self._color
    
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
            if fillColor.alpha() < 255:
                chessboardPattern = QtGui.QPixmap(16,16)
                patternPainter = QtGui.QPainter(chessboardPattern)
                # NOTE: 2021-05-14 21:36:53
                # keep this as an option!
                if self._strongTransparentPattern:
                    patternPainter.fillRect(0,0,8,8, QtCore.Qt.black)
                    patternPainter.fillRect(8,8,8,8, QtCore.Qt.black)
                    patternPainter.fillRect(0,8,8,8, QtCore.Qt.white)
                    patternPainter.fillRect(8,0,8,8, QtCore.Qt.white)
                else:
                    patternPainter.fillRect(0,0,8,8, QtCore.Qt.darkGray)
                    patternPainter.fillRect(8,8,8,8, QtCore.Qt.darkGray)
                    patternPainter.fillRect(0,8,8,8, QtCore.Qt.lightGray)
                    patternPainter.fillRect(8,0,8,8, QtCore.Qt.lightGray)
                patternPainter.end()
                painter.fillRect(rect, QtGui.QBrush(chessboardPattern))
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
        
        
#class ColorPushButton(ColorButtonMixin, QtWidgets.QPushButton):
    #changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    #def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 #alphaChannelEnabled:bool = True, useDefaultColor=True,
                 #strongTransparentPattern:bool=False,
                 #parent:typing.Optional[QtWidgets.QWidget]=None):
        #super().__init__(color, defaultColor,
                    #alphaChannelEnabled=alphaChannelEnabled,
                    #useDefaultColor=useDefaultColor,
                    #strongTransparentPattern=strongTransparentPattern,
                    #parent=parent)
        #QtWidgets.QPushButton.__init__(self, parent=parent)
        #self.setAcceptDrops(True)
        #self.clicked.connect(self._chooseColor)
        
        
#class ColorToolButton(ColorButtonMixin, QtWidgets.QToolButton):
    #changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    #def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 #alphaChannelEnabled:bool = True, useDefaultColor=True,
                 #strongTransparentPattern:bool=False,
                 #parent:typing.Optional[QtWidgets.QWidget]=None):
        #super().__init__(color, defaultColor,
                         #alphaChannelEnabled=alphaChannelEnabled,
                         #useDefaultColor=useDefaultColor,
                         #strongTransparentPattern=strongTransparentPattern,
                         #parent=parent)
        #QtWidgets.QToolButton.__init__(self, parent=parent)
        #self.setAcceptDrops(True)
        #self.triggered.connect(self._chooseColor)
    
class ColorComboDelegate(QtWidgets.QAbstractItemDelegate):
    ItemRoles = IntEnum(value="ItemRoles", names=[("ColorRole", QtCore.Qt.UserRole +1)], 
                        module=__name__, qualname="ColorComboDelegate.ItemRoles")
    
    LayoutMetrics = IntEnum(value="LayoutMetrics", names={"FrameMargin":3},
                            module=__name__, qualname="ColorComboDelegate.LayoutMetrics")
    
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        super().__init__(parent)
    
    @no_sip_autoconversion(QtCore.QVariant)
    def paint(self, painter:QtGui.QPainter, option:QtWidgets.QStyleOptionViewItem,
              index:QtCore.QModelIndex):
        innerColor = QtGui.QColor(QtCore.Qt.white)
        isSelected = (option.state and QtWidgets.QStyle.State_Selected)
        paletteBrush = colorComboDelegateBrush(index, QtCore.Qt.BackgroundRole).style() == QtCore.Qt.NoBrush
        
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
        if isinstance(cv, QtGui.QColor):
            if cv.isValid():
                innerColor = cv
                paletteBrush = False
                painter.setPen(QtCore.Qt.transparent)
                painter.setBrush(innerColor)
                tmpRenderHints = painter.renderHints()
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.drawRoundedRect(innerRect, 2, 2)
                painter.setRenderHints(tmpRenderHints)
                painter.setBrush(QtCore.Qt.NoBrush)
                
        tv = index.data(QtCore.Qt.DisplayRole)
        #if tv.type() == QtCore.QVariant.String:
        #print(type(tv))
        if isinstance(tv, str):
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
    #_activated = pyqtSignal(int, name="_activated")
    #_highlighted = pyqtSignal(int, name="_highlighted")
    def __init__(self, color:typing.Optional[QtGui.QColor]=None, 
                 defaultColor:typing.Optional[QtGui.QColor]=None,
                 palette:typing.Optional[list]=None,
                 alphaChannelEnabled:bool=True,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__()
        QtWidgets.QComboBox.__init__(self, parent=parent)
        self._colorList = []
        self._customColor = QtGui.QColor(QtCore.Qt.white)
        self._internalColor = QtGui.QColor()
        self._alphaChannelEnabled = alphaChannelEnabled
        
        if palette is not None:
            if not isinstance(palette, (tuple, list)):
                raise TypeError("palette expected to be a sequence, or None; got %s instead" % type(palette).__name__)
            
            elif not all([isinstance(e, (tuple, list)) and len(e) in (3,4) and all([isinstance(v, int) and v >= 0 and v < 256 for v in e]) for e in palette]):
                raise ValueError("palette must contain sequences of 3 or 4 int with values in the semi-open interval [0 .. 256)")
            
        self._palette = palette
        
        self.setItemDelegate(ColorComboDelegate(self))
        self._addColors()
        super().activated[int].connect(self._slotActivated)
        super().highlighted[int].connect(self._slotHighlighted)
        #self._activated[int].connect(self._slotActivated) 
        #self._highlighted[int].connect(self._slotHighlighted)
        self.setCurrentIndex(1)
        self._slotActivated(1)
        self.setMaxVisibleItems(13)
        
    def _addColors(self):
        self.addItem(self.tr("Custom...", "@item:inlistbox Custom color"))
        
        palette = self._palette if self._palette else standardPalette
        
        if len(self._colorList):
            for k in range(len(self._colorList)):
                c = self._colorList[k]
                if c.isValid():
                    self.addItem("")
                    self.setItemData(k + 1, c, ColorComboDelegate.ItemRoles.ColorRole)
                
        else:
            for k in range(len(palette)):
                c = paletteColor(palette, k)
                if c.isValid():
                    self.addItem("")
                    self.setItemData(k + 1, c, ColorComboDelegate.ItemRoles.ColorRole)
        pass
    
    def _setCustomColor(self, color:QtGui.QColor, lookupInPresets:bool=True):
        if not color.isValid():
            return 
        
        palette = self._palette if self._palette else standardPalette
        
        if lookupInPresets:
            if len(self._colorList) and color in self._colorList:
                i = self._colorList.index(color)
                self.setCurrentIndex(i+1)
                self._internalColor = color
                return
            else:
                #for i in range(len(standardPalette)):
                for i in range(len(palette)):
                    #if standardColor(i) == color:
                    if paletteColor(palette, i) == color:
                        self.setCurrentIndex(i+1)
                        self._internalColor = color
                        return
                    
        self._internalColor = color
        self._customColor = color
        self.setItemData(0, self._customColor, ColorComboDelegate.ItemRoles.ColorRole)
    
    @pyqtSlot(int)
    @safeWrapper
    def _slotActivated(self, index:int):
        palette = self._palette if self._palette else standardPalette
        
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
                
        elif len(self._colorList) == 0:
            #c = standardColor(index-1)
            c = paletteColor(palette, index-1)
            if c.isValid():
                self._internalColor = c
            
        elif index <= len(self._colorList):
            c = self._colorList[index - 1]
            if c.isValid():
                self._internalColor = c
        else:
            return
        
        self.activated[QtGui.QColor].emit(self._internalColor)
    
    @pyqtSlot(int)
    @safeWrapper
    def _slotHighlighted(self, index:int):
        palette = self._palette if self._palette else standardPalette
        
        if index == 0:
            self._internalColor = self._customColor
        elif len(self._colorList) == 0:
            #c = standardColor(index - 1)
            c = paletteColor(palette, index - 1)
            if c.isValid():
                self._internalColor = c
        elif index <= len(self._colorList):
            c = self._colorList[index - 1]
            if c.isValid():
                self._internalColor = c
        else:
            return
        
        self.highlighted[QtGui.QColor].emit(self._internalColor)
    
    @property
    def isCustomColor(self):
        return self._internalColor == self._customColor
        #return self._isCustomColor
    
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
        if len(self._colorList):
            return self._colorList
        else:
            return [QtGui.QColor(c[0],c[1],c[2]) for c in standardPalette]
    
    @colors.setter
    def colors(self, colorList:typing.Sequence[QtGui.QColor]):
        self.clear()
        self._colorList[:] = colorList
        self._addColors()
    
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
        painter.setBrush(QtGui.QBrush(self._internalColor))
        painter.drawRoundedRect(frame.adjusted(1, 1, -1, -1), 2, 2)
        painter.end()
