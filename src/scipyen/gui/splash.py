# -*- coding: utf-8 -*-
# $Id: splash.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import sys, os, typing
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, )
from qtpy.QtCore import (Signal, Slot, Property,)
__has_PySide6__ = False
__has_PyQt6__ =False
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
        from qtpy.uic import loadUiType
        QAction = QtWidgets.QAction
        QActionGroup = QtWidgets.QActionGroup
        QShortcut = QtWidgets.QShortcut
        
        __has_qtdbus__ = False
try:
    from qtpy import QtDBus
    __has_qtdbus__ = True
except:
    __has_qtdbus__ = False
                    
# from core.prog import (safewrapper, safeguiwrapper, scipwarn, printStyled)
# from core.sysutils import adapt_ui_path

__module_path__ = os.path.abspath(os.path.dirname(__file__))


class ScipyenSplash(QtWidgets.QSplashScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show()
        
    @Slot(str)
    def _slot_showMessage(self, val:str, color:typing.Optional[typing.Union[str, QtGui.QColor]] = None) -> None:
        if isinstance(val, str) and len(val.strip()):
            if isinstance(color, str):
                try:
                    color = QtGui.QColor(color)
                except:
                    color = QtGui.QColor("yellow")
                    
            elif not isinstance(color, QtGui.QColor):
                color = QtGui.QColor("yellow")
                    
            self.showMessage(val, QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter, color)
            
    
