# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import os  # noqa: I001
import qtpy  # noqa: F401
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6  # noqa: I001
    from PySide6 import Shiboken # noqa: F401
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True
    from qtpy.uic import loadUiType # noqa: F401
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut

__has_qtdbus__ = False
try:
    from qtpy import QtDBus  # noqa: F401
    __has_qtdbus__ = True
except: # noqa
    __has_qtdbus__ = False



# END import modules

class FileColumnView(QtWidgets.QColumnView):
    r"""I am not entirey happy with how QColumnView handles multiple selections.
This is intended to provide a fix in the future (if at all)

For now it just inherits QColumnView without addinf=g significant functionality.

If you dislike an extra level of indirection then change mainwindow.ui to use
QColumnView directly, instead of this class (in Qt6 Designer, select the
'fileSystemColumnView' object and from its context menu activate
"Demote to QColumnView" - DON'T FORGET to save the ui file then in a terminal
generate its python counterpart (from within the active scipyenv environment!))

"""
    def __init__(self, parent: QtWidgets.QWidget | None = None, **kwargs):
        super().__init__(parent)
        self.installEventFilter(self)
        self.viewportEntered.connect(self._slot_viewPortEntered_)

    def eventFilter(self, obj, event) -> bool:
        if isinstance(event, QtGui.QMouseEvent): #and event.type() == QtCore.QEvent.MouseButtonRelease:
            print(f"{self.__class__.__name__}.eventFilter({obj}, {event})")
            print(f"\n\tevent type {event.type()}")
        return super().eventFilter(obj, event)

    def childEvent(self, obj):
        # print(f"{self.__class__.__name__}.childEvent({obj})")
        return super().childEvent(obj)

    def viewportEvent(self, obj):
        # print(f"{self.__class__.__name__}.viewportEvent({obj})")
        return super().viewportEvent(obj)

    def mouseReleaseEvent(self, evt):
        print(f"{self.__class__.__name__}.mouseReleaseEvent")
        keyboardModifiers = QtWidgets.QApplication.keyboardModifiers()
        if not (keyboardModifiers & QtCore.Qt.ShiftModifier or keyboardModifiers & QtCore.Qt.ControlModifier):
            super().mouseReleaseEvent(evt)
        evt.accept()

    def selectionChanged(self, *args):
        print(f"{self.__class__.__name__}.selectionChanged({args})")
        print(f"\n\t{len(self.selectedIndexes())} indexes selected")
        super().selectionChanged(*args)


    @Slot()
    def _slot_viewPortEntered_(self):
        print(f"{self.__class__.__name__}._slot_viewPortEntered_()")
        print(f"\tsender: {self.sender()}")
