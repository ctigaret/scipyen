# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, traceback, inspect, subprocess
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork, sip
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safewrapper, safeguiwrapper, scipywarn
from core.sysutils import adapt_ui_path
from gui.workspacegui import WorkspaceGuiMixin
# import numpy as np # cheeky
__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,'pythonhelpwidget.ui')

Ui_PythonHelpWidget, QWidget = __loadUiType__(__ui_path__)

class _PythonHelpThread_(QtCore.QThread):
    ready = Signal(str, name="ready")
    
    def __init__(self, parent: QtCore.QObject):
        QtCore.QThread.__init__(self, parent)
        self.helpCommand = None
        self.helpProcess = None
        self.columns = 4
        self.width = 80

    def run(self):
        if isinstance(self.helpCommand, str) and len(self.helpCommand.strip()):
            cmdParts = self.helpCommand.split(" ")
            fullcmd = [sys.executable, "-m", "pydoc"] + cmdParts
            self.helpProcess = subprocess.run(fullcmd, capture_output=True)
            if self.helpProcess.returncode == 0:
                reply = self.helpProcess.stdout.decode()
                out = list()
                out += ['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"',
                        '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
                        '<html>',]
                if self.helpCommand in ("keywords", "symbols", "topics"):
                    parts = reply.split("help.")
                    parts[0] += "help."
                    items = list(sorted(map(lambda x: x.strip(), filter(lambda x: len(x.strip()), parts[1].replace("\n", " ").split(" ")))))
                    out += ["<head>", 
                            f"<title>{parts[0]}</title>", 
                            '<meta> name="generator" content="Kate Editor"</meta>', 
                            "</head>"]
                    out.append("<body>")
                    out.append(f"<h3>{parts[0]}</h3>")
                    out.append("<table>")
                    k = 0
                    while k < len(items):
                        c = 0
                        while c < self.columns:
                            if k == len(items):
                                break
                            if c == 0:
                                out.append("<tr>")
                            out += ["<td>", items[k], "</td>"]
                            k += 1
                            if c == 3:
                                out.append("</tr>")
                            c += 1
                                
                    out.append("</table>")
                    out.append("</body>")
                else:
                    out.append("<body>")
                    items = reply.replace("\n", "<br>")
                    out.append(items)
                    out.append("</body>")
                out.append("</html>")
                reply = "\n".join(out)
                    
                self.ready.emit(reply)
            else:
                scipywarn(f"Process returned {self.helpProcess.returncode}: {self.helpProcess.stderr}")
            self.helpCommand = None

class PythonHelpWidget(QWidget, WorkspaceGuiMixin, Ui_PythonHelpWidget):
    _instance = None # singleton pattern
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            
        return cls._instance
        
    def __init__(self, parent:typing.Optional[QtWidgets.QMainWindow] = None, **kwargs):
        # if sys.platform.startswith("win32") or os.name == "nt" or platform.uname().system == "Windows":
        #     parent = None
        # elif sys.platform.startswith("linux") and os.getenv("XDG_SESSION_TYPE").lower() == "wayland":
        #     parent = None
            
        super(QWidget, self).__init__(parent)
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        
        self._helpThread_ = _PythonHelpThread_(self)
        self._helpThread_.ready[str].connect(self._slot_displayHelp)
        self._configureUI_()
        
        
    def _configureUI_(self):
        self.setupUi(self)
        self.queryLineEdit.returnPressed.connect(self._slot_processQuery)
        
        
    @Slot()
    def _slot_processQuery(self):
        query = self.queryLineEdit.text()
        if len(query.strip()):
            self._helpThread_.helpCommand = query
            self._helpThread_.run()
        
    @Slot(str)
    def _slot_displayHelp(self, txt):
        if len(txt.strip()):
            self.helpDisplay.setHtml(txt)
            # self.helpDisplay.setPlainText(txt)
        else:
            self.helpDisplay.clear()
        
