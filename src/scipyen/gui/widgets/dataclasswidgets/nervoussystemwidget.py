# -*- coding: utf-8 -*-
# $Id: nervoussystemwidgets.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
# import numbers
# import numpy as np
# import quantities as pq
import pandas as pd
# import neo
# from tribool import Tribool

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
from core import taxonbridge
from core import bgbridge
from gui import datatreeviewer
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_NervousSystemWidget, _ = loadUiType(
    os.path.join(__module_path__, "nervoussystemwidget.ui")
    )

class NervousSystemWidget(Ui_NervousSystemWidget, DataClassWidget):
    r"""NOTE: This relates to ALL organs in a BrainGlobeAtlas, not just the brain!"""
    _objectTypes_ = (sdc.NervousSystem, )
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.BiologicalSource] = None,
                 **kwargs):
        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        DataClassWidget.__init__(self, parent=parent)

        if not isinstance(obj, self._objectTypes_):
            self._data_ = self._objectTypes_[0]()
        else:
            self._data_ = obj

        self._bman_ = bgbridge.BrainAtlasManager(self)

        self._atlas_ = None
        self._availableStructures_ = None

        self._localAtlasNames_ = ["Undefined"]
        # self._atlasStructureNamesAcronyms_ = {"Undefined": "Undefined"}

        if bgbridge.hasBrainGlobe and bgbridge.hasBrainGlobeAtlasAPI:
            for atlasName, atlasVersion in self._bman_.localAtlases.items():
                self._localAtlasNames_.append(f"{atlasName} ({atlasVersion})")

            if self._data_.atlasName in self._bman_.localAtlases:
                self._atlas_ = self._bman_.initAtlas(self._data_.atlasName)
                self._availableStructures_ = self._atlas_.lookup_df

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.bgStructureWidget.containerWidget = self

        self.dataExchangeWidget.dataType = type(self._data_)
        self.dataExchangeWidget.sig_requestDataExport.connect(self._slot_dataExportRequested)
        self.sig_dataExporting.connect(self.dataExchangeWidget.slot_exportData)
        self.dataExchangeWidget.sig_requestDataSave.connect(self._slot_dataSaveRequested)
        self.sig_dataSaving.connect(self.dataExchangeWidget.slot_saveData)
        self.dataExchangeWidget.sig_requestDataCopy.connect(self._slot_dataCopyRequested)
        self.sig_dataCopy.connect(self.dataExchangeWidget.slot_copyData)
        self.dataExchangeWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)
        self.dataExchangeWidget.sig_dataLoaded.connect(self._slot_dataReceived)
        self.dataExchangeWidget.sig_dataImported.connect(self._slot_dataReceived)
        self.dataExchangeWidget.sig_symbolChanged.connect(self._slot_symbolChanged)

        self.nameDescriptionWidget.dataName = self._data_.name
        self.nameDescriptionWidget.dataDescription = self._data_.description
        self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
        self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
        self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
        self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
        self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
        self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)

        for t in self._localAtlasNames_:
            self.brainAtlasComboBox.addItem(t)

        if isinstance(self._data_.atlasName, str) and self._data_.atlasName in self._bman_.localAtlases.keys():
            ndx = list(self._bman_.localAtlases.keys()).index(self._data_.atlasName) + 1 # to account for "Undefined"
            self.brainAtlasComboBox.setCurrentIndex(ndx)

        else:
            self.brainAtlasComboBox.setCurrentIndex(0) # use "Undefined"

        self.brainAtlasComboBox.currentIndexChanged.connect(self._slot_atlasChanged)

        if (bgbridge.hasBrainGlobe
            and bgbridge.hasBrainGlobeAtlasAPI):
            if (isinstance(self._atlas_, bgbridge.BrainGlobeAtlas)
            and "brainglobe_atlasapi" in type(self._atlas_).__module__):
                self.bgStructureWidget.atlas = self._atlas_
                if (isinstance(self._data_.structure, bgbridge.Structure)
                    and "brainglobe_atlasapi" in type(self._data_.structure).__module__):
                    self.bgStructureWidget.setValue(self._data_.structure)

        self.bgStructureWidget.sig_valueChanged.connect(self._slot_structureChanged)

    @Slot(object)
    def _slot_structureChanged(self, val: object):
        self._data_.structure = val

    @Slot(int)
    def _slot_atlasChanged(self, val: int):
        if not isinstance(val, int) or val <= 0 or val >=len(self._bman_.localAtlases):
            self._data_.atlasName = pd.NA

        else:
            self._data_.atlasName = list(self._bman_.localAtlases.keys())[val-1]

        if self._data_.atlasName in self._bman_.localAtlases:
            self._atlas_ = self._bman_.initAtlas(self._data_.atlasName)
            self.bgStructureWidget.atlas = self._atlas_
            if self._data_.structure["id"] not in self._atlas_.structures:
                self._data_.structure = None
                self.bgStructureWidget.setValue(None)


        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_lookupStructure(self):
        pass


