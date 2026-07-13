# -*- coding: utf-8 -*-
# $Id: dataclasswidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
from functools import singledispatchmethod
# import numbers
# import dataclasses
# import numpy as np
# import quantities as pq
# import pandas as pd
# import neo
# from tribool import Tribool

# import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot)# , Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
    __has_PySide6__ = True
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from core.prog import scipywarn #, safewrapper, print_styled
# from core.sysutils import adapt_ui_path

# import core.bgbridge as bgbridge

from core import scipyen_quantities as scq
# from core import strutils
# from core.datatypes import UnitTypes, GENOTYPES

# from core import workspacefunctions as wsf
# from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
# from gui.widgets.datatreeview import DataTreeView

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
from core import qtutils
# from gui import guiutils, textviewer, datatreeviewer
from gui.datatreeviewer import DataTreeViewer
from gui.textviewer import TextViewer
from gui.widgets.dataclasswidgets.dataexchangewidget import DataExchangeWidget
from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets import small_widgets as smw
# from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

class DataClassWidget(QtWidgets.QWidget, WorkspaceGuiMixin):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_dataSaving = Signal(object, name="sig_dataSaving")
    sig_dataExporting = Signal(object, name="sig_dataExporting")
    sig_dataCopy = Signal(object, name="sig_dataCopy")
    sig_detailedView = Signal(object, str, name="sig_detailedView")
    _objectTypes_ = tuple()

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None, **kwargs):
        isAttribute = kwargs.pop("isAttribute", False)
        self._objSymbol_ = kwargs.pop("objSymbol", None)

        self.dataExchangeWidget = None
        self.nameDescriptionWidget = None
        self.editParentToolButton = None
        self.parentEditor = None

        QtWidgets.QWidget.__init__(self, parent=parent)
        self._isAttribute_: bool = isAttribute
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)

        if self._objSymbol_ is None or (isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()) == 0):
            objSymbols = self.getDataSymbolInWorkspace(self._data_)
            if isinstance(objSymbols, typing.Sequence) and len(objSymbols) > 0:
                self._objSymbol_ = objSymbols[0]

    def _configureUI_(self):
        r"""MUST be called in the subclass once self._data_ was established,
        AND first thing after setupUi() was called in the subclass"""
        if isinstance(self.dataExchangeWidget, DataExchangeWidget) and isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
            self.dataExchangeWidget.setValue(self._data_, self._objSymbol_)
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
            self.nameDescriptionWidget.sig_parentEditRequest.connect(self._slot_editParent)
            self.nameDescriptionWidget.sig_newParentRequest.connect(self._slot_chooseNewParentType)
            self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
            self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
            self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)

            self.nameDescriptionWidget.editParentToolButton.setEnabled(False)
            self.nameDescriptionWidget.editParentToolButton.setVisible(False)
            self.nameDescriptionWidget.replaceParentToolButton.setEnabled(False)
            self.nameDescriptionWidget.replaceParentToolButton.setVisible(False)

            if (
                hasattr(self, "_data_")
                and hasattr(self._data_, "parent")
                ):
                self.nameDescriptionWidget.editParentToolButton.setEnabled(True)
                self.nameDescriptionWidget.editParentToolButton.setVisible(True)

                if (
                    hasattr(self._data_, "parentTypes")
                    and len(self._data_.parentTypes) > 1
                    ):
                    self.nameDescriptionWidget.replaceParentToolButton.setEnabled(True)
                    self.nameDescriptionWidget.replaceParentToolButton.setVisible(True)

    def value(self) -> None:
        r"""Must override in subclasses"""
        pass

    def setValue(self, *args, **kwargs):
        r"""Must override in subclasses, and called from there as super().setValue(…).
        Implementations must make sure it emits sig_valueChanged Qt signal.
        """
        if len(args):
            value = args[0]
            self._objSymbol_ = kwargs.pop("objSymbol", None)
            if self._objSymbol_ is None or (isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()) == 0):
                objSymbols = self.getDataSymbolInWorkspace(value)
                if len(objSymbols) > 0:
                    self._objSymbol_ = objSymbols[0]
                else:
                    self._objSymbol_ = ""

            if isinstance(self.dataExchangeWidget, DataExchangeWidget) and isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
                if hasattr(self, "_data_"):
                    sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                                        (
                                            self.dataExchangeWidget,
                                            self.nameDescriptionWidget,
                                            )
                                        )
                                    )

                    self.dataExchangeWidget.setValue(self._data_, self._objSymbol_)
                    self.nameDescriptionWidget.dataName = self._data_.name
                    self.nameDescriptionWidget.dataDescription = self._data_.description

                    if (isinstance(self.nameDescriptionWidget.detailsViewer, DataTreeViewer)
                        and self.nameDescriptionWidget.detailsViewer.isVisible()):
                        self.nameDescriptionWidget.detailsViewer.view(self._data_,
                                                                    doc_title = self._objSymbol_,
                                                                    name = self._objSymbol_)

                    self.nameDescriptionWidget.editParentToolButton.setEnabled(False)
                    self.nameDescriptionWidget.editParentToolButton.setVisible(False)
                    self.nameDescriptionWidget.replaceParentToolButton.setEnabled(False)
                    self.nameDescriptionWidget.replaceParentToolButton.setVisible(False)

                    if hasattr(self._data_, "parent"):
                        self.nameDescriptionWidget.editParentToolButton.setEnabled(True)
                        self.nameDescriptionWidget.editParentToolButton.setVisible(True)

                        if (
                            hasattr(self._data_, "parentTypes")
                            and len(self._data_.parentTypes) > 1
                            ):
                            self.nameDescriptionWidget.replaceParentToolButton.setEnabled(True)
                            self.nameDescriptionWidget.replaceParentToolButton.setVisible(True)

    @property
    def isAttribute(self) -> bool:
        return self._isAttribute_

    @isAttribute.setter
    def isAttribute(self, val: bool):
        self._isAttribute_ = val is True

    @Slot()
    def _slot_dataExportRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataExporting.emit(self._data_)

    @Slot()
    def _slot_newObjectRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.setValue(type(self._data_)())

    @Slot()
    def _slot_dataCopyRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataCopy.emit(self._data_)

    @Slot()
    def _slot_dataSaveRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataSaving.emit(self._data_)

    @Slot(object)
    def _slot_dataReceived(self, obj):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.setValue(obj)

    @Slot(str)
    def _slot_dataNameChanged(self, val: str):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self._data_.name = val
            self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_dataDescriptionChanged(self, val:str):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self._data_.description = val
            self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_symbolChanged(self, val:str):
        from gui.widgets.dataclasswidgets import namedescriptionwidget
        if (hasattr(self, "nameDescriptionWidget")
            and isinstance(self.nameDescriptionWidget, namedescriptionwidget.NameDescriptionWidget)):
            self.nameDescriptionWidget._slot_symbolChanged(val)
        # pass

    @Slot()
    def _slot_viewDetails(self):
        from gui.widgets.dataclasswidgets import dataexchangewidget
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self, "dataExchangeWidget")
            and isinstance(self.dataExchangeWidget, dataexchangewidget.DataExchangeWidget)):
            varName = self.dataExchangeWidget.varName
            self.sig_detailedView.emit(self._data_, varName)

    @Slot()
    def _slot_detailsChanged(self):
        r"""Must override in subclasses"""
        pass

    @Slot(object)
    def _slot_parentChanged(self, value: object):
        # print(f"{self.__class__.__name__}._slot_parentChanged")
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_editParent(self):
        parent = None
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self._data_, "parentTypes")
            and hasattr(self._data_, "parent")
            and isinstance(self._data_.parent, self._data_.parentTypes)): # dataclasses.is_dataclass(self._data_.parent)):
            parent = self._data_.parent

        # print(f"{self.__class__.__name__}._slot_editParent -> {parent}")

        if isinstance(self.parentEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.parentEditor):
            editor = self._createParentEditor_(parent)
            editor.sig_valueChanged.connect(self._slot_parentChanged)
            if type(editor) is not type(self.parentEditor):
                self.parentEditor.close()
                self.parentEditor.deleteLater()
                self.parentEditor = editor
                # self.parentEditor.sig_valueChanged.connect(self._slot_parentChanged)

        else:
            self.parentEditor = self._createParentEditor_(parent)
            self.parentEditor.sig_valueChanged.connect(self._slot_parentChanged)

        self.parentEditor.show()
        self.parentEditor.setWindowTitle(f"Edit Parent: {type(parent).__name__}")


        # TODO: 2026-06-25 16:47:07 finalize me
        # what are the possible parents of the CellCompartment/NeuronCompartment
        # propose creating a new one (add create new button to these widgets)

    @Slot()
    def _slot_chooseNewParentType(self):
        from gui.itemslistdialog import ItemsListDialog
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self._data_, "parentTypes")):

            parentTypeNames = list(map(lambda t: t.__name__, self._data_.parentTypes))

            if hasattr(self._data_, "parent"):
                parentTypeNdx = self._data_.parentTypes.index(type(self._data_.parent))
                preSelected = parentTypeNames[parentTypeNdx]
            else:
                preSelected = parentTypeNames[0]

            dlg = ItemsListDialog(parent=self, itemsList=parentTypeNames,
                                title="Create New Parent",
                                preSelected=preSelected,
                                modal=True,
                                selectmode = QtWidgets.QAbstractItemView.SingleSelection)

            if dlg.exec() == 1  :
                parentTypeName = dlg.selection
                ndx = parentTypeNames.index(parentTypeName)
                self._slot_newParent(self._data_.parentTypes[ndx])

    @Slot(type)
    def _slot_newParent(self, value: type):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self._data_, "parentTypes")
            and value in self._data_.parentTypes
            ):

            newParent = value()
            self._data_.parent = newParent
            self._slot_parentChanged(self._data_.parent)

            self._slot_editParent()

    @singledispatchmethod
    def _createParentEditor_(self, obj):
        raise NotImplementedError(f"{type(obj)} objects are not supported")

    @_createParentEditor_.register(sdc.Neuron)
    def __createParentEditor(self, obj: sdc.Neuron):
        from gui.widgets.dataclasswidgets.cellwidgets import NeuronWidget
        return NeuronWidget(obj, objSymbol="parent")

    @_createParentEditor_.register(sdc.Cell)
    def __createParentEditor(self, obj: sdc.Cell):
        from gui.widgets.dataclasswidgets.cellwidgets import CellWidget
        return CellWidget(obj, objSymbol="parent")

    @_createParentEditor_.register(sdc.CellCompartment)
    @_createParentEditor_.register(sdc.NeuronCompartment)
    def __createParentEditor(self, obj: sdc.CellCompartment):
        from gui.widgets.dataclasswidgets.cellcompartmentwidget import CellCompartmentWidget
        return CellCompartmentWidget(obj, objSymbol="parent")

    @_createParentEditor_.register(sdc.ChemicalSynapse)
    def __createParentEditor(self, obj: sdc.ChemicalSynapse):
        from gui.widgets.dataclasswidgets.chemicalsynapsewidget import ChemicalSynapseWidget
        return ChemicalSynapseWidget(obj, objSymbol="parent")

    @_createParentEditor_.register(sdc.Organism)
    def __createParentEditor(self, obj: sdc.Organism):
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        return OrganismWidget(obj, objSymbol="parent")

    @_createParentEditor_.register(sdc.Organ)
    @_createParentEditor_.register(sdc.Tissue)
    def __createParentEditor(self, obj: sdc.Organ):
        from gui.widgets.dataclasswidgets.organtissuewidgets import OrganWidget, TissueWidget
        if isinstance(obj, sdc.Tissue):
            return TissueWidget(obj, objSymbol="parent")
        return OrganWidget(obj, objSymbol="parent")

    @_createParentEditor_.register(sdc.NervousSystem)
    def __createParentEditor(self, obj: sdc.NervousSystem):
        from gui.widgets.dataclasswidgets.nervoussystemwidget import NervousSystemWidget
        return NervousSystemWidget(obj, objSymbol="parent")

    def closeEvent(self, evt):
        # print(f"{self.__class__.__name__}.closeEvent")
        self.closeChildren()
        # if isinstance(self.parentEditor, QtWidgets.QWidget):
        #     self.parentEditor.close()
        #     self.parentEditor.deleteLater()
        #     self.parentEditor = None
        #
        # self.nameDescriptionWidget.closeChildren()

        super().closeEvent(evt)
        evt.accept()

    def closeChildren(self):
        if isinstance(self.parentEditor, QtWidgets.QWidget):
            self.parentEditor.close()
            self.parentEditor.deleteLater()
            self.parentEditor = None

        self.nameDescriptionWidget.closeChildren()




