# -*- coding: utf-8 -*-
# $Id: anchoredwidgetmixin.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""WARNING: do not use yet!
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
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip # noqa
    # from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True


from core.prog import scipywarn #noqa
from core import qtutils
# from gui import textviewer, datatreeviewer
# from gui.widgets.dataclasswidgets.dataexchangewidget import DataExchangeWidget

class AnchoredWidgetMixin(QtCore.QObject):
    sig_closing = Signal(name="sig_closing")
    sig_moved = Signal(QtCore.QPoint, name="sig_moved")
    sig_collapsed = Signal(name="sig_collapsed")

    def __init__(self, parent: QtWidgets.QWidget,
                 anchoringWidget: QtWidgets.QWidget,
                 **kwargs):
        r"""Injects animated show/hide and anchoring behaviour to a QWidget.

        Parameters:
        ===========
        :parent: the QWidget which will gain animated show/hide and anchorin behaviour

        :anchoringWidget: the QWidget to which this is anchored

        WARNING: Widgets where this behaviour is desired MUST contain an instance
        of this as instance attributes, BUT MUST NOT inherit from this.

        I.e., the new functionality is gained through composition rather than
        inheritance.

        Keyword parameters:
        ===================
        :overrideAnchor: bool

        :opacityEffect: bool

        """
        assert isinstance(parent, QtWidgets.QWidget), f"Parent MUST be a QWidget; got a {type(parent).__name__} instead"
        assert isinstance(anchoringWidget, QtWidgets.QWidget), f"Anchoring widget MUST be a QWidget; got a {type(anchoringWidget).__name__} instead"

        # init the QObject to enable signal/slot mechanism
        super().__init__(parent=parent)

        self._overrideAnchor_ = kwargs.pop("overrideAnchor", False)
        self._useOpacityEffect_ = kwargs.pop("opacityEffect", False)

        # self._isSubWidget_: bool = False
        self._positionHint_: typing.Optional[QtCore.QPoint] = None
        self._closeRequested_: bool = False

        self._anchoringWidget_ = anchoringWidget
        # self._isSubWidget_ = True
        self._positionHint_ = anchoringWidget.geometry().topRight()

        if hasattr(self._anchoringWidget_, "sig_moved"):
            self._anchoringWidget_.sig_moved.connect(self._slot_anchoringWidgetMoved)

        windowFlags = kwargs.pop("windowFlags", None)
        if isinstance(windowFlags, QtCore.Qt.WindowType):
            self.setWindowFlags(windowFlags)
        else:
            self.setWindowFlags(QtCore.Qt.Tool)

        # NOTE: 2026-07-18 14:46:13
        # revisit the usefulness of this - is there a reason one may want to pass
        # None for anchoringWidget, here? In case the anchoring functionality is
        # NOT needed then just don't add an instance of this object to its parent !

#         if isinstance(anchoringWidget, QtWidgets.QWidget):
#             self._anchoringWidget_ = anchoringWidget
#             self._isSubWidget_ = True
#             self._positionHint_ = anchoringWidget.geometry().topRight()
#
#             if hasattr(self._anchoringWidget_, "sig_moved"):
#                 self._anchoringWidget_.sig_moved.connect(self.sig_moved)
#
#             windowFlags = kwargs.pop("windowFlags", None)
#             if isinstance(windowFlags, QtCore.Qt.WindowType):
#                 self.setWindowFlags(windowFlags)
#             else:
#                 self.setWindowFlags(QtCore.Qt.Tool)
#
#         else:
#             self._anchoringWidget_ = None
#

        self._sizeAnimationMax_ = 200
        self._sizeAnimation_ = QtCore.QPropertyAnimation(self, b'parentWidgetWidth', self)
        self._sizeAnimation_.setStartValue(0)
        self._sizeAnimation_.setDuration(200) # ms
        self._sizeAnimation_.setEndValue(self._sizeAnimationMax_)
        self._sizeAnimation_.valueChanged.connect(self._slot_setParentWidgetWidth)

        self._opacityEffect_ = QtWidgets.QGraphicsOpacityEffect(self)
        # if self._isSubWidget_:
        if self._useOpacityEffect_:
            self._opacityEffect_.setOpacity(0.0)
        else:
            self._opacityEffect_.setOpacity(1.0)

        self._opacityAnimation_ = QtCore.QPropertyAnimation(self._opacityEffect_, b'opacity', self.parent())
        self._opacityAnimation_.setStartValue(0.0)
        self._opacityAnimation_.setDuration(200)
        self._opacityAnimation_.setEndValue(1.0)
        self._opacityAnimation_.valueChanged.connect(self._slot_setOpacity)

        # if self._isSubWidget_:
        if self._useOpacityEffect_:
            self.parent().setGraphicsEffect(self._opacityEffect_)

        self._animationGroup_ = QtCore.QParallelAnimationGroup()
        self._animationGroup_.addAnimation(self._sizeAnimation_)
        if self._useOpacityEffect_:
            self._animationGroup_.addAnimation(self._opacityAnimation_)
        self._animationGroup_.stateChanged.connect(self._slot_animationStateChanged)


    @QtCore.Property(int)
    def parentWidgetWidth(self) -> int:
        return self.parent().width()

    @parentWidgetWidth.setter
    def parentWidgetWidth(self, value: int):
        self.parent().setFixedWidth(value)

    @Slot(QtCore.QVariant)
    def _slot_setParentWidgetWidth(self, val: int | QtCore.QVariant):
        if not isinstance(val, int):
            val = val.value()
        self.parent().setFixedWidth(val)

    @Slot(QtCore.QVariant)
    def _slot_setOpacity(self, val: float | QtCore.QVariant):
        if not isinstance(val, float):
            val = val.value()

        if val < 0:
            val = 0.
        if val > 1:
            val = 1.

        self._opacityEffect_.setOpacity(val)

    @Slot(QtCore.QAbstractAnimation.State, QtCore.QAbstractAnimation.State)
    def _slot_animationStateChanged(self, newState: QtCore.QAbstractAnimation.State,
                                    oldState: QtCore.QAbstractAnimation.State):

        if (not isinstance(self._animationGroup_, QtCore.QParallelAnimationGroup)
            or not qtutils.isQObjectAlive(self._animationGroup_)):
            return

        parent = self.parent()

        if newState == QtCore.QAbstractAnimation.Running:
            parent.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            if self._useOpacityEffect_:
                self._opacityAnimation_.start()

        elif newState == QtCore.QAbstractAnimation.Stopped:
            # TODO: 2026-07-18 14:55:15 FIXME deal with opacity here
            parent.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
            if self._animationGroup_.direction() == QtCore.QAbstractAnimation.Backward:
                self.sig_collapsed.emit()
                if self._closeRequested_ is True:
                    parent.close()
                else:
                    parent.setVisible(False)

            else:
                # re-allow manual resizing
                parent.setMinimumSize(QtCore.QSize(0,0))
                parent.setMaximumSize(QtCore.QSize(QtWidgets.QWIDGETSIZE_MAX, QtWidgets.QWIDGETSIZE_MAX))

    @property
    def anchoringWidget(self) -> QtWidgets.QWidget | None:
        return self._anchoringWidget_

    @anchoringWidget.setter
    def anchoringWidget(self, obj: QtWidgets.QWidget):
        if isinstance(obj, QtWidgets.QWidget):
            self._anchoringWidget_ = obj
            # self._isSubWidget_ = True
        else:
            self._anchoringWidget_ = None
            # self._isSubWidget_ = False

    def expand(self):
        parent = self.parent()
        self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Forward)
        self._sizeAnimation_.setEndValue(parent.sizeHint().width())

        geometry = parent.geometry()

        topRight = self.anchoringWidget.geometry().topRight()
        if isinstance(self.anchoringWidget.parent(), QtWidgets.QWidget):
            self._positionHint_ = self.anchoringWidget.parent().mapToGlobal(topRight)
        else:
            self._positionHint_ = topRight

        geometry.setX(self._positionHint_.x())
        geometry.setY(self._positionHint_.y())
        parent.setGeometry(geometry)

        self._animationGroup_.start()
        # super().show()

    def collapse(self, close: bool=False):
        parent = self.parent()
        if hasattr(parent, "collapseSubWidgets"):
            parent.collapseSubWidgets(close)
        self._animationGroup_.setDirection(QtCore.QAbstractAnimation.Backward)
        self._closeRequested_ = close
        self._animationGroup_.start()

    @Slot(QtCore.QPoint)
    def _slot_anchoringWidgetMoved(self, pos: QtCore.QPoint):
        # print(f"{self.__class__.__name__}<{self.objectName()}>._slot_anchoringWidgetMoved({pos})\n")
        # if not self.isVisible():
        #     return

        parent = self.parent()

        if not isinstance(self._anchoringWidget_, QtWidgets.QWidget):
            return

        if isinstance(parent.parent(), QtWidgets.QWidget):
            return

        if isinstance(self._anchoringWidget_.parent(), QtWidgets.QWidget):
            newPos = self._anchoringWidget_.parent().mapToGlobal(self._anchoringWidget_.geometry().topRight())

        else:
            newPos = self._anchoringWidget_.frameGeometry().topRight()

        self.parent.move(newPos)

    def _getAnchoringWidget_(self) -> QtWidgets.QWidget | None:
        parent = self.parent()
        if isinstance(self.anchoringWidget, QtWidgets.QWidget) and self.overrideAnchor:
            return self.anchoringWidget

        if parent.parent() is None:
            return parent

        return None
