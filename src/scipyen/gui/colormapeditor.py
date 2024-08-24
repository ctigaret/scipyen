# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# don't use this yet, until we fully understand how to deal with VigraQt colormap
# mechanism from Python side
Ui_EditColorMapWidget, QWidget = __loadUiType__(adapt_ui_path(__module_path__,os.path.join("widgets","editcolormap2.ui")))


####don't use this yet, until we fully understand how to deal with VigraQt colormap
####mechanism from Python side
class ColorMapEditor(QWidget, Ui_EditColorMapWidget):
 def __init__(self, parent = None):
   super(ColorMapEditor, self).__init__(parent);
   self.setupUi(self);
   self.colormapeditor = VigraQt.ColorMapEditor(EditColorMapWidget);
   self.colormapeditor.setObjectName(_fromUtf8("ColorMapEditor"));
   self.verticalLayout.addWidget(self.colormapeditor);


