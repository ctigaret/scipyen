# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
See https://pyqt.riverbankcomputing.narkive.com/4Atl8IgU/how-to-detect-if-an-object-has-been-deleted
solution by Giovanni Bajo
"""
import sys, os, typing # noqa
import datetime
# import contextlib
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6 # noqa
    from PySide6 import Shiboken # noqa
    # from PySide6.QtCore import (Signal, Slot, Property,)
    # from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction # noqa
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
        
    from qtpy import sip
    # from qtpy.uic import loadUiType # noqa
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

# import qtpy
# qtpy.API = os.environ["QT_API"]
# if os.environ["QT_API"] == "pyside6":
#     import PySide6
#     from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
#     from PySide6.QtCore import Signal, Slot, Property
# else:
#     from qtpy import QtCore, QtGui, QtWidgets, QtSvg
#     from qtpy.QtCore import Signal, Slot, Property

# from core.prog import safewrapper # noqa
# from core.sysutils import adapt_ui_path


__module_path__ = os.path.abspath(os.path.dirname(__file__))

# from qt import *
# import weakref

# class QtRef(weakref.ref):
#     __slots__ = "_callback",
#
#     def __new__(typ, obj, callback=None):
#         if not isinstance(obj, QtCore.QObject):
#             wr = weakref.ref.__new__(weakref.ref, obj, callback)
#             wr.__init__(obj, callback)
#             return wr
#         wr = weakref.ref.__new__(typ, obj)
#         if callback is not None:
#             wr._callback = lambda: callback(wr) # noqa
#             QtCore.QObject.connect(o, SIGNAL("destroyed()"), wr._callback)
#             return wr
#
#     def __call__(self, *args, **kwargs):
#         obj = super(qtref, self).__call__(*args, **kwargs)
#         if obj is None:
#             return None
#         try:
#             obj.parent()
#         except RuntimeError:
#             return None
#         return obj
#
#     def __repr__(self):
#         obj = self()
#         if obj is not None:
#             return "<qtweakref at %08X; to '%.50s' at %08X>" % (id(self),
#         type(obj).__name__, id(obj))
#         return "<qtweakref at %08X; is dead>" % id(self)

class SignalBlocker():
    def __init__(self, widgets: typing.Union[QtWidgets.QWidget,
                                             typing.Sequence[QtWidgets.QWidget]]):
        self._blockers_ = tuple()
        if isinstance(widgets, QtWidgets.QWidget):
            self._widgets_ = (widgets, )
        else:
            self._widgets_ = tuple(
                filter(
                    lambda w: isinstance(w, QtWidgets.QWidget),
                    widgets
                    )
                )

    def __enter__(self):
        self._blockers_ = tuple(
            map(
                lambda w: QtCore.QSignalBlocker(w),
                tuple(
                    filter(
                        lambda w: isQObjectAlive(w),
                        self._widgets_
                        )
                    )
                )
            )

    def __exit__(self, exc_type, exc_value, traceback):
        # if len(self._blockers_) and all(isinstance(b, QtCore.QSignalBlocker) for b in self._blockers_):
        #     for b in self._blockers_:
        #         # b.deleteLater()
        #         b = None

        self._blockers_ = tuple()

def isQObjectDeleted(obj:QtCore.QObject):
    if not __has_sip__:
        return False # fallback
    
    if not isinstance(obj, QtCore.QObject):
        return True
    
    try:
        sip.unwrapinstance(obj)
    except RuntimeError:
        return True
    return False

def isQObjectAlive(obj:QtCore.QObject):
    if not isinstance(obj, QtCore.QObject):
        return False
    
    try:
        obj.parent()
    except RuntimeError:
        return False
    
    return True

def datetime2Qt(d:datetime.datetime)->QtCore.QDateTime:
    from core import utilities
    
    timeStamp = int(utilities.posixUTC(d))
    return QtCore.QDateTime.fromSecsSinceEpoch(timeStamp) # converts to local time,

def datetimeFromQt(d:QtCore.QDateTime)->datetime.datetime:
    timeStamp = d.toSecsSinceEpoch()
    return datetime.datetime.fromtimestamp(timeStamp) # converts to local time,
    
