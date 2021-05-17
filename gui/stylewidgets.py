import array, os, typing
import numpy as np

from enum import IntEnum
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__

from core.prog import (safeWrapper, no_sip_autoconversion)

from .scipyen_colormaps import (qtGlobalColors, standardPalette,
                                standardPaletteDict, svgPalette,
                                getPalette, paletteQColors, paletteQColor, 
                                standardQColor, svgQColor,
                                qtGlobalColors, mplColors)

from .colorwidgets import (make_transparent_pattern, )

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class PenComboDelegate(QtWidgets.QAbstractItemDelegate):
    pass

class BrushComboDelegate(QtWidgets.QAbstractItemDelegate):
    pass

class PenComboBox(QtWidgets.QComboBox):
    pass

class BrushComboBox(QtWidgets.QComboBox):
    pass

