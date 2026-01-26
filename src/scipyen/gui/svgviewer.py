# -*- coding: utf-8 -*-
# $Id: svgviewer.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
r"""SVG viewer
"""
# NOTE 2026-01-16 10:39:45
# adpot SVGView example in qt/qsvg tree

#### BEGIN core python modules
from __future__ import print_function
import os, typing, types, re, xml
#### END core python modules

#### BEGIN 3rd party modules
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
    

#### END 3rd party modules

#### BEGIN pict.core modules
import core.xmlutils as xmlutils
import core.strutils as strutils
#### END pict.core modules

#### BEGIN pict.gui modules
from gui.scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from gui import quickdialog
# from . import resources_rc
# from . import icons_rc
#### END pict.gui modules

import iolib.pictio as pio
from core import strutils, xmlutils
from core.prog import scipywarn
from gui.widgets import svgwidgets

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
__scipyen_plugin__ = None

class SVGViewer(ScipyenViewer):
    viewer_for_types = {strutils.is_svg:100,
                        xmlutils.is_svg:100}

    def __init__(self, data:typing.Optional[str]=None, 
                 parent:typing.Optional[QtWidgets.QWidget]=None,
                 ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, 
                 doc_title: (str, type(None)) = None, 
                 *args, **kwargs):
        super(QtWidgets.QMainWindow, self).__init__(parent)
        self._configureUI_()
        super().__init__(data=data, parent=parent, ID = ID, win_title=win_title, doc_title=doc_title, *args, **kwargs)
        
    def _configureUI_(self):
        self._svgWidget_ = svgwidgets.SimpleSVGWidget(parent=self)
        self._svgWidget_.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setCentralWidget(self._svgWidget_)
        
    def _set_data_(self, data:str, *args, **kwargs):
        if strutils.is_svg(data):
            self._data_ = data
            self._svgWidget_.setSvg(data)
        elif xmlutils.is_svg(data):
            svgElements = data.getElementsByTagName("svg")
            if len(svgElements):
                svgElement = svgElements[0]
                self._data_ = svgElement
                self._svgWidget_.setSvg(svgElement)
            else:
                scipywarn("The XML Document does not seem to contain SVG data")
                return


        else:
            raise TypeError("Expecting an SVG string")
        
        
        if kwargs.get("show", True):
            self.activateWindow()
