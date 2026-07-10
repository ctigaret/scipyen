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


from core.prog import scipywarn
# from core.sysutils import adapt_ui_path

import core.bgbridge as bgbridge # noqa

# from core import scipyen_quantities as scq
# from core import strutils
# from core.datatypes import UnitTypes, GENOTYPES

# from core import workspacefunctions as wsf
# from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget

from core.prog import scipywarn # noqa
from gui import textviewer, datatreeviewer
# from iolib import pictio as pio


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

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None, **kwargs):
        QtCore.QObject.__init__(self, parent=parent)

        self._dataName_ = ""
        self._dataDescription_ = ""
        self._objSymbol_ = kwargs.pop("objSymbol", "")

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)
        self.descriptionEditor = None
        self.detailsViewer = None
        self.nameLineEdit.setText(self._dataName_)
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

        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            sigBlockers.append(QtCore.QSignalBlocker(self.descriptionEditor))

        if hasattr(val, "description") and isinstance(val.description, str):
            self._dataDescription_ = val.description
            if isinstance(self.descriptionEditor, textviewer.TextViewer):
                self.descriptionEditor.setText(self._dataDescription_)

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
    def _slot_editDescription(self):
        if not isinstance(self.descriptionEditor, textviewer.TextViewer):
            self.descriptionEditor = textviewer.TextViewer(self._dataDescription_,
                                                parent=self, edit=True,
                                                win_title="Edit description",
                                                doc_title="Edit description",
                                                title="Description")
            # self.descriptionEditor.setVisible(False)
            self.descriptionEditor.sig_textChanged.connect(self._slot_descriptionChanged)

        self.descriptionEditor.setData(self._dataDescription_)
        self.descriptionEditor.show()

    @Slot(str)
    def _slot_symbolChanged(self, val:str):
        self._objSymbol_ = val
        if isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer):
            self.detailsViewer.setRootName(self._objSymbol_)

    @Slot()
    def _slot_descriptionChanged(self):
        r"""Captures changes in the description editor"""
        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            self._dataDescription_ = self.descriptionEditor.text(plain=True)
            self.sig_descriptionChanged.emit(self._dataDescription_)

    @Slot(object, str)
    def slot_viewDetails(self, obj: object, varName: str):
        # print(f"{self.__class__.__name__}.slot_viewDetails({obj}, \n{varName})")
        doc_title =  varName if len(varName.strip()) else {getattr(obj, 'name', type(obj).__name__)}
        # win_title = f"Details of {varName}"
        win_title = "Details"
        if not isinstance(self.detailsViewer, datatreeviewer.DataTreeViewer):
            self.detailsViewer = datatreeviewer.DataTreeViewer(
                parent=self,
                doc_title=doc_title,
                title="Detailed view",
                # appWindow = self,
                )

            self.detailsViewer.autoRaise = False

            self.detailsViewer.view(obj, doc_title = doc_title, name=doc_title)
            self.detailsViewer.winTitle = win_title
            self.detailsViewer.sig_modelDataChanged.connect(self._slot_dataChangedInDetailsViewer)
        else:
            # sigBlock = QtCore.QSignalBlocker(self.detailsViewer)
            self.detailsViewer.view(obj, doc_title = doc_title, name=doc_title)
            self.detailsViewer.winTitle = win_title
            self.detailsViewer.docTitle = doc_title
            self.detailsViewer.slot_refreshDataDisplay()

        self.detailsViewer.show()

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
        if isinstance(self.descriptionEditor, textviewer.TextViewer):
            sigBlock = QtCore.QSignalBlocker(self.descriptionEditor)
            self.descriptionEditor.setText(self._dataDescription_)
        self.sig_descriptionChanged.emit(self._dataDescription_)
