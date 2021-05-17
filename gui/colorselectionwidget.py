import os, typing

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from . import colorwidgets
from .colorwidgets import (ColorComboBox, ColorPushButton,
                           paletteQColor, standardQColor, standardPalette,)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class ColorSelectionWidget(QtWidgets.QWidget):
    """Not really useful!
    """
    colorChanged = pyqtSignal(QtGui.QColor, name="colorChanged")
    
    def __init__(self, color:typing.Optional[QtGui.QColor]=None,
                 defaultColor:typing.Optional[QtGui.QColor]=None,
                 palette:typing.Optional[typing.Union[dict,list, tuple, str]]=None,
                 useDefaultColor:bool=True,
                 alphaChannelEnabled:bool = True, 
                 transparentPixmap:typing.Optional[QtGui.QPixmap]=None,
                 keepAlphaOnDropPaste:bool=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._color = color

        self._colorPushButton = ColorPushButton(color=color, 
                                                defaultColor=defaultColor,
                                                alphaChannelEnabled=alphaChannelEnabled,
                                                useDefaultColor=useDefaultColor,
                                                keepAlphaOnDropPaste=keepAlphaOnDropPaste,
                                                transparentPixmap=transparentPixmap,
                                                parent=self)
        
        self._colorComboBox = ColorComboBox(color,
                                            palette=palette,
                                            alphaChannelEnabled=alphaChannelEnabled,
                                            transparentPixmap=transparentPixmap,
                                            parent=self)
        
        self._configureUI_()
        
    def _configureUI_(self):
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(2)
        for w in (self._colorComboBox, self._colorPushButton):
            self._layout.addWidget(w)
            
        # NOTE: required when self._color is None
        if not self._color:
            sigblock = QtCore.QSignalBlocker(self._colorPushButton)
            self._colorPushButton.color = self._colorComboBox.color
            self._color = self._colorComboBox.color

        self._colorComboBox.activated.connect(self._colorPushButton.slot_setColor)
        self._colorComboBox.activated.connect(self.colorChanged)
        self._colorPushButton.changedColor.connect(self._colorComboBox.slot_setColor)
        self._colorPushButton.changedColor.connect(self.colorChanged)
            
        
    @pyqtSlot(QtGui.QColor)
    def slot_setColor(self, color):
        self._color = color
        sigblock = QCore.QSignalBlocker(self._colorPushButton)
        self._colorPushButton.color = color
        self._colorComboBox._setCustomColor(color)
        
        
    @property
    def color(self):
        return self._color
    
    @color.setter
    def color(self, value:QtGui.QColor):
        if isinstance(value, QtGui.QColor) and value.isValid():
            self._color = color
            sigblock = QCore.QSignalBlocker(self._colorPushButton)
            self._colorPushButton.color = color
            self._colorComboBox._setCustomColor(color)
            self.colorChanged.emit(self._color)
            
    @property
    def palette(self):
        return self._colorComboBox.colors
    
    @palette.setter
    def palette(self, value):
        self._colorComboBox.colors = palette
