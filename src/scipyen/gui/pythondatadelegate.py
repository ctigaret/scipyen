# -*- coding: utf-8 -*-
# $Id: pythondatadelegate.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
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

from core.prog import (safewrapper, safeguiwrapper, scipwarn, printStyled)
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import quantities as pq
from core import scipyen_quantities as scq
from gui.widgets import small_widgets as smw
from gui import quickdialog as qd

class PythonDataDelegate(QtWidgets.QStyleItemDelegate):
    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self._model_ = None
        
    def createEditor(self, parent:QtWidgets.QWidget, option:int, index:QtCore.QModelIndex) -> QtWidgets.QWidget | None:
        data = index.data(QtCore.Qt.EditRole)
        
        if isinstance(data, int):
            widget = QtWidgets.QSpinBox(parent)
        elif isinstance(data, float):
            widget = QtWidgets.QDoubleSpinBox(parent)
        elif isinstance(data, pq.Quantity):
            if not isinstance(data, pq.UnitQuantity):
                widget = smw.QuantitySpinBox(parent)
            else:
                widget = smw.QuantityChooserWidget(parent)
        elif isinstance(data, str):
            widget = QtWidgets.QLineEdit(parent)
        else: # TODO: 2025-09-23 16:16:56 FIXME use a pushbutton to open a complex viewer/editor
            widget = QtWidgets.QLineEdit(parent)
        widget.setFrame(False)
        widget.setAutoFillBackground(True)
        return widget
        
