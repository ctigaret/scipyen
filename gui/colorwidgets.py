import os, typing

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, )

__module_path__ = os.path.abspath(os.path.dirname(__file__))

def populateMimeData(mimeData:QtCore.QMimeData, color:QtGui.QColor):
    mimeData.setColorData(color)
    mimeData.setText(color.name())
    
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
        return mimeData.colorData().value()
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
    painter.end() # not in Python!
    drag.setMimeData(mime)
    drag.setPixmap(colorPix)
    drag.setHotSpot(QtCore.QPoint(-5, -7))
    return drag

class ColorButton(QtWidgets.QPushButton):
    """Blunt port (read "almost verbatim code translation") of KColorButton
    """
    changedColor = pyqtSignal(QtGui.QColor, name="changedColor")
    
    def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 alphaChannelEnabled:bool = True, useDefaultColor=True,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        
        self._color = color
        self._defaultColor = defaultColor
        self._changed = False
        self._alphaChannelEnabled = alphaChannelEnabled
        self._useDefaultColor = useDefaultColor
        self._mPos = QtCore.QPoint()
        self._dialog = None
        
        self.setAcceptDrops(True)
        self.clicked.connect(self._chooseColor)
        
    def _initStyleOption(self, opt:QtWidgets.QStyleOptionButton):
        opt.initFrom(self)
        opt.state = QtWidgets.QStyle.State_Sunken if self.isDown() else QtWidgets.QStyle.State_Raised
        if self.isDefault():
            opt.features |= QtWidgets.QStyleOptionButton.DefaultButton
        #opt.text.clear()
        opt.text=""
        opt.icon = QtGui.QIcon()
        
    @property
    def changed(self) -> bool:
        return self._changed
        
    @property
    def color(self) -> QtGui.QColor:
        return self._color
    
    @color.setter
    def color(self, qcolor:QtGui.QColor):
        self._color = QtGui.QColor(qcolor)
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
                patternPainter = QtGui.QPainter(chessboardPainter)
                patternPainter.fillRect(0,0,8,8, QtCore.Qt.black)
                patternPainter.fillRect(8,8,8,8, QtCore.Qt.black)
                patternPainter.fillRect(0,8,8,8, QtCore.Qt.white)
                patternPainter.fillRect(8,0,8,8, QtCore.Qt.white)
                patternPainter.end() # not in Python!
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
    
    def dragEnterEvent(self, ev:QtGui.QDragEnterEvent):
        ev.setAccepted(canDecode(ev.mimeData()) and self.isEnabled())
    
    def dropEvent(self, ev:QtGui.QDropEvent):
        c =QtGui.QColor(fromMimeData(ev.mimeData()))
        if c.isValid():
            self.color = c
    
    def keyPressEvent(self, ev:QtGui.QKeyEvent):
        key = ev.key() | ev.modifiers()
        
        if key in QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Copy):
            mime = QtCore.QMimeData()
            populateMimeData(mime, self.color)
            QtWidgets.QApplication.clipboard().setMimeData(mime, QtGui.QClipboard.Clipboard)
            
        elif key in  QtGui.QKeySequence.keyBindings(QtGui.QKeySequence.Paste):
            color = fromMimeData(QtWidgets.QApplication.clipboard().mimeData(QtGui.QClipboard.Clipboard))
            self.color = color
            
        else:
            super().keyPressEvent(ev)
    
    def mousePressEvent(self, ev:QtGui.QMouseEvent):
        self._mPos  =ev.pos()
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
        
        
    
