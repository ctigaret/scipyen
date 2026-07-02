# -*- coding: utf-8 -*-
# $Id: collapsiblewidgettree.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later
r"""
Modified from
// Source - https://stackoverflow.com/a/49941230
// Posted by CodingCat, modified by community. See post 'Timeline' for change history
// Retrieved 2026-07-01, License - CC BY-SA 3.0
"""

import sys, os, typing, types, warnings, math, cmath # noqa
# import numbers
# import numpy as np
# import quantities as pq
import pandas as pd
# import neo
# from tribool import Tribool

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
from core import strutils
# from core import scipyendataclasses as sdc
# from core import scipyen_quantities as scq
# from core import taxonbridge
# from gui import datatreeviewer
from gui.widgets import small_widgets as smw
from gui.widgets import dataclasswidgets as dcw
# from gui.workspacegui import WorkspaceGuiMixin
# from gui.widgets.datawidgetmixin import DataWidgetMixin

# class SectionExpandButton(QtWidgets.QPushButton):
# class SectionExpandButton(QtWidgets.QToolButton):
class SectionExpandButton(QtWidgets.QWidget):
    """Toolbutton-like widget that can expand or collapse its section
    """
    def __init__(self, item: QtWidgets.QTreeWidgetItem, text: str = "",
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.toolButton = QtWidgets.QToolButton(self)
        self.toolButton.setAutoRaise(True)
        self.toolButton.setArrowType(QtCore.Qt.RightArrow)
        self.toolButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolButton.setText(text)
        self.headerLine = QtWidgets.QFrame(self)
        self.headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.headerLine.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Minimum)


        self.innerLayout = QtWidgets.QHBoxLayout(self)
        self.innerLayout.setSpacing(0)
        self.innerLayout.setContentsMargins(0,0,0,0)
        self.innerLayout.addWidget(self.toolButton)
        self.innerLayout.addWidget(self.headerLine)

        # self.mainLayout = QtWidgets.QGridLayout(self)
        # self.mainLayout.setVerticalSpacing(0)
        # self.mainLayout.setHorizontalSpacing(0)
        # self.mainLayout.setContentsMargins(0,0,0,0)
        # self.mainLayout.addLayout(self.innerLayout)
        # self.setLayout(self.mainLayout)

        self.section = item
        self.toolButton.clicked.connect(self.on_clicked)


        # super().__init__(text, parent)
        # self.setAutoRaise(True)
        # self.setArrowType(QtCore.Qt.RightArrow)
        # self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        # self.setText(text)
        # self.section = item
        # self.clicked.connect(self.on_clicked)

    def on_clicked(self):
        """toggle expand/collapse of section by clicking
        """
        if self.section.isExpanded():
            self.section.setExpanded(False)
            self.toolButton.setArrowType(QtCore.Qt.RightArrow)
        else:
            self.section.setExpanded(True)
            self.toolButton.setArrowType(QtCore.Qt.DownArrow)


# class CollapsibleDialog(QDialog):
class CollapsibleWidgetTree(QtWidgets.QWidget):
    """A widget to which collapsible sections can be added;
    subclass and reimplement define_sections() to define sections and
        add them as (title, widget) tuples to self.sections
    """
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)
        self.tree.setIndentation(0)

        # self.sections = []
        # self.define_sections()
        # self.add_sections()

        self.sections = dict() # section name ↦ tuple(qtreewidgetitem, widget)

    def removeSection(self, title:str) -> tuple:
        if title not in self.sections:
            return tuple()

        ndx = list(self.sections.keys()).index(title)
        qtwi = self.tree.takeTopLevelItem(ndx)
        qtwi_, widget = self.sections.pop(title)
        print(qtwi == qtwi_)
        return qtwi, widget


    def replaceSection(self, title:str, widget: QtWidgets.QWidget) -> tuple:
        r"""Returns the replaced section """
        if title not in self.sections:
            scipywarn(f"There is no section entitled {title}")
            return tuple()

        ndx = list(self.sections.keys()).index(title)
        qtwi_, w_ = self.sections[title]
        qtwi = self.tree.takeTopLevelItem(ndx)
        item = self.addButton(title, ndx)
        child = self.addWidget(item, widget)
        self.sections[title] = (item, widget)
        return qtwi, w_

    def addSection(self, title: str, widget: QtWidgets.QWidget):
        if title in self.sections:
            scipywarn(f"A section entitled {title} already exist; please remove it first")
            return
            # qtwi, wid = self.sections.pop(title)
            # self.tree.removeItemWidget(qtwi, 0)
            # wid.close()
            # del wid
        item = self.addButton(title)
        child = self.addWidget(item, widget)
        item.addChild(child)
        self.sections[title] = (item, widget)

    def addButton(self, title: str, ndx: typing.Optional[int] = None) -> QtWidgets.QTreeWidgetItem:
        """creates a QTreeWidgetItem containing a button
        to expand or collapse its section
        """
        if not isinstance(title, str) or len(title.strip()) == 0:
            title = strutils.counter_suffix("Section", list(self.sections.keys()), returns_counter=False)
        item = QtWidgets.QTreeWidgetItem()
        if isinstance(ndx, int):
            self.tree.insertTopLevelItem(ndx, item)
        else:
            self.tree.addTopLevelItem(item)
        self.tree.setItemWidget(item, 0, SectionExpandButton(item, text = title))
        # self.items.append(item)
        return item

    def addWidget(self, button: QtWidgets.QTreeWidgetItem, widget: QtWidgets.QWidget) -> QtWidgets.QTreeWidgetItem:
        """creates a QTreeWidgetItem containing the widget,
        as child of the button-QWidgetItem
        """
        section = QtWidgets.QTreeWidgetItem(button)
        section.setDisabled(True)
        self.tree.setItemWidget(section, 0, widget)
        return section


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = CollapsibleDialog()
#     window.show()
#     sys.exit(app.exec_())
