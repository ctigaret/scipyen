# -*- coding: utf-8 -*-
# $Id: biologicalproductwidget.py $
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

# from core.prog import scipywarn
from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
# from core import taxonbridge
# from gui import datatreeviewer
# from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
# from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_BiologicalProductWidget, _ = loadUiType(
    os.path.join(__module_path__, "biologicalproductwidget.ui")
    )

class BiologicalProductWidget(Ui_BiologicalProductWidget, DataClassWidget):
    _objectTypes_ = (sdc.BiologicalProduct, )
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

        if not isinstance(obj, self._objectTypes_):
            self._data_ = self._objectTypes_[0]()
        else:
            self._data_ = obj

        self._entityTypeNames_ = list(sdc.BioProductType.names())

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupui(self)

        super()._configureUI_()
#
#         self.dataExchangeWidget.dataType = type(self._data_)
#         self.dataExchangeWidget.sig_requestDataExport.connect(self._slot_dataExportRequested)
#         self.sig_dataExporting.connect(self.dataExchangeWidget.slot_exportData)
#         self.dataExchangeWidget.sig_requestDataSave.connect(self._slot_dataSaveRequested)
#         self.sig_dataSaving.connect(self.dataExchangeWidget.slot_saveData)
#         self.dataExchangeWidget.sig_requestDataCopy.connect(self._slot_dataCopyRequested)
#         self.sig_dataCopy.connect(self.dataExchangeWidget.slot_copyData)
#         self.dataExchangeWidget.sig_requestNewObject.connect(self._slot_newObjectRequested)
#         self.dataExchangeWidget.sig_dataLoaded.connect(self._slot_dataReceived)
#         self.dataExchangeWidget.sig_dataImported.connect(self._slot_dataReceived)
#         self.dataExchangeWidget.sig_symbolChanged.connect(self._slot_symbolChanged)
#
#         self.nameDescriptionWidget.dataName = self._data_.name
#         self.nameDescriptionWidget.dataDescription = self._data_.description
#         self.nameDescriptionWidget.sig_nameChanged.connect(self._slot_dataNameChanged)
#         self.nameDescriptionWidget.sig_descriptionChanged.connect(self._slot_dataDescriptionChanged)
#         self.nameDescriptionWidget.sig_detailedViewRequest.connect(self._slot_viewDetails)
#         self.sig_detailedView.connect(self.nameDescriptionWidget.slot_viewDetails)
#         self.nameDescriptionWidget.sig_detailsChanged.connect(self._slot_detailsChanged)
#         self.sig_valueChanged.connect(self.nameDescriptionWidget._slot_dataChanged)

        for t in self._entityTypeNames_:
            self.bioSourceTypeComboBox.addItem(t)

        ndx = self._entityTypeNames_.index(self._data_.type.name)
        self.bioSourceTypeComboBox.setCurrentIndex(ndx)

        self.bioSourceTypeComboBox.currentIndexChanged.connect(self._slot_bioSourceTypeChanged)

    @Slot(int)
    def _slot_bioSourceTypeChanged(self, val: int):
        self._data_.type = sdc.BioProductType[self._entityTypeNames_[val]]

        self.sig_valueChanged.emit(self._data_)
