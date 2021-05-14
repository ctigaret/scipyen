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
import os, typing

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, )

__module_path__ = os.path.abspath(os.path.dirname(__file__))

qtGlobalColors = dict(("QtCore.Qt.%s" % x,n) for x, n in vars(QtCore.Qt).items() if isinstance(n, QtCore.Qt.GlobalColor))

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

def fromMimeData(mimeData:QtCore.QMimeData) -> QtGui.QColor:
    if mimeData.hasColor():
        # NOTE: 2021-05-14 21:26:16 ATTENTION
        #return mimeData.colorData().value() 
        # sip "autoconverts" QVariant<QColor> to an int, therefore constructing
        # a QColor from that results in an unintended color!
        # Therefore we temporarily suppress autoconversion of QVariant here
        import sip
        sip.enableautoconversion(QtCore.QVariant, False)
        ret = mimeData.colorData().value() # This is a python-wrapped QVariant<QColor>
        sip.enableautoconversion(QtCore.QVariant, True)
        return ret
    if canDecode(mimeData):
        return QtGui.QColor(mimeData.text())
    return QtGui.QColor()

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


class ColorButtonMixin(QtGui.QAbstractButton):
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
        
    def _initStyleOption(self, opt:QtWidgets.QStyleOptionButton):
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
        self._initStyleOption(opt)
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
            focusOpt.backgroundCoor = self.palette().window().color()
            style.drawPrimitive(QtWidgets.QStyle.PE_FrameFocusRect, focusOpt, painter, self)
        
    def sizeHint(self) -> QtCore.QSize:
        opt = QtWidgets.QStyleOptionButton()
        self._initStyleOption(opt)
        return self.style().sizeFromContents(QtWidgets.QStyle.CT_PushButton, opt, QtCore.QSize(16,16), self)

    def minimumSizeHint(self) -> QtCore.QSize:
        opt = QtWidgets.QStyleOptionButton()
        self._initStyleOption(opt)
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
    
    def mousePressEvent(self, ev:QtGui.QMouseEvent):
        self._mPos = ev.pos()
        super().mousePressEvent(ev)
    
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
        
        
class ColorPushButton(ColorButtonMixin, QtWidgets.QPushButton):
    changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 alphaChannelEnabled:bool = True, useDefaultColor=True,
                 strongTransparentPattern:bool=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(color, defaultColor,
                    alphaChannelEnabled=alphaChannelEnabled,
                    useDefaultColor=useDefaultColor,
                    strongTransparentPattern=strongTransparentPattern,
                    parent=parent)
        QtWidgets.QPushButton.__init__(self, parent=parent)
        self.setAcceptDrops(True)
        self.clicked.connect(self._chooseColor)
        
        
class ColorToolButton(ColorButtonMixin, QtWidgets.QToolButton):
    changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 alphaChannelEnabled:bool = True, useDefaultColor=True,
                 strongTransparentPattern:bool=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(color, defaultColor,
                         alphaChannelEnabled=alphaChannelEnabled,
                         useDefaultColor=useDefaultColor,
                         strongTransparentPattern=strongTransparentPattern,
                         parent=parent)
        QtWidgets.QToolButton.__init__(self, parent=parent)
        self.setAcceptDrops(True)
        self.clicked.connect(self._chooseColor)
        

