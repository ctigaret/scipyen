# -*- coding: utf-8 -*-
"""Common widget for meta-information in results
"""
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing # noqa
import pathlib # noqa
from functools import singledispatchmethod # noqa
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
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


from core.prog import safewrapper, scipywarn, print_styled # noqa
from core.sysutils import adapt_ui_path # noqa

__module_path__ = os.path.abspath(os.path.dirname(__file__))

import math, datetime # noqa
import numpy as np # noqa
import quantities as pq # noqa
import pandas as pd # noqa

import core.bgbridge as bgbridge # noqa

from core import scipyendataclasses as sdc # noqa
from core import basescipyen as bsc # noqa
from core import scipyen_quantities as scq # noqa
from core import strutils # noqa
from core import qtutils # noqa
from core.datatypes import UnitTypes, GENOTYPES # noqa

from core import workspacefunctions as wsf # noqa
from dataclasses import (dataclass, asdict) # noqa

from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget # noqa
from gui.widgets.small_widgets import QuantitySpinBox, QuantityChooserWidget # noqa
# from gui.textviewer import TextViewer
# from gui.widgets.datatreeview import DataTreeView

Ui_MetaDataWidget, QWidget = loadUiType(os.path.join(__module_path__, "metadatawidget.ui"))

class MetaDataWidget(Ui_MetaDataWidget, DataClassWidget):
    r"""Widget for displaying BaseScipyenData objectx.
    Where implemented, it also supports editing.
    NOTE/WARNING: Under development
    """
    sig_valueChanged = Signal(object, name="sig_valueChanged")
    # default_brain_atlas_name =  'whs_sd_rat_39um'
    # default_species = "Rattus norvegicus"

    _objectTypes_ = (bsc.BaseScipyenData, )

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]=None,
                 obj: typing.Optional[bsc.BaseScipyenData] = None,
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

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

        self.biologicalSourceEditor = None
        self._collapsibleChildren_["biologicalSourceEditor"] = self.biologicalSourceEditor
        self.procedureEditor = None
        self._collapsibleChildren_["procedureEditor"] = self.procedureEditor

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_() # DataClassWidget!

        file_origin = ""
        if isinstance(self._data_.file_origin, pathlib.Path):
            file_origin = self._data_.file_origin.as_posix()

        elif isinstance(self._data_.file_origin, str):
            file_origin = self._data_.file_origin

        if isinstance(self._data_.file_datetime, datetime.datetime):
            file_datetime = f"{self._data_.file_datetime}"
        else:
            file_datetime = ""

        if len(file_origin.strip()):
            if len(file_datetime.strip()):
                self.fileOriginLabel.setText(f"{file_origin} ({file_datetime})")
            else:
                self.fileOriginLabel.setText(file_origin)
        else:
            self.fileOriginLabel.setText("")

        if isinstance(self._data_.rec_datetime, datetime.datetime):
            self.recDateTimeLabel.setText(f"{self._data_.rec_datetime}")
        else:
            self.recDateTimeLabel.setText("")

        if isinstance(self._data_.analysis_datetime, datetime.datetime):
            self.analysisDateTimeEdit.setDateTime(qtutils.datetime2Qt(self._data_.analysis_datetime))
        else:
            self.analysisDateTimeEdit.setDateTime(qtutils.datetime2Qt(datetime.datetime.now()))

        self.analysisDateTimeEdit.dateTimeChanged.connect(self._slot_analysisDateTimeChanged)

        self.toggleSourceEditorToolButton.toggled.connect(self._slot_toggleBioSourceEditor)

        self.toggleProcedureEditorToolButton.toggled.connect(self._slot_toggleProcedureEditor)

    def closeEvent(self, evt):
        self.closeSubWidgets()
        super().closeEvent(evt)
        evt.accept()

    def closeSubWidgets(self):
        if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
            self.biologicalSourceEditor.close()
            self.biologicalSourceEditor.deleteLater()
            self.biologicalSourceEditor = None

        if isinstance(self.procedureEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.procedureEditor):
            self.procedureEditor.close()
            self.procedureEditor.deleteLater()
            self.procedureEditor = None

        super().closeSubWidgets()

    def value(self):
        r"""Returns a dict with field values takes from individual children
        """
        return self._data_

    def setValue(self, data: bsc.BaseScipyenData, **kwargs):
        if not isinstance(data, bsc.BaseScipyenData):
            self._data_ = bsc.BaseScipyenData()
        else:
            self._data_ = data

        super().setValue(self._data_, **kwargs)

        if isinstance(self.biologicalSourceEditor, DataClassWidget):
            sb = QtCore.QSignalBlocker(self.biologicalSourceEditor) # noqa
            self.biologicalSourceEditor.setValue(self._data_.source, objSymbol="source")

    @Slot()
    def _slot_editBiologicalSource(self):
        from gui.widgets.dataclasswidgets.biologicalsourcewidget import BiologicalSourceWidget
        anchoringWidget = self.provideAnchoringWidget()
        if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
            if not isinstance(self.biologicalSourceEditor, BiologicalSourceWidget):
                self.biologicalSourceEditor.collapse(True)
                self.biologicalSourceEditor.deleteLater()
                self.biologicalSourceEditor = None

                self.biologicalSourceEditor = self._setupCollapsibleChild_(
                    BiologicalSourceWidget,
                    "biologicalSourceEditor",
                    self._slot_biologicalSourceChanged,
                    self.toggleSourceEditorToolButton,
                    anchoringWidget,
                    self._data_.source,
                    objSymbol="source"
                    )

                # self.biologicalSourceEditor = BiologicalSourceWidget(self._data_.source, objSymbol="source", anchoringWidget=anchoringWidget)
                # # self.biologicalSourceEditor.setWindowTitle("Source")
                # self.biologicalSourceEditor.sig_valueChanged.connect(self._slot_biologicalSourceChanged)
                # self.biologicalSourceEditor.sig_closing.connect(self._slot_biologicalSourceEditorClosing)
                # self.biologicalSourceEditor.sig_collapsed.connect(self._slot_biologicalSourceEditorCollapsed)
                # self.biologicalSourceEditor.setObjectName("biologicalSourceEditor")

        else:
            self.biologicalSourceEditor = self._setupCollapsibleChild_(
                BiologicalSourceWidget,
                "biologicalSourceEditor",
                self._slot_biologicalSourceChanged,
                self.toggleSourceEditorToolButton,
                anchoringWidget,
                self._data_.source,
                objSymbol="source"
                )

            # self.biologicalSourceEditor = BiologicalSourceWidget(self._data_.source, objSymbol="source", anchoringWidget=anchoringWidget)
            # # self.biologicalSourceEditor.setWindowTitle("Source")
            # self.biologicalSourceEditor.sig_valueChanged.connect(self._slot_biologicalSourceChanged)
            # self.biologicalSourceEditor.sig_closing.connect(self._slot_biologicalSourceEditorClosing)
            # self.biologicalSourceEditor.sig_collapsed.connect(self._slot_biologicalSourceEditorCollapsed)
            # self.biologicalSourceEditor.setObjectName("biologicalSourceEditor")


        # self._collapsibleChildren_["biologicalSourceEditor"] = self.biologicalSourceEditor
        # self.biologicalSourceEditor.setValue(self._data_.source, objSymbol="source")

        if not self.biologicalSourceEditor.isVisible():
            self.biologicalSourceEditor.show()

        if isinstance(self._data_.source.name, str) and len(self._data_.source.name.strip()):
            self.biologicalSourceEditor.setWindowTitle(f"Source: {self._data_.source.name} ({type(self._data_.source).__name__})")
        else:
            self.biologicalSourceEditor.setWindowTitle(f"Source: {type(self._data_.source).__name__}")

    @Slot()
    def _slot_biologicalSourceEditorCollapsed(self):
        sb = QtCore.QSignalBlocker(self.toggleSourceEditorToolButton) # noqa
        self.toggleSourceEditorToolButton.setChecked(False)

    @Slot()
    def _slot_biologicalSourceEditorClosing(self):
        sb = QtCore.QSignalBlocker(self.toggleSourceEditorToolButton) # noqa
        self.toggleSourceEditorToolButton.setChecked(False)

    @Slot(object)
    def _slot_biologicalSourceChanged(self, val: sdc.BiologicalSource):
        if isinstance(val, sdc.BiologicalSource):
            self._data_.source = val
        else:
            self._data_.source = sdc.BiologicalSource()

        self.sig_valueChanged.emit(self._data_)

    @Slot(bool)
    def _slot_toggleBioSourceEditor(self, val: bool):
        if val is True:
            self._slot_editBiologicalSource()
        else:
            if isinstance(self.biologicalSourceEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.biologicalSourceEditor):
                sb = QtCore.QSignalBlocker(self.biologicalSourceEditor) # noqa
                self.biologicalSourceEditor.collapse(False)

    @Slot(bool)
    def _slot_toggleProcedureEditor(self, val: bool):
        if val is True:
            self._slot_editProcedure()
        else:
            if isinstance(self.procedureEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.procedureEditor):
                self.procedureEditor.collapse(False)

    @Slot()
    def _slot_editProcedure(self): # TODO
        from gui.widgets.dataclasswidgets.procedurewidget import ProcedureWidget
        anchoringWidget = self.provideAnchoringWidget()
        # anchoringWidget = self.anchoringWidget if (isinstance(self._anchoringWidget_, QtWidgets.QWidget) and self.overrideAnchor) else self if self.parent() is None else None

        if isinstance(self.procedureEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.procedureEditor):
            if not isinstance(self.procedureEditor, ProcedureWidget):
                self.procedureEditor.collapse(True)
                self.procedureEditor.deleteLater()
                self.procedureEditor = None

                self.procedureEditor = self._setupCollapsibleChild_(
                    ProcedureWidget,
                    "procedureEditor",
                    self._slot_procedureChanged,
                    self.toggleSourceEditorToolButton,
                    anchoringWidget,
                    windowTitle =
                    self._data_.procedure, objSymbol="procedure"
                    )

                # self.procedureEditor = ProcedureWidget(self._data_.procedure, objSymbol="procedure", anchoringWidget=anchoringWidget)
                # self.procedureEditor.sig_valueChanged.connect(self._slot_procedureChanged)
                # self.procedureEditor.sig_closing.connect(self._slot_procedureEditorClosing)
                # self.procedureEditor.sig_collapsed.connect(self._slot_procedureEditorCollapsed)
                # self.procedureEditor.setObjectName("procedureEditor")

        else:
            self.procedureEditor = self._setupCollapsibleChild_(
                ProcedureWidget,
                "procedureEditor",
                self._slot_procedureChanged,
                self.toggleSourceEditorToolButton,
                anchoringWidget,
                self._data_.procedure, objSymbol="procedure"
                )
            # self.procedureEditor = ProcedureWidget(self._data_.procedure, objSymbol="procedure", anchoringWidget=anchoringWidget)
            # self.procedureEditor.sig_valueChanged.connect(self._slot_procedureChanged)
            # self.procedureEditor.sig_closing.connect(self._slot_procedureEditorClosing)
            # self.procedureEditor.sig_collapsed.connect(self._slot_procedureEditorCollapsed)
            # self.procedureEditor.setObjectName("procedureEditor")

        if not self.procedureEditor.isVisible():
            self.procedureEditor.show()

        if isinstance(self._data_.procedure.name, str) and len(self._data_.procedure.name.strip()):
            self.procedureEditor.setWindowTitle(f"Procedure: {self._data_.procedure.name} ({type(self._data_.procedure).__name__})")
        else:
            self.procedureEditor.setWindowTitle(f"Procedure: {type(self._data_.procedure).__name__}")

    @Slot()
    def _slot_procedureEditorClosing(self):
        sb = QtCore.QSignalBlocker(self.toggleProcedureEditorToolButton) # noqa
        self.toggleProcedureEditorToolButton.setChecked(False)

    @Slot()
    def _slot_procedureEditorCollapsed(self):
        sb = QtCore.QSignalBlocker(self.toggleProcedureEditorToolButton) # noqa
        self.toggleProcedureEditorToolButton.setChecked(False)


    @Slot(object)
    def _slot_procedureChanged(self, value: sdc.Procedure):
        self._data_.procedure = value
        self.sig_valueChanged.emit(self._data_)

    @Slot(QtCore.QDateTime)
    def _slot_analysisDateTimeChanged(self, val: QtCore.QDateTime):
        self._data_.analysis_datetime = qtutils.datetimeFromQt(val)

        self.sig_valueChanged.emit(self._data_)

    @property
    def field(self):
        return self._field

    @field.setter
    def field(self, value:typing.Union[str, type(pd.NA)]):
        signalBlocker = QtCore.QSignalBlocker(self.fieldIDLineEdit) # noqa
        if isinstance(value, str) and len(value.strip()):
            self._field = value
            if self._field in ("NA", "<NA>"):
                self._field = pd.NA
        else:
            self._field = pd.NA

        self.fieldIDLineEdit.setText(f"{self._field}")

        self.sig_valueChanged.emit()

