# -*- coding: utf-8 -*-
# $Id: pvimporter.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing
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

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

from core.prog import (scipywarn, print_styled)
from core.sysutils import adapt_ui_path
from core.utilities import safewrapper
from core.neoutils import (concatenate_blocks, concatenate_signals,set_relative_time_start)
from core.traitcontainers import DataBag
from core.triggerevent import (TriggerEvent, TriggerEventType, )
from core.triggerprotocols import (TriggerProtocol,
                                   auto_detect_trigger_protocols,
                                   embed_trigger_protocol,
                                   embed_trigger_event,
                                   parse_trigger_protocols,
                                   remove_trigger_protocol,
                                   parse_trigger_protocols)
import iolib.pictio as pio
from systems.PrairieView import *
from systems.PrairieView import loadPrairieViewXML
from gui import quickdialog as qd
from gui.triggerdetectgui import TriggerDetectDialog, TriggerDetectWidget
from gui.triggerprotocolseditordialog import TriggerProtocolsEditorDialog
from gui import pictgui as pgui
from gui.workspacegui import WorkspaceGuiMixin
import gui.signalviewer as sv
from imaging import (imageprocessing as imgp, axisutils, axiscalibration,)
from imaging.scandata import (ScanData, ScanDataOptions, scanDataOptions,)

from imaging.vigrautils import (concatenateImages, insertAxis)

from imaging.axisutils import (axisTypeFromString, axisTypeName,
                               axisTypeSymbol, axisTypeUnits,)

from imaging.axiscalibration import (AxesCalibration,
                                     CalibrationData,
                                     ChannelCalibrationData,
                                     AxisCalibrationData)

import ephys.ephys as ephys

try:
    from systems.PrairieImporter_ui import Ui_PrairieImporterDialog

except:
    __ui_path__ = adapt_ui_path(__module_path__, "PrairieImporter.ui")

    if os.environ["QT_API"] in ("pyqt5", "pyside2"):
        Ui_PrairieImporterDialog, _ = loadUiType(__ui_path__, from_imports=True, import_from="gui")
    else:
        Ui_PrairieImporterDialog, _ = loadUiType(__ui_path__)



class PrairieViewImporter(QtWidgets.QDialog, Ui_PrairieImporterDialog, WorkspaceGuiMixin):
    sig_protocolRemoved = Signal(int, name="sig_protocolRemoved")

    def __init__(self, parent=None,
                 name: typing.Optional[str] = None,
                 pvScanFileName: typing.Optional[typing.Union[pathlib.Path, str]]=None,
                 optionsFileName: typing.Optional[typing.Union[pathlib.Path, str]]=None,
                 ephysFileNames: typing.Optional[typing.Union[pathlib.Path, str, tuple, list]]=None,
                 protocolFileName: typing.Optional[typing.Union[pathlib.Path, str]]=None,
                 clearTriggerEvents: typing.Optional[bool]=False,
                 auto_export:bool = False,
                 **kwargs): # parent, flags - see documentation for QDialog constructor in Qt Assistant
        r"""
        Parameters:
        -----------
        name: (optional, default is None) - name of generated ScanData
        pvScanFileName: (optional, default is None) - name of PrairieView scan
            experiment (XML) file
        optionsFileName: (optional, default is None) - name of a pickle (*pkl)
            file containing ScanData options
        ephysFileNames: name, or names, of Axon file(s) , or pickle (*.pkl) files,
            containing associated electrophysiology data.

            The Axon files can be text (*.atf) or binary (*.abf) files.

            Optional; default is None

        protocolFileName: name of pickle (*.pkl) file with TriggerProtocols

        clearTriggerEvents:bool (optional, default is False)
                            When True (default), remove all neo.Event objects
                            embedded in the electrophysiology data, before
                            detecting trigger events.

        auto_export: bool (optional, default is False)
            When True, pressing "OK" button will export the generated ScanData
            to the workspace.

            This is a convenience to place data directly in Scipyen's workspace.

            When False (the default) the dialog simply generates the Scandata
            object and stores it in the "scanData" attribute. TODO: Because this
            can be time consuming best is to call this asynchronously, when
            auto_export is False.

        """
        # NOTE: 2021-04-18 11:49:52
        # 'parent' parameter is required; when called from a PyQt5 slot, 'parent'
        # should be set to the object which own the slot, so that it will take
        # owership fo the dialog; otherwise, the dialog will go out of scope when
        # the slot returns - this means its window will close and the C/C++
        # objects that compose it will be garbage collected (also meaning that
        # later delete actions on these objects will throw exceptions)
        #
        # see also scipyen gui.mainwindow.ScipyenWindow.slot_importPrairieView()
        super().__init__(parent)
        super(Ui_PrairieImporterDialog, self).__init__()
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        #super(WorkspaceGuiMixin, self).__init__(parent, **kwargs)

        self._scandata_ = None # the outcome: a ScanData object

        self._pvscan_ = None # the xml.dom.minidom.Document that specifies the
                            # the PVScan experiment

        self.dataName = "" # the value of lsdata "name" attribute

        self.pvScanFileName:pathlib.Path = pathlib.Path() # the PV Scan XML document file - contains
                                 # scan experiment information & location of
                                 # the files with the numerical data of lsdata

        self.scanDataVarName:str = "" # the name that will be assigned to lsdata in the
                                # user's workspace

        self.protocolFileName:pathlib.Path = pathlib.Path() # pickle file containing the trigger protocols

        self.optionsFileName:pathlib.Path = pathlib.Path() # pickle file containing saved ESPCaT options

        self.ephysFileNames:typing.List[pathlib.Path] = list()

        self.scanDataOptions:ScanDataOptions = ScanDataOptions.default() # ScanDataOptions object - to be assigned to lsdata

        self._ephys_:typing.Optional[neo.Block] = None # a neo.Block with electrophysiology recordings associated
                            # with lsdata


        self.clearEvents:bool = clearTriggerEvents if isinstance(clearTriggerEvents, bool) else False

        self.triggerProtocols = list()  # list of TriggerProtocol objects associated
                                        # with lsdata

        self.cachedEvents = list()
        self.cachedProtocols = list()
        self.cachedProtocolFileName:pathlib.Path = pathlib.Path()

        if isinstance(name, str) and len(name.strip()):
            self.dataName = name
            self.scanDataVarName = strutils.str2symbol(self.dataName)

        if isinstance(pvScanFileName, pathlib.Path):
            self.pvScanFileName = pvScanFileName

        elif isinstance(pvScanFileName, str) and len(pvScanFileName.strip()):
            if os.path.isfile(pvScanFileName) and any([mime in pio.mimetypes.guess_type(pvScanFileName)[0] for mime in ("xml", "pickle")]):
                self.pvScanFileName = pathlib.Path(pvScanFileName)

        if isinstance(optionsFileName, pathlib.Path):
            self.optionsFileName = optionsFileName

        elif isinstance(optionsFileName, str) and len(optionsFileName.strip()):
            if os.path.isfile(optionsFileName) and "pickle" in pio.mimetypes.guess_type(optionsFileName)[0]:
                self.optionsFileName = pathlib.Path(optionsFileName)

        if isinstance(ephysFileNames, pathlib.Path):
            self.ephysFileNames = [ephysFileNames]

        elif isinstance(ephysFileNames, str) and len(ephysFileNames.strip()):
            if os.path.isfile(ephysFileNames) and any([mime in pio.mimetypes.guess_type(ephysFileNames)[0] for mime in ("pickle", "axon")]):
                self.ephysFileNames = list(map(lambda f: pathlib.Path(f), [ephysFileNames]))

        elif isinstance(ephysFileNames, (tuple, list)):
            if all(isinstance(v, pathlib.Path) for v in ephysFileNames):
                self.ephysFileNames = ephysFileNames
            elif all([isinstance(v, str) for v in ephysFileNames]):
                self.ephysFileNames = list(map(lambda f: pathlib.Path(f), filter(lambda f: len(f.strip()) and any([mime in pio.mimetypes.guess_type(f)[0]]), ephysFileNames)))
            # self.ephysFileNames = [s for s in ephysFileNames if (len(s.strip()) and any([mime in pio.mimetypes.guess_type(s)[0]]))]

        if isinstance(protocolFileName, pathlib.Path):
            self.protocolFileName = protocolFileName

        elif isinstance(protocolFileName, str) and len(protocolFileName.strip()):
            if os.path.isfile(self.protocolFileName) and "pickle" in pio.mimetypes.guess_type(self.protocolFileName)[0]:
                self.protocolFileName = pathlib.Path(protocolFileName)

        self.auto_export = auto_export

        self._configureUI_()
        self.setSizeGripEnabled(True)

    def _configureUI_(self):
        self.setupUi(self)

        self.dataNameLineEdit.undoAvailable=True
        self.dataNameLineEdit.redoAvailable=True
        self.dataNameLineEdit.setClearButtonEnabled(True)
        if len(self.dataName):
            self.dataNameLineEdit.setText(self.dataName)
        self.dataNameLineEdit.editingFinished.connect(self._slot_setDataName)
        self.dataNameLineEdit.textChanged.connect(self._slot_setDataName)

        self.pvScanFileNameLineEdit.undoAvailable=True
        self.pvScanFileNameLineEdit.redoAvailable=True
        self.pvScanFileNameLineEdit.setClearButtonEnabled(True)
        if self.pvScanFileName.is_file():
            self.pvScanFileNameLineEdit.setText(self.pvScanFileName.as_posix())
        self.pvScanFileNameLineEdit.editingFinished.connect(self._slot_setPVScanFileName)
        self.pvScanFileNameLineEdit.textChanged.connect(self._slot_setPVScanFileName)

        self.pvScanFileChooserToolButton.clicked.connect(self._slot_choosePVScanFile)
        self.pvScanImportFromWorkspaceToolButton.clicked.connect(self._slot_importPVScanFromWorkspace)

        self.optionsFileNameLineEdit.undoAvailable=True
        self.optionsFileNameLineEdit.redoAvailable=True
        self.optionsFileNameLineEdit.setClearButtonEnabled(True)

        if self.optionsFileName.is_file():
            self.optionsFileNameLineEdit.setText(self.optionsFileName.as_posix())
        self.optionsFileNameLineEdit.editingFinished.connect(self._slot_setOptionsFileName)
        self.optionsFileNameLineEdit.textChanged.connect(self._slot_setOptionsFileName)

        self.optionsFileChooserToolButton.clicked.connect(self._slot_chooseOptionFile)
        self.optionsImportToolButton.clicked.connect(self._slot_importOptionsFromWorkspace)

        self.ephysFileNameLineEdit.undoAvailable=True
        self.ephysFileNameLineEdit.redoAvailable=True
        self.ephysFileNameLineEdit.setClearButtonEnabled(True)
        self.ephysFileNameLineEdit.setText(os.pathsep.join(list(map(lambda f: f.as_posix(), self.ephysFileNames))))
        self.ephysFileNameLineEdit.editingFinished.connect(self._slot_setEphysFileNames)

        self.ephysFileChooserToolButton.clicked.connect(self._slot_chooseEphysFiles)
        self.ephysImportFromWorkspaceToolButon.clicked.connect(self._slot_importEphysFromWorkspace)

        self.triggerProtocolFileNameLineEdit.undoAvailable=True
        self.triggerProtocolFileNameLineEdit.redoAvailable=True
        self.triggerProtocolFileNameLineEdit.setClearButtonEnabled(True)

        if self.protocolFileName.is_file():
            self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName.as_posix())
        self.triggerProtocolFileNameLineEdit.editingFinished.connect(self._slot_setProtocolFileName)
        self.triggerProtocolFileNameLineEdit.textChanged.connect(self._slot_setProtocolFileName)


        self.triggerProtocolFileChooserToolButton.clicked.connect(self._slot_chooseProtocolFile)

        self.protocolsImportToolButton.clicked.connect(self._slot_importProtocolFromWorkspace)

        self.detectTriggersToolButton.clicked.connect(self._slot_startTriggerEventDetectionGui)
        self.editTriggerProtocolsToolButton.clicked.connect(self._slot_editTriggerProtocols)
        self.buildScandataToolButton.clicked.connect(self.slot_generateScanData)

        # NOTE: 2021-10-09 23:55:03
        # below self._scipyenWindow_ is inherited from WorkspaceGuiMixin (initialized)
        self.ephysPreview = sv.SignalViewer(win_title = "Trigger Events Detection")

        # NOTE: 2021-03-21 11:35:59 just a "place holder" here; the actual dialog
        # created in _slot_startTriggerEventDetectionGui()
        self.eventDetectionDialog = None # when a TriggerDetectDialog, this caches the detection options & events

        self.protocolEditorDialog = TriggerProtocolsEditorDialog(title = "Edit Trigger Protocols")

        # the TriggerProtocolsEditorDialog works on a reference to the list of
        # TriggerProtocols stored in here.
        self.protocolEditorDialog.triggerProtocols = self.triggerProtocols
        self.protocolEditorDialog.sig_detectTriggers.connect(self._slot_startTriggerEventDetectionGui)
        self.protocolEditorDialog.sig_removeProtocol.connect(self._slot_removeProtocol)
        self.protocolEditorDialog.sig_requestProtocolAdd.connect(self._slot_protocolAddRequest)
        self.protocolEditorDialog.finished.connect(self._slot_protocolEditorFinished)

    @Slot(int)
    def _slot_removeProtocol(self, index):
        r"""Removes a trigger protocol.
        """
        # TODO: contemplate the use of the traitlets' observer paradigm with
        # TriggerProtocol objects.

        if index < len(self.triggerProtocols):
            tp = self.triggerProtocols[index]

            if isinstance(self._scandata_, ScanData):
                self._scandata_.removeTriggerProtocol(index)

            if isinstance(self._ephys_, neo.Block):
                remove_trigger_protocol(tp, self._ephys_)

            self.sig_protocolRemoved.emit(index)

    @Slot()
    def _slot_protocolAddRequest(self):
        pass

    @Slot()
    def _slot_editTriggerProtocols(self):
        self.protocolEditorDialog.triggerProtocols = self.triggerProtocols
        self.protocolEditorDialog.open()

    @Slot()
    def _slot_protocolEditorFinished(self):
        pass

    @Slot()
    @safewrapper
    def _slot_startTriggerEventDetectionGui(self):
        r"""Opens the trigger event detection dialog.
        The following signals are connected to this slot:
            detectTriggersToolButton.clicked()
            protocolEditorDialog.sig_detectTrigger()
        """
        if self._ephys_ is None:
            return

        if isinstance(self._ephys_, neo.Block) and len(self._ephys_.segments):
            if self.eventDetectionDialog is None:
                self.eventDetectionDialog = TriggerDetectDialog(ephysdata=self._ephys_,
                                                                clearEvents=True,
                                                                ephysViewer = self.ephysPreview)
                                                                #parent=self._scipyenWindow_)
                self.eventDetectionDialog.finished.connect(self._slot_stopTriggerEventDetectionGui)

            #self.ephysPreview.plot(self._ephys_) # done in TriggerDetectDialog c'tor

            # NOTE: 2021-04-11 14:06:55
            # call open() instead of anything else to keep the GUI loop running
            # and NOT block interaction with other windows, especially with the
            # SignalViewer that plots the ephys data
            self.eventDetectionDialog.adjustSize()
            self.eventDetectionDialog.open()

    @Slot()
    def _slot_stopTriggerEventDetectionGui(self):
        r"""Closes trigger event detection dialog and interprets the result.
        If dialog.result() is "accepted" (or yes/ok) then a new set collection
        of trigger protocols is generated.

        The following signals are connected to this slot:
            eventDetectionDialog.finished()
        """
        self.ephysPreview.close()
        if self.eventDetectionDialog.result():
            if not self.eventDetectionDialog.detected:
                self.eventDetectionDialog.detect_triggers()

            if len(self.eventDetectionDialog.triggerProtocols[:]):
                self.cachedProtocols[:] = self.triggerProtocols[:]
                self.cachedProtocolFileName = self.triggerProtocolFileNameLineEdit.text()
                self.triggerProtocols[:] = self.eventDetectionDialog.triggerProtocols[:]

                self.triggerProtocolFileNameLineEdit.setText("<detected>")

            else:
                self.triggerProtocolFileNameLineEdit.setText("")

    @Slot()
    def _slot_undoTriggers(self):
        if self._ephys_ is None:
            return

        signalblockers = [QtCore.QSignalBlocker(self.triggerProtocolFileNameLineEdit)]

        for k,s in enumerate(self._ephys_.segments):
            s.events.clear()
            if k < len(self.cachedEvents):
                s.events = self.cachedEvents[k]

        self.triggerProtocols[:] = self.cachedProtocols[:]
        self.ephysPreview.plot(self._ephys_)
        self.updateProtocolEditor()

        if len(self.protocolFileName):
            self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)

    @Slot(int)
    def _slot_clearEventsChanged(self, value):
        self.clearEvents = self.clearEventsCheckBox.isChecked()

    @Slot()
    @safewrapper
    def _slot_setPVScanFileName(self):
        # connected to editing the PVScan field
        if "imported" in self.pvScanFileNameLineEdit.text():
            return

        self.pvScanFileName = self.pvScanFileNameLineEdit.text().strip()

        if len(self.pvScanFileName.strip()):
            ret = self.loadPVScan(self.pvScanFileName)
            if not ret:
                self.pvScanFileName = ""
                self._pvscan_ = None
                self._scandata_ = None

        else:
            self.pvScanFileName = ""
            self._pvscan_ = None
            self._scandata_ = None

    @Slot()
    @safewrapper
    def _slot_choosePVScanFile(self):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
        fileFilter = ";;".join(["XML Files (*.xml)", "Pickle files (*.pkl)", "All files (*.*)"])

        fn, _ = self.chooseFile(caption="Open PrairieView file",
                                   fileFilter=fileFilter)
        if not isinstance(fn, str) or len(fn.strip()) == 0:
            return

        self.pvScanFileName = pathlib.Path(fn)
        if not self.pvScanFileName.is_file():
            scipywarn(f"File {self.pvScanFileName} does not exist")
            return

        # if len(self.pvScanFileName.strip()):
        if self.pvScanFileName.is_file():
            self._scandata_ = None # because we need to rebuild the scanData
            if self.loadPVScan(self.pvScanFileName):
                self.pvScanFileNameLineEdit.setText(self.pvScanFileName.as_posix())
            else:
                self.pvScanFileNameLineEdit.clear()
                self.pvScanFileName = ""
                self._pvscan_ = None

        else:
            self.pvScanFileNameLineEdit.clear()
            self.pvScanFileName = ""
            self._pvscan_ = None

    @Slot()
    @safewrapper
    def _slot_setOptionsFileName(self):
        # connected to editing Options field
        if "imported" in self.optionsFileNameLineEdit.text():
            return
        self.optionsFileName = self.optionsFileNameLineEdit.text()
        if len(self.optionsFileName.strip()):
            ret = self.loadOptions(self.optionsFileName)
            if not ret:
                self.optionsFileName = ""
                # NOTE: 2024-07-28 10:06:23
                # this may overwrite prev options, so chuck it
                # self.scanDataOptions = ScanDataOptions.default()

        else:
            self.optionsFileName = ""
            # see NOTE: 2024-07-28 10:06:23
            # self.scanDataOptions = ScanDataOptions.default()

    @Slot()
    @safewrapper
    def _slot_chooseOptionFile(self):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
        caption = "Open ScanData Options file for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open EPSCaT Options file"

        self.optionsFileName, _ = self.chooseFile(caption=caption, fileFilter="HDF5 Files (*.h5)")
        # self.optionsFileName, _ = self.chooseFile(caption=caption, fileFilter="Pickle Files (*.pkl)")

        if len(self.optionsFileName.strip()):
            if self.loadOptions(self.optionsFileName):
                self.optionsFileNameLineEdit.setText(self.optionsFileName)

            else:
                self.optionsFileName = ""
                self.optionsFileNameLineEdit.clear()
                self.scanDataOptions = None

        else:
            self.optionsFileName = ""
            self.optionsFileNameLineEdit.clear()
            self.scanDataOptions = None

    @Slot()
    @safewrapper
    def _slot_setEphysFileNames(self):
        # NOTE: 2020-12-26 12:17:01 This always generates a list of str even if
        # the split results in only one element.
        if any([v in self.ephysFileNameLineEdit.text() for v in ("mutliple files", "imported")]):
            return

        self.ephysFileNames = self.ephysFileNameLineEdit.text().split(os.pathsep)

        if len(self.ephysFileNames):
            ret = self.loadEphys(self.ephysFileNames)
            if not ret:
                self._ephys_ = None

        else:
            self._ephys_ = None

    @Slot()
    @safewrapper
    def _slot_chooseEphysFiles(self):
        signalblockers =[QtCore.QSignalBlocker(w) for w in (self.ephysFileNameLineEdit,)]

        #targetDir = os.getcwd()
        caption = "Open Electrophysiology Data file(s) for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open Electrophysiology Data file(s)"

        fileFilter = ";;".join(["Axon files (*.abf)", "Pickle files (*.pkl)"])

        fNames, _ = self.chooseFile(caption=caption, fileFilter=fileFilter, single=False)
        self.ephysFileNames = list(map(lambda f: pathlib.Path(f), fNames))

        if len(self.ephysFileNames) == 1:
            self.ephysFileNameLineEdit.setText(self.ephysFileNames[0].as_posix)

        elif len(self.ephysFileNames) > 1:
            self.ephysFileNameLineEdit.setText("<multiple files>")

        else:
            self.ephysFileNameLineEdit.clear()

        if len(self.ephysFileNames):
            ret = self.loadEphys(self.ephysFileNames)
            if not ret:
                self.ephysFileNameLineEdit.clear()
                self._ephys_ = None

    @Slot()
    @safewrapper
    def _slot_setDataName(self):
        self.dataName = self.dataNameLineEdit.text()
        if len(self.dataName.strip()):
            self.scanDataVarName = strutils.str2symbol(self.dataName)

    @Slot()
    @safewrapper
    def _slot_setProtocolFileName(self):
        if any([v in self.triggerProtocolFileNameLineEdit.text() for v in ("imported", "detected")]):
            return
        self.protocolFileName = pathlib.Path(self.triggerProtocolFileNameLineEdit.text())
        if self.protocolFileName.is_file():
            if self.loadProtocols(self.protocolFileName):
                self.cachedProtocolFileName = self.protocolFileName

        else:
            self.triggerProtocols.clear()

    @Slot()
    @safewrapper
    def _slot_chooseProtocolFile(self):
        signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
        targetdir = os.getcwd()
        caption = "Open Trigger Protocol file for %s" % self.scanDataVarName if (isinstance(self.scanDataVarName, str) and len(self.scanDataVarName.strip())) else "Open Trigger Protocol file"

        fName, _ = self.chooseFile(caption=caption, fileFilter="Pickle Files (*.pkl)")
        if not isinstance(fName, str) or len(fName.strip()) == 0:
            return
        self.protocolFileName = pathlib.Path(fname)

        if self.protocolFileName.is_file():
            if self.loadProtocols(self.protocolFileName):
                self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName.as_posix())
                self.cachedProtocolFileName = self.protocolFileName

        else:
            self.triggerProtocolFileNameLineEdit.setText(self.cachedProtocolFileName.as_posix())
            self.triggerProtocols.clear()

    @Slot()
    @safewrapper
    def _slot_importPVScanFromWorkspace(self):
        vars_ = self.importWorkspaceData([xmlutils.xml.dom.minidom.Document, PVScan],
                                         title="Import PVScan",
                                         single=True)

        if len(vars_):
            if isinstance(vars_[0], xmlutils.xml.dom.minidom.Document):
                self._pvscan_ = PVScan(vars_[0])
            elif isinstance(vars_[0], PVScan):
                self._pvscan_ = vars_[0]
            else:
                self.errorMessage("Import PrairieView", "Expecting a PVScan or an XML document; got %s instead." % type(vars_[0]).__name__)

            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
            self.pvScanFileNameLineEdit.setText("<imported>")

    @Slot()
    @safewrapper
    def _slot_importOptionsFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, dict],
                                        title="Import Options",
                                        single=True)

        if len(vars_):
            options = vars_[0]

            if isinstance(options, ScanData):
                options = options.analysisOptions

            self.scanDataOptions = options
            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
            self.optionsFileNameLineEdit.setText("<imported>")

    @Slot()
    @safewrapper
    def _slot_importEphysFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, neo.Block, neo.Segment,
                                          neo.AnalogSignal, tuple, list],
                                        title="Import electrophysiology",
                                        single=False)
        if len(vars_):
            if len(vars_) == 1:
                if isinstance(vars_[0], ScanData):
                    self._ephys_ = vars_[0].electrophysiology

                elif isinstance(vars_[0], neo.Block):
                    self._ephys_ = vars_[0]

                elif isinstance(vars_[0], neo.Segment):
                    self._ephys_ = neo.Block()
                    self._ephys_.segments[:] = vars_[0]

                elif isinstance(vars_[0], (tuple, list)) and len(vars_[0]):
                    if all([isinstance(v, neo.Segment) for v in vars_[0]]):
                        self._ephys_ = neo.Block()
                        self._ephys_.segments[:] = vars_[0][:]

                    elif all([isinstance(v, neo.Block) for v in vars_[0]]):
                        self._ephys_ = concatenate_blocks(*vars_[0])

                    else:
                        self.errorMessage("PrairieView Importer", "Import electrophysiology: \nCannot import from data %s which is %s" % (vars_[0], type(vars_[0].__name__)))
                        return

                else:
                    self.errorMessage("PrairieView Importer", "Import electrophysiology: \nCannot import from data %s which is %s" % (vars_[0], type(vars_[0].__name__)))
                    return

            elif len(vars_) > 1:
                if all([isinstance(v, neo.Segment) for v in vars_]):
                    self._ephys_ = neo.Block()
                    self._ephys_.segments[:] = vars_[:]

                elif all([isinstance(v, neo.Block) for v in vars_]):
                    self._ephys_ = concatenate_blocks(*vars_)

                else:
                    self.errorMessage("PrairieView Importer", "Import electrophysiology: \nExpecting a sequnce of neo.Segment or neo.Block objects")
                    return

            signalblockers =[QtCore.QSignalBlocker(w) for w in (self.ephysFileNameLineEdit,)]
            self.ephysFileNameLineEdit.setText("<imported>")

    @Slot()
    @safewrapper
    def _slot_importProtocolFromWorkspace(self):
        vars_ = self.importWorkspaceData([ScanData, TriggerProtocol, tuple, list],
                                         title="Import Protocol",
                                         single=False)

        if len(vars_):
            if len(vars_) == 1:
                if isinstance(vars_[0], ScanData):
                    self.triggerProtocols[:] = vars_[0].triggerProtocols[:]

                elif isinstance(vars_[0], (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in vars_[0]]):
                    self.triggerProtocols[:] = vars_[0][:]

                elif isinstance(vars_[0], TriggerProtocol):
                    self.triggerProtocols = [vars_[0]]

                else:
                    self.errorMessage("PrairieView Importer", "Expecting a ScanData, a TriggerProtocol or a sequence of TriggerProtocol objects; got %s instead" % vars_[0])
                    return

            else:
                if all([isinstance(v, TriggerProtocol) for v in vars_]):
                    self.triggerProtocols[:] = vars_[:]

                else:
                    self.errorMessage("PrairieView Importer", "Expecting a multiple selection of TriggerProtocol objects; got %s instead" % vars_)
                    return

            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
            self.cachedProtocolFileName = self.triggerProtocolFileNameLineEdit.text()
            self.triggerProtocolFileNameLineEdit.setText("<imported>")

    @Slot()
    def _slot_addProtocol(self):
        newProtocol = TriggerProtocol()
        if self._scandata_ is not None:
            segments_with_protocol = [p.segmentIndices() for p in self._scandata_.triggerProtocols]

            data_segments = [k for k in range(self._scandata_.scansFrames)]

    @safewrapper
    def loadPVScan(self, fileName:typing.Union[pathlib.Path, str]) -> bool:
        if isinstance(fileName, str) and len(fileName.strip()):
            fileName = pathlib.Path(fileName)

        if not isinstance(fileName, pathlib.Path) or not fileName.is_file():
            self.errorMessage("PrairieView Import", f"Expecting a str for an existing file name or a valid Path")
            return False

        if not fileName.is_file():
            self.errorMessage("PrairieView Import", f"File {fileName} not found")
            return False

        mime_type, file_type, encoding = pio.getMimeAndFileType(fileName)

        if "xml" in mime_type:
            pvscanDoc = pio.loadXMLFile(fileName)
            pvscanAttrs = xmlutils.attributesToDict(pvscanDoc.documentElement)
            pvVersion = pvscanAttrs.get("version", None)
            if not isinstance(pvVersion, str) or len(pvVersion.strip()) == 0:
                scipywarn(f"Invalid 'version' attribute ({pvVersion})")
                return False

            if pvVersion < "5.5":
                self._pvscan_ = PVScan(fileName)
            else:
                pvFile = pathlib.Path(fileName).relative_to(pathlib.Path.cwd())
                pvEnvFile = pathlib.Path(pvFile.parent / (pvFile.stem + ".env"))
                if not pvEnvFile.is_file():
                    fn, _ = self.chooseFile("Select PrairieView Environment File",
                                                ".env")
                    if len(fn.strip()) == 0:
                        scipywarn(f"PVScan acquired with PrairieView version {pvVersion} require an 'environment' file (*.env)")
                        return False

                    pvEnvFile = pathlib.Path(fn)

                self._pvscan_ = PVScan(fileName, pvEnvFile)

        else:
            self.errorMessage("PrairieView Import - Prairiew View Scan file", "%s is not an XML file" % self.pvScanFileName)
            return False

        # tempDataVarName = os.path.splitext(os.path.basename(fileName))[0]
        tempDataVarName = fileName.stem
        if len(self.scanDataVarName.strip()) == 0:
            self.scanDataVarName = strutils.str2symbol(tempDataVarName)

        if len(self.dataName.strip()) == 0:
            #self.dataName = self.scanDataVarName
            self.dataNameLineEdit.setText(self.scanDataVarName)

        if fileName != self.pvScanFileName:
            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.pvScanFileNameLineEdit, self.dataNameLineEdit)]
            self.pvScanFileName = fileName
            self.pvScanFileNameLineEdit.setText(self.pvScanFileName.as_posix())

        return True

    @safewrapper
    def loadEphys(self, fileNamesList): # TODO 2024-07-28 09:49:36 streamline
        if len(fileNamesList):
            fileNamesList = [f for f in fileNamesList if len(f.strip())]
            if len(fileNamesList) == 0:
                return

            bad_files = [f for f in fileNamesList if not os.path.isfile(f)]
            if len(bad_files):
                self.errorMessage("PrairieView Importer", "The following files: %s could not be found" % os.pathsep.join(fileNamesList))
                return False

            blocks = list()

            if all([any([s in pio.getMimeAndFileType(f)[0] for s in ("axon", "abf", "atf")]) for f in fileNamesList]):
                # NOTE 2020-10-06 16:24:08
                # this is simple: each axon file generates one block
                blocks[:] = [pio.loadAxonFile(f) for f in fileNamesList]

            elif all(["pickle" in pio.getMimeAndFileType(f)[0] for f in fileNamesList]):
                # CAUTION 2020-10-06 16:22:25
                # when loading pickle files, they can contain either:
                # a) one block with one segment for each sweep => concatenate them
                # b) a single block with as many segments as sweeps => use ths first
                # block and discard the others
                blocks[:] = [pio.loadPickleFile(f) for f in fileNamesList]

            else:
                self.errorMessage("PrairieView Importer", "Electrophysiology files\nExpecting Axon or Pickle files for electrophysiology")
                return False

            if len(blocks):
                if all([isinstance(b, neo.Block) for b in blocks]):
                    self._ephys_ = set_relative_time_start(concatenate_blocks(*blocks))
                    self.cachedEvents = [s.events for s in self._ephys_.segments]
                    return True

                elif all([isinstance(b, neo.Segment) for b in blocks]):
                    self._ephys_ = neo.Block()
                    self._ephys_.segments[:] = blocks[:]
                    self.cachedEvents = [s.events for s in self._ephys_.segments]

                    return True

                else:
                    self.errorMessage("PrairieView Importer", "Electrophysiology files must contain neo.Blocks or individual neo.Segments")
                    return False

                # WARNING 2024-07-27 09:42:55
                # concatenate_blocks does not reset the signals start time to 0
                # anymore - this is because the correct times are needed for
                # establishing the correct temporal succession of the records in
                # post hoc analyses
                #
                # This MUST be taken into account in scandata analysis, downstream.

        else:
            return False

    @safewrapper
    def loadOptions(self, fileName): # TODO 2024-07-28 09:49:36 streamline
        # if len(fileName) and os.path.isfile(fileName) and "pickle" in pio.getMimeAndFileType(fileName)[0]:
        if len(fileName) == 0 or not os.path.isfile(fileName) or pio.getMimeAndFileType(fileName)[0] != "application/x-hdf":
            self.errorMessage("PrairieView Importer", f"Load options from file:\n{fileName} is not a suitable file" )
            return False

        self.scanDataOptions = pio.loadHDF5File(fileName)

        if fileName != self.optionsFileName:
            signalblockers = [QtCore.QSignalBlocker(w) for w in (self.optionsFileNameLineEdit,)]
            self.optionsFileName = fileName
            self.optionsFileNameLineEdit.setText(self.optionsFileName)

        return True

    @safewrapper
    def loadProtocols(self, fileName):
        mime_type = pio.getMimeAndFileType(fileName)[0]

        if len(fileName) and os.path.isfile(fileName) and "pickle" in mime_type:
            tp = pio.loadPickleFile(fileName)

            if isinstance(tp, (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in tp]):
                self.triggerProtocols = tp

                if fileName != self.protocolFileName:
                    signalblockers = [QtCore.QSignalBlocker(w) for w in (self.triggerProtocolFileNameLineEdit,)]
                    self.protocolFileName = fileName
                    self.triggerProtocolFileNameLineEdit.setText(self.protocolFileName)

                return True

            else:
                self.errorMessage("PrairieView Importer", "Load protocols from file:\nNo trigger protocols found in pickle file %s " % fileName)
                return False

        else:
            self.errorMessage("PrairieView Importer", "Load protocols from file:\nExpecting a Pickle file; got %s which is a %s instead" % (fileName, mime_type))
            return False

    @Slot()
    def done(self, value):
        r"""Generates ScanData object (if accepted) and closes the dialog.
        value: a QtWidgets.QDialog.DialogCode (Accepted = 1, Rejected = 2)
        NOTE: Clients need to connect custom slots to this dialog's accepted(),
        rejected(), or finished(int) signals
        """
        # print(f"Slot {self.__class__.__name__}.done")
        if value == QtWidgets.QDialog.Accepted:
            self.slot_generateScanData()

        super().done(value)

    @Slot()
    def accept(self):
        # NOTE: 2021-04-16 11:24:35 this calls done(QDialog.Accepted)
        super().accept()

    @Slot()
    def reject(self):
        # NOTE: 2021-04-16 11:24:48 this calls done(QDialog.Rejected)
        super().reject()

    @Slot()
    @safewrapper
    def slot_generateScanData(self):
        r"""Creates a ScanData object based on the loaded data files.
        The created ScanData object is available as the property `scandata` or
        `scanData`. If self.auto_export is True, the ScanData object is also
        exported to the Scipyen workspace.
        """
        # print(f"{self.__class__.__name__}.slot_generateScanData")
        if isinstance(self._pvscan_, PVScan):
            self._scandata_ = self._pvscan_.scandata()

        if isinstance(self._scandata_, ScanData):
            if len(self.dataName):
                self._scandata_.name = self.dataName

            #print("ephys", type(self._ephys_))
            if isinstance(self._ephys_, neo.Block):
                self._scandata_.electrophysiology = self._ephys_

                self._scandata_.electrophysiology.name = self._scandata_.name
                for k, segment in enumerate(self._scandata_.electrophysiology.segments):
                    if not isinstance(segment.name, str) or len(segment.name.strip()) == 0:
                        segment.name = f"Sweep {k}"

            if isinstance(self.scanDataOptions, (ScanDataOptions, dict)):
                self._scandata_.analysisOptions = self.scanDataOptions

            if isinstance(self.triggerProtocols, (tuple, list)) and all([isinstance(v, TriggerProtocol) for v in self.triggerProtocols]):
                self._scandata_.triggerProtocols = list(self.triggerProtocols)

            if self.auto_export:
                self._scipyenWindow_.assignToWorkspace(self.scanDataVarName, self.scanData)

    def updateProtocolEditor(self):
        self.protocolEditorDialog.triggerProtocols = self.triggerProtocols

    @property
    def ephysdata(self):
        return self._ephys_

    @property
    def pvscan(self):
        return self._pvscan_

    @property
    def scanData(self):
        return self._scandata_

    @property
    def scandata(self):
        r"""Alias to self.scanData
        """
        return self.scanData
