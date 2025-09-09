# -*- coding: utf-8 -*-
# $Id: Abou new small widgets.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# CAUTION Won't compile

Might not be necesary to subclass stock QtWidgets below.

Editables:
    int -> IntWidget(QSpinBox)
        singleStep:int=1
        minimum:int, maximum:int by cconstructor
        prefix:str, suffix:str by constructor
        stepType:QAbstractSpinBox.StepType = QAbstractSpinBox.defaultStepType
        
    float -> FloatWidget (QDoubleSpinBox):
        decimals by constructor

    complex -> two FloatWidgets (real, imag)

    Quantity -> QuantityChooserWidget Quantitywidget
        
    str: QLineEdit

    bool: QCheckBox

    tribool: QCheckBox (tristate=True)

Non-editables:
    Enum -> EnumWidget (QComboBox):
        editable:bool = False
        maxCount:int = number of enum values defined in the Enum (sub)class
        duplicatesEnabled:bool = False
        maxVisibleItems:int = min(10, maxCount)
        
        contentx by constructor
        
        to connect to currentIndexChanged(int), currentTextChanged(str)
        
    VigraArray, 2D+ numpy array with non-singleton axes -> QPushButton, launch imageviewer, or, if 2D/3D signalviewer or matplotlib figure
    neo data object, ≤2D numpy array -> QPushButton, launch signalviewer or matplotlib figure
    neo collection object -> signalviewer

Compound:
    dataclass: QPushButton, label is the field name:
        action -> launch another window (or dialog?) with dataclasswidget 
    
    list, tuple, deque: QTableView with delegates according to element type (see Non-editables)
        In addition, allow insertion/removal of elements in list & deque
        
    dict, mapping:
        InteractiveTreeWidget using delegate widgets according to element type, as describe throughout here

