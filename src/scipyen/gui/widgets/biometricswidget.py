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
import pandas as pd
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
from core import scipyen_quantities as scq
from gui import guiutils, textviewer
from gui.widgets import small_widgets as smw
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_BiometricsWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "biometricswidget.ui")
    )

T = sdc.Biometrics

class BiometricsWidget(Ui_BiometricsWidget, QWidget, WorkspaceGuiMixin):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    _objectTypes_ = (sdc.Biometrics,)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.Biometrics] = None,
                 **kwargs):

        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        QWidget.__init__(self, parent=parent)
        title = kwargs.pop("title", f"{self._objectTypes_.__name__} Widget")
        WorkspaceGuiMixin.__init__(self, parent=parent, title=title, **kwargs)

        if not isinstance(obj, self._objectTypes_):
            self._data_ =  self._objectTypes_()
        else:
            self._data_ = obj

        self._geneticSexNames_ = list(sdc.GeneticSex.names())
        self._devStageNames_ = list(sdc.DevelopmentalStage.names())
        self._descriptionEditor = None

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.dataExchangeWidget.dataType = self._objectTypes_

        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.redoAvailable = True
        self.nameLineEdit.undoAvailable = True
        self.nameLineEdit.setText(self._data_.name)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)


        if isinstance(self._data_.genotype, str):
            self.genotypeLineEdit.setText(self._data_.genotype)
        else:
            self.genotypeLineEdit.setText(f"{self._data_.genotype}")

        self.genotypeLineEdit.setClearButtonEnabled(True)
        self.genotypeLineEdit.redoAvailable = True
        self.genotypeLineEdit.undoAvailable = True
        self.genotypeLineEdit.textChanged.connect(self._slot_genotypeNameChanged)
        # self.genotypeLineEdit.sig_enterPressed.connect(self._slot_genotypeChanged)

        for text in self._geneticSexNames_:
            self.geneticSexComboBox.addItem(text)

        ndx = self._geneticSexNames_.index(self._data_.geneticSex.name)
        self.geneticSexComboBox.setCurrentIndex(ndx)

        self.geneticSexComboBox.currentIndexChanged.connect(self._slot_geneticSexChanged)

        for text in self._devStageNames_:
            self.devStageComboBox.addItem(text)
        ndx = self._devStageNames_.index(self._data_.stage.name)
        self.devStageComboBox.setCurrentIndex(ndx)

        self.devStageComboBox.currentIndexChanged.connect(self._slot_devStageChanged)

        self.ageSpinBox.familyRestriction = "Time"
        self.ageSpinBox.setValue(self._data_.age)
        self.ageSpinBox.sig_valueChanged.connect(self._slot_ageChanged)

        self.weightSpinBox.familyRestriction = "Mass"
        self.weightSpinBox.setValue(self._data_.weight)
        self.weightSpinBox.sig_valueChanged.connect(self._slot_weightChanged)

        self.heightSpinBox.familyRestriction = "Length"
        self.heightSpinBox.setValue(self._data_.height)
        self.heightSpinBox.sig_valueChanged.connect(self._slot_heightChanged)

        self.descriptionToolButton.clicked.connect(self._slot_editDescription)


    @Slot(str)
    def _slot_nameChanged(self, val: str):
        if val is None:
            val = ""

        self._data_.name = val

        self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_genotypeNameChanged(self, val: str):
        if isinstance(val, str):
            if "NA" in val:
                self._data_.genotype = pd.NA
            else:
                self._data_.genotype = val
        else:
            self._data_.genotype = ""

        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_geneticSexChanged(self, val: int):
        name = self._geneticSexNames_[val]
        self._data_.geneticSex = sdc.GeneticSex[name]

        self.sig_valueChanged.emit(self._data_)

    @Slot(int)
    def _slot_devStageChanged(self, val:int):
        name = self._devStageNames_[val]
        self._data_.stage = sdc.DevelopmentalStage[name]

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_ageChanged(self):
        self._data_.age = self.ageSpinBox.value()

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_weightChanged(self):
        self._data_.weight = self.weightSpinBox.value()

        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_heightChanged(self):
        self._data_.height = self.heightSpinBox.value()

        self.sig_valueChanged.emit(self._data_)

    def setValue(self, val: typing.Optional[T] = None):
        if not isinstance(val, self._objectTypes_):
            val =  self._objectTypes_()

        self._data_ = val

        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                               (
                                   self.nameLineEdit,
                                   self.genotypeLineEdit,
                                   self.geneticSexComboBox,
                                   self.devStageComboBox,
                                   self.ageSpinBox,
                                   self.heightSpinBox,
                                   self.weightSpinBox
                                )
                               )
                           )

        self.nameLineEdit.setText(self._data_.name)
        self.genotypeLineEdit.setText(f"{self._data_.genotype}")
        ndx = self._geneticSexNames_.index(self._data_.geneticSex.name)
        self.geneticSexComboBox.setCurrentIndex(ndx)
        ndx = self._devStageNames_.index(self._data_.stage.name)
        self.devStageComboBox.setCurrentIndex(ndx)
        self.ageSpinBox.setValue(self._data_.age)
        self.weightSpinBox.setValue(self._data_.weight)
        self.heightSpinBox.setValue(self._data_.height)

    def value(self) -> T:
        return self._data_

    @property
    def objectSymbolVisible(self) -> bool:
        return self.objectSymbolLabel.isVisible()

    @objectSymbolVisible.setter
    def objectSymbolVisible(self, val: bool):
        self.objectSymbolLabel.setVisible(val is True)

    @Slot()
    def _slot_descriptionChanged(self):
        if isinstance(self._descriptionEditor, textviewer.TextViewer):
            self._data_.description = self._descriptionEditor.text(plain=True)
            self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_editDescription(self):
        if not isinstance(self._descriptionEditor, QtWidgets.QWidget):
            self._descriptionEditor = textviewer.TextViewer(self._data_.description,
                                                parent=self, edit=True,
                                                win_title="Edit description",
                                                doc_title="Edit description",
                                                title="Biometrics")
            # self._descriptionEditor.setVisible(False)
            self._descriptionEditor.sig_textChanged.connect(self._slot_descriptionChanged)

        self._descriptionEditor.setData(self._data_.description)
        self._descriptionEditor.show()

