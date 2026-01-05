# -*- coding: utf-8 -*-
# $Id: pythonhelpwidget.py $
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r""" A QWidget offering a very basic — yet workable — interface to Python's help.

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
from tempfile import TemporaryDirectory
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
from core import strutils
from helpsystem import helputils
from gui.workspacegui import WorkspaceGuiMixin
__module_path__ = os.path.abspath(os.path.dirname(__file__))
__ui_path__ = adapt_ui_path(__module_path__,'pythonhelpwidget.ui')

Ui_PythonHelpWidget, QWidget = loadUiType(__ui_path__)

class _PythonHelpThread_(QtCore.QThread):
    # ready = Signal(str, name="ready")
    # ready = Signal(QtGui.QTextDocument, TemporaryDirectory, name="ready")
    ready = Signal(dict, name="ready")
    message = Signal(str, name="ready")
    # threadRunning = Signal(str, name="threadRunning")
    
    def __init__(self, parent: QtCore.QObject, shell:InteractiveShell):
        QtCore.QThread.__init__(self, parent)
        self.shell = shell
        self.helpCommand = None
        self.helpProcess = None
        self.columns = 4
        self.width = 80
        self.tempdir = None

    def run(self):
        # doc = QtGui.QTextDocument()
        reformat:bool = False
        qreply = {"query":self.helpCommand, "tempdir":self.tempdir, "contents":None, "success":False}
        if isinstance(self.helpCommand, str) and len(self.helpCommand.strip()):
            cmdParts = self.helpCommand.split(" ")
            # if any(s in cmdParts for s in ("modules", "module")):
            if "modules" in cmdParts:
                contents = helputils.module_infos("Modules", 
                                                   "Module names and their aliases.<p>",
                                                  self.columns)
                # doc.setHtml(helputils.module_infos("Modules", 
                #                                    "Module names and their aliases.<p>",
                #                                   self.columns))
                qreply["contents"] = contents
                # self.ready.emit(qreply)
                # self.ready.emit(doc)
                # return
            else:
                # NOTE: 2025-06-02 17:02:10
                # do NOT delete the next line - it works (kind of)
                # fullcmd = [sys.executabdle, "-Xfrozen_modules=off", "-m", "pydoc"] + cmdParts
                # NOTE: 2025-06-02 17:01:56
                # testing, don't delete
                # fullcmd = [sys.executable, "-Xfrozen_modules=off", "-m", helputils.__name__] + cmdParts
                # self.message.emit("Please wait...")
                reply = None
                # errors = None
                reformat = False
                # print(f"{self.__class__.__name__}.run: fullcmd = {fullcmd}")
                try:
                    reply, reformat = helputils.run_help_command(self.shell, " ".join(cmdParts),
                                                                 tempdir=self.tempdir)
                except:
                    traceback.print_exc()

                if isinstance(reply, str) and len(reply.strip()):
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
                        if reply.startswith("Help on"):
                            body = helputils.format_python_help_output(reply)
                        else:
                            body = reply.replace("\n", "<br>")
                    else:
                        body = reply

                    if "No Python documentation" in body:
                        qreply["success"] = False
                    else:
                        qreply["success"] = True

                    out.append(body)
                    out.append("</body>")
                    out.append("</html>")
                    contents = "\n".join(out)
                else:
                    contents = None
                    qreply["success"] = False
                    # doc.setHtml()
                    
            qreply["contents"] = contents
                
            self.ready.emit(qreply)
            self.helpCommand = None
                
class PythonHelpWidget(QtWidgets.QWidget, Ui_PythonHelpWidget, WorkspaceGuiMixin, ):
    _instance = None # singleton patformat_common_help_replytern
    
    # NOTE: 2025-06-25 16:45:49
    # see NOTE: 2025-06-20 23:27:26 WARNING in gui.mainwindow
    if not __has_PyQt6__:
        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super().__new__(cls, *args, **kwargs)
                
            return cls._instance
        
    _scipyen_specific_ = "\n".join(["Scipyen-specific NOTES:",
                                "------------------------ ",
                                "Enter a query to access the help system of IPython (e.g. one of `thing`, `?thing`, `thing?`, `??thing`, `thing??`, `?`, or `??`) or Python (e.g., `help(thing)`)",
                                "Supports help-related IPython tools: `?`, `??`, and the line magics `quickref` and `psearch`",
                                "Enter the magic name without the `%` prefix, followed by arguments, to execute it (e.g. `psearch <pattern…>`), or the magic name WITH the `%` prefix to read its documentation (e.g. `%psearch`)",
                                "NOTE: This does not substitute the Python 'help' command or IPython's help system ('?<object>') at the console, but it does help to 'free' up the console during such queries."])
    
    def __init__(self, shell:InteractiveShell, parent:typing.Optional[QtWidgets.QMainWindow] = None,
                 **kwargs):
        if __has_PySide6__:# or __has_PyQt6__:
            super().__init__(parent)
        else:
            super(QtWidgets.QWidget, self).__init__(parent)
            
        # self.tempdir = None
        self._cache_ = dict()
        
        self._helpThread_ = _PythonHelpThread_(self, shell)
        self._helpThread_.message[str].connect(self._slot_displayMessage)
        self._helpThread_.ready[dict].connect(self._slot_displayReply)
        self._queryHistory_ = deque()
        self.placeHolder_msg = 'Enter a help topic in the field above (e.g., "topics", "pywt.Wavelet"), "?", or "help"'
        try:
            with io.StringIO() as bf:
                helper = pydoc.Helper(output = bf)
                helper.intro()
                msg = bf.getvalue()
                parts = list(map(lambda s: s.replace("\n", " "), msg.split("\n\n")))
                parts = parts[:-1]
                parts += (self._scipyen_specific_.splitlines())
                # parts.append("\n".join(["Scipyen-specific NOTES:",
                #                         "---------------------- ",
                #                         "Queries for Python objects must be entered by their fully-qualified names, and not by alias: e.g., search for 'gui.scipyenviewer' and not for 'scipyenviewer', or whatever alias there may be, such as 'sv', etc.",
                #                         "This window is not a substitute to the Python 'help' command or IPython's help system ('?<object>') at the console, but it does 'free' up the console during such queries.",
                #                         "(Expect many bugs 😦)"]))
                self.intro_msg = "\n\n".join(parts)
                # print(f"{self.__class__.__name__}.__init__: placeHolder_msg = {self.placeHolder_msg}")
            
        except:
            traceback.print_exc()
            self.intro_msg = ""
        
        WorkspaceGuiMixin.__init__(self, parent=parent, **kwargs)
        
        self._textColorCache_ = QtWidgets.QApplication.palette().color(QtGui.QPalette.Text)
        
        self._lastQuery_ = None
        
        self._configureUI_()
        self._showCustomPlaceHolderText_()
        self.__class__._instance = self
        
    def _configureUI_(self):
        self.setupUi(self)
        # self.helpDisplay.setPlaceholderText(self.placeHolder_msg)
        self.helpDisplay.setPlaceholderText('Enter a help topic in the field above (e.g., "topics", "pywt.Wavelet"), "?", or "help"')
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
        
    def _showCustomPlaceHolderText_(self):
        self.helpDisplay.clear()
        if len(self.intro_msg):
            self._textColorCache_ = self.helpDisplay.textColor()
            self.helpDisplay.setTextColor(QtWidgets.QApplication.palette().color(QtGui.QPalette.PlaceholderText))
            self.helpDisplay.setPlainText(self.intro_msg)
            
    def processQuery(self, query:str):
        self._slot_displayMessage("Please wait...")
        if len(query.strip()):
            if self.queryComboBox.count() > 0:
                # NOTE: 2025-05-31 22:22:42
                # insert policy of my combobox here is insertAtTop
                self.nextToolButton.setEnabled(self.queryComboBox.currentIndex() > 0)
                self.prevToolButton.setEnabled(self.queryComboBox.currentIndex() < self.queryComboBox.count()-1)
            else:
                self.prevToolButton.setEnabled(False)
                self.nextToolButton.setEnabled(False)

            if query in self._cache_:
                cquery = {"query":query, "tempdir": self._cache_[query]["tempdir"], "contents":self._cache_[query]["contents"], "success":self._cache_[query]["success"]}
                self._slot_displayReply(cquery)
            else:
                    
                self._helpThread_.helpCommand = query
                self._helpThread_.tempdir = TemporaryDirectory(ignore_cleanup_errors=True, delete=False)
                self._helpThread_.run()
        
    @Slot(str)
    def _slot_queryTextChanged(self, text:str):
        if len(text.strip()) == 0:
            self._showCustomPlaceHolderText_()
        
    @Slot()
    def _slot_processQuery(self):
        query = self.queryComboBox.lineEdit().text()
        if query != self._lastQuery_:
            self._lastQuery_ = query
            self.processQuery(query)
            
    @Slot(int)
    def _slot_processQueryNdx(self, index:int):
        query = self.queryComboBox.itemText(index)
        if query == self.queryComboBox.lineEdit().text():
            if query != self._lastQuery_:
                self._lastQuery_ = query
                self.processQuery(query)
            
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
        query = self.queryComboBox.itemText(index)
        signalBlocker = QtCore.QSignalBlocker(self.queryComboBox)
        self.queryComboBox.removeItem(index)
        self._lastQuery_ = None
        cquery = self._cache_.pop(query, None)
        if isinstance(cquery, dict) and isinstance(cquery.get("tempdir", None), TemporaryDirectory):
            cquery["tempdir"].cleanup()
        if self.queryComboBox.count() > 0:
            self._slot_processQueryNdx(self.queryComboBox.currentIndex())
        
    @Slot()
    def _slot_clearQueryHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.queryComboBox)
        self.queryComboBox.clear()
        self._lastQuery_ = None
        for q in self._cache_:
            if isinstance(q.get("tempdir", None), TemporaryDirectory):
                q["tempdir"].cleanup()
                
        self._cache_.clear()
        
    @Slot(str)
    def _slot_displayMessage(self, txt:str):
        if len(txt.strip()):
            self.helpDisplay.setPlainText(txt)
            if self.helpDisplay.textColor() == QtWidgets.QApplication.palette().color(QtGui.QPalette.PlaceholderText):
                self.helpDisplay.setTextColor(self._textColorCache_)
        else:
            self._showCustomPlaceHolderText_()
        
    # @Slot(QtGui.QTextDocument, TemporaryDirectory)
    # @Slot(str, TemporaryDirectory)
    # @Slot(QtGui.QTextDocument, TemporaryDirectory)
    @Slot(dict)
    # def _slot_displayReply(self, doc:typing.Union[QtGui.QTextDocument, str], tempdir:TemporaryDirectory):
    def _slot_displayReply(self, reply:dict):
        contents = reply.get("contents", None)
        tempdir = reply.get("tempdir", None)
        query = reply.get("query", None)
        success = reply.get("success", False)

        if not isinstance(contents, str) or len(contents.strip()) == 0:
            self._showCustomPlaceHolderText_()
            if isinstance(tempdir, TemporaryDirectory):
                tempdir.cleanup()
        else:
            if strutils.is_html(contents):
                doc = QtGui.QTextDocument()
                doc.setHtml(contents)
                self.helpDisplay.setDocument(doc)
            else:
                self.helpDisplay.setPlainText(doc)
                if self.helpDisplay.textColor() == QtWidgets.QApplication.palette().color(QtGui.QPalette.PlaceholderText):
                    self.helpDisplay.setTextColor(self._textColorCache_)

            if query not in self._cache_:
                self._cache_[query] = {"contents":contents, "tempdir":tempdir, "success":success}

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
        if len(self.helpWidget._cache_):
            for cquery in self.helpWidget._cache_.values():
                if isinstance(cquery, dict) and isinstance(cquery.get("tempdir", None), TemporaryDirectory):
                    cquery["tempdir"].cleanup()
