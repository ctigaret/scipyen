# -*- coding: utf-8 -*-
# $Id: procedurewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
TODO: 2026-07-17 10:18:10 FIXME

• in ProcedureWidget: when widget's data is a PPLProcedure (i.e. a regulated
procedure) check that the PPLProtocol is among the protocols authorized on the PPL
and that the PPLProtocolStep is among the steps authorized in the PPLProtocol

• also check that their respective parents (PPL for PPLProtocol, and PPLProtocol
for a PPLProtocolStep) are in agreement with the authorizations in place.
"""

import sys, os, typing, types, warnings, math, cmath, datetime # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot)#, Property,)
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    from PySide6.QtCore import (Signal, Slot, Property,) # noqa
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


# from core.prog import scipywarn
# from core import scipyen_quantities as scq
from core import scipyendataclasses as sdc
from core import qtutils
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

try:
    from gui.widgets.dataclasswidgets.procedurewidget_ui import Ui_ProcedureWidget

except:
    Ui_ProcedureWidget, _ = loadUiType(
        os.path.join(__module_path__, "procedurewidget.ui")
        )

try:
    from gui.widgets.dataclasswidgets.simpleprocedurewidget_ui import Ui_SimpleProcedureWidget

except:
    Ui_SimpleProcedureWidget, _ = loadUiType(
        os.path.join(__module_path__, "simpleprocedurewidget.ui")
        )

class SimpleProcedureWidget(Ui_SimpleProcedureWidget, DataClassWidget):
    _objectTypes_ = (sdc.Procedure, )
    procedureTypeNames = list(sdc.ProcedureType.names())
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.CellCompartment] = None,
                 **kwargs):
        super(Ui_SimpleProcedureWidget, self).__init__9
        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        if not isinstance(obj, self._objectTypes_):
            obj = sdc.Procedure()

        self._data_ = obj

        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        ndx = self.procedureTypeNames.index(self._data_.procedureType.name)
        self.typeComboBox.addItems(self.procedureTypeNames)
        self.typeComboBox.setCurrentIndex(ndx)
        self.typeComboBox.currentIndexChanged.connect(self._slot_procedureTypeChanged)

        self.sig_uiConfigured.emit()

    def value(self) -> sdc.Procedure:
        return self._data_

    def setValue(self, val: sdc.Procedure, **kwargs):
        if not isinstance(val, sdc.Procedure):
            val = sdc.Procedure()

        self._data_ = val

        ndx = self.procedureTypeNames.index(self._data_.procedureType.name)

        with qtutils.SignalBlocker(self.typeComboBox):
            self.typeComboBox.setCurrentIndex(ndx)

    @Slot(int)
    def _slot_procedureTypeChanged(self, val: int):
        self._data_.procedureType = sdc.ProcedureType[self.procedureTypeNames[val]]
        self.sig_valueChanged.emit(self._data_)

class ProcedureWidget(Ui_ProcedureWidget, DataClassWidget):
    # TODO: 2026-07-17 10:44:58 FIXME
    # • include a field to edit the legal framework (currently this is fixed to
    #   "ASPA 1986")
    _objectTypes_ = (sdc.Procedure, )
    procedureTypeNames = list(sdc.ProcedureType.names())

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None,
                 obj: typing.Optional[sdc.CellCompartment] = None,
                 **kwargs):
        super(Ui_ProcedureWidget, self).__init__()
        if isinstance(parent, self._objectTypes_):
            obj_ = parent
            if isinstance(obj, QtWidgets.QWidget):
                parent = obj
            else:
                parent = None

            obj = obj_

        if not isinstance(obj, self._objectTypes_):
            obj = sdc.Procedure()

        self._data_ = obj


        DataClassWidget.__init__(self, parent=parent, **kwargs)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        super()._configureUI_()

        ndx = self.procedureTypeNames.index(self._data_.procedureType.name)
        self.typeComboBox.addItems(self.procedureTypeNames)
        self.typeComboBox.setCurrentIndex(ndx)
        self.typeComboBox.currentIndexChanged.connect(self._slot_procedureTypeChanged)

        if isinstance(self._data_, sdc.PPLProcedure):
            self.isRegulatedCheckBox.setChecked(True)
            self.pplWidget.setValue(self._data_.procedure.ppl)
            self.pilWidget.setValue(self._data_.procedure.pil)
            self.protocolWidget.setValue(self._data_.procedure.protocol)
            self.protocolStepWidget.setValue(self._data_.procedure.protocolStep)
            self.asruTabWidget.setEnabled(True)

        else:
            self.isRegulatedCheckBox.setChecked(False)
            self.pplWidget.setValue(sdc.PPL())
            self.pilWidget.setValue(sdc.PIL())
            self.protocolWidget.setValue(sdc.PPLProtocol)
            self.protocolStepWidget.setValue(sdc.PPLProtocolStep)
            self.asruTabWidget.setEnabled(False)

        self.pplWidget.sig_valueChanged.connect(self._slot_pplChanged)
        self.pilWidget.sig_valueChanged.connect(self._slot_pilChanged)
        self.protocolWidget.sig_valueChanged.connect(self._slot_pplProtocolChanged)
        self.protocolStepWidget.sig_valueChanged.connect(self._slot_pplProtocolStepChanged)
        self.isRegulatedCheckBox.toggled.connect(self._slot_setIsRegulatedProcedure)

        self.sig_uiConfigured.emit()

    def value(self) -> sdc.Procedure:
        return self._data_

    def setValue(self, val: sdc.Procedure, **kwargs):
        if not isinstance(val, sdc.Procedure):
            val = sdc.Procedure()

        self._data_ = val

        ndx = self.procedureTypeNames.index(self._data_.procedureType.name)
        with qtutils.SignalBlocker(self.typeComboBox):
            self.typeComboBox.setCurrentIndex(ndx)

    @Slot(int)
    def _slot_procedureTypeChanged(self, val: int):
        self._data_.procedureType = sdc.ProcedureType[self.procedureTypeNames[val]]
        self.sig_valueChanged.emit(self._data_)

    @Slot(bool)
    def _slot_setIsRegulatedProcedure(self, val: bool):
        with qtutils.SignalBlocker(
                (
                    self.pilWidget,
                    self.pplWidget,
                    self.protocolWidget,
                    self.protocolStepWidget,
                    self.typeComboBox,
                )
            ):
            self.asruTabWidget.setEnabled(val is True)

            if val is True:
                # switch to regulated procedure if current procedure is not regulated
                if not isinstance(self._data_, sdc.PPLProcedure):
                    pil = sdc.PIL()
                    ppl = sdc.PPL()
                    pplProtocol = sdc.PPLProtocol(parent=ppl)
                    pplProtocolStep = sdc.PPLProtocolStep(parent=pplProtocol)
                    procedure = sdc.PPLProcedure(ppl=ppl, pil=pil,
                                                protocol=pplProtocol,
                                                protocolStep=pplProtocolStep,
                                                procedureType=self._data_.procedureType,
                                                name=self._data_.name,
                                                description=self._data_.description)

                    self._data_ = procedure

                    self.pilWidget.setValue(pil)
                    self.pplWidget.setValue(ppl)
                    self.protocolWidget.setValue(pplProtocol)
                    self.protocolStepWidget.setValue(pplProtocolStep)

                    ndx = self.procedureTypeNames.index(self._data_.procedureType.name)
                    self.typeComboBox.setCurrentIndex(ndx)

                    self.sig_valueChanged.emit(self._data_)

            else:
                # switch to non-regulated if current procedure is regulated
                if isinstance(self._data_, sdc.PPLProcedure):
                    procedure = sdc.Procedure(name=self._data_.name,
                                            description=self._data_.description,
                                            procedureType=self._data_.procedureType)

                    self._data_ = procedure

                    self.pplWidget.setValue(sdc.PPL())
                    self.pilWidget.setValue(sdc.PIL())
                    self.protocolWidget.setValue(sdc.PPLProtocol)
                    self.protocolStepWidget.setValue(sdc.PPLProtocolStep)

                    ndx = self.procedureTypeNames.index(self._data_.procedureType.name)
                    self.typeComboBox.setCurrentIndex(ndx)

                    self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_pplChanged(self, value: sdc.PPL):
        if not isinstance(self._data_.procedure, sdc.PPLProcedure):
            return

        if not isinstance(value, sdc.PPL):
            value = sdc.PPL()

        self._data_.procedure.ppl = value
        self._data_.procedure.protocol.parent = value

        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_pilChanged(self, value: sdc.PIL):
        if not isinstance(self._data_.procedure, sdc.PPLProcedure):
            return

        if not isinstance(value, sdc.PIL):
            value = sdc.PIL()

        self._data_.procedure.pil = value

        self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_pplProtocolChanged(self, value: sdc.PPLProtocol):
        # TODO: 2026-07-17 10:47:16 FIXME streamline this !
        if not isinstance(self._data_.procedure, sdc.PPLProcedure):
            return

        if not isinstance(value, sdc.PPLProtocol):
            value = sdc.PPLProtocol(parent=self._data_.ppl)

        if value.parent != self._data_.ppl:
            # check that the new protocol has the same licence
            # if different, offer the option to adopt the new licence, pending
            # the protocol and the current protocol step are in agreement
            carryOn = self.questionMessage("PPL Protocol",
                                          "The new protocol has a different PPL. Adopt it?")
            if carryOn == QtWidgets.QMessageBox.Yes:
                # check that protocol is on its parent PPL; if not, then ask to
                # adopt it to the PPL else give up
                if len(value.parent.protocols) and value not in value.parent.protocols:
                    override = self.questionMessage("PPL Protocol",
                                                    "The new protocol does not appear to be authorized on this PPL. Continue?")
                    if override == QtWidgets.QErrorMessage.Yes:
                        value.parent.protocols.append(value)
                    else:
                        return

                # check that the protocol step is on this new protocol; if not,
                # then ask to adopt the step to the new protocol, else give up
                if len(value.steps) and self._data_.protocolStep not in value.steps:
                    override = self.questionMessage("PPL Protocol",
                                                    "The new protocol does not appear to authorise the current step. Continue?")
                    if override == QtWidgets.QMessageBox.Yes:
                        value.steps.append(self._data_.protocolStep)
                    else:
                        return

                self._data_.protocol = value
                self._data_.ppl = value.parent
                self._data_.protocolStep.parent=value

                with qtutils.SignalBlocker((self.pplWidget, self.protocolStepWidget)):
                    self.pplWidget.setValue(self._data_.ppl)
                    self.protocolStepWidget.setValue(self._data_.protocolStep)

                self.sig_valueChanged.emit(self._data_)
        else:
            # check that protocol is on its parent PPL; if not, then ask to
            # adopt it to the PPL else give up
            if len(value.parent.protocols) and value not in value.parent.protocols:
                override = self.questionMessage("PPL Protocol",
                                                "The new protocol does not appear to be authorized on this PPL. Continue?")
                if override == QtWidgets.QErrorMessage.Yes:
                    value.parent.protocols.append(self)
                else:
                    return

            # check that the protocol step is on this new protocol; if not,
            # then ask to adopt the step to the new protocol, else give up
            if len(value.steps) and self._data_.protocolStep not in value.steps:
                override = self.questionMessage("PPL Protocol",
                                                "The new protocol does not appear to authorise the current step. Continue?")
                if override == QtWidgets.QMessageBox.Yes:
                    value.steps.append(self._data_.protocolStep)
                else:
                    return

            self._data_.protocol = value
            self._data_.ppl = value.parent
            self._data_.protocolStep.parent=value

            with qtutils.SignalBlocker((self.pplWidget, self.protocolStepWidget)):
                self.pplWidget.setValue(self._data_.ppl)
                self.protocolStepWidget.setValue(self._data_.protocolStep)

            self.sig_valueChanged.emit(self._data_)

    @Slot(object)
    def _slot_pplProtocolStepChanged(self, value: sdc.PPLProtocolStep):
        if not isinstance(self._data_.procedure, sdc.PPLProcedure):
            return

        if not isinstance(value, sdc.PPLProtocolStep):
            value = sdc.PPLProtocolStep(parent=self._data_.protocol)

        if value.parent != self._data_.protocol:
            carryOn = self.questionMessage("PPL Protocol Step",
                                          "The new step belongs to a different PPL Protocol. Adopt it?")

            if carryOn == QtWidgets.QMessageBox.Yes:
                if value.parent.parent != self._data_.ppl:
                    override = self.questionMessage("PPL Protocol Step",
                                                    "The protocol of this step appears to be authorized on a different PPL. Adopt it?")
                    if override:
                        self._slot_pplProtocolChanged(value.parent)
                        return

                    else:
                        return

                if len(self._data_.protocol.steps) and value not in self._data_.protocol.steps:
                    override = self.questionMessage("PPL Protocol Step",
                                                    "The new step does not appear to be authorized on the current PPL Protocol. Continue?")
                    if override == QtWidgets.QErrorMessage.Yes:
                        self._data_.protocol.steps.append(value)
                    else:
                        return

            self._data_.protocolStep = value

            with qtutils.SignalBlocker((self.pplWidget, self.protocolStepWidget)):
                self.protocolStepWidget.setValue(value)

            self.sig_valueChanged.emit(self._data_)

        else:
            if len(self._data_.protocol.steps) and value not in self._data_.protocol.steps:
                override = self.questionMessage("PPL Protocol Step",
                                                "The new step does not appear to be authorized on the current PPL Protocol. Continue?")
                if override == QtWidgets.QErrorMessage.Yes:
                    self._data_.protocol.steps.append(value)
                else:
                    return

            self._data_.protocolStep = value

            with qtutils.SignalBlocker((self.pplWidget, self.protocolStepWidget)):
                self.protocolStepWidget.setValue(value)

            self.sig_valueChanged.emit(self._data_)





