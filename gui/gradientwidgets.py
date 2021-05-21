""" see qt examples/widgets/painting/gradients
"""
import array, os, typing, numbers
import numpy as np
from collections import OrderedDict
from enum import IntEnum, auto
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

from .colorwidgets import (transparent_painting_bg, make_checkers,
                           comboDelegateBrush)

class ShadeWidget(QtWidgets.QWidget):
    class ShadeType(IntEnum):
        RedShade = auto()
        GreenShade = auto()
        Blueshade = auto()
        ARGBShade = auto()
        
    def __init__(self, shadeType:ShadeWidget.ShadeType, 
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        
        super().__init__(parent=parent)
        
        self._shadeType = shadeType
        
        self._alphaGradient = QtGui.QLinearGradient(0, 0, 0, 0)
        
        if self._shadeType == Shadewidget.ShadeType.ARGBShade:
            # create checkers background for Alpha channel display
            pm = make_checkers(QtCore.Qt.lightGray, QtCore.Qt.darkGray, 20)
            pal = QtGui.QPalette()
            pal.setBrush(self.backgroundRole(), QtGui.QBrush(pm))
            self.setAutoFillBackground(True)
            self.setPalette(pal)
            
        else:
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
            
        points = QtGui.QPolygonF([QtCore.QPointF(0, self.sizeHint().heignt()),
                                  QtCore.QPointF(self.sizeHint().width(), 0)])
            
        
