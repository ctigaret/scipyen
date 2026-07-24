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

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 **kwargs):
        # isAttribute = kwargs.pop("isAttribute", False)
        # anchoringWidget = kwargs.pop("anchoringWidget", None)
        # self._overrideAnchor_ = kwargs.pop("overrideAnchor", False)
        # windowFlags = kwargs.pop("windowFlags", None)
        self._objSymbol_ = kwargs.pop("objSymbol", None)

        # self._isSubWidget_: bool = False
        # self._moveEventDispatcher_ = None

        # self._topWidgetCollapsed_:bool = False
        # self._outerFrameGeometry_ = None

        # self._positionHint_: typing.Optional[QtCore.QPoint] = None
        # # self._closeRequestedEvent_: typing.Optional[QtGui.QCloseEvent] = None
        # self._closeRequested_: bool = False
        self._needsNewParentWidget_: bool =  True

        # if isinstance(anchoringWidget, QtWidgets.QWidget):
        #     self._anchoringWidget_ = anchoringWidget
        #     self._isSubWidget_ = True
        #     self._positionHint_ = anchoringWidget.geometry().topRight()
        #
        # else:
        #     self._anchoringWidget_ = None

        # self.dataExchangeWidget = None
        self.nameDescriptionWidget = None
        self.editParentToolButton = None
        self.parentEditor = None
        self.organismEditor = None


        # self._isAttribute_: bool = isAttribute

        AnchoringCollapsibleWidget.__init__(self, parent=parent, **kwargs)
        # WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)

        # self._collapsibleChildren_ = {"parentEditor":self.parentEditor,
        #                               "organismEditor":self.organismEditor}

        # if anchoringWidget:
        #     if isinstance(windowFlags, QtCore.Qt.WindowType):
        #         self.setWindowFlags(windowFlags)
        #     else:
        #         self.setWindowFlags(QtCore.Qt.Tool)

        if self._objSymbol_ is None or (isinstance(self._objSymbol_, str) and len(self._objSymbol_.strip()) == 0):
            objSymbols = self.getDataSymbolInWorkspace(self._data_)
            if isinstance(objSymbols, typing.Sequence) and len(objSymbols) > 0:
                self._objSymbol_ = objSymbols[0]

        # self._sizeAnimationMax_ = 200
        # self._sizeAnimation_ = QtCore.QPropertyAnimation(self, b'widgetWidth', self)
        # self._sizeAnimation_.setStartValue(0)
        # self._sizeAnimation_.setDuration(200) # ms
        # self._sizeAnimation_.setEndValue(self._sizeAnimationMax_)
        # self._sizeAnimation_.valueChanged.connect(self._slot_setWidgetWidth)

        # self._opacityEffect_ = QtWidgets.QGraphicsOpacityEffect(self)
        # if self._isSubWidget_:
        #     self._opacityEffect_.setOpacity(0.0)
        # else:
        #     self._opacityEffect_.setOpacity(1.0)
        #
        # self._opacityAnimation_ = QtCore.QPropertyAnimation(self._opacityEffect_, b'opacity', self)
        # self._opacityAnimation_.setStartValue(0.0)
        # self._opacityAnimation_.setDuration(200)
        # self._opacityAnimation_.setEndValue(1.0)
        # self._opacityAnimation_.valueChanged.connect(self._slot_setOpacity)

        # if self._isSubWidget_:
        #     self.setGraphicsEffect(self._opacityEffect_)

        # self._animationGroup_ = QtCore.QParallelAnimationGroup()
        # self._animationGroup_.addAnimation(self._sizeAnimation_)
        # # self._animationGroup_.addAnimation(self._opacityAnimation_)
        # self._animationGroup_.stateChanged.connect(self._slot_animationStateChanged)

    def _configureUI_(self):
        self.sig_uiConfigured.connect(self._slot_uiConfigured_)
        r"""MUST be called in the subclass once self._data_ was established,
        AND first thing after setupUi() was called in the subclass"""
        # if isinstance(self.dataExchangeWidget, DataExchangeWidget) and isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
        if isinstance(self.nameDescriptionWidget, NameDescriptionWidget):
            self.nameDescriptionWidget.setData(self._data_)#, self._objSymbol_)
            self.nameDescriptionWidget.dataName = self._data_.name
            self.nameDescriptionWidget.dataDescription = self._data_.description

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

            self.nameDescriptionWidget.editParentToolButton.setEnabled(False)
            self.nameDescriptionWidget.editParentToolButton.setVisible(False)
            self.nameDescriptionWidget.replaceParentToolButton.setEnabled(False)
            self.nameDescriptionWidget.replaceParentToolButton.setVisible(False)
            self.nameDescriptionWidget.organismToolButton.setEnabled(False)
            self.nameDescriptionWidget.organismToolButton.setVisible(False)

            if hasattr(self, "_data_"):
                if hasattr(self._data_, "parent"):
                    self.nameDescriptionWidget.editParentToolButton.setEnabled(True)
                    self.nameDescriptionWidget.editParentToolButton.setVisible(True)


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

        # if (
        #     isinstance(self._anchoringWidget_, QtWidgets.QWidget)
        #     ):
        #     if hasattr(self._anchoringWidget_, "sig_moved"):
        #         self._anchoringWidget_.sig_moved.connect(self._slot_anchoringWidgetMoved)
            # else:
            #     self._moveEventDispatcher_ = MoveEventFilterObject(self,
            #                                                        anchoredWidget=self)
            #     self._anchoringWidget_.installEventFilter(self._moveEventDispatcher_)


    # @QtCore.Property(int)
    # def widgetWidth(self) -> int:
    #     return self.width()
    #
    # @widgetWidth.setter
    # def widgetWidth(self, value: int):
    #     self.setFixedWidth(value)

    @Slot(object)
    def _slot_dataReceived(self, obj: typing.Any):
        if isinstance(obj, self._objectTypes_):
            self.setValue(obj)

    # @Slot(QtCore.QVariant)
    # def _slot_setWidgetWidth(self, val: int | QtCore.QVariant):
    #     if not isinstance(val, int):
    #         val = val.value()
    #     self.setFixedWidth(val)

    # @Slot(QtCore.QVariant)
    # def _slot_setOpacity(self, val: float | QtCore.QVariant):
    #     if not isinstance(val, float):
    #         val = val.value()
    #
    #     if val < 0:
    #         val = 0.
    #     if val > 1:
    #         val = 1.
    #
    #     self._opacityEffect_.setOpacity(val)

    # @Slot(QtCore.QAbstractAnimation.State, QtCore.QAbstractAnimation.State)
    # def _slot_animationStateChanged(self, newState: QtCore.QAbstractAnimation.State,
    #                                 oldState: QtCore.QAbstractAnimation.State):
    #
    #     if (not isinstance(self._animationGroup_, QtCore.QParallelAnimationGroup)
    #         or not qtutils.isQObjectAlive(self._animationGroup_)):
    #         return
    #
    #     if newState == QtCore.QAbstractAnimation.Running:
    #         self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
    #         # self._parentOpacityAnimation_.start()
    #     elif newState == QtCore.QAbstractAnimation.Stopped:
    #         self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
    #         # if isinstance(self._closeRequestedEvent_, QtGui.QCloseEvent):
    #         if self._animationGroup_.direction() == QtCore.QAbstractAnimation.Backward:
    #             self.sig_collapsed.emit()
    #             if self._closeRequested_ is True:
    #                 self.close()
    #             else:
    #                 self.setVisible(False)
    #
    #         else:
    #             # re-allow manual resizing
    #             self.setMinimumSize(QtCore.QSize(0,0))
    #             self.setMaximumSize(QtCore.QSize(QtWidgets.QWIDGETSIZE_MAX, QtWidgets.QWIDGETSIZE_MAX))

    def value(self) -> None:
        r"""Must override in subclasses"""
        pass

    # def show(self):
    #     if self.isVisible():
    #         return
    #
    #     # print(f"{self.__class__.__name__}.show(): sub widget: {self._isSubWidget_}")
    #     if self._isSubWidget_:
    #         self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Forward)
    #         geometry = self.geometry()
    #         # height = geometry.height()
    #         heightHint = self.sizeHint().height()
    #         # print(f"height hint: {heightHint} -> height: {height}")
    #         self._sizeAnimation_.setEndValue(self.sizeHint().width())
    #         topRight = self._anchoringWidget_.geometry().topRight()
    #         if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
    #             self._positionHint_ = self._anchoringWidget_.parent().mapToGlobal(topRight)
    #         else:
    #             self._positionHint_ = topRight
    #         geometry.setX(self._positionHint_.x())
    #         geometry.setY(self._positionHint_.y())
    #         geometry.setHeight(heightHint)
    #         self.setGeometry(geometry)
    #         self._animationGroup_.start()
    #         super().show()
    #
    #     else:
    #         super().show()

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

                    # print(f"{self.__class__.__name__}.setValue(): checking for organism access")
                    if (
                        not isinstance(self._data_, (sdc.Organism, sdc.Organ))
                        and hasattr(self._data_, "getOrganism")
                        and hasattr(self._data_, "setOrganism")
                        ):
                        self.nameDescriptionWidget.organismToolButton.setEnabled(True)
                        self.nameDescriptionWidget.organismToolButton.setVisible(True)

    # @property
    # def isAttribute(self) -> bool:
    #     return self._isAttribute_
    #
    # @isAttribute.setter
    # def isAttribute(self, val: bool):
    #     self._isAttribute_ = val is True

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

    @Slot()
    def _slot_viewDetails(self):
        # from gui.widgets.dataclasswidgets import dataexchangewidget
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            # and hasattr(self, "dataExchangeWidget")
            # and isinstance(self.dataExchangeWidget, dataexchangewidget.DataExchangeWidget)
            ):
            varName = self.nameDescriptionWidget.dataExchangeWidget.varName
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

    @Slot()
    def _slot_editParent(self):
        anchoringWidget = self.provideAnchoringWidget()
        parent = None
        if (hasattr(self, "_data_")
            and hasattr(self, "_objectTypes_")
            and isinstance(self._data_, self._objectTypes_)
            and hasattr(self._data_, "parentTypes")
            and hasattr(self._data_, "parent")
            and isinstance(self._data_.parent, self._data_.parentTypes)): # dataclasses.is_dataclass(self._data_.parent)):
            parent = self._data_.parent

        if isinstance(self.parentEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.parentEditor):
            editorWidgetType = self._setParentEditorType_(parent)
            if self._needsNewParentWidget_ or type(self.parentEditor) is not editorWidgetType:
                self.parentEditor.close()
                self.parentEditor.deleteLater()
                # self.parentEditor = editor
                self.parentEditor.setObjectName("parentEditor")

                self.parentEditor = self._setupCollapsibleChild_(
                    editorWidgetType,
                    "parentEditor",
                    self._slot_parentChanged,
                    self.nameDescriptionWidget.editParentToolButton,
                    anchoringWidget,
                    parent,
                    objSymbol="parent"
                    )

                # editor = editorWidgetType(parent, objSymbol="parent", anchoringWidget=anchoringWidget)
                # editor.sig_valueChanged.connect(self._slot_parentChanged)
                # editor.sig_closing.connect(self._slot_parentEditorClosing)
                # editor.sig_collapsed.connect(self._slot_parentEditorCollapsed)
                # if type(editor) is not type(self.parentEditor):
                #     self.parentEditor.close()
                #     self.parentEditor.deleteLater()
                #     self.parentEditor = editor
                #     self.parentEditor.setObjectName("parentEditor")

        else:
            editorWidgetType = self._setParentEditorType_(parent)
            self.parentEditor = self._setupCollapsibleChild_(
                editorWidgetType,
                "parentEditor",
                self._slot_parentChanged,
                self.nameDescriptionWidget.editParentToolButton,
                anchoringWidget,
                parent,
                objSymbol="parent"
                )
            # self.parentEditor = editorWidgetType(parent, objSymbol="parent", anchoringWidget=anchoringWidget)
            # self.parentEditor.sig_valueChanged.connect(self._slot_parentChanged)
            # self.parentEditor.sig_closing.connect(self._slot_parentEditorClosing)
            # self.parentEditor.sig_collapsed.connect(self._slot_parentEditorCollapsed)
            # self.parentEditor.setObjectName("parentEditor")

        self._needsNewParentWidget_ = False
        # self._collapsibleChildren_["parentEditor"] = self.parentEditor
        self.parentEditor.show()
        self.parentEditor.setWindowTitle(f"Parent: {type(parent).__name__}")


        # TODO: 2026-06-25 16:47:07 finalize me
        # what are the possible parents of the CellCompartment/NeuronCompartment
        # propose creating a new one (add create new button to these widgets)

    # @Slot()
    # def _slot_parentEditorClosing(self):
    #     sb = QtCore.QSignalBlocker(self.nameDescriptionWidget.editParentToolButton) # noqa
    #     self.nameDescriptionWidget.editParentToolButton.setChecked(False)
    #
    # @Slot()
    # def _slot_organismEditorClosing(self):
    #     sb = QtCore.QSignalBlocker(self.nameDescriptionWidget.organismToolButton) # noqa
    #     self.nameDescriptionWidget.organismToolButton.setChecked(False)

    # @Slot(int, int)
    # def _slot_splitterMoved(self, pos: int, index: int):
    #     # print(f"\n{self.__class__.__name__}._slot_splitterMoved(pos={pos}, index={index})")
    #     topWidgetHeightHint = self.splitter.widget(0).sizeHint().height()
    #     topWidgetHeight = self.splitter.sizes()[0]
    #     bottomWidgetHeightHint = self.splitter.widget(1).sizeHint().height()
    #     bottomWidgetHeight = self.splitter.sizes()[1]
    #     # print(f"\n\t top: -> hint {topWidgetHeightHint} -> size {topWidgetHeightHint}")
    #     # print(f"\n\t bottom: -> hint {bottomWidgetHeightHint} -> size {bottomWidgetHeight}" )
    #     if pos == 0:
    #         self.sig_topWidgetCollapsed.emit()
    #
    #     elif pos == topWidgetHeightHint:
    #         self.sig_topWidgetRestored.emit()

    # @Slot()
    # def _slot_topWidgetCollapsed(self):
    #     if self._topWidgetCollapsed_:
    #         return
    #     # return # for now !!!
    #     print("\n*** collapsed ***\n")
    #     topWidgetHeightHint = self.splitter.widget(0).sizeHint().height()
    #     # topWidgetHeight = self.splitter.sizes()[0]
    #     # bottomWidgetHeightHint = self.splitter.widget(1).sizeHint().height()
    #     # bottomWidgetHeight = self.splitter.sizes()[1]
    #     parent = self.parent()
    #     if parent is None:
    #         topW = self
    #     while isinstance(parent, QtWidgets.QWidget):
    #         topW = parent
    #         parent=parent()
    #     sb = list(map(lambda w: QtCore.QSignalBlocker(w), (self, self.splitter, topW))) # noqa
    #     # sizes = self.splitter.sizes()
    #     # sizes[0] = 0
    #     # sizes[-1] = bottomWidgetHeight
    #     # self.splitter.setSizes(sizes)
    #     geometry = topW.frameGeometry()
    #     newHeight = geometry.height() - topWidgetHeightHint
    #     geometry.setHeight(newHeight)
    #     topW.setGeometry(geometry)
    #     self._topWidgetCollapsed_ = True
    #     print(f"collapsed: {self._topWidgetCollapsed_}")
    #
    # @Slot()
    # def _slot_topWidgetRestored(self):
    #     if self.splitter.sizes()[0]> 0:
    #         return
    #     print("\n*** restored ***\n")
    #     topWidgetHeightHint = self.splitter.widget(0).sizeHint().height()
    #     # topWidgetHeight = self.splitter.sizes()[0]
    #     # bottomWidgetHeightHint = self.splitter.widget(1).sizeHint().height()
    #     bottomWidgetHeight = self.splitter.sizes()[1]
    #     # print(f"\n{self.__class__.__name__}._slot_topWidgetRestored")
    #     # print(f"\ntop -> hint {topWidgetHeightHint} for {topWidgetHeight}")
    #     # print(f"\nbottom -> hint {bottomWidgetHeightHint} for {bottomWidgetHeight}")
    #     parent = self.parent()
    #     if parent is None:
    #         topW = self
    #     while isinstance(parent, QtWidgets.QWidget):
    #         topW = parent
    #         parent=parent()
    #     sb = list(map(lambda w: QtCore.QSignalBlocker(w), (self, self.splitter, topW))) # noqa
    #     sizes = self.splitter.sizes()
    #     sizes[0] = topWidgetHeightHint
    #     sizes[-1] = bottomWidgetHeight
    #     self.splitter.setSizes(sizes)
    #     geometry = topW.frameGeometry()
    #     newHeight = geometry.height() + topWidgetHeightHint
    #     geometry.setHeight(newHeight)
    #     topW.setGeometry(geometry)
    #     self._topWidgetCollapsed_ = False

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
            self._needsNewParentWidget_ = type(newParent) is not type(self._data_.parent)
            self._data_.parent = newParent
            self._slot_parentChanged(self._data_.parent)
            self.nameDescriptionWidget.editParentToolButton.setChecked(True)

    @Slot(bool)
    def _slot_toggleOrganismEditor(self, val: bool):
        if val is True:
            self._slot_editOrganism()
        else:
            if isinstance(self.organismEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.organismEditor):
                self.organismEditor.collapse(False)

    @Slot()
    def _slot_editOrganism(self):
        from gui.widgets.dataclasswidgets.organismwidget import OrganismWidget
        anchoringWidget = self.provideAnchoringWidget()
        try:
            organism = self._data_.getOrganism()
        except: # noqa
            organism = sdc.Organism()
        if isinstance(self.organismEditor, QtWidgets.QWidget) and qtutils.isQObjectAlive(self.organismEditor):
            if not isinstance(self.organismEditor, OrganismWidget):
                self.organismEditor.close()
                self.organismEditor.deleteLater()
                self.organismEditor = None

                self.organismEditor = self._setupCollapsibleChild_(
                    OrganismWidget,
                    "organismEditor",
                    self._slot_organismChanged,
                    self.nameDescriptionWidget.organismToolButton,
                    anchoringWidget,
                    organism,
                    objSymbol="organism"
                    )

                # self.organismEditor = OrganismWidget(anchoringWidget=anchoringWidget)
                # # self.organismEditor.setWindowTitle("Organism")
                # self.organismEditor.sig_valueChanged.connect(self._slot_organismChanged)
                # self.organismEditor.sig_closing.connect(self._slot_organismEditorClosing)
                # self.organismEditor.sig_collapsed.connect(self._slot_organismEditorCollapsed)


        # self._collapsibleChildren_["organismEditor"] = self.organismEditor
        else:
            self.organismEditor = self._setupCollapsibleChild_(
                OrganismWidget,
                "organismEditor",
                self._slot_organismChanged,
                self.nameDescriptionWidget.organismToolButton,
                anchoringWidget,
                organism,
                objSymbol="organism"
                )

        # self.organismEditor.setValue(organism, objSymbol="organism")

        if not self.organismEditor.isVisible():
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

    # @Slot()
    # def _slot_organismEditorCollapsed(self):
    #     sb = QtCore.QSignalBlocker(self.nameDescriptionWidget) # noqa
    #     self.nameDescriptionWidget.organismToolButton.setChecked(False)
    #
    # @Slot()
    # def _slot_parentEditorCollapsed(self):
    #     sb = QtCore.QSignalBlocker(self.nameDescriptionWidget) # noqa
    #     self.nameDescriptionWidget.editParentToolButton.setChecked(False)

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
        raise NotImplementedError(f"{type(obj)} objects are not supported")

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

    # def collapse(self, close: bool=False):
    #     if self._isSubWidget_:
    #         self.collapseSubWidgets(close)
    #         self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Backward)
    #         self._closeRequested_ = close
    #         self._animationGroup_.start()
    #
    # def collapseSubWidgets(self, close: bool= False):
    #     for obj, toggle in self._collapsibleChildren_.values():
    #         if isinstance(obj, QtWidgets.QWidget) and qtutils.isQObjectAlive(obj):
    #             try:
    #                 obj.collapse(close)
    #             except: # noqa
    #                 pass

    # def closeEvent(self, evt):
    #     # print(f"{self.__class__.__name__}.closeEvent")
    #     self.sig_closing.emit()
    #     self.closeSubWidgets()
    #     super().closeEvent(evt)
    #     evt.accept()

    def closeSubWidgets(self):
        super().closeSubWidgets()
        # if isinstance(self.parentEditor, QtWidgets.QWidget):
        #     # sb = QtCore.QSignalBlocker(self.parentEditor) # noqa
        #     self.parentEditor.close()
        #     self.parentEditor.deleteLater()
        #     self.parentEditor = None
        #
        # if isinstance(self.organismEditor, QtWidgets.QWidget):
        #     # sb = QtCore.QSignalBlocker(self.organismEditor) # noqa
        #     self.organismEditor.close()
        #     self.organismEditor.deleteLater()
        #     self.organismEditor = None

        self.nameDescriptionWidget.closeSubWidgets()

    # def moveEvent(self, evt):
    #     self.sig_moved.emit(evt.pos())# - evt.oldPos())
    #     evt.accept()

    # @property
    # def overrideAnchor(self) -> bool:
    #     return self._overrideAnchor_
    #
    # @overrideAnchor.setter
    # def overrideAnchor(self, val: bool):
    #     self._overrideAnchor_ = val is True

    # @property
    # def anchoringWidget(self) -> QtWidgets.QWidget | None:
    #     return self._anchoringWidget_

    # @anchoringWidget.setter
    # def anchoringWidget(self, obj: QtWidgets.QWidget):
    #     if isinstance(obj, QtWidgets.QWidget):
    #         self._anchoringWidget_ = obj
    #         if hasattr(self._anchoringWidget_, "sig_moved"):
    #             self._anchoringWidget_.sig_moved.connect(self._slot_anchoringWidgetMoved)
    #         # else:
    #         #     self._moveEventDispatcher_ = MoveEventFilterObject(self,
    #         #                                                        anchoredWidget=self)
    #         #     self._anchoringWidget_.installEventFilter(self._moveEventDispatcher_)
    #
    #         self._isSubWidget_ = True
    #     else:
    #         self._anchoringWidget_ = None
    #         self._isSubWidget_ = False

    # @Slot(QtCore.QPoint)
    # def _slot_anchoringWidgetMoved(self, pos: QtCore.QPoint):
    #     # print(f"{self.__class__.__name__}<{self.objectName()}>._slot_anchoringWidgetMoved({pos})\n")
    #     # if not self.isVisible():
    #     #     return
    #
    #     if not isinstance(self._anchoringWidget_, QtWidgets.QWidget):
    #         return
    #
    #     if isinstance(self.parent(), QtWidgets.QWidget):
    #         return
    #
    #     if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
    #         newPos = self._anchoringWidget_.parent().mapToGlobal(self._anchoringWidget_.geometry().topRight())
    #
    #     else:
    #         newPos = self._anchoringWidget_.frameGeometry().topRight()
    #
    #     self.move(newPos)


