# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
See https://pyqt.riverbankcomputing.narkive.com/4Atl8IgU/how-to-detect-if-an-object-has-been-deleted
solution by Giovanni Bajo
"""
import sys, os, typing
import datetime
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path


__module_path__ = os.path.abspath(os.path.dirname(__file__))

# from qt import *
import weakref

class QtRef(weakref.ref):
    __slots__ = "_callback",

    def __new__(typ, o, callback=None):
        if not isinstance(o, QObject):
            wr = weakref.ref.__new__(weakref.ref, o, callback)
            wr.__init__(o, callback)
            return wr
        wr = weakref.ref.__new__(typ, o)
        if callback is not None:
            wr._callback = lambda: callback(wr)
            QObject.connect(o, SIGNAL("destroyed()"), wr._callback)
            return wr

    def __call__(self, *args, **kwargs):
        o = super(qtref, self).__call__(*args, **kwargs)
        if o is None:
            return None
        try:
            o.parent()
        except RuntimeError:
            return None
        return o

    def __repr__(self):
        o = self()
        if o is not None:
            return "<qtweakref at %08X; to '%.50s' at %08X>" % (id(self),
        type(o).__name__, id(o))
        return "<qtweakref at %08X; dead>" % id(self)
    
def isQObjectDeleted(obj:QtCore.QObject):
    import sip
    
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
        # obj.name()
        obj.parent()
    except RuntimeError:
        return False
    
    return True

def datetime2Qt(d:datetime.datetime)->QtCore.QDateTime:
    from core import utilities
    
    timeStamp = utilities.posixUTC(d)
    return QtCore.QDateTime.fromSecsSinceEpoch(timeStamp) # converts to local time,

def datetimeFromQt(d:QtCore.QDateTime)->datetime.datetime:
    timeStamp = d.toSecsSinceEpoch()
    return datetime.datetime.fromtimestamp(timeStamp) # converts to local time,
    
