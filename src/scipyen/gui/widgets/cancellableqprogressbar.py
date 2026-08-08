# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os
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
    

import typing, os
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

try:
    from gui.widgets.cancellableqprogressbar_ui import Ui_CancellableQProgressBar

except:
    __ui_path__ = adapt_ui_path(__module_path__, "cancellableqprogressbar.ui")
    Ui_CancellableQProgressBar, QWidget = loadUiType(__ui_path__)


class CancellableQProgressBar(QtWidgets.QWidget, Ui_CancellableQProgressBar):
    r"""No frills; just adds a cancel button.
    Minimal funcitonality; additional code to be implemented (currently, the
    following properties are as per QProgressBar default, and those markes with
    ✓ are accessible here as read-only):
    • alignment
    • format
    • invertedAppearance
    • orientation
    • text  ✓
    • textDirection ✓
    • textVisible ✓
    
    NOTE: The QPRogressBar API is nevertheless fully accessible through the 
    `self.progressBar` attribute!
    
    """
    canceled = Signal(name="canceled")
    valueChanged = Signal(int, name="valueChanged")
    
    def __init__(self, parent = None, **kwargs):
        super().__init__(parent=parent)
        super(Ui_CancellableQProgressBar, self).__init__()
        self._configureUI_()
        
    def _configureUI_(self):
        self.setupUi(self)
        self.progressBar.setRange(0,0)
        self.progressBar.valueChanged[int].connect(self.valueChanged)
        # self.cancelButton.triggered[object].connect(self._slot_cancel())
        # self.cancelButton.clicked.connect(self._slot_cancel())
        self.cancelButton.clicked.connect(self.canceled)
        
    def minimum(self):
        return self.progressBar.minimum()
    
    def maximum(self):
        return self.progressBar.maximum()
    
    def resetFormat(self):
        self.progressBar.resetFormat()
        
    def text(self) -> str:
        return self.progressBar.text()
    
    def textDirection(self) -> QtWidgets.QProgressBar.Direction:
        return self.progressBar.textDirection()
    
    def value(self) -> int:
        return self.progressBar.value()
    
    def isTextVisible(self)->bool:
        return self.progressBar.isTextVisible()
    
    def format(self) -> str:
        return self.progressBar.format()
    
    # @Slot(object)
    # def _slot_cancel(self, o:object):
    @Slot()
    def _slot_cancel(self):
        self.canceled.emit()
        
    @Slot(int)
    def setValue(self, val:int):
        self.progressBar.setValue(val)
    
    @Slot(int)
    def setMinimum(self, val:int):
        self.progressBar.setMinimum(val)
        
    @Slot(int)
    def setMaximum(self, val:int):
        self.progressBar.setMaximum(val)
        
    @Slot(int, int)
    def setRange(self, minimum:int, maximum:int):
        self.progressBar.setRange(minimum, maximum)
        
    @Slot()
    def reset(self):
        self.progressBar.reset()
        
    @Slot()
    def close(self):
        super().close()
        
