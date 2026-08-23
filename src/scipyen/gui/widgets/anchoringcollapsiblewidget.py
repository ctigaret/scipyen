# -*- coding: utf-8 -*-
# $Id: anchoringcollapsibleWidget.py $
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


import typing, warnings, os, inspect, sys, traceback, types # noqa
# import pathlib
from pprint import pprint # noqa
from traitlets import (config, Bunch) # noqa
# import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ =False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    # from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
    QWIDGETSIZE_MAX = 16777215
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
    # from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    QWIDGETSIZE_MAX = QtWidgets.QWIDGETSIZE_MAX

from core import qtutils
from core import desktoputils
from gui.workspacegui import WorkspaceGuiMixin

class AnchoringCollapsibleWidget(QtWidgets.QWidget, WorkspaceGuiMixin):
    # sig_moved = Signal(QtCore.QPoint, name="sig_moved")
    sig_closing = Signal(name="sig_closing")
    sig_collapsed = Signal(name="sig_collapsed")
    sig_uiConfigured = Signal(name="sig_uiConfigured")

    def __init__(self, parent:typing.Optional[QtWidgets.QWidget] = None,
                 **kwargs):
        anchoringWidget = kwargs.pop("anchoringWidget", None)
        self._overrideAnchor_ = kwargs.pop("overrideAnchor", False)
        self._useOpacityEffect_: bool = kwargs.pop("useOpacityEffect", False)
        self._windowFlags_ = kwargs.pop("windowFlags", None)

        # NOTE: does not work on Wayland!
        self._positionHint_: typing.Optional[QtCore.QPoint] = None

        self._closeRequested_: bool = False
        self._anchoringWidget_ = None
        self._sizeAnimationMax_ = None
        self._sizeAnimation_ = None
        self._opacityEffect_ = None
        self._opacityAnimation_ = None
        self._animationGroup_ = None
        self._positionHint_ = None

        self._collapsibleChildren_ = dict() # Qt objectName ↦ (collapsible widget, toggle control widget, collapsible widget id)

        if isinstance(anchoringWidget, QtWidgets.QWidget):
            self._anchoringWidget_ = anchoringWidget

        QtWidgets.QWidget.__init__(self, parent=parent)

        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)

    def getHighestAncestor(self) -> QtWidgets.QWidget:
        r"""Retrieves the highest level QMainWindow that contains this object.
        This may be:
        * the object itself, if the object is a QMainWindow, or a QWidget without
        parent (in which case the system's window manager automatically encloses
        the widget in a window instance)
        * the object's immediate parent, if the parent is a QMainWindow
        * the window enclosing all the parent hierarchy of this object

        NOTE: 2026-08-23 22:34:06 DEPRECATED
        To be replaced with guituils.getEnclosingQMainWindow
        """
        parent = self.parent()
        if parent is None:
            topW = self

        while isinstance(parent, QtWidgets.QWidget):
            topW = parent
            parent = parent.parent()

        return topW

    def _setupCollapsibleChild_(self, widgetType:type, objectName: str,
                                valueChangedSlot: Slot,
                                toggleControl:QtWidgets.QWidget,
                                anchoringWidget, # = None,
                                *args, **kwargs):
        r"""
        :widgetType: child widget class
        :objectName: Qt name of the new child widget instance
        :valueChangeSlot: Qt slot to be connected to the child widget's "sig_valueChanged" signal
        :toggleControl: a QWidget with setChecked method (e.g., a QToolButton or a QCheckBox, etc)
        :anchoringWidget: widget
        Passed to the child widget c'tor
        :*args:
        :**kwargs:

        """
        # print(f"{self.__class__.__name__}._setupCollapsibleChild_: anchoringWidget = {anchoringWidget}")
        child = widgetType(*args, **kwargs, anchoringWidget=anchoringWidget)
        if len(objectName.strip()) == 0:
            objectName = widgetType.__name__
            objectName = objectName[0].lower() + objectName[1:]
        child.setObjectName(objectName)
        if hasattr(child, "sig_valueChanged") and inspect.ismethod(valueChangedSlot):
            child.sig_valueChanged.connect(valueChangedSlot)
        if hasattr(child, "sig_closing"):
            child.sig_closing.connect(self._slot_anchoredWidgetClosingOrCollapsing, QtCore.Qt.QueuedConnection)
        if hasattr(child, "sig_collapsed"):
            child.sig_collapsed.connect(self._slot_anchoredWidgetClosingOrCollapsing, QtCore.Qt.QueuedConnection)
        if hasattr(child, "_slot_anchoringWidgetMoved"):
            self.sig_moved.connect(child._slot_anchoringWidgetMoved)

        if not isinstance(getattr(anchoringWidget, "_collapsibleChildren_", None), dict):
            anchoringWidget._collapsibleChildren_ = dict()

        # anchoringWidget._collapsibleChildren_[objectName] = (child, toggleControl)
        anchoringWidget._collapsibleChildren_[id(child)] = (child, toggleControl, objectName)

        # print(f"\tchild: {child} anchored to {child.anchoringWidget}")

        return child

    def _removeAnchoringCollapsibleWidget_(self, widget: QtWidgets.QWidget):
        if isinstance(widget, QtWidgets.QWidget):
            wid = id(widget)

            if qtutils.isQObjectAlive(widget):
                widget.close()
                if widget.isAnchoredWidget and wid in widget.anchoringWidget._collapsibleChildren_:
                    toggle = widget.anchoringWidget._collapsibleChildren_[wid][1]
                    if (
                        isinstance(toggle, QtWidgets.QWidget)
                        and hasattr(toggle, "setChecked")
                        and qtutils.isQObjectAlive(toggle)
                        ):
                        sb = QtCore.QSignalBlocker(toggle) # noqa
                        toggle.setChecked(False)
                    del widget.anchoringWidget._collapsibleChildren_[wid]
                widget.deleteLater()
                widget = None

    @Slot()
    def _slot_uiConfigured_(self):
        r"""Required to set up geometries etc AFTER UI components in the subclass
            instance have been initialized by calling self._configureUI_.
        """
        if self.anchoringWidget:
            if desktoputils.is_wayland():
                # self.setWindowFlag(QtCore.Qt.Popup, True)
                # self.setWindowFlag(QtCore.Qt.Dialog, True)
    #             self.setWindowFlags(
    # QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowStaysOnTopHint
    #                 )
                self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
                self.setWindowFlag(QtCore.Qt.ExpandedClientAreaHint, True)
            else:
                if isinstance(self._windowFlags_, QtCore.Qt.WindowType):
                    self.setWindowFlags(self._windowFlags_)
                else:
                    self.setWindowFlags(QtCore.Qt.Tool)

            geometry = self.geometry()
            heightHint = self.sizeHint().height()
            widthHint = self.sizeHint().width()
            # print(f"{self.__class__.__name__}._slot_uiConfigured_:")
            # print(f"\theightHint -> {heightHint}, widthHint -> {widthHint}")
            self._positionHint_ = self.anchoringWidget.geometry().topRight()
            self._sizeAnimationMax_ = widthHint
            # self._sizeAnimation_.setEndValue(widthHint)
            # self._sizeAnimationMax_ = 200
            self._sizeAnimation_ = QtCore.QPropertyAnimation(self, b'widgetWidth', self)
            self._sizeAnimation_.setStartValue(0)
            self._sizeAnimation_.setDuration(200) # ms
            self._sizeAnimation_.setEndValue(self._sizeAnimationMax_)
            self._sizeAnimation_.valueChanged.connect(self._slot_setWidgetWidth)

            if self._useOpacityEffect_:
                self._opacityEffect_ = QtWidgets.QGraphicsOpacityEffect(self)
                if self._anchoringWidget_:
                    self._opacityEffect_.setOpacity(0.0)
                    self.setGraphicsEffect(self._opacityEffect_)
                    self._opacityAnimation_ = QtCore.QPropertyAnimation(self._opacityEffect_, b'opacity', self)
                    self._opacityAnimation_.setStartValue(0.0)
                    self._opacityAnimation_.setDuration(200)
                    self._opacityAnimation_.setEndValue(1.0)
                    self._opacityAnimation_.valueChanged.connect(self._slot_setOpacity)
                # else:
                #     self._opacityEffect_.setOpacity(1.0)

            self._animationGroup_ = QtCore.QParallelAnimationGroup()
            self._animationGroup_.addAnimation(self._sizeAnimation_)

            if self._useOpacityEffect_:
                self._animationGroup_.addAnimation(self._opacityAnimation_)
            self._animationGroup_.stateChanged.connect(self._slot_animationStateChanged)

            # topRight = self._anchoringWidget_.geometry().topRight()
            geometry.setX(self._positionHint_.x())
            geometry.setY(self._positionHint_.y())
            geometry.setHeight(heightHint)
            geometry.setWidth(widthHint)
            self.setGeometry(geometry)

            if hasattr(self._anchoringWidget_, "sig_moved"):
                self._anchoringWidget_.sig_moved.connect(self._slot_anchoringWidgetMoved)

    @Slot()
    def _slot_anchoredWidgetClosingOrCollapsing(self):
        # BUG?: 2026-07-24 16:25:48 FIXME?
        # the problem here is that the widget might have been already removed
        # from _collapsibleChildren_, or not even having been added to this, but
        # rather in an anchoring widget higher up th hierarchy
        #
        # The latter case is NOT A BUG but it MUST be captured in closeSubWidgets
        widget = self.sender()
        # print(f"{self.__class__.__name__}._slot_anchoredWidgetClosingOrCollapsing: widget = {widget}")
        wid = id(widget)
        if (
            isinstance(getattr(widget, "anchoringWidget", None), QtWidgets.QWidget)
            and len(getattr(widget.anchoringWidget, "_collapsibleChildren_", dict()))
            ):
            aw = widget.anchoringWidget
            ccd = aw._collapsibleChildren_
            if wid in ccd:
                # toggle = self._collapsibleChildren_[widget.objectName()][1]
                toggle = ccd[wid][1]
                # print(f"{self.__class__.__name__}._slot_anchoredWidgetClosingOrCollapsing: toggle -> {toggle}")

                if (
                    isinstance(toggle, QtWidgets.QWidget)
                    and hasattr(toggle, "setChecked")
                    and qtutils.isQObjectAlive(toggle)
                    ):
                    sb = QtCore.QSignalBlocker(toggle) # noqa
                    toggle.setChecked(False)

    def provideAnchoringWidget(self, widget: typing.Optional[QtWidgets.QWidget] = None) -> QtWidgets.QWidget | None:
        r"""Provides an anchoring widget to a collapsible child widget, if required.
        The anchoring of collapsible children is the window frame enclosing
        this widget (and its parents, if any).

        Collapsible children are used mainly in the DataClassWidget hierarchy.

        Parameters:
        ===========
        widget: the anchored widget

        """
        topWindow = self.getHighestAncestor()
        aw = None
        if (
            getattr(self, "overrideAnchor", False)
            and isinstance(getattr(self, "anchoringWidget", None), QtWidgets.QWidget)
            ):
            # if overrideAnchor is True while THIS widget has its own anhoring widget,
            # then the child index will be anchored to the same anchoring as this one - not sure this is good
            aw = self.anchoringWidget

        if not isinstance(aw, QtWidgets.QWidget):
            if self.parent() is None:
                # null parent means that this widget is wrapped in a window by
                # the underlying OS/Desktop system; this means the widget CAN
                # (and SHOULD) be used as anchoring widget
                aw = self
            else:
                # the immediate parent might itself be a child widget, hence
                # without an anchoring
                # therefore the anchoring offered here is corresponding to the
                # highest parent in the hierarchy, so that there is a window
                # frame to serve as anchor
                aw = topWindow

        return aw

    @property
    def isAnchoredWidget(self):
        return isinstance(self.anchoringWidget, QtWidgets.QWidget)

    def collapse(self, close: bool=False):
        if hasattr(self, "collapseSubWidgets"):
            self.collapseSubWidgets(close)
        self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Backward)
        self._closeRequested_ = close
        self._animationGroup_.start()

        if close:
            self.close()

    def collapseSubWidgets(self, close: bool= False):
        if len(self._collapsibleChildren_) == 0:
            return
        # print(f"{self._collapsibleChildren_}")
        for obj, toggle, objName in self._collapsibleChildren_.values():
            if isinstance(obj, QtWidgets.QWidget) and qtutils.isQObjectAlive(obj):
                try:
                    obj.collapse(close)
                except: # noqa
                    pass

    def closeEvent(self, evt):
        self.sig_closing.emit()
        self.closeSubWidgets()
        if hasattr(super(), "closeEvent"):
            super().closeEvent(evt)
        evt.accept()

    def closeSubWidgets(self):
        if len(self._collapsibleChildren_) == 0:
            return

        # NOTE: 2026-07-24 16:35:05
        # cache widget IDs to avoid _collapsibleChildren_ changing size during iteration
        wids = list()
        for obj, toggle, objName in self._collapsibleChildren_.values():
            if isinstance(obj, QtWidgets.QWidget):
                if obj.isAnchoredWidget:
                    objId = id(obj)
                    # wids.append(id(obj))

                # NOTE: 2026-07-24 16:28:06
                # see # BUG?: 2026-07-24 16:25:48 FIXME?
                if (
                    isinstance(toggle, QtWidgets.QWidget)
                    and hasattr(toggle, "setChecked")
                    and qtutils.isQObjectAlive(toggle)
                    ):
                    sb = QtCore.QSignalBlocker(toggle) # noqa
                    toggle.setChecked(False)

                if qtutils.isQObjectAlive(obj):
                    obj.close()
                    obj.deleteLater()
                wids.append(objId)
                obj = None

        for wid in wids:
            if wid in self._collapsibleChildren_:
                del self._collapsibleChildren_[wid]

            if self.anchoringWidget:
                if wid in self.anchoringWidget._collapsibleChildren_:
                    del self.anchoringWidget._collapsibleChildren_[wid]


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
            if hasattr(self._anchoringWidget_, "sig_moved"):
                self._anchoringWidget_.sig_moved.connect(self._slot_anchoringWidgetMoved)
        else:
            self._anchoringWidget_ = None

    @Slot(QtCore.QPoint)
    def _slot_anchoringWidgetMoved(self, pos: QtCore.QPoint):
        if not isinstance(self._anchoringWidget_, QtWidgets.QWidget):
            return

        if isinstance(self.parent(), QtWidgets.QWidget):
            return

        if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
            newPos = self._anchoringWidget_.parent().mapToGlobal(self._anchoringWidget_.geometry().topRight())

        else:
            newPos = self._anchoringWidget_.frameGeometry().topRight()

        self.move(newPos)

    @Slot(QtCore.QAbstractAnimation.State, QtCore.QAbstractAnimation.State)
    def _slot_animationStateChanged(self, newState: QtCore.QAbstractAnimation.State,
                                    oldState: QtCore.QAbstractAnimation.State):

        if not self.anchoringWidget:
            return

        if (not isinstance(self._animationGroup_, QtCore.QParallelAnimationGroup)
            or not qtutils.isQObjectAlive(self._animationGroup_)):
            return

        if newState == QtCore.QAbstractAnimation.Running:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            # self._parentOpacityAnimation_.start()
        elif newState == QtCore.QAbstractAnimation.Stopped:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
            if self._animationGroup_.direction() == QtCore.QAbstractAnimation.Backward:
                self.sig_collapsed.emit()
                if self._closeRequested_ is True:
                    self.close()
                else:
                    self.setVisible(False)

            else:
                # re-allow manual resizing
                self.setMinimumSize(QtCore.QSize(0,0))
                self.setMaximumSize(QtCore.QSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX))

    def show(self):
        # if self.isVisible():
        #     return

        if self.isAnchoredWidget:
            self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Forward)
            geometry = self.geometry()
            # height = geometry.height()
            heightHint = self.sizeHint().height()
            # print(f"height hint: {heightHint} -> height: {height}")
            self._sizeAnimation_.setEndValue(self.sizeHint().width())
            topRight = self._anchoringWidget_.geometry().topRight()
            geometry.setHeight(heightHint)
            if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
                self._positionHint_ = self._anchoringWidget_.parent().mapToGlobal(topRight)
            else:
                self._positionHint_ = topRight
            if not desktoputils.is_wayland():
                geometry.setX(self._positionHint_.x())
                geometry.setY(self._positionHint_.y())
            self.setGeometry(geometry)
            self._animationGroup_.start()
            super().show()

        else:
            super().show()
