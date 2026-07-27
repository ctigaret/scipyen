# -*- coding: utf-8 -*-
# $Id: namedescriptionwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
# import numbers
# import numpy as np
# import quantities as pq
# import pandas as pd
# import neo
# from tribool import Tribool

import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot) #, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
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
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from core.prog import scipywarn #noqa
from core import qtutils
from iolib import pictio as pio

from gui import textviewer, datatreeviewer
# from gui.workspacegui import WorkspaceGuiMixin
from gui.widgets.dataclasswidgets.dataexchangewidget import DataExchangeWidget
from gui.widgets.anchoringcollapsiblewidget import AnchoringCollapsibleWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_NameDescriptionWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "namedescriptionwidget.ui")
    )

class NameDescriptionWidget(Ui_NameDescriptionWidget, AnchoringCollapsibleWidget):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_detailsChanged = Signal(name="sig_dataChanged")
    sig_nameChanged = Signal(str, name="sig_nameChanged")
    sig_descriptionChanged = Signal(str, name="sig_descriptionChanged")
    sig_detailedViewRequest = Signal(name="sig_detailedViewRequest")
    sig_parentEditRequest = Signal(bool, name="sig_parentEditRequest")
    sig_newParentRequest = Signal(name="sig_newParentRequest")
    sig_organismEditRequest = Signal(bool, name="sig_organismEditRequest")
    sig_requestNewObject = Signal(name="sig_requestNewObject")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[typing.Any] = None,
                 **kwargs):
        if not isinstance(parent, QtWidgets.QWidget):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        self._data_ = obj
        self._objectType_ = type(self._data_)

        self._dataName_ = kwargs.pop("dataName", "")
        self._dataDescription_ = kwargs.pop("dataDescription", "")
        self._objSymbol_ = kwargs.pop("objSymbol", "")

        AnchoringCollapsibleWidget.__init__(self, parent=parent, **kwargs)
        # QtCore.QObject.__init__(self, parent=parent)

        self.dataExchangeWidget = None

        # WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.descriptionEditor = None
        self.detailsViewer = None
        self.nameLineEdit.lazy = True
        self.nameLineEdit.undoAvailable=True
        self.nameLineEdit.redoAvailable=True
        self.nameLineEdit.setText(self._dataName_)
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.setToolTip(f"Name of the {self._objectType_.__name__} object")
        self.nameLineEdit.setWhatsThis(f"Name of the {self._objectType_.__name__} object")
        self.nameLineEdit.setStatusTip(f"Name of the {self._objectType_.__name__} object")

        self.nameLineEdit.sig_textChanged.connect(self._slot_nameChanged)
        self.descriptionToolButton.clicked.connect(self._slot_editDescription)
        self.viewDetailsToolButton.clicked.connect(self.sig_detailedViewRequest)
        self.toggleParentEditorToolButton.toggled.connect(self.sig_parentEditRequest)
        self.replaceParentToolButton.clicked.connect(self.sig_newParentRequest)
        self.organismToolButton.toggled.connect(self.sig_organismEditRequest)
        self.toggleDataExchangeWidgetToolButton.toggled.connect(self._slot_toggleDataExchangeWidget)

        self.sig_uiConfigured.emit()

    @Slot(bool)
    def _slot_toggleDataExchangeWidget(self, val: bool):
        if val is True:
            self._slot_showDataExchangeWidget()
        else:
            if isinstance(self.dataExchangeWidget, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.dataExchangeWidget):
                self.dataExchangeWidget.collapse(False)

    @Slot()
    def _slot_showDataExchangeWidget(self):
        anchoringWidget = self.provideAnchoringWidget()
        # print(f"{self.__class__.__name__}._slot_showDataExchangeWidget: anchoringWidget -> {anchoringWidget} for anchored widget")
        if not isinstance(self.dataExchangeWidget, DataExchangeWidget):
            if isinstance(self.dataExchangeWidget, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.dataExchangeWidget):
                self._removeAnchoringCollapsibleWidget_(self.dataExchangeWidget)

            self.dataExchangeWidget = self._setupCollapsibleChild_(
                DataExchangeWidget,
                "dataExchangeWidget",
                None,
                self.toggleDataExchangeWidgetToolButton,
                anchoringWidget,
                self._data_,
                objSymbol = self._objSymbol_
                )

            self.dataExchangeWidget.setWindowTitle("Input/Output")
            # self.dataExchangeWidget.setVisible(False)
            self.dataExchangeWidget.sig_requestDataExport.connect(self.slot_exportData)
            self.dataExchangeWidget.sig_requestDataSave.connect(self.slot_saveData)
            self.dataExchangeWidget.sig_requestDataCopy.connect(self.slot_copyData)
            self.dataExchangeWidget.sig_requestImportData.connect(self._slot_importData)
            self.dataExchangeWidget.sig_requestLoadData.connect(self._slot_loadData)
            self.dataExchangeWidget.sig_requestNewObject.connect(self.sig_requestNewObject)

        self.dataExchangeWidget.setValue(self._data_, self._objSymbol_)

        self.dataExchangeWidget.show()

    @Slot()
    def _slot_dataExportRequested(self):
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)):
            self.sig_dataExporting.emit(self._data_)

    @Slot(object)
    def _slot_dataChanged(self, val: object):
        r"""Captures changes made externally"""
        # print(f"{self.__class__.__name__}._slot_dataChanged")
        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                              (self.nameLineEdit,
                               )))

        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            sigBlockers.append(QtCore.QSignalBlocker(self.descriptionEditor))

        if hasattr(val, "description") and isinstance(val.description, str):
            self._dataDescription_ = val.description
            if isinstance(self.descriptionEditor, textviewer.TextViewer):
                self.descriptionEditor.setText(self._dataDescription_, show=False)

        if hasattr(val, "name") and isinstance(val.name, str):
            self._dataName_ = val.name
            self.nameLineEdit.setText(self._dataName_)

        if isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer):# and self.detailsViewer.isVisible():
            # print(f"\n\t-> call self.detailsViewer.view({val},\n{self.symbol})")
            self.detailsViewer.view(val, doc_title=self.symbol, autoRaise=False)
            self.detailsViewer.slot_refreshDataDisplay()


    @Slot(str)
    def _slot_nameChanged(self, val:str):
        r"""Captures changes in the nameLineEdit"""
        self._dataName_ = val
        self.sig_nameChanged.emit(self._dataName_)

    @Slot()
    def _slot_descriptionEditorClosed(self):
        if isinstance(self.descriptionEditor, textviewer.TextViewer) and qtutils.isQObjectAlive(self.descriptionEditor):
            self.descriptionEditor.deleteLater()
            self.descriptionEditor = None

    @Slot()
    def _slot_editDescription(self):
        topWindow = self.getHighestAncestor()
        if topWindow is self:
            appWindow = None
        else:
            appWindow = topWindow

        if not isinstance(self.descriptionEditor, textviewer.TextViewer):
            self.descriptionEditor = textviewer.TextViewer(self._dataDescription_,
                                                parent=self, edit=True,
                                                win_title="Edit description",
                                                doc_title="Edit description",
                                                title="Description",
                                                appWindow = appWindow)
            self.descriptionEditor.sig_textChanged.connect(self._slot_descriptionChanged)
            self.descriptionEditor.sig_closeMe.connect(self._slot_descriptionEditorClosed)

        self.descriptionEditor.setData(self._dataDescription_, show=False)
        self.descriptionEditor.show()

    @Slot()
    def _slot_descriptionChanged(self):
        r"""Captures changes in the description editor"""
        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            self._dataDescription_ = self.descriptionEditor.text(plain=True)
            self.sig_descriptionChanged.emit(self._dataDescription_)

    @Slot(object, str)
    def slot_viewDetails(self, obj: object, varName: str):
        # print(f"{self.__class__.__name__}.slot_viewDetails({obj}, \n{varName})")
        doc_title =  varName if len(varName.strip()) else getattr(obj, 'name', type(obj).__name__)
        # win_title = f"Details of {varName}"
        # win_title = "Details"
        if not isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer):
            topWindow = self.getHighestAncestor()
            if topWindow is self:
                appWindow = None
            else:
                appWindow = topWindow
            self.detailsViewer = datatreeviewer.DataTreeViewer(
                parent=self,
                doc_title=doc_title,
                appWindow = appWindow,
                )

            self.detailsViewer.autoRaise = False

            self.detailsViewer.view(obj, doc_title = doc_title, name=doc_title)
            self.detailsViewer.sig_modelDataChanged.connect(self._slot_dataChangedInDetailsViewer)
        else:
            # sigBlock = QtCore.QSignalBlocker(self.detailsViewer)
            self.detailsViewer.view(obj, doc_title = doc_title, name=doc_title)
            # self.detailsViewer.winTitle = win_title
            self.detailsViewer.docTitle = doc_title
            self.detailsViewer.slot_refreshDataDisplay()

        self.detailsViewer.show()

    @Slot()
    def _slot_dataChangedInDetailsViewer(self):
        r"""Captures changes in the details viewer (a DataTreeViewer)"""
        self.sig_detailsChanged.emit()

    @Slot()
    def _slot_loadData(self):
        fileNameFilter = "*.pkl"
        fn, fl = self.chooseFile(caption = "Open Pickle File",
                                fileFilter = fileNameFilter,
                                single=True)

        if len(fn.strip()):
            self._data_ = pio.loadFile(fn)
            varName = os.path.basename(fn)
            self._updateSymbol_(varName)
            self.sig_valueChanged.emit(self._data_)

    @Slot()
    def slot_saveData(self):
        if self._data_ is None:
            return

        fileNameFilter = "*.pkl"

        fn, fl = self.chooseFile(caption = f"Save {type(self._data_).__name__} as Pickle File",
                                fileFilter = fileNameFilter,
                                single=True, save=True)

        if len(fn.strip()):
            pio.savePickle(self._data_, fn)


    @Slot()
    def _slot_importData(self):
        if self._data_ is None:
            ret = self.importFromWorkSpace(
                title = "Select Object in Workspace",
                single=True,
                with_varName=True,
                retrieve_all = True,
                )
        else:
            ret = self.importFromWorkSpace(
                dataTypes = self._objectType_,
                title=f"Select {self._objectType_.__name__} Object in Workspace",
                single=True,
                with_varName=True,
                retrieve_all = True
                )

        if isinstance(ret, dict) and len(ret) == 1:
            varName = list(ret.keys())[0]
            self._data_ = ret[varName]
            self._updateSymbol_(varName)
            self.sig_valueChanged.emit(self._data_)

    @Slot()
    def slot_exportData(self):
        if self._data_ is None:
            return
        name = getattr(self._data_, "name", self._objSymbol_)
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = type(self._data_).__name__.lower()

        newSymbol = self.exportDataToWorkspace(self._data_, name)
        self._updateSymbol_(newSymbol)

    def _updateSymbol_(self, val: str):
        if isinstance(val, str) and len(val.strip()):
            self._objSymbol_ = val
            if (
                isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer)
                and qtutils.isQObjectAlive(self.detailsViewer)
                ):
                self.detailsViewer.setRootName(self._objSymbol_)

            if (
                isinstance(self.dataExchangeWidget, DataExchangeWidget)
                and qtutils.isQObjectAlive(self.dataExchangeWidget)
                ):
                self.dataExchangeWidget.setObjectSymbol(self._objSymbol_)

    @Slot()
    def slot_copyData(self):
        from copy import deepcopy
        if self._data_ is None:
            return
        obj1 = deepcopy(self._data_)
        name = getattr(self._data_, "name", self._objSymbol_)
        if not isinstance(name, str) or len(name.strip()) == 0:
            name = type(self._data_).__name__.lower()

        self.exportDataToWorkspace(obj1, name)

    @property
    def symbol(self) -> str:
        return self._objSymbol_

    @symbol.setter
    def symbol(self, val:str):
        self._updateSymbol_(val)

    @property
    def dataName(self) -> str:
        return self._dataName_

    @dataName.setter
    def dataName(self, val:str):
        self._dataName_ = val
        with qtutils.SignalBlocker(self.nameLineEdit) as sb: # noqa
            self.nameLineEdit.setText(self._dataName_)
        self.sig_nameChanged.emit(self._dataName_)

    @property
    def dataDescription(self) -> str:
        return self._dataDescription_

    @dataDescription.setter
    def dataDescription(self, val:str):
        self._dataDescription_ = val
        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            sigBlock = QtCore.QSignalBlocker(self.descriptionEditor) # noqa
            self.descriptionEditor.setText(self._dataDescription_, show=False)
        self.sig_descriptionChanged.emit(self._dataDescription_)

    def closeEvent(self, evt):
        self.closeSubWidgets()
        evt.accept()

    def closeSubWidgets(self):
        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            self.descriptionEditor.close()
            self.descriptionEditor.deleteLater()
            self.descriptionEditor = None

        if isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer):
            self.detailsViewer.close()
            self.detailsViewer.deleteLater()
            self.detailsViewer = None

        if isinstance(self.dataExchangeWidget, DataExchangeWidget):
            self.dataExchangeWidget.close()
            self.dataExchangeWidget.deleteLater()
            self.dataExchangeWidget = None

    def setData(self, obj: typing.Any):
        self._data_ = obj
        self._objectType_ = type(self._data_)
