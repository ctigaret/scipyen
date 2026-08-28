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
# __has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    # import PySide6 # noqa
    # from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
    __has_PySide6__ = True
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    # from qtpy import sip # noqa
    # from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    # __has_sip__ = True


from core.prog import scipywarn #, safewrapper, print_styled
from core import desktoputils
# from core.sysutils import adapt_ui_path
import core.taxonbridge as taxonbridge
# import core.bgbridge as bgbridge

# from core import scipyen_quantities as scq
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
# from gui.textviewer import TextViewer
# from gui.widgets.dataclasswidgets.dataexchangewidget import DataExchangeWidget
from gui.widgets.anchoringcollapsiblewidget import AnchoringCollapsibleWidget
from gui.widgets.dataclasswidgets.namedescriptionwidget import NameDescriptionWidget
# from gui.workspacegui import WorkspaceGuiMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

class DataClassWidget(AnchoringCollapsibleWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_dataSaving = Signal(object, name="sig_dataSaving")
    sig_dataExporting = Signal(object, name="sig_dataExporting")
    sig_dataCopy = Signal(object, name="sig_dataCopy")
    sig_detailedView = Signal(object, str, name="sig_detailedView")
    # sig_closing = Signal(name="sig_closing")
    # sig_moved = Signal(QtCore.QPoint, name="sig_moved")
    # sig_collapsed = Signal(name="sig_collapsed")

    _objectTypes_ = tuple()

    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 **kwargs):
        self._objSymbol_ = kwargs.pop("objSymbol", None)

        self._needsNewParentWidget_: bool =  True

        self.nameDescriptionWidget = None
        self.toggleParentEditorToolButton = None
        self.parentEditor = None
        self.organismEditor = None
        # self._data_ = None

        super().__init__(parent, **kwargs)

        if (
            (
                self._objSymbol_ is None
                or (isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()) == 0)
            )
            and (hasattr(self, "_data_") and self._data_ is not None)
            ):
            objSymbols = self.getDataSymbolInWorkspace(self._data_)
            if isinstance(objSymbols, typing.Sequence) and len(objSymbols) > 0:
                self._objSymbol_ = objSymbols[0]

        # self._configureUI_() # --- ?!?

    def _configureUI_(self):
        self.sig_uiConfigured.connect(self._slot_uiConfigured_)
        r"""MUST be called in the subclass once self._data_ was established,
        AND first thing after setupUi() was called in the subclass"""
        # if isinstance(self.dataExchangeWidget, DataExchangeWidget) and isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
        if isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
            self.nameDescriptionWidget.setData(self._data_)#, self._objSymbol_)
            self.nameDescriptionWidget.dataName = self._data_.name
            self.nameDescriptionWidget.dataDescription = self._data_.description
            self.nameDescriptionWidget.symbol = self._objSymbol_

            self.nameDescriptionWidget.sig_valueChanged.connect(self._slot_dataReceived)
            self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
            self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
            self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
            self.nameDescriptionWidget.sig_parentEditRequest.connect(self._slot_toggleParentEditor)
            self.nameDescriptionWidget.sig_newParentRequest.connect(self._slot_chooseNewParentType)
            self.nameDescriptionWidget.sig_organismEditRequest.connect(self._slot_toggleOrganismEditor)
            self.nameDescriptionWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)
            self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
            self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
            self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)

            self.nameDescriptionWidget.toggleParentEditorToolButton.setEnabled(False)
            self.nameDescriptionWidget.toggleParentEditorToolButton.setVisible(False)
            self.nameDescriptionWidget.replaceParentToolButton.setEnabled(False)
            self.nameDescriptionWidget.replaceParentToolButton.setVisible(False)
            self.nameDescriptionWidget.organismToolButton.setEnabled(False)
            self.nameDescriptionWidget.organismToolButton.setVisible(False)

            if hasattr(self, "_data_"):
                if hasattr(self._data_, "parent"):
                    self.nameDescriptionWidget.toggleParentEditorToolButton.setEnabled(True)
                    self.nameDescriptionWidget.toggleParentEditorToolButton.setVisible(True)


                if (
                    hasattr(self._data_, "parentTypes")
                    and len(self._data_.parentTypes) > 1
                    ):
                    self.nameDescriptionWidget.replaceParentToolButton.setEnabled(True)
                    self.nameDescriptionWidget.replaceParentToolButton.setVisible(True)

                # print(f"{self.__class__.__name__}._configureUI_: checking for organism access")

                if (
                    not isinstance(self._data_, (sdc.Organism, sdc.Organ))
                    and hasattr(self._data_, "getOrganism")
                    and hasattr(self._data_, "setOrganism")
                    ):
                    self.nameDescriptionWidget.organismToolButton.setEnabled(True)
                    self.nameDescriptionWidget.organismToolButton.setVisible(True)

    @Slot(object)
    def _slot_dataReceived(self, obj: typing.Any):
        if isinstance(obj, self._objectTypes_):
            self.setValue(obj)

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
                if isinstance(objSymbols, typing.Sequence) and len(objSymbols) > 0:
                    self._objSymbol_ = objSymbols[0]
                else:
                    self._objSymbol_ = ""

            # if isinstance(self.dataExchangeWidget, DataExchangeWidget) and isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
            if isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
                if hasattr(self, "_data_"):
                    sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w), # noqa
                                        (
                                            # self.dataExchangeWidget,
                                            self.nameDescriptionWidget,
                                            )
                                        )
                                    )

                    # self.nameDescriptionWidget.dataExchangeWidget.setValue(self._data_, self._objSymbol_)
                    self.nameDescriptionWidget.setData(self._data_)
                    self.nameDescriptionWidget.dataName = self._data_.name
                    self.nameDescriptionWidget.symbol = self._objSymbol_
                    self.nameDescriptionWidget.dataDescription = self._data_.description

                    if (isinstance(self.nameDescriptionWidget.detailsViewer, DataTreeViewer)
                        and self.nameDescriptionWidget.detailsViewer.isVisible()):
                        self.nameDescriptionWidget.detailsViewer.view(self._data_,
                                                                    doc_title = self._objSymbol_,
                                                                    name = self._objSymbol_)

                    self.nameDescriptionWidget.toggleParentEditorToolButton.setEnabled(False)
                    self.nameDescriptionWidget.toggleParentEditorToolButton.setVisible(False)
                    self.nameDescriptionWidget.replaceParentToolButton.setEnabled(False)
                    self.nameDescriptionWidget.replaceParentToolButton.setVisible(False)

                    if hasattr(self._data_, "parent"):
                        self.nameDescriptionWidget.toggleParentEditorToolButton.setEnabled(True)
                        self.nameDescriptionWidget.toggleParentEditorToolButton.setVisible(True)

                        if (
                            hasattr(self._data_, "parentTypes")
                            and len(self._data_.parentTypes) > 1
                            ):
                            self.nameDescriptionWidget.replaceParentToolButton.setEnabled(True)
                            self.nameDescriptionWidget.replaceParentToolButton.setVisible(True)

                    # print(f"{self.__class__.__name__}.setValue(): checking for organism access")
                    if (
                        not isinstance(self._data_, (sdc.Organism, sdc.Organ))
                        and hasattr(self._data_, "getOrganism")
                        and hasattr(self._data_, "setOrganism")
                        ):
                        self.nameDescriptionWidget.organismToolButton.setEnabled(True)
                        self.nameDescriptionWidget.organismToolButton.setVisible(True)

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
            and isinstance(obj, self._objectTypes_)):
            self.setValue(obj)

    @Slot(str)
    def _slot_dataNameChanged(self, val: str):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")):
            if not isinstance(self._data_, self._objectTypes_):
                self._make_value_()
            self._data_.name = val
            self.sig_valueChanged.emit(self._data_)

    @Slot(str)
    def _slot_dataDescriptionChanged(self, val:str):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")):
            if not isinstance(self._data_, self._objectTypes_):
                self._make_value_()
            self._data_.description = val
            self.sig_valueChanged.emit(self._data_)

    @Slot()
    def _slot_viewDetails(self):
        # from gui.widgets.dataclasswidgets import dataexchangewidget
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            ):
            # varName = self.nameDescriptionWidget.dataExchangeWidget.varName
            varName = self.nameDescriptionWidget._objSymbol_
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


    @Slot(bool)
    def _slot_toggleParentEditor(self, val: bool):
        if val is True:
            self._slot_editParent()

        else:
            if isinstance(self.parentEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.parentEditor):
                self.parentEditor.collapse(False)

    # def _makeParentEditor(self, editorWidgetType, data):
    #     anchoringWidget = self.provideAnchoringWidget()
    #     self.parentEditor = self._setupCollapsibleChild_(
    #         editorWidgetType,
    #         "parentEditor",
    #         self._slot_parentChanged,
    #         self.nameDescriptionWidget.toggleParentEditorToolButton,
    #         anchoringWidget,
    #         not desktoputils.is_wayland(),
    #         data,
    #         objSymbol="parent"
    #         )


    @Slot()
    def _slot_editParent(self):
        parentData = None
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self._data_, "parentTypes")
            and hasattr(self._data_, "parent")
            and isinstance(self._data_.parent, self._data_.parentTypes)): # dataclasses.is_dataclass(self._data_.parent)):
            parentData = self._data_.parent

        editorWidgetType = self._setParentEditorType_(parentData)

        if editorWidgetType is None:
            return

        if isinstance(self.parentEditor, QtWidgets.QWidget):
            if (
                not qtutils.isQObjectAlive(self.parentEditor)
                or type(self.parentEditor) is not editorWidgetType
                or self._needsNewParentWidget_):
                self._removeAnchoringCollapsibleWidget_(self.parentEditor)
                self.parentEditor = self._makeEditorWidget(editorWidgetType, "parentEditor",
                                       self._slot_parentChanged,
                                       self.nameDescriptionWidget.toggleParentEditorToolButton,
                                       parentData, "parent")

            else:
                self.parentEditor.setValue(parentData, objSymbol="parent")

        else:
            self.parentEditor = self._makeEditorWidget(editorWidgetType, "parentEditor",
                                    self._slot_parentChanged,
                                    self.nameDescriptionWidget.toggleParentEditorToolButton,
                                    parentData, "parent")

        self._needsNewParentWidget_ = False
        self.parentEditor.setWindowTitle(f"Parent: {type(parentData).__name__}")
        self.parentEditor.show()

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
            organism = self._data_.getOrganism()
            newParent = value()
            newParent.setOrganism(organism)
            self._needsNewParentWidget_ = type(newParent) is not type(self._data_.parent)
            self._data_.parent = newParent
            self._slot_parentChanged(self._data_.parent)
            self.nameDescriptionWidget.toggleParentEditorToolButton.setChecked(True)

    @Slot(bool)
    def _slot_toggleOrganismEditor(self, val: bool):
        if val is True:
            self._slot_editOrganism()
        else:
            if isinstance(self.organismEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.organismEditor):
                self.organismEditor.collapse(False)

    def _makeEditorWidget(self, widgetType: type, widgetName: str,
                          valueChangedSlot: Slot,
                          toggleControl: QtWidgets.QWidget,
                          data: object,
                          dataSymbol: str,
                          ) -> QtWidgets.QWidget:
        anchoringWidget = self.provideAnchoringWidget()
        obj = self._setupCollapsibleChild_(
            widgetType,
            widgetName,
            valueChangedSlot,
            toggleControl,
            anchoringWidget,
            not desktoputils.is_wayland(),
            data,
            dataSymbol="organism"
            )

        return obj


    # def _makeOrganismEditor(self, data):
    #     from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
    #     anchoringWidget = self.provideAnchoringWidget()
    #
    #     self.organismEditor = self._setupCollapsibleChild_(
    #         OrganismWidget,
    #         "organismEditor",
    #         self._slot_organismChanged,
    #         self.nameDescriptionWidget.organismToolButton,
    #         anchoringWidget,
    #         not desktoputils.is_wayland(),
    #         data,
    #         objSymbol="organism"
    #         )


    @Slot()
    def _slot_editOrganism(self):
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        try:
            organism = self._data_.getOrganism()
        except: # noqa
            organism = sdc.Organism()

        if isinstance(self.organismEditor, QtWidgets.QWidget):
            if not qtutils.isQObjectAlive(self.organismEditor) or not isinstance(self.organismEditor, OrganismWidget):
                self._removeAnchoringCollapsibleWidget_(self.organismEditor)
                # self.organismEditor = None

            # if not isinstance(self.organismEditor, OrganismWidget):
            #     self._removeAnchoringCollapsibleWidget_(self.organismEditor)
                self.organismEditor = self._makeEditorWidget(OrganismWidget, "organismEditor",
                                       self._slot_organismChanged,
                                       self.nameDescriptionWidget.organismToolButton,
                                       organism, "organism")
                # self._makeOrganismEditor(organism)

            else:
                self.organismEditor.setValue(organism, objSymbol="organism")

        else:
            self.organismEditor = self._makeEditorWidget(OrganismWidget, "organismEditor",
                                    self._slot_organismChanged,
                                    self.nameDescriptionWidget.organismToolButton,
                                    organism, "organism")
            # self._makeOrganismEditor(organism)

        self.organismEditor.show()

        taxon = organism.taxon

        if taxonbridge.isTaxoniqTaxon(taxon):
            taxonName = taxon.scientific_name

        elif isinstance(taxon, str) and len(taxon.strip()):
            taxonName = taxon

        else:
            taxonName = ""

        if isinstance(organism.name, str) and len(organism.name.strip()):
            wTitle = f"Organism: {organism.name}"

        else:
            wTitle = "Organism:"

        if len(taxonName.strip()):
            wTitle += f" ({taxonName})"

        self.organismEditor.setWindowTitle(wTitle)

    @Slot(object)
    def _slot_organismChanged(self, value: object):
        if not isinstance(value, sdc.Organism):
            value = sdc.Organism()
        try:
            self._data_.setOrganism(value)
            self.sig_valueChanged.emit(self._data_)
        except: # noqa
            pass

    @singledispatchmethod
    def _setParentEditorType_(self, obj) -> type:
        scipywarn(f"{type(obj)} objects are not supported")
        return
        # raise NotImplementedError(f"{type(obj)} objects are not supported")

    @_setParentEditorType_.register(sdc.Neuron)
    def __setParentEditorType__(self, obj: sdc.Neuron) -> type:
        from gui.widgets.dataclasswidgets.cellwidgets import NeuronWidget
        return NeuronWidget

    @_setParentEditorType_.register(sdc.Cell)
    def __setParentEditorType__(self, obj: sdc.Cell) -> type: # noqa
        from gui.widgets.dataclasswidgets.cellwidgets import CellWidget
        return CellWidget

    @_setParentEditorType_.register(sdc.CellCompartment)
    @_setParentEditorType_.register(sdc.NeuronCompartment)
    def __setParentEditorType__(self, obj: sdc.CellCompartment) -> type: # noqa
        from gui.widgets.dataclasswidgets.cellcompartmentwidget import CellCompartmentWidget
        return CellCompartmentWidget

    @_setParentEditorType_.register(sdc.ChemicalSynapse)
    def __setParentEditorType__(self, obj: sdc.ChemicalSynapse) -> type: # noqa
        from gui.widgets.dataclasswidgets.chemicalsynapsewidget import ChemicalSynapseWidget
        return ChemicalSynapseWidget

    @_setParentEditorType_.register(sdc.Organism)
    def __setParentEditorType__(self, obj: sdc.Organism) -> type: # noqa
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        return OrganismWidget

    @_setParentEditorType_.register(sdc.Organ)
    @_setParentEditorType_.register(sdc.Tissue)
    def __setParentEditorType__(self, obj: sdc.Organ) -> type: # noqa
        from gui.widgets.dataclasswidgets.organtissuewidgets import OrganWidget, TissueWidget
        if isinstance(obj, sdc.Tissue):
            return TissueWidget
        return OrganWidget

    @_setParentEditorType_.register(sdc.NervousSystem)
    def __setParentEditorType__(self, obj: sdc.NervousSystem) -> type: # noqa
        from gui.widgets.dataclasswidgets.nervoussystemwidget import NervousSystemWidget
        return NervousSystemWidget

    def closeSubWidgets(self):
        super().closeSubWidgets()

        if isinstance(self.nameDescriptionWidget, QtWidgets.QWidget) and hasattr(self.nameDescriptionWidget, "closeSubWidgets"):
            self.nameDescriptionWidget.closeSubWidgets()

    def _make_value_(self):
        r"""SHOULD override this in subclasses"""
        if hasattr(self, "_objectTypes_"):
            self._data_ = self._objectTypes_[0]()
