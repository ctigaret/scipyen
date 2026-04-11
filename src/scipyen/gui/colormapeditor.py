# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing
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
    

from core.prog import safewrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# don't use this yet, until we fully understand how to deal with VigraQt colormap
# mechanism from Python side
Ui_EditColorMapWidget, QWidget = loadUiType(adapt_ui_path(__module_path__,os.path.join("widgets","editcolormap2.ui")))


####don't use this yet, until we fully understand how to deal with VigraQt colormap
####mechanism from Python side
class ColorMapEditor(QWidget, Ui_EditColorMapWidget):
 def __init__(self, parent = None):
   super(ColorMapEditor, self).__init__(parent);
   self.setupUi(self);
   self.colormapeditor = VigraQt.ColorMapEditor(EditColorMapWidget);
   self.colormapeditor.setObjectName(_fromUtf8("ColorMapEditor"));
   self.verticalLayout.addWidget(self.colormapeditor);


