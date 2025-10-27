# -*- coding: utf-8 -*-
# $Id: delegates.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import os, sys, typing, math
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
    
__has_qtdbus__ = False

try:
    from qtpy import QtDBus
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from core.prog import (safewrapper, safeguiwrapper, scipywarn, print_styled)
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import quantities as pq
from core import scipyen_quantities as scq
from gui.widgets import small_widgets as smw
from gui import quickdialog as qd

class PythonItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self._model_ = None
        
    def createEditor(self, parent:QtWidgets.QWidget, option:int, index:QtCore.QModelIndex) -> QtWidgets.QWidget | None:
        # NOTE: 2025-09-27 10:29:14 ATTENTION
        # editor data, although it can also be set here, it should be set through
        # self.setEditorData(), overridden below
        data = index.data(QtCore.Qt.EditRole)
        disp = index.data(QtCore.Qt.DisplayRole)
        
        # NOTE: 2025-09-27 11:06:52
        # some models may be able to prevent editing indexes with certain rows
        # and/or columns; AFAIK, this functionality is not provided by stock Qt 
        # item# models and must be implemented in my custom QAbstractItemModel
        # subclasses (e.g. TabularDataModel in tableeditorwidget.py). My implementation
        # uses two pythonic properties of the item model: 'immutableColumns' and
        # 'immutableRows', which I use below
        model = index.model()
        
        if hasattr(model, "immutableColumns") and hasattr(model, "immutableRows"):
            if index.column() in model.immutableColumns and index.row() in model.immutableRows:
                return
        
        # print(f"{self.__class__.__name__}.createEditor:\n\t data type: {type(data).__name__}")
        
        # TODO: 2025-09-25 23:42:02
        # for datetime.datetime use QDateTimeEdit (with QDate and QTime)
        # for datetime.date use QDateEdit (with QDate)
        # for datetime.time use QTimeEdit (with QTime)
        
        if isinstance(data, int) or "int" in type(data).__name__: # to include numpy array int dtypes
            widget = QtWidgets.QSpinBox(parent)
            widget.setMinimum(-1000)
            widget.setMaximum(1000)
            
        elif isinstance(data, float) or "float" in type(data).__name__: # to include numpy array float dtypes
            widget = QtWidgets.QDoubleSpinBox(parent)
            widget.setMinimum(-1e3)
            widget.setMaximum(1e3)
            widget.setSingleStep(1)
            
        elif isinstance(data, pq.Quantity):
            if isinstance(data, pq.UnitQuantity): # unlikely, but here we go...
                widget = smw.QuantityChooserWidget(parent)
            else:
                if data.ndim > 0: # no editing of Quantity ARRAYS; only scalar Quantities can be edited; unlikely to encounter this, but here we go...
                    return
                widget = smw.QuantitySpinBox(parent, enforceImmutableUnits=True) # disallow units change for individual data points in a Quantity
                widget.setMinimum(-math.inf * data.units)
                widget.setMaximum(math.inf * data.units)
                widget.setSingleStep(1.0  * data.units)
                widget.disableUnitChange = True
                
        elif isinstance(data, str) or "str" in type(a).__name__: # for numpy.str_ type
            widget = QtWidgets.QLineEdit(parent)
            
        else: # TODO: 2025-09-23 16:16:56 FIXME use a pushbutton to open a complex viewer/editor
            return
        
        widget.setFrame(False)
        widget.setAutoFillBackground(True)
        return widget
    
    def setEditorData(self, editor:QtWidgets.QWidget, index:QtCore.QModelIndex):
        data = index.data(QtCore.Qt.EditRole)
        disp = index.data(QtCore.Qt.DisplayRole)

        if isinstance(data, int) or "int" in type(data).__name__:
            assert isinstance(editor, QtWidgets.QSpinBox), f"Incompatible editor widget type ({type(editor).__name__}) for integer data"
            editor.setValue(data)
            
        elif isinstance(data, float) or "float" in type(data).__name__:
            assert isinstance(editor, QtWidgets.QDoubleSpinBox), f"Incompatible editor widget type ({type(editor).__name__}) for floating point data"
            # NOTE: 2025-09-27 10:31:43
            # figure out how many decimals we've got here, see also NOTE: 2025-09-27 10:31:23
            if "." in disp:
                decimals = len(disp[disp.index("."):])
            else:
                decimals = 0
            editor.setDecimals(decimals)
            editor.setValue(data)
            
        elif isinstance(data, pq.Quantity):
            if isinstance(data, pq.UnitQuantity):
                assert isinstance(editor, smw.QuantityChooserWidget), f"Incompatible editor widget type ({type(editor).__name__}) for UnitQuantity data"
            else:
                assert isinstance(editor, smw.QuantitySpinBox), f"Incompatible editor widget type ({type(editor).__name__}) for Quantity data"
                if data.ndim > 0: # no editing of Quantity ARRAYS; only scalar Quantities can be edited; unlikely to encounter this, but here we go...
                    return
                # NOTE: 2025-09-27 10:31:23
                # figure out how many decimals are shown — needed to set up the "decimals" property of the spin box
                # (NOTE: the actual number of decimals displayed in the spin box depends on the column width, 
                #        but at least we avoid scientific notation which can hide the visual of the value)
                # below, 's0' is the string representation of the Quantity's magnitude (as a float)
                units_str = data.units.dimensionality.unicode
                if units_str in disp:
                    s0 = disp.strip(units_str).strip()
                else:
                    s0 = disp.split(" ")[0].strip()
                    
                if "." in s0:
                    decimals = len(s0[s0.index(".")-1:]) # count the dot as well
                else:
                    decimals = 0
                    
                editor.setDecimals(decimals)
                # editor.setSingleStep(1.0  * data.units)
            editor.setValue(data)
                
        elif isinstance(data, str) or "str" in type(a).__name__:
            assert isinstance(editor, QtWidgets.QLineEdit), f"Incompatible editor editor type ({type(editor).__name__}) for string data"
            editor.setText(data)
            
            
    def setModelData(self, editor:QtWidgets.QWidget, model:QtCore.QAbstractItemModel, index:QtCore.QModelIndex):
        if isinstance(editor, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox, smw.QuantitySpinBox)):
            data = editor.value()
        elif isinstance(editor, QtWidgets.QLineEdit):
            data = editor.text()
        # print(f"{self.__class__.__name__}.setModelData -> data = {data}")
        model.setData(index, data, QtCore.Qt.EditRole)
