# -*- coding: utf-8 -*-
# $Id: pythonhelpwidget.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" A QWidget offering a veru basic — yet workable — interface to Python's help.

Allow accessing Python's help in parallel (and without interfering) with the 
user's workflow at Scipyen console.

WARNING:
package names, modules and submodules MUST be passed by their real name, and NOT
by alias; e.g. typing "signalviewer" will correctly show a help message for that 
module, but typing "sv" (which is an alias for signalviewr in the workspacw) will
fail

"""
# TODO: 2025-06-03 14:56:22 FIXME
# 0. Implement interface to IPython's '?' help system
#
# 1. delegate all calls to appropriate functions in `helputils` module.
# (for example, this is done for calling pydoc helper on a StringIO, for
# objects NOT found by running python3 in a subprocess)
#
# 2. migrate all formating code below to `helputils` module.
#
# 3. careful how to deal with `apropos` and `apropos -k` help commands: pydoc 
# is loading ALL packages it can find; when run from Scipyen, this WILL crash
# crash the application (I guess this is because it loads & executes Qt5-dependent
# code while already running in a Qt5 event loop already)
# 
# NOTE: This is the very reason why calling pydoc in a subprocess seemed
# like a good idea. The downside is that Scipyen modules are not to be 
# seen in this approach.
# 
# NOTE: The alternative is loading/executing helputils as a standalone
# module in a separate python subprocess, but it opens another big can of worms 
# related to various circular/incomplete imports (which are avoided when
# Scipyen is launched normally). While this may merit some investigation
# (with the potential of massive restructuring the source code tree) I 
# think it is more worthy to try to delegate as much as possible to
# 'helputils' module within the same (current) process while avoiding pydoc
# quirks...
# 
# For now, thus provides a very basic — yet workable — interface to python's
# help system, which is enough to have it as a help window at hand.
#
#
import sys, os, io, typing, traceback, inspect, subprocess, pydoc, runpy
from collections import deque
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
    


from IPython.core.interactiveshell import InteractiveShell
from core import prog
from core.prog import safewrapper, safeguiwrapper, scipywarn
from core.sysutils import adapt_ui_path
from core import helputils
from gui.workspacegui import WorkspaceGuiMixin
# import numpy as np # cheeky
__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,'pythonhelpwidget.ui')

Ui_PythonHelpWidget, QWidget = loadUiType(__ui_path__)

class _PythonHelpThread_(QtCore.QThread):
    # ready = Signal(str, name="ready")
    ready = Signal(QtGui.QTextDocument, name="ready")
    message = Signal(str, name="ready")
    # threadRunning = Signal(str, name="threadRunning")
    
    def __init__(self, parent: QtCore.QObject, shell:InteractiveShell):
        QtCore.QThread.__init__(self, parent)
        self.shell = shell
        self.helpCommand = None
        self.helpProcess = None
        self.columns = 4
        self.width = 80

    def run(self):
        doc = QtGui.QTextDocument()
        reformat:bool = False
        if isinstance(self.helpCommand, str) and len(self.helpCommand.strip()):
            cmdParts = self.helpCommand.split(" ")
            # if any(s in cmdParts for s in ("modules", "module")):
            if "modules" in cmdParts:
                doc.setHtml(helputils.module_infos("Modules", 
                                                   "Here is a list of discovered modules, given as name or name (alias) where appropriate.<p>",
                                                  self.columns))
                # doc.setHtml(helputils.module_infos("Package modules", 
                #                                    "Here is a list of discovered modules, given as name or name (alias) where appropriate.<br>In the field above type one of the names below (or alias) for details",
                #                                   self.columns))
                self.ready.emit(doc)
                return
            else:
                # NOTE: 2025-06-02 17:02:10
                # do NOT delete the next line - it works (kind of)
                fullcmd = [sys.executable, "-Xfrozen_modules=off", "-m", "pydoc"] + cmdParts
                # NOTE: 2025-06-02 17:01:56
                # testing, don;t delete
                # fullcmd = [sys.executable, "-Xfrozen_modules=off", "-m", helputils.__name__] + cmdParts
                self.message.emit("Please wait...")
                reply = None
                errors = None
                try:
                    self.helpProcess = subprocess.run(fullcmd, capture_output=True, check=True)
                    reply = self.helpProcess.stdout.decode()
                    reformat = True
                except subprocess.CalledProcessError as e:
                    reply = e.output.decode()
                    errors = e.stderr.decode()
                    retcode = e.returncode
                    if "No Python documentation found" in reply:
                        try:
                            reply = helputils.run_help_command(" ".join(cmdParts), self.shell)
                            reformat = True
                        except:
                            traceback.print_exc()
                    else:
                        scipywarn(f"Subprocess returned {retcode}")
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
                        if "symbols" in self.helpCommand:
                            cols = len(pydoc.Helper.symbols)//3 + len(pydoc.Helper.symbols) % 3
                        else:
                            cols = self.columns
                        out.append(helputils.make_HTML_table(parts[1], cols))
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
                        if reformat:
                            body = reply.replace("\n", "<br>\n")
                        else:
                            body = reply
                        out.append(body)
                        out.append("</body>")
                        out.append("</html>")
                        doc.setHtml("\n".join(out))
                        # print(reply.split("\n"))
                        # doc.setMarkdown(reply)
                        # doc.setHtml(reply)
                
            self.ready.emit(doc)
            self.helpCommand = None
                
class PythonHelpWidget(QtWidgets.QWidget, Ui_PythonHelpWidget, WorkspaceGuiMixin, ):
    _instance = None # singleton pattern
    
    # NOTE: 2025-06-25 16:45:49
    # see NOTE: 2025-06-20 23:27:26 WARNING in gui.mainwindow
    if not __has_PyQt6__:
        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super().__new__(cls, *args, **kwargs)
                
            return cls._instance
        
    def __init__(self, shell:InteractiveShell, parent:typing.Optional[QtWidgets.QMainWindow] = None,
                 **kwargs):
        if __has_PySide6__:# or __has_PyQt6__:
            super().__init__(parent)
        else:
            super(QtWidgets.QWidget, self).__init__(parent)
            
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        
        self._helpThread_ = _PythonHelpThread_(self, shell)
        self._helpThread_.message[str].connect(self._slot_displayMessage)
        self._helpThread_.ready[QtGui.QTextDocument].connect(self._slot_displayReply)
        self._queryHistory_ = deque()
        try:
            with io.StringIO() as bf:
                helper = pydoc.Helper(output = bf)
                helper.intro()
                msg = bf.getvalue()
                parts = list(map(lambda s: s.replace("\n", " "), msg.split("\n\n")))
                parts = parts[:-1]
                parts.append("\n".join(["Scipyen-specific NOTES:",
                                        "---------------------- ",
                                        "Queries for Python objects must be entered by their fully-qualified names, and not by alias: e.g., search for 'gui.scipyenviewer' and not for 'scipyenviewer', or whatever alias there may be, such as 'sv', etc.",
                                        "This window is not a substitute to the Python 'help' command or IPython's help system ('?<object>') at the console, but it does 'free' up the console during such queries.",
                                        "(Expect many bugs 😦)"]))
                self.intro_msg = "\n\n".join(parts)
                
        except:
            self.intro_msg = 'Enter a help topic in the field above (e.g., "topics", "pywt.Wavelet", etc)'
        
        self._configureUI_()
        self.__class__._instance = self
        
    def _configureUI_(self):
        self.setupUi(self)
        self.helpDisplay.setPlaceholderText(self.intro_msg)
        self.removQueryAction = QAction(QtGui.QIcon.fromTheme("edit-delete"),
                                                                "Remove this query from history",
                                                                self.queryComboBox.lineEdit())
        self.removQueryAction.setToolTip("Remove this query from history")
        self.removQueryAction.triggered.connect(self._slot_removeCurrentQuery)
        self.clearQueryHistoryAction = QAction(QtGui.QIcon.fromTheme("final_activity"),
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
        self.queryComboBox.lineEdit().textChanged[str].connect(self._slot_queryTextChanged)
        self.queryComboBox.currentIndexChanged[int].connect(self._slot_processQueryNdx)
        
        self.prevToolButton.clicked.connect(self._slot_prevQuery)
        self.nextToolButton.clicked.connect(self._slot_nextQuery)
        
    @Slot(str)
    def _slot_queryTextChanged(self, text:str):
        if len(text.strip()) == 0:
            self.helpDisplay.clear()
        
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
            if self.queryComboBox.count() > 0:
                # NOTE: 2025-05-31 22:22:42
                # insert policy of my combobox here is insertAtTop
                self.nextToolButton.setEnabled(self.queryComboBox.currentIndex() > 0)
                self.prevToolButton.setEnabled(self.queryComboBox.currentIndex() < self.queryComboBox.count()-1)
            else:
                self.prevToolButton.setEnabled(False)
                self.nextToolButton.setEnabled(False)
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

class PythonHelpWindow(QtWidgets.QMainWindow, WorkspaceGuiMixin):
    def __init__(self, shell, parent=None):
        super().__init__(parent=parent)
        WorkspaceGuiMixin.__init__(self, parent=parent)
        self.setWindowTitle("Scipyen — Python help")
        self.helpWidget = PythonHelpWidget(shell, self)
        self.setCentralWidget(self.helpWidget)
        
        self.loadSettings()

    def closeEvent(self, evt):
        self.saveSettings()
