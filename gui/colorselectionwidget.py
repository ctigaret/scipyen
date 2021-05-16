import os, typing

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from . import colorwidgets
from .colorwidgets import (ColorComboBox, ColorPushButton,
                           paletteColor, standardColor, standardPalette,)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class ColorSelectionWidget(QtWidgets.QWidget):
    def __init__(self, color:QtGui.QColor, defaultColor:QtGui.QColor,
                 alphaChannelEnabled:bool = True, useDefaultColor=True,
                 palette:typing.Optional[list]=None,
                 strongTransparentPattern:bool=False, 
                 keepAlphaOnDropPaste=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._colorPushButton = colorwidgets.ColorPushButton(color=color, 
                                                            defaultColor=defaultColor,
                                                            alphaChannelEnabled=alphaChannelEnabled,
                                                            useDefaultColor=useDefaultColor,
                                                            strongTransparentPattern=strongTransparentPattern,
                                                            keepAlphaOnDropPaste=keepAlphaOnDropPaste,
                                                            parent=self)
        
        self._comboColorBox = colorwidgets.ColorComboBox(palette=palette,
                                                        alphaChannelEnabled=alphaChannelEnabled,
                                                        parent=self)
        
        self._configureUI_()
        
    def _configureUI_(self):
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(2)
        for w in (self._comboColorBox, self._colorPushButton):
            self._layout.addWidget(w)
            
        
        
        
