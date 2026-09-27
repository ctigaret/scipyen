# $Id: aboutdialog.py $
# SPDX-FileCopyrightText: 2026 Cezar M. Tigaret <cezar.tigaret@proton.me>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

import sys, os, types, typing
import inspect
import traceback
import qtpy # noqa
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False

__has_qtdbus__ = False

if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    # import PySide6
    # from PySide6 import Shiboken # noqa
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

if sys.platform == "linux":
    try:
        from qtpy import QtDBus
        __has_qtdbus__ = True

    except: # noqa
        __has_qtdbus__ = False

__module_path__ = os.path.abspath(os.path.dirname(__file__))

try:
    from gui.aboutdialog_ui import Ui_AboutDialog
except:
    Ui_AboutDialog, _ = loadUiType(os.path.join(__module_path__, "AboutDialog.ui"))

class AboutDialog(QtWidgets.QDialog, Ui_AboutDialog):
    def __init__(self, txt, parent, aboutSuffix: str | None = None):
        QtWidgets.QDialog.__init__(self, parent)
        super(Ui_AboutDialog, self).__init__()
        self._configureUI_()

        self.textBrowser.setHtml(txt)
        wintitle = f"About {aboutSuffix}"
        self.setWindowTitle(wintitle)
        self.show()

    def _configureUI_(self):
        self.setupUi(self)
        self.textBrowser.anchorClicked.connect(self.slot_openLink)

    @Slot(QtCore.QUrl)
    def slot_openLink(self, link: QtCore.QUrl):
        # print(f"{self.__class__.__name__}.slot_openLink: {link.scheme()}")
        if link.scheme() == "scipyen":
            # NOTE: 2025-06-02 16:42:38
            # this below needs to take into account the casefolding in Urls
            cmd = link.toString().replace("scipyen://", "")
            # print(f"cmd: {cmd}")
            method = getattr(self.parent(), cmd, None)
            if inspect.ismethod(method):
                try:
                    method.__call__()

                except: # noqa
                    traceback.print_exc()

        elif not link.isRelative():
            QtGui.QDesktopServices.openUrl(link)

