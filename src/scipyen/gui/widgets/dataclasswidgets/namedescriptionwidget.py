# -*- coding: utf-8 -*-
# $Id: namedescriptionwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
import numbers
import numpy as np
import quantities as pq
import pandas as pd
import neo
from tribool import Tribool

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from core.prog import safewrapper, scipywarn, print_styled
from core.sysutils import adapt_ui_path

import core.bgbridge as bgbridge

from core import scipyen_quantities as scq
from core import strutils
from core.datatypes import UnitTypes, GENOTYPES

from core import workspacefunctions as wsf
from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget
from gui.widgets.datatreeview import DataTreeView

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
from core import scipyen_quantities as scq
from gui import guiutils, textviewer, datatreeviewer
from gui.widgets import small_widgets as smw
from gui.workspacegui import WorkspaceGuiMixin
from iolib import pictio as pio


__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_NameDescriptionWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "namedescriptionwidget.ui")
    )

class NameDescriptionWidget(Ui_NameDescriptionWidget, QWidget): #, WorkspaceGuiMixin):
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    sig_detailsChanged = Signal(name="sig_dataChanged")
    sig_nameChanged = Signal(str, name="sig_nameChanged")
    sig_descriptionChanged = Signal(str, name="sig_descriptionChanged")
    sig_detailedViewRequest = Signal(name="sig_detailedViewRequest")

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        QtCore.QObject.__init__(self, parent=parent)

        self._dataName_ = ""
        self._dataDescription_ = ""
        self._objSymbol_ = ""

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self._descriptionEditor_ = None
        self._detailsViewer_ = None
        self.nameLineEdit.setText(self._dataName_)
        # self.nameLineEdit.undoEnabled = True
        # self.nameLineEdit.redoEnabled = True
        self.nameLineEdit.setClearButtonEnabled(True)
        self.nameLineEdit.textChanged.connect(self._slot_nameChanged)
        self.descriptionToolButton.clicked.connect(self._slot_editDescription)
        self.viewDetailsToolButton.clicked.connect(self.sig_detailedViewRequest)

    @Slot(object)
    def _slot_dataChanged(self, val: object):
        r"""Captures changes made externally"""
        # print(f"{self.__class__.__name__}._slot_dataChanged")
        sigBlockers = list(map(lambda w: QtCore.QSignalBlocker(w),
                              (self.nameLineEdit,
                               )))

        # if isinstance(self._detailsViewer_, datatreeviewer.DataTreeViewer):
        #     sigBlockers.append(QtCore.QSignalBlocker(self._detailsViewer_))

        if isinstance(self._descriptionEditor_, textviewer.TextViewer):
            sigBlockers.append(QtCore.QSignalBlocker(self._descriptionEditor_))

        if hasattr(val, "description") and isinstance(val.description, str):
            self._dataDescription_ = val.description
            if isinstance(self._descriptionEditor_, textviewer.TextViewer):
                self._descriptionEditor_.setText(self._dataDescription_)

        if hasattr(val, "name") and isinstance(val.name, str):
            self._dataName_ = val.name
            self.nameLineEdit.setText(self._dataName_)

        if isinstance(self._detailsViewer_, datatreeviewer.DataTreeViewer):# and self._detailsViewer_.isVisible():
            # print(f"\n\t-> call self._detailsViewer_.view({val},\n{self.symbol})")
            self._detailsViewer_.view(val, doc_title=self.symbol, autoRaise=False)
            self._detailsViewer_.slot_refreshDataDisplay()


    @Slot(str)
    def _slot_nameChanged(self, val:str):
        r"""Captures changes in the nameLineEdit"""
        self._dataName_ = val
        self.sig_nameChanged.emit(self._dataName_)

    @Slot()
    def _slot_editDescription(self):
        if not isinstance(self._descriptionEditor_, textviewer.TextViewer):
            self._descriptionEditor_ = textviewer.TextViewer(self._dataDescription_,
                                                parent=self, edit=True,
                                                win_title="Edit description",
                                                doc_title="Edit description",
                                                title="Description")
            # self._descriptionEditor_.setVisible(False)
            self._descriptionEditor_.sig_textChanged.connect(self._slot_descriptionChanged)

        self._descriptionEditor_.setData(self._dataDescription_)
        self._descriptionEditor_.show()

    @Slot(str)
    def _slot_symbolChanged(self, val:str):
        self._objSymbol_ = val

    @Slot()
    def _slot_descriptionChanged(self):
        r"""Captures changes in the description editor"""
        if isinstance(self._descriptionEditor_, textviewer.TextViewer):
            self._dataDescription_ = self._descriptionEditor_.text(plain=True)
            self.sig_descriptionChanged.emit(self._dataDescription_)

    @Slot(object, str)
    def slot_viewDetails(self, obj: object, varName: str):
        # print(f"{self.__class__.__name__}.slot_viewDetails({obj}, \n{varName})")
        win_title = f"Details of {getattr(obj, 'name', type(obj).__name__)}"
        doc_title =  varName if len(varName.strip()) else ""
        if not isinstance(self._detailsViewer_, datatreeviewer.DataTreeViewer):
            self._detailsViewer_ = datatreeviewer.DataTreeViewer(
                parent=self,
                doc_title=doc_title,
                title="Detailed view"
                )

            self._detailsViewer_.autoRaise = False

            self._detailsViewer_.view(obj, doc_title = doc_title)
            self._detailsViewer_.sig_dataChanged.connect(self._slot_dataChangedInDetailsViewer)
        else:
            sigBlock = QtCore.QSignalBlocker(self._detailsViewer_)
            self._detailsViewer_.winTitle = win_title
            self._detailsViewer_.docTitle = doc_title
            self._detailsViewer_.slot_refreshDataDisplay()

        self._detailsViewer_.show()

    @Slot()
    def _slot_dataChangedInDetailsViewer(self):
        r"""Captures changes in the details viewer (a DataTreeViewer)"""
        self.sig_detailsChanged.emit()

    @property
    def symbol(self) -> str:
        return self._objSymbol_

    @symbol.setter
    def symbol(self, val:str):
        self._objSymbol_ = val

    @property
    def dataName(self) -> str:
        return self._dataName_

    @dataName.setter
    def dataName(self, val:str):
        self._dataName_ = val
        sigBlock = QtCore.QSignalBlocker(self.nameLineEdit)
        self.nameLineEdit.setText(self._dataName_)
        self.sig_nameChanged.emit(self._dataName_)

    @property
    def dataDescription(self) -> str:
        return self._dataDescription_

    @dataDescription.setter
    def dataDescription(self, val:str):
        self._dataDescription_ = val
        if isinstance(self._descriptionEditor_, textviewer.TextViewer):
            sigBlock = QtCore.QSignalBlocker(self._descriptionEditor_)
            self._descriptionEditor_.setText(self._dataDescription_)
        self.sig_descriptionChanged.emit(self._dataDescription_)
