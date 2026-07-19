# -*- coding: utf-8 -*-
# $Id: dataexchangewidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import sys, os, typing, types, warnings, math, cmath # noqa
import numbers # noqa
# import dataclasses
import numpy as np # noqa
import quantities as pq # noqa
# import neo
from tribool import Tribool # noqa

import qtpy # noqa
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

    from qtpy import sip# noqa
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

try:
    from qtpy import QtDBus# noqa
    __has_qtdbus__ = True
except: # noqa
    __has_qtdbus__ = False

from core import datatypes # noqa
from core import qtutils
from core.prog import scipywarn # noqa
# from core import utilities
from gui import (guiutils, interact) # noqa
from gui.workspacegui import WorkspaceGuiMixin

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

Ui_DataExchangeWidget, QWidget = loadUiType(
    os.path.join(__module_path__, "dataexchangewidget.ui")
    )

class DataExchangeWidget(Ui_DataExchangeWidget, QWidget, WorkspaceGuiMixin):
    r"""Common widget to use as 1st level child in various Scipyen compound widgets.
Contains a set of tool buttons for loading/saving data to/from piclkle files and
for importing/exporting data to the user workspace.

For information purposes, the widget also contains a label with the workspace
symbol bound to the data (if any).

The widget is meant to be used as a child widget of more complex widgets in Scipyen,
to offset data input/output operations here (loading from/saving to pickle files,
importing from/exporting to the user's workspace).

These operations communicate with the parent widget via Qt signal/slots.

The only prerequisites for the parent widget are:

1. On the "output side": the parent widget shoulwd sends the data object via one
of two signals: sig_dataSaving and sig_dataExporting to trigger respectively,
saving and exporting logic. These two signals (in the parent widget) MUST be
connected to the public Qt slots of this widget: ``slot_saveData`` and ``slot_exportData``.

2. On the "input side": the parent widget should have at least one Qt slot connected to this
widget's Qt signals ``sig_dataLoaded`` and ``sig_dataImported`` to receive the incoming
data object after loading from file or importing from the workspace.

"""
    # sig_dataLoaded = Signal(object, name="sig_dataLoaded")
    sig_requestLoadData = Signal(name="sig_requestLoadData")
    sig_requestImportData = Signal(name="sig_requestImportData")
    # sig_dataImported = Signal(object, name="sig_dataImported")
    sig_requestDataExport = Signal(name="sig_requestDataExport")
    sig_requestDataSave = Signal(name="sig_requestDataSave")
    sig_requestDataCopy = Signal(name="sig_requestDataCopy")
    sig_requestNewObject = Signal(name="sig_requestNewObject")
    sig_symbolChanged = Signal(str, name="sig_symbolChanged")
    sig_closing = Signal(name="sig_closing")
    sig_moved = Signal(QtCore.QPoint, name="sig_moved")
    sig_collapsed = Signal(name="sig_collapsed")

    def __init__(self, objType: typing.Optional[type]=None,
                 parent: typing.Optional[QtWidgets.QWidget] = None,
                 **kwargs):
        anchoringWidget = kwargs.pop("anchoringWidget", None)
        self._overrideAnchor_ = kwargs.pop("overrideAnchor", False)
        windowFlags = kwargs.pop("windowFlags", None)

        if isinstance(objType, QtWidgets.QWidget):
            obj_ = parent
            if isinstance(parent, type):
                parent = objType
            else:
                parent = None
            objType = obj_

        if objType is None:
            objType = type(None)

        self._objectType_ = objType
        self._objSymbol_ = None

        QtCore.QObject.__init__(self, parent=parent)

        self._isSubWidget_: bool = False
        self._closeRequested_: bool = False

        self._positionHint_: typing.Optional[QtCore.QPoint] = None

        if isinstance(anchoringWidget, QtWidgets.QWidget):
            self._anchoringWidget_ = anchoringWidget
            self._isSubWidget_ = True
            self._positionHint_ = anchoringWidget.geometry().topRight()

        else:
            self._anchoringWidget_ = None

        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)

        if anchoringWidget:
            if isinstance(windowFlags, QtCore.Qt.WindowType):
                self.setWindowFlags(windowFlags)
            else:
                self.setWindowFlags(QtCore.Qt.Tool)

        self._sizeAnimationMax_ = 200
        self._sizeAnimation_ = QtCore.QPropertyAnimation(self, b'widgetWidth', self)
        self._sizeAnimation_.setStartValue(0)
        self._sizeAnimation_.setDuration(200) # ms
        self._sizeAnimation_.setEndValue(self._sizeAnimationMax_)
        self._sizeAnimation_.valueChanged.connect(self._slot_setWidgetWidth)

        self._animationGroup_ = QtCore.QParallelAnimationGroup()
        self._animationGroup_.addAnimation(self._sizeAnimation_)
        # self._animationGroup_.addAnimation(self._opacityAnimation_)
        self._animationGroup_.stateChanged.connect(self._slot_animationStateChanged)

        self._configureUI_()

    def _configureUI_(self):
        self.setupUi(self)

        self.loadToolButton.clicked.connect(self.sig_requestLoadData)
        self.importToolButton.clicked.connect(self.sig_requestImportData)
        self.saveToolButton.clicked.connect(self.sig_requestDataSave)
        self.copyToolButton.clicked.connect(self.sig_requestDataCopy)
        self.exportToolButton.clicked.connect(self.sig_requestDataExport)
        self.newObjectToolButton.clicked.connect(self.sig_requestNewObject)

        if (
            isinstance(self._anchoringWidget_, QtWidgets.QWidget)
            and hasattr(self._anchoringWidget_, "_slot_anchoringWidgetMoved")
            ):
            self._anchoringWidget_.sig_moved.connect(self._slot_anchoringWidgetMoved)

    @property
    def overrideAnchor(self) -> bool:
        return self._overrideAnchor_

    @overrideAnchor.setter
    def overrideAnchor(self, val: bool):
        self._overrideAnchor_ = val is True

    @property
    def anchoringWidget(self) -> QtWidgets.QWidget | None:
        return self._anchoringWidget_

    @anchoringWidget.setter
    def anchoringWidget(self, obj: QtWidgets.QWidget):
        if isinstance(obj, QtWidgets.QWidget):
            self._anchoringWidget_ = obj
            self._isSubWidget_ = True
        else:
            self._anchoringWidget_ = None
            self._isSubWidget_ = False

    @Slot(QtCore.QPoint)
    def _slot_anchoringWidgetMoved(self, pos: QtCore.QPoint):
        # print(f"{self.__class__.__name__}<{self.objectName()}>._slot_anchoringWidgetMoved({pos})\n")
        # if not self.isVisible():
        #     return

        if not isinstance(self._anchoringWidget_, QtWidgets.QWidget):
            return

        if isinstance(self.parent(), QtWidgets.QWidget):
            return

        if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
            newPos = self._anchoringWidget_.parent().mapToGlobal(self._anchoringWidget_.geometry().topRight())

        else:
            newPos = self._anchoringWidget_.frameGeometry().topRight()

        self.move(newPos)

    def setObjectSymbol(self, val: str):
        self.objectSymbolLabel.setText(val)

    def closeEvent(self, evt):
        # print(f"{self.__class__.__name__}.closeEvent")
        self.sig_closing.emit()
        # self.closeSubWidgets()
        super().closeEvent(evt)
        evt.accept()

    def collapse(self, close: bool=False):
        if self._isSubWidget_:
            # self.collapseSubWidgets(close)
            self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Backward)
            self._closeRequested_ = close
            self._animationGroup_.start()

    def show(self):
        if self.isVisible():
            return

        if self._isSubWidget_:
            self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Forward)
            geometry = self.geometry()
            self._sizeAnimation_.setEndValue(self.sizeHint().width())
            topRight = self._anchoringWidget_.geometry().topRight()
            if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
                self._positionHint_ = self._anchoringWidget_.parent().mapToGlobal(topRight)
            else:
                self._positionHint_ = topRight

            geometry.setX(self._positionHint_.x())
            geometry.setY(self._positionHint_.y())
            self.setGeometry(geometry)
            self._animationGroup_.start()
            super().show()

        else:
            super().show()

    @property
    def varName(self) -> str:
        ret = self.objectSymbolLabel.text()
        if not isinstance(ret, str):
            return ""
        else:
            return ret

    @property
    def dataType(self) -> type:
        return self._objectType_

    @dataType.setter
    def dataType(self, val:type):
        if val is None:
            self._objectType_ = type(None)
        elif not isinstance(val, type):
            raise TypeError(f"Expecting a type or None; instead got {type(val).__name__}")

        self._objectType_ = val

    @QtCore.Property(int)
    def widgetWidth(self) -> int:
        return self.width()

    @widgetWidth.setter
    def widgetWidth(self, value: int):
        self.setFixedWidth(value)

    @Slot(QtCore.QVariant)
    def _slot_setWidgetWidth(self, val: int | QtCore.QVariant):
        if not isinstance(val, int):
            val = val.value()
        self.setFixedWidth(val)

    @Slot(QtCore.QAbstractAnimation.State, QtCore.QAbstractAnimation.State)
    def _slot_animationStateChanged(self, newState: QtCore.QAbstractAnimation.State,
                                    oldState: QtCore.QAbstractAnimation.State):

        if (not isinstance(self._animationGroup_, QtCore.QParallelAnimationGroup)
            or not qtutils.isQObjectAlive(self._animationGroup_)):
            return

        if newState == QtCore.QAbstractAnimation.Running:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            # self._parentOpacityAnimation_.start()
        elif newState == QtCore.QAbstractAnimation.Stopped:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
            # if isinstance(self._closeRequestedEvent_, QtGui.QCloseEvent):
            if self._animationGroup_.direction() == QtCore.QAbstractAnimation.Backward:
                self.sig_collapsed.emit()
                if self._closeRequested_ is True:
                    self.close()
                else:
                    self.setVisible(False)

            else:
                # re-allow manual resizing
                self.setMinimumSize(QtCore.QSize(0,0))
                self.setMaximumSize(QtCore.QSize(QtWidgets.QWIDGETSIZE_MAX, QtWidgets.QWIDGETSIZE_MAX))

    # @Slot()
    # def _slot_loadData(self):
    #     fileNameFilter = "*.pkl"
    #     fn, fl = self.chooseFile(caption = f"Open {self._objectType_.__name__} Pickle File",
    #                             fileFilter = fileNameFilter,
    #                             single=True)
    #
    #     if len(fn.strip()):
    #         obj = pio.loadFile(fn)
    #         if isinstance(obj, self._objectType_):
    #             if self.receivers(self.sig_dataLoaded) > 0:
    #                 self.sig_dataLoaded.emit(obj)
    #                 # varName = os.path.basename(fn)
    #                 # self.objectSymbolLabel.setText(varName)
    #                 # self.objectSymbolLabel.setToolTip(f"'{varName}' is a {type(obj).__name__} object")
    #             else:
    #                 self.setValue(obj)
    #
    #         else:
    #             self.errorMessage(title = f"Open {self._objectType_.__name__} Pickle File",
    #                             text = f"Expecting a {self._objectType_.__name__}; intead got a {type(obj).__name__}")

    # @Slot(object)
    # def slot_saveData(self, obj):
    #     if not isinstance(obj, self._objectType_):
    #         return
    #
    #     fileNameFilter = "*.pkl"
    #
    #     fn, fl = self.chooseFile(caption = f"Save {self._objectType_.__name__} as Pickle File",
    #                             fileFilter = fileNameFilter,
    #                             single=True, save=True)
    #
    #     if len(fn.strip()):
    #         pio.savePickle(obj, fn)


    # @Slot()
    # def _slot_importData(self):
    #     ret = self.importFromWorkSpace(dataTypes = self._objectType_,
    #                                 title=f"Select {self._objectType_.__name__} Object in Workspace",
    #                                 single=True,
    #                                 with_varName=True,
    #                                 retrieve_all = True)
    #     if isinstance(ret, dict) and len(ret) == 1:
    #         varName = list(ret.keys())[0]
    #         obj = ret[varName]
    #         if isinstance(obj, self._objectType_):
    #             self._objSymbol_ = varName
    #             if self.receivers(self.sig_dataImported) > 0:
    #                 self.sig_symbolChanged.emit(self._objSymbol_)
    #                 self.sig_dataImported.emit(obj)
    #                 # self.objectSymbolLabel.setText(varName)
    #                 # self.objectSymbolLabel.setToolTip(f"'{varName}' is bound to a {type(obj).__name__} object in the workspace")

    # @Slot(object)
    # def slot_exportData(self, obj):
    #     if isinstance(obj, self._objectType_):
    #         if not isinstance(self._objSymbol_, str) or len(self._objSymbol_.strip()) == 0:
    #             name = obj.name
    #         else:
    #             name = self._objSymbol_
    #         if not isinstance(name, str) or len(name.strip()) == 0:
    #             name = self._objectType_.__name__.lower()
    #
    #         newSymbol = self.exportDataToWorkspace(obj, name)
    #
    #         if isinstance(newSymbol, str) and len(newSymbol.strip()):
    #             self._objSymbol_ = newSymbol
    #
    #         if isinstance(self._objSymbol_, str):
    #             self.objectSymbolLabel.setText(self._objSymbol_)
    #             self.objectSymbolLabel.setToolTip(f"'{self._objSymbol_}' is bound to a {type(obj).__name__} object in the workspace")
    #             self.sig_symbolChanged.emit(self._objSymbol_)

    # @Slot(object)
    # def slot_copyData(self, obj):
    #     from copy import deepcopy
    #     if isinstance(obj, self._objectType_):
    #         obj1 = deepcopy(obj)
    #         if not isinstance(self._objSymbol_, str) or len(self._objSymbol_.strip()) == 0:
    #             name = obj1.name
    #         else:
    #             name = self._objSymbol_
    #
    #         if not isinstance(name, str) or len(name.strip()) == 0:
    #             name = self._objectType_.__name__.lower()
    #
    #         self.exportDataToWorkspace(obj1, name)

    def setValue(self, obj: typing.Any, objSymbol:typing.Optional[str]=None):
        self.dataType = type(obj)
        if isinstance(objSymbol, str) and len(objSymbol.strip()):
            self._objSymbol_ = objSymbol
        else:
            candidateSymbols = self.getDataSymbolInWorkspace(obj)
            if isinstance(candidateSymbols, str):
                self._objSymbol_ = candidateSymbols

            elif (isinstance(candidateSymbols, typing.Sequence) and
                len(candidateSymbols) and
                all(isinstance(s, str) for s in candidateSymbols)):
                self._objSymbol_ = candidateSymbols[0]
            else:
                self._objSymbol_ = None

        if isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()):
            self.objectSymbolLabel.setText(self._objSymbol_)
            self.objectSymbolLabel.setToolTip(f"'{self._objSymbol_}' is bound to a {type(obj).__name__} object in the workspace")
            self.sig_symbolChanged.emit(self._objSymbol_)
        else:
            self.objectSymbolLabel.clear()
            self.objectSymbolLabel.setToolTip("")
            self.sig_symbolChanged.emit("")

    def _getAnchoringWidget_(self) -> QtWidgets.QWidget | None:
        if isinstance(self._anchoringWidget_, QtWidgets.QWidget) and self.overrideAnchor:
            return self._anchoringWidget_

        if self.parent() is None:
            return self

        return None


