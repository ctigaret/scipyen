# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
import os
import qtpy as QtAPI
QtAPI.API = os.environ["QT_API"]
if os.environ["QT_API"] == "pyside6":
    import PySide6
    QtAPI = PySide6
else:
    pass
from qtpy import QtCore, QtGui, QtWidgets, QtXml
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__

from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__, "linearrangemappingwidget.ui")

# Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(os.path.join(__module_path__, "linearrangemappingwidget.ui"))
Ui_LinearRangeMappingWidget, QWidget = __loadUiType__(__ui_path__)

# TODO
