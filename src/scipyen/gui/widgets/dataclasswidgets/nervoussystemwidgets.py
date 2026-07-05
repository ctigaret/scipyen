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

Ui_BGAtlasStructureLookupWidget, _ = loadUiType(
    os.path.join(__module_path__, "brainglobeatlasstructurelookup.ui")
    )

class BGAtlasStructureLookupWidget(Ui_BGAtlasStructureLookupWidget, QtWidgets.QWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 atlas: typing.Optional[bgbridge.BrainGlobeAtlas] = None,
                 structure: typing.Optional[bgbridge.Structure] = None,
                 **kwargs):
        super().__init__(parent=parent)


        self._atlas_ = atlas
        self._structure_ = structure
        self._parseStructureAncestorsAndDescendants()

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self._setup_UIFields()
        self.acronymOrNameEdit.lazy=True
        self.acronymOrNameEdit.undoEnabled = True
        self.acronymOrNameEdit.redoEnabled = True
        self.acronymOrNameEdit.setClearButtonEnabled(True)
        self.acronymOrNameEdit.sig_enterPressed.connect(self._slot_lookupStructure)
        self.ancestorComboBox.currentIndexChanged.connect(self._slot_ancestorSelected)
        self.descendantComboBox.currentIndexChanged.connect(self._slot_descendantSelected)


    def _setup_UIFields(self):
        sigBlockers = list(
                            map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (self.ancestorComboBox,
                                 self.descendantComboBox,
                                 self.acronymOrNameEdit
                                )
                               )
                           )

        self.structureIDAcroNameLabel.setText(self._structureIdentityText_)
        self.ancestorComboBox.clear()

        for t in ["None"] + list(self._ancestors_.keys()):
            self.ancestorComboBox.addItem(t)

        self.ancestorComboBox.setCurrentIndex(0)

        self.descendantComboBox.clear()

        for t in ["None"] + list(self._descendants_.keys()):
            self.descendantComboBox.addItem(t)

        self.descendantComboBox.setCurrentIndex(0)
        self.structureTreeView.readOnly=True
        self.structureTreeView.setData(self._structure_, "structure")
        self.acronymOrNameEdit.clear()

    def _getStructure_(self, val: str) -> bgbridge.Structure | None:
        if (
            bgbridge.hasBrainGlobe and bgbridge.hasBrainGlobeAtlasAPI
            and isinstance(self._atlas_, bgbridge.BrainGlobeAtlas)
            and "brainglobe_atlasapi" in type(self._atlas_).__module__
            ):
            return bgbridge.get_atlas_structure(val, self._atlas_)


    def _parseStructureAncestorsAndDescendants(self):
        self._ancestors_ = dict()
        self._descendants_ = dict()
        self._structureIdentityText_ = ""

        if (
            bgbridge.hasBrainGlobe and bgbridge.hasBrainGlobeAtlasAPI
            ):
            if isinstance(self._structure_, bgbridge.Structure) and "brainglobe_atlasapi" in type(self._structure_).__module__:
                self._structureIdentityText_ = f"{self._structure_['acronym']}: {self._structure_['name']} (ID: {self._structure_['id']})"

                if isinstance(self._atlas_, bgbridge.BrainGlobeAtlas) and "brainglobe_atlasapi" in type(self._atlas_).__module__:
                    self._ancestors_ = dict(
                        map(
                            lambda a: (self._atlas_.structures[a]["acronym"],
                                       (self._atlas_.structures[a]["name"], self._atlas_.structures[a]["id"])),
                            list(reversed(self._atlas_.get_structure_ancestors(self._structure_["id"])))
                            )
                        )

                    self._descendants_ = dict(
                        map(
                            lambda a: (self._atlas_.structures[a]["acronym"],
                                       (self._atlas_.structures[a]["name"], self._atlas_.structures[a]["id"])),
                            list(reversed(self._atlas_.get_structure_descendants(self._structure_["id"])))
                            )
                        )

    @Slot(str)
    def _slot_lookupStructure(self, val: str):
        if (bgbridge.hasBrainGlobe and bgbridge.hasBrainGlobeAtlasAPI
            and isinstance(self._atlas_, bgbridge.BrainGlobeAtlas) and "brainglobe_atlasapi" in type(self._atlas_).__module__):
            self._structure_ = self._getStructure_(val)
            if isinstance(self._structure_, bgbridge.Structure):
                self._parseStructureAncestorsAndDescendants()
                self._setup_UIFields()
                self.sig_valueChanged.emit(self._structure_)

    @Slot(int)
    def _slot_ancestorSelected(self, val: int):
        if (not bgbridge.hasBrainGlobe or not bgbridge.hasBrainGlobeAtlasAPI or len(self._ancestors_) == 0):
            return

        if val > 0:
            name = list(self._ancestors_.keys())[val-1]
            self._structure_ = self._getStructure_(name)
            if isinstance(self._structure_, bgbridge.Structure):
                self._parseStructureAncestorsAndDescendants()
                self._setup_UIFields()
                self.sig_valueChanged.emit(self._structure_)

    @Slot(int)
    def _slot_descendantSelected(self, val: str):
        if (not bgbridge.hasBrainGlobe or not bgbridge.hasBrainGlobeAtlasAPI or len(self._descendants_) == 0):
            return

        if val > 0:
            name = list(self._descendants_.keys())[val-1]
            self._structure_ = self._getStructure_(name)
            if isinstance(self._structure_, bgbridge.Structure):
                self._parseStructureAncestorsAndDescendants()
                self._setup_UIFields()
                self.sig_valueChanged.emit(self._structure_)

    @property
    def atlas(self) -> bgbridge.BrainGlobeAtlas | None:
        return self._atlas_

    @atlas.setter
    def atlas(self, val: bgbridge.BrainGlobeAtlas):
        self._atlas_ = val
        self._parseStructureAncestorsAndDescendants()
        self._setup_UIFields()
        self.sig_valueChanged.emit(self._structure_)

    def value(self) -> bgbridge.Structure:
        return self._structure_

    def setValue(self, val: bgbridge.Structure):
        self._structure_ = val
        self._parseStructureAncestorsAndDescendants()
        self._setup_UIFields()
        self.sig_valueChanged.emit(self._structure_)



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

        if isinstance(self._data_.atlasName, str) and self._data_.atlasName in bman.localAtlases.keys():
            ndx = list(bman.localAtlases.keys()).index(self._data_.atlasName) + 1 # to account for "Undefined"
            self.brainAtlasComboBox.setCurrentIndex(ndx)

        else:
            self.brainAtlasComboBox.setCurrentIndex(0) # use "Undefined"

        self._structureLookupWidget_ = None

        self.brainAtlasComboBox.currentIndexChanged.connect(self._slot_atlasChanged)

        self.structureLookupToolButton.clicked.connect(self._slot_lookupStructure)

    @Slot(int)
    def _slot_atlasChanged(self, val: int):
        if not isinstance(val, int) or val <= 0 or val >=len(bman.localAtlases):
            self._data_.atlasName = pd.NA

        else:
            self._data_.atlasName = list(bman.localAtlases.keys())[val-1]

        # if self._data_atlasName in bman.localAtlases:


        self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_lookupStructure(self):
        pass


