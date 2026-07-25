# -*- coding: utf-8 -*-
# $Id: bgatlasstructurewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
# import numbers
# import numpy as np
# import quantities as pq
# import pandas as pd
# import neo
# from tribool import Tribool

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
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
# from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
# from core import taxonbridge
from core import bgbridge
from core import qtutils
from gui import datatreeviewer
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

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

        containerWidget: typing.Optional[QtWidgets.QWidget] = kwargs.pop("containerWidget", None)

        p = self.parent()
        parents = list()
        while isinstance(p, QtWidgets.QWidget):
            parents.append(p)
            p = p.parent()

        if isinstance(containerWidget, QtWidgets.QWidget) and containerWidget in parents:
            self._containerWidget_ = containerWidget

        else:
            self._containerWidget_ = None

        self._atlas_ = atlas
        self._structure_ = structure
        self._parseStructureAncestorsAndDescendants()
        self.detailsViewer = None

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self._setup_UIFields()
        self.acronymOrNameEdit.lazy=True
        self.acronymOrNameEdit.undoEnabled = True
        self.acronymOrNameEdit.redoEnabled = True
        self.acronymOrNameEdit.setClearButtonEnabled(True)
        self.acronymOrNameEdit.sig_textChanged.connect(self._slot_lookupStructure)
        self.ancestorComboBox.currentIndexChanged.connect(self._slot_ancestorSelected)
        self.descendantComboBox.currentIndexChanged.connect(self._slot_descendantSelected)
        self.structureTreeView.readOnly=True
        self.detailsToolButton.clicked.connect(self._slot_showDetails)

    def _setup_UIFields(self):
        # BUG: 2026-07-06 11:10:34 FIXME in DataTreeViewer TODO
        # do NOT block signals from this one as it will prevent updating itself
        #
        sigBlockers = list(
                            map(
                                lambda w: QtCore.QSignalBlocker(w),
                                (self.ancestorComboBox,
                                 self.descendantComboBox,
                                 self.acronymOrNameEdit,
                                 # self.detailsViewer,
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
        self.acronymOrNameEdit.clear()

        if isinstance(self._containerWidget_, DataClassWidget):
            self.structureTreeView.setEnabled(False)
            self.structureTreeView.setVisible(False)
            self.detailsToolButton.setEnabled(True)
            self.detailsToolButton.setVisible(True)
            if (isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer)
                and self.detailsViewer.isVisible()
                ):
                # print(f"{self.__class__.__name__}._setup_UIFields -> updating details viewer for structure {self._structure_}")
                self.detailsViewer.view(self._structure_, doc_title="structure")

        else:
            self.structureTreeView.setEnabled(True)
            self.structureTreeView.setVisible(True)
            self.detailsToolButton.setEnabled(False)
            self.detailsToolButton.setVisible(False)
            self.structureTreeView.setData(self._structure_, "structure")

        # self.structureTreeView.readOnly=True

    def closeEvent(self, evt):
        if isinstance(self.detailsViewer, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.detailsViewer):
            self.detailsViewer.close()
            self.detailsViewer.deleteLater()
            self.detailsViewer = None

        super.closeEvent(evt)
        evt.accept()

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
        if not isinstance(val, str) or len(val.strip()) == 0:
            return
        if (bgbridge.hasBrainGlobe and bgbridge.hasBrainGlobeAtlasAPI
            and isinstance(self._atlas_, bgbridge.BrainGlobeAtlas) and "brainglobe_atlasapi" in type(self._atlas_).__module__):
            self._structure_ = self._getStructure_(val)
            if isinstance(self._structure_, bgbridge.Structure):
                self._parseStructureAncestorsAndDescendants()
                self._setup_UIFields()
                self.sig_valueChanged.emit(self._structure_)

    @Slot()
    def _slot_showDetails(self):
        if not isinstance(self._containerWidget_, DataClassWidget):
            return

        if not isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer):
            scipyenWindow = getattr(self.containerWidget, "scipyenWindow", None)
            self.detailsViewer = datatreeviewer.DataTreeViewer(
                scipyenWindow = scipyenWindow,
                readOnly=True
                )
            # self.detailsViewer.readOnly = True

        self.detailsViewer.view(self._structure_, doc_title="structure")


    @Slot(int)
    def _slot_ancestorSelected(self, val: int):
        # print(f"{self.__class__.__name__}._slot_ancestorSelected({val})")
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
        # print(f"{self.__class__.__name__}._slot_descendantSelected({val})")
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
    def containerWidget(self) -> QtWidgets.QWidget | None:
        return self._containerWidget_

    @containerWidget.setter
    def containerWidget(self, obj: typing.Optional[QtWidgets.QWidget] = None):
        if not isinstance(obj, QtWidgets.QWidget):
            self._containerWidget_ = None

        parents = list()
        p = self.parent()
        while isinstance(p, QtWidgets.QWidget):
            parents.append(p)
            p = p.parent()

        if obj in parents:
            self._containerWidget_ = obj

        self._setup_UIFields()


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

