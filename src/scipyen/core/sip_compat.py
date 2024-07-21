# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from qtpy import QtCore, QtGui, QtWidgets, QtXml, QtSvg
from qtpy.QtCore import Signal, Slot, Property
# from qtpy.QtCore import Signal, Slot, QEnum, Property

try:
    from qtpy import sip as sip
    has_sip = True
except:
    has_sip = False
    
def no_sip_autoconversion(klass):
    """Decorator for classes to suppresses sip autoconversion of Qt to Python
    types.
    
    Mostly useful to prevent sip to convert QVariant to a python type when
    a QVariant is passed as argument to methods of Qt objects, inside the
    decorated function or method.
    
    Parameter:
    ==========
    klass: a Qt :class:
    
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # import sip
            # only works with pyqt5/6
            if has_sip:
                oldValue = sip.enableautoconversion(klass, False)
            ret = func(*args, *kwargs)
            if has_sip:
                sip.enableautoconversion(klass, oldValue)
            return ret
        return wrapper
    return decorator

@no_sip_autoconversion(QtCore.QVariant)
def fromMimeData(mimeData:QtCore.QMimeData) -> QtGui.QColor:
    """Only works with PyQt5/6; PySide2/6 does not implement sip"""
    if mimeData.hasColor():
        # NOTE: 2021-05-14 21:26:16 ATTENTION
        # sip "autoconverts" QVariant<QColor> to an int, therefore constructing
        # a QColor from that results in an unintended color!
        # Therefore we temporarily suppress autoconversion of QVariant here
        # NOTE: 2021-05-15 14:06:57 temporary sip disabling by means of the 
        # decorator core.prog.no_sip_autoconversion
        #
        # WARNING
        ret = mimeData.colorData().value() # This is a python-wrapped QVariant<QColor>
        return ret
    if canDecode(mimeData):
        return QtGui.QColor(mimeData.text())
    return QtGui.QColor()

@no_sip_autoconversion(QtCore.QVariant)
def comboDelegateBrush(index:QtCore.QModelIndex, role:int) -> QtGui.QBrush:
    brush = QtGui.QBrush()
    v = QtCore.QVariant(index.data(role))
    if v.type() == QtCore.QVariant.Brush:
        brush = v.value()
        
    elif v.type() == QtCore.QVariant.Color:
        brush = QtGui.QBrush(v.value())
    return brush
