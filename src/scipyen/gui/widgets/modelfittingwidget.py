# -*- coding: utf-8 -*-
# $Id: modelfittingwidget.py $
# SPDX-FileCopyrightText: 2022 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Widget for model parameter inputs
"""
import math, numbers, typing, os
import numpy as np
import quantities as pq
import pandas as pd
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True
    
from core.strutils import str2symbol
from core import models
from gui import guiutils
import gui.quickdialog as qd
from gui.widgets.small_widgets import QuantitySpinBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))
Ui_ModelFittingWidget, QWidget = loadUiType(os.path.join(__module_path__, "ModelFittingWidget.ui"))

class ModelFittingWidget(Ui_ModelFittingWidget, QWidget):
    def __init__(self, parent=None, **kwargs):
        QWidget.__init__(self, parent=parent)
        
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        
        self.modelParamsWidget.spinStep = 1e-4
        self.modelParamsWidget.spinDecimals = 4
        
        self.modelParamsWidget.sig_parameterChanged[str, str].connect(self._slot_modelParameterChanged)
        self.modelParamsWidget.sig_badBounds[str].connect(self._slot_badBounds)
        self.modelParamsWidget.sig_infeasible_x0[str].connect(self._slot_infeasible_x0s)
        
