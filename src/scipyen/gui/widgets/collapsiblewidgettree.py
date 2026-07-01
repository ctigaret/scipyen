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

class SectionExpandButton(QtWidgets.QPushButton):
    """a QPushbutton that can expand or collapse its section
    """
    def __init__(self, item, text = "", parent = None):
        super().__init__(text, parent)
        self.section = item
        self.clicked.connect(self.on_clicked)

    def on_clicked(self):
        """toggle expand/collapse of section by clicking
        """
        if self.section.isExpanded():
            self.section.setExpanded(False)
        else:
            self.section.setExpanded(True)


# class CollapsibleDialog(QDialog):
class CollapsibleWidgetTree(QtWidgets.QWidget):
    """A widget to which collapsible sections can be added;
    subclass and reimplement define_sections() to define sections and
        add them as (title, widget) tuples to self.sections
    """
    def __init__(self, parent=None):
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

    def add_section(self, title: str, widget: QtWidgets.QWidget):
        if title in self.sections:
            qtwi, wid = self.sections.pop(title)
            self.tree.removeItemWidget(qtwi)
            wid.close()
            del wid
        item = self.add_button(title)
        child = self.add_widget(item, widget)
        item.addChild(child)
        self.sections[title] = (item, widget)


    # def add_sections(self):
    #     """adds a collapsible sections for every
    #     (title, widget) tuple in self.sections
    #     """
    #     for (title, widget) in self.sections:
    #         button1 = self.add_button(title)
    #         section1 = self.add_widget(button1, widget)
    #         button1.addChild(section1)

    # def define_sections(self):
    #     """reimplement this to define all your sections
    #     and add them as (title, widget) tuples to self.sections
    #     """
    #     widget = QtWidgets.QFrame(self.tree)
    #     layout = QtWidgets.QHBoxLayout(widget)
    #     layout.addWidget(QtWidgets.QLabel("Bla"))
    #     layout.addWidget(QtWidgets.QLabel("Blubb"))
    #     title = "Section 1"
    #     self.sections.append((title, widget))

    def add_button(self, title: str) -> QtWidgets.QTreeWidgetItem:
        """creates a QTreeWidgetItem containing a button
        to expand or collapse its section
        """
        if not isinstance(title, str) or len(title.strip()) == 0:
            title = strutils.counter_suffix("Section", list(self.sections.keys()), returns_counter=False)
        item = QtWidgets.QTreeWidgetItem()
        self.tree.addTopLevelItem(item)
        self.tree.setItemWidget(item, 0, SectionExpandButton(item, text = title))
        # self.items.append(item)
        return item

    def add_widget(self, button: QtWidgets.QTreeWidgetItem, widget: QtWidgets.QWidget) -> QtWidgets.QTreeWidgetItem:
        """creates a QWidgetItem containing the widget,
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
