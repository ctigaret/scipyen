# -*- coding: utf-8 -*-
# $Id: drawerwidget.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""

import sys, os, typing, types, warnings, math, cmath # noqa
import numbers
import numpy as np
import quantities as pq
import pandas as pd
import neo
from tribool import Tribool

import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
__has_qtdbus__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
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

from core.prog import scipywarn # noqa
from core import scipyendataclasses as sdc
from core import scipyen_quantities as scq
from core import qtutils
from gui import guiutils
from gui.widgets import small_widgets as smw
from gui.widgets.dataclasswidgets.dataclasswidget import DataClassWidget
from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin
from iolib import pictio as pio

__module_path__ = os.path.abspath(os.path.dirname(__file__))
__module_file_name__ = os.path.splitext(os.path.basename(__file__))[0]

class WidgetAction(QtWidgets.QWidgetAction):
    def __init__(self, widget: QtWidgets.QWidget, /,
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)


        self._widget_ = widget
        if isinstance(self._widget_, QtWidgets.QWidget):
            self._originalWidgetParent_ = self._widget_.parentWidget()
        else:
            self._originalWidgetParent_ = None

        self._widget_.setParent(self.parent(), QtCore.Qt.Popup)
        self.setDefaultWidget(self._widget_)

    def createWidget(self, parent) -> QtWidgets.QWidget:
        self._widget_.setParent(parent)
        return self._widget_

    def deleteWidget(self, widget: QtWidgets.QWidget):
        widget.hide()
        # if self.parent() is None:
        #     super().deleteWidget(widget)
        # else:
        #     widget.hide()

class WidgetMenu(QtWidgets.QMenu):
    r"""Holds a single QWidgetAction"""
    def __init__(self, widget: QtWidgets.QWidget,
                parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self.setTearOffEnabled(True)
        self._widget_ = widget
        self._action_ = WidgetAction(self._widget_, parent=self)
        self.addAction(self._action_)
        self.setDefaultAction(self._action_)

class DrawerWidget(QtWidgets.QWidget):
    def __init__(self, drawnWidget: QtWidgets.QWidget,
                 drawerOrientation: QtCore.Qt.Orientation = QtCore.Qt.Horizontal,
                 drawerVerticalAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignTop,
                 drawerHorizontalAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignLeft,
                 parent: typing.Optional[QtWidgets.QWidget] = None,
                 ):

        super().__init__(parent=parent)
        self._drawnWidget_ = drawnWidget
        self._drawerOrientation_ = drawerOrientation
        self._drawerVerticalAlignment_ = drawerVerticalAlignment
        self._drawerHorizontalAlignment_ = drawerHorizontalAlignment

        if isinstance(self._drawnWidget_, QtWidgets.QWidget):
            if self._drawerOrientation_ == QtCore.Qt.Horizontal:
                self._sizeAnimationMax_ = self._drawnWidget_.sizeHint().width()
            else:
                self._sizeAnimationMax_ = self._drawnWidget_.sizeHint().height()
        else:
            self._sizeAnimationMax_ = 200

        self._configureUI_()

    def _configureUI_(self):
        self._toggleButton_ = QtWidgets.QToolButton(self)#, popupMode=QtWidgets.QToolButton.InstantPopup)
        self._toggleButton_.setIcon(guiutils.getIcon("application-menu"))
        # self._toggleButton_.setCheckable(True)
        self._toggleButton_.setAutoRaise(True)
        self._toggleButton_.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self._toggleButton_.clicked.connect(self._slot_openWidgetMenu)
        # self._toggleButton_.toggled.connect(self._slot_drawerToggled)

        # self._widgetMenu_ =  WidgetMenu(self._drawnWidget_, parent=self)
        self._widgetMenu_ = None
        self._widgetAction_ = None
        # # # self._widgetMenu_ =  QtWidgets.QMenu(parent=self)
        # # # self._widgetMenu_.setTearOffEnabled(True)
        # # # if isinstance(self._drawnWidget_, QtWidgets.QWidget):
        # # #     self._widgetAction_ = WidgetAction(self._drawnWidget_, self._widgetMenu_)
        # # # else:
        # # #     self._widgetAction_ = None

        # NOTE: 2026-07-04 11:06:55
        # no need to connect valueChanged signal, as the property for the size
        # animation is read/write!
        # if self._drawerOrientation_ == QtCore.Qt.Horizontal:
        #     self._drawnWidget_.setFixedWidth(0)
        #     self._sizeAnimation_ = QtCore.QPropertyAnimation(self, b'drawerWidgetWidth', self)
        #     # self._sizeAnimation_.valueChanged.connect(self._slot_setDrawnWidgetWidth)
        # else:
        #     self._drawnWidget_.setFixedHeight(0)
        #     self._sizeAnimation_ = QtCore.QPropertyAnimation(self, b'drawerWidgetHeight', self)
        #     # self._sizeAnimation_.valueChanged.connect(self._slot_setDrawnWidgetHeight)
        #
        # self._sizeAnimation_.setStartValue(0)
        # self._sizeAnimation_.setDuration(200)
        # self._sizeAnimation_.setEndValue(self._sizeAnimationMax_)
        #
        # self._opacityEffect_ = QtWidgets.QGraphicsOpacityEffect(self)
        # self._opacityEffect_.setOpacity(0.0)
        #
        # self._opacityAnimation_ = QtCore.QPropertyAnimation(self._opacityEffect_, b'opacity', self)
        # self._opacityAnimation_.setStartValue(0.0)
        # self._opacityAnimation_.setDuration(200)
        # self._opacityAnimation_.setEndValue(1.0)
        # self._opacityAnimation_.valueChanged.connect(self._slot_setOpacity)
        #
        # self._drawnWidget_.setGraphicsEffect(self._opacityEffect_)

        # self._parentOpacityAnimation_ = QtCore.QPropertyAnimation(self, b'parentopacity')
        # self._parentOpacityAnimation_.setStartValue(255)
        # self._parentOpacityAnimation_.setDuration(200)
        # self._parentOpacityAnimation_.setEndValue(127)
        #
        # self._parentOpacityAnimation_.valueChanged.connect(self._slot_setParentOpacity)

        # self._animationGroup_ = QtCore.QParallelAnimationGroup()
        # self._animationGroup_.addAnimation(self._sizeAnimation_)
        # self._animationGroup_.addAnimation(self._opacityAnimation_)
        # # self._animationGroup_.addAnimation(self._parentOpacityAnimation_)
        # self._animationGroup_.stateChanged.connect(self._slot_animationStateChanged)

        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self._toggleButton_, 0, 0, 1, 1, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        # layout.addWidget(self._drawnWidget_, 1, 0, 1, 2, self._drawerVerticalAlignment_ | self._drawerHorizontalAlignment_)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        # parent = self.parent()
        # if isinstance(parent, QtWidgets.QWidget):
        #     parent.installEventFilter(self)

    @QtCore.Property(int)
    def drawerWidgetWidth(self) -> int:
        return self._drawnWidget_.width()

    @drawerWidgetWidth.setter
    def drawerWidgetWidth(self, val:int):
        # print(f"{self.__class__.__name__}.drawerWidgetWidth.setter({val})")
        self._drawnWidget_.setFixedWidth(val)
        # h = self._drawnWidget_.height()
        # self._drawnWidget_.resize(QtCore.QSize(val, h))

    @QtCore.Property(int)
    def drawerWidgetHeight(self) -> int:
        return self._drawnWidget_.height()

    @drawerWidgetHeight.setter
    def drawerWidgetHeight(self, val: int):
        # print(f"{self.__class__.__name__}.drawerWidgetHeight.setter({val})")
        self._drawnWidget_.setFixedHeight(val)
        # w = self._drawnWidget_.width()
        # self._drawnWidget_.resize(QtCore.QSize(w,val))


    def setIcon(self, icon: QtGui.QIcon):
        self._toggleButton_.setIcon(icon)

    def setEndValue(self, val: int):
        self._sizeAnimation_.setEndValue(val)

    def setDuration(self, val: int):
        self._sizeAnimation_.setDuration(val)
        self._opacityAnimation_.setDuration(val)
        # self._parentOpacityAnimation_.setDuration(val)

    def setOrientation(self, val: QtCore.Qt.Orientation):
        self._drawerOrientation_ = val
        if self._drawerOrientation_ == QtCore.Qt.Horizontal:
            self._drawnWidget_.setFixedWidth(0)
            self._sizeAnimation_.setPropertyName(b'width')
            self._sizeAnimation_.valueChanged.disconnect()
            self._sizeAnimation_.valueChanged.connect(self._drawnWidget_.setFixedWidth)
        else:
            self._drawnWidget_.setFixedHeight(0)
            self._sizeAnimation_.setPropertyName(b'height')
            self._sizeAnimation_.valueChanged.disconnect()
            self._sizeAnimation_.valueChanged.connect(self._drawnWidget_.setFixedHeight)

    def setWidget(self, obj: QtWidgets.QWidget):
        self._drawnWidget_ = obj

    # def eventFilter(self, obj: QtCore.QObject, evt: QtCore.QEvent):
    #     parent = self.parent()
    #     if isinstance(parent, QtWidgets.QWidget):
    #         if isinstance(obj, type(self.__parent)):
    #             if evt.type() == QtCore.QEvent.MouseButtonRelease:
    #                 if self._sizeAnimation_.currentValue() == self._sizeAnimation_.endValue():
    #                     self._toggleButton_.toggle()
    #     return super().eventFilter(obj, e)

    @Slot(QtCore.QVariant)
    def _slot_setDrawnWidgetWidth(self, val: QtCore.QVariant):
        if not isinstance(val, int):
            val = val.value()
        # print(f"\n**\n{self.__class__.__name__}._slot_setDrawnWidgetWidth({val})")
        self._drawnWidget_.setFixedWidth(val)

    @Slot(QtCore.QVariant)
    def _slot_setDrawnWidgetHeight(self, val: QtCore.QVariant):
        if not isinstance(val, int):
            val = val.value()
        # print(f"{self.__class__.__name__}._slot_setDrawnWidgetHeight({val})")
        self._drawnWidget_.setFixedHeight(val)

    @Slot(QtCore.QVariant)
    def _slot_setOpacity(self, val: QtCore.QVariant):
        if not isinstance(val, float):
            val = val.value()
        # print(f"{self.__class__.__name__}._slot_setOpacity({val})")
        self._opacityEffect_.setOpacity(val)

    # @Slot(QtCore.QVariant)
    # def _slot_setParentOpacity(self, val: QtCore.QVariant):
    #     return # no-op for now
    #     parent = self.parent()
    #     if not isinstance(parent, QtWidgets.QWidget):
    #         return
    #     palette = parent.palette()
    #     palette.setColor(QtGui.QPalette.Window, QtGui.Qolor(255,255,255, val.value()))
    #     parent.setPalette(palette)

    @Slot(QtCore.QAbstractAnimation.State, QtCore.QAbstractAnimation.State)
    def _slot_animationStateChanged(self, newState: QtCore.QAbstractAnimation.State,
                                    oldState: QtCore.QAbstractAnimation.State):
        # print(f"{self.__class__.__name__}._slot_animationStateChanged(newState = {newState}, oldState={oldState})")
        if newState == QtCore.QAbstractAnimation.Running:
            self._drawnWidget_.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            # self._parentOpacityAnimation_.start()
        elif newState == QtCore.QAbstractAnimation.Stopped:
            self._drawnWidget_.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

    @Slot()
    def _slot_openWidgetMenu(self):
        if not isinstance(self._drawnWidget_, QtWidgets.QWidget):
            return
            # if isinstance(self._drawnWidget_, QtWidgets.QWidget):
            #     self._widgetAction_ = WidgetAction(self._drawnWidget_, self._widgetMenu_)
            # else:
            #     return
        # pos = self.mapToGlobal(self._toggleButton_.geometry().bottomRight())
        # pos = self.mapToGlobal(self.geometry().topLeft())
        # pos = self.mapToGlobal(self.boundingRect().topLeft())

        if isinstance(self._widgetMenu_, QtWidgets.QMenu) and qtutils.isQObjectAlive(self._widgetMenu_):
            # actions = self._widgetMenu_.actions()
            if isinstance(self._drawnWidget_, QtWidgets.QWidget) and qtutils.isQObjectAlive(self._drawnWidget_):
                self._widgetAction_.releaseWidget(self._drawnWidget_)
            self._widgetMenu_.close()
            self._widgetMenu_.deleteLater()
            self._widgetAction_.deleteLater()
            self._widgetMenu_ = None
            self._widgetAction_ = None

        self._widgetMenu_ = QtWidgets.QMenu(parent=self)
        self._widgetMenu_.setTearOffEnabled(True)

        if isinstance(self._drawnWidget_, QtWidgets.QWidget):
            self._widgetAction_ = WidgetAction(self._drawnWidget_, self._widgetMenu_)
            self._widgetMenu_.addAction(self._widgetAction_)
            pos = self.mapToGlobal(self._toggleButton_.geometry().topRight())
            # print(f"{self.__class__.__name__}._slot_openWidgetMenu -> pos = {pos}")
            self._widgetMenu_.popup(pos)
        else:
            self._widgetAction_ = None




    @Slot(bool)
    def _slot_drawerToggled(self, val: bool):
        # print(f"{self.__class__.__name__}._slot_drawerToggled({val})")

        # if (
        #     isinstance(self._widgetMenu_, WidgetMenu)
        #     and qtutils.isQObjectAlive(self._widgetMenu_)
        #     ):
        #
        #     self._widgetMenu_.close()
        #     self._widgetMenu_.deleteLater()
        #     self._widgetMenu_ = None

        # self._widgetMenu_ = WidgetMenu(self._drawnWidget_, parent=self)
        # pos = self.mapToGlobal(QtCore.QPoint(0,0))
        if val is True:
            pos = self.mapToGlobal(self._toggleButton_.geometry().bottomLeft())
            self._widgetMenu_.popup(pos)
        else:
            self._widgetMenu_.close()
        # options = QtWidgets.QStyleOptionMenuItem()
        # options.initFrom(self)

        # action = WidgetAction()

        # if val is True:
        #     self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Forward)
        #     # self._toggleButton_.hide()
        #
        # else:
        #     self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Backward)
        #     # self._toggleButton_.show()
        #
        # self._animationGroup_.start()
