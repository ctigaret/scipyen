# -*- coding: utf-8 -*-
# $Id: biometricswidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
import numbers
import numpy as np
import quantities as pq
import neo
from tribool import Tribool

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus # noqa
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
from gui import guiutils
from gui.widgets import small_widgets as smw

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_BiometricsWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "biometricswidget.ui")
    )

class BiometricsWidget(Ui_BiometricsWidget, QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.Biometrics] = None)

    QWidget.__init__(self, parent=parent)`

    if not isinstance(obj, sdc.Biometrics):
        self._data_ = sdc.Biometrics()
    else:
        self._data_ = obj

    self._geneticSexNames_ = list(sdc.GeneticSex.names())
    self._devStageNames_ = list(sdc.DevelopmentalStage.names())

    self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        if isinstance(self._data_.genotype, str):
            self.genotypeLineEdit.setText(self._data_.genotype)
        else:
            self.genotypeLineEdit.setText(f"{self._data_.genotype}")
        self.genotypeLineEdit.
        for text in self._geneticSexNames_:
            self.geneticSexComboBox.addItem(text)
            ndx = self._geneticSexNames_.index(self._data_.geneticSex.name)
            self.geneticSexComboBox.setCurrentIndex(ndx)

        for text in self._devStageNames_:
            self.devStageComboBox.addItem(text)
            ndx = self._devStageNames_.index(self._data_.stage)
            self.devStageComboBox.setCurrentIndex(ndx)

        self.ageSpinBox.setValue(self._data_.age)
        self.weightSpinBox.setValue(self._data_.weight)
        self.heightSpinBox.setValue(self._data_.height)
