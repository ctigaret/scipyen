# -*- coding: utf-8 -*-
# $Id: pythonhelpwidget.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" A QWidget to facilitate access to Python's help system, in parallel, and
not interfering with, your console workflow.
TODO: Work in progress...
"""
import sys, os, typing, traceback, inspect, subprocess
from collections import deque
from qtpy import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork, sip
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core import prog
from core.prog import safewrapper, safeguiwrapper, scipywarn
from core.sysutils import adapt_ui_path
from core import helputils
from gui.workspacegui import WorkspaceGuiMixin
# import numpy as np # cheeky
__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,'pythonhelpwidget.ui')

Ui_PythonHelpWidget, QWidget = __loadUiType__(__ui_path__)

class _PythonHelpThread_(QtCore.QThread):
    # ready = Signal(str, name="ready")
    ready = Signal(QtGui.QTextDocument, name="ready")
    message = Signal(str, name="ready")
    # threadRunning = Signal(str, name="threadRunning")
    
    def __init__(self, parent: QtCore.QObject):
        QtCore.QThread.__init__(self, parent)
        self.helpCommand = None
        self.helpProcess = None
        self.columns = 4
        self.width = 80

    def run(self):
        # TODO: 2025-06-01 12:42:08
        # delegate to core.helputils when the subprocess below fails
        # try to see what IPython is doing
        doc = QtGui.QTextDocument()
        if isinstance(self.helpCommand, str) and len(self.helpCommand.strip()):
            cmdParts = self.helpCommand.split(" ")
            # if any(s in cmdParts for s in ("modules", "module")):
            if "modules" in cmdParts:
                doc.setHtml(helputils.format_infos("Package modules", 
                                                  "Here is a list of discovered modules. In the field above type 'module' and one of the names below for details",
                                                  self.columns))
                self.ready.emit(doc)
                return
            else:
                fullcmd = [sys.executable, "-Xfrozen_modules=off", "-m", "pydoc"] + cmdParts
                self.message.emit("Please wait...")
                reply = None
                errors = None
                try:
                    self.helpProcess = subprocess.run(fullcmd, capture_output=True, check=True)
                    reply = self.helpProcess.stdout.decode()
                except subprocess.CalledProcessError as e:
                    reply = e.output.decode()
                    errors = e.stderr.decode()
                    if "No Python documentation found" in reply:
                        pass
                    scipywarn(f"Subprocess returned {e.returncode}")
                    if len(errors.strip()):
                        scipywarn(f"Errors:\n{errors}")
                except:
                    traceback.print_exc() 
                
                if isinstance(reply, str) and len(reply.strip()):
                    if self.helpCommand in ("keywords", "symbols", "topics"):
                        out = list()
                        out += ['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"',
                                '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">']
                        out.append('<html>')
                        parts = reply.split("help.")
                        parts[0] += "help."
                        out += ["<head>", 
                                f"<title>{parts[0]}</title>", 
                                '<meta> name="generator" content="Kate Editor"</meta>', 
                                "</head>"]
                        out.append("<body>")
                        out.append(f"<h3>{parts[0]}</h3>")
                        out.append(helputils.make_HTML_table(parts[1], self.columns))
                        out.append("</body>")
                        out.append("</html>")
                        doc.setHtml("\n".join(out))
                    else:
                        out = list()
                        out += ['<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"',
                                '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">']
                        out.append('<html>')
                        out += ["<head>", 
                                f"<title>{self.helpCommand}</title>", 
                                '<meta> name="generator" content="Kate Editor"</meta>', 
                                "</head>"]
                        out.append("<body>")
                        body = reply.replace("\n", "<br>\n")
                        out.append(body)
                        out.append("</body>")
                        out.append("</html>")
                        doc.setHtml("\n".join(out))
                        # print(reply.split("\n"))
                        # doc.setMarkdown(reply)
                        # doc.setHtml(reply)
                
            self.ready.emit(doc)
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
        self._helpThread_.message[str].connect(self._slot_displayMessage)
        self._helpThread_.ready[QtGui.QTextDocument].connect(self._slot_displayReply)
        self._queryHistory_ = deque()
        self._configureUI_()
        
        
    def _configureUI_(self):
        self.setupUi(self)
        self.removQueryAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"),
                                                                "Remove this query from history",
                                                                self.queryComboBox.lineEdit())
        self.removQueryAction.setToolTip("Remove this query from history")
        self.removQueryAction.triggered.connect(self._slot_removeCurrentQuery)
        self.clearQueryHistoryAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"),
                                                           "Clear query list",
                                                           self.queryComboBox.lineEdit())
        self.clearQueryHistoryAction.setToolTip("Clear query list")
        self.clearQueryHistoryAction.triggered.connect(self._slot_clearQueryHistory)
        self.queryComboBox.lineEdit().setClearButtonEnabled(True)
        self.queryComboBox.lineEdit().redoAvailable = True
        self.queryComboBox.lineEdit().undoAvailable = True
        self.queryComboBox.lineEdit().addAction(self.clearQueryHistoryAction,
                                                QtWidgets.QLineEdit.TrailingPosition)
        self.queryComboBox.lineEdit().addAction(self.removQueryAction,
                                     QtWidgets.QLineEdit.TrailingPosition)
        self.queryComboBox.lineEdit().returnPressed.connect(self._slot_processQuery)
        self.queryComboBox.currentIndexChanged[int].connect(self._slot_processQueryNdx)
        
        self.prevToolButton.clicked.connect(self._slot_prevQuery)
        self.nextToolButton.clicked.connect(self._slot_nextQuery)
        
        
    @Slot()
    def _slot_processQuery(self):
        query = self.queryComboBox.lineEdit().text()
        if len(query.strip()):
            # if query not in self._queryHistory_:
            #     self._queryHistory_.append(query)
            if self.queryComboBox.count() > 0:
                # NOTE: 2025-05-31 22:22:42
                # insert policy is insertAtTop
                self.nextToolButton.setEnabled(self.queryComboBox.currentIndex() > 0)
                self.prevToolButton.setEnabled(self.queryComboBox.currentIndex() < self.queryComboBox.count()-1)
            else:
                self.prevToolButton.setEnabled(False)
                self.nextToolButton.setEnabled(False)
                
            self._helpThread_.helpCommand = query
            self._helpThread_.run()
            
    @Slot(int)
    def _slot_processQueryNdx(self, index:int):
        query = self.queryComboBox.itemText(index)
        if len(query.strip()):
            # if query not in self._queryHistory_:
            #     self._queryHistory_.append(query)
            if self.queryComboBox.count() > 0:
                # NOTE: 2025-05-31 22:22:42
                # insert policy is insertAtTop
                self.nextToolButton.setEnabled(self.queryComboBox.currentIndex() > 0)
                self.prevToolButton.setEnabled(self.queryComboBox.currentIndex() < self.queryComboBox.count()-1)
            else:
                self.prevToolButton.setEnabled(False)
                self.nextToolButton.setEnabled(False)
            # if len(self._queryHistory_) > 0:
            #     ndx = self._queryHistory_.index(query)
            #     self.prevToolButton.setEnabled(ndx > 0)
            #     self.nextToolButton.setEnabled(ndx < len(self._queryHistory_)-1)
            # else:
            #     self.prevToolButton.setEnabled(False)
            #     self.nextToolButton.setEnabled(False)
            self._helpThread_.helpCommand = query
            self._helpThread_.run()
            
    @Slot()
    def _slot_nextQuery(self):
        index = self.queryComboBox.currentIndex() - 1
        if index >= 0:
            self.queryComboBox.setCurrentIndex(index)
            
    @Slot()
    def _slot_prevQuery(self):
        index = self.queryComboBox.currentIndex() + 1
        if index < self.queryComboBox.count():
            self.queryComboBox.setCurrentIndex(index)
            
    @Slot()
    def _slot_removeCurrentQuery(self):
        index = self.queryComboBox.currentIndex()
        signalBlocker = QtCore.QSignalBlocker(self.queryComboBox)
        self.queryComboBox.removeItem(index)
        
    @Slot()
    def _slot_clearQueryHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.queryComboBox)
        self.queryComboBox.clear()
        
        
    @Slot(str)
    def _slot_displayMessage(self, txt:str):
        if len(txt.strip()):
            self.helpDisplay.setPlainText(txt)
        else:
            self.helpDisplay.clear()
        
    @Slot(QtGui.QTextDocument)
    @Slot(str)
    def _slot_displayReply(self, doc:typing.Union[QtGui.QTextDocument, str]):
        if isinstance(doc, QtGui.QTextDocument):
            if doc.isEmpty():
                self.helpDisplay.clear()
            else:
                self.helpDisplay.setDocument(doc)
                
        elif isinstance(doc, str):
            if len(doc.strip()):
                self.helpDisplay.setPlainText(doc)
            else:
                self.helpDisplay.clear()
