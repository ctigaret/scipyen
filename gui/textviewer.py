# -*- coding: utf-8 -*-

#### BEGIN core python modules
from __future__ import print_function
import os
#### END core python modules

#### BEGIN 3rd party modules
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty
from PyQt5.uic import loadUiType as __loadUiType__
#### END 3rd party modules

#### BEGIN pict.core modules
import core.xmlutils as xmlutils
#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
#### END pict.gui modules

# TODO: 2019-11-10 13:12:40
# configure text syntax highlighting
class TextViewer(ScipyenViewer):
    sig_activated = pyqtSignal(int)
    closeMe  = pyqtSignal(int)
    signal_window_will_close = pyqtSignal()
    
    supported_types = (str, QtGui.QTextDocument)
    view_action_name = "Text"
    
    # FIXME/TODO: 2019-11-10 13:16:56
    highlighter_types = ("plain", "xml", "html")
    
    def __init__(self, data: (object, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 pWin: (QtWidgets.QMainWindow, type(None))= None, ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 *args, **kwargs) -> None:
        super().__init__(data=data, parent=parent, pWin=pWin, ID = ID, win_title=win_title, doc_title=doc_title, *args, **kwargs)
            
    def _configureUI_(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction("&Save As...", self.saveAsFile, "Ctrl+Shift+S")
        
        self._docViewer_ = QtWidgets.QTextEdit(self)
        self._docViewer_.setReadOnly(True)
        self._docViewer_.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        
        self.setCentralWidget(self._docViewer_)
        
        #self._defaultCursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        
        self._docViewer_.setDocument(QtGui.QTextDocument())
        
    def _set_data_(self, data, *args, **kwargs):
        if isinstance(data, QtGui.QTextDocument):
            self._docViewer_.setDocument(data)
            
        elif isinstance(data, str):
            from html.parser import HTMLParser
            
            parser = HTMLParser(convert_charrefs=True)
            
            parser.feed(data)
            
            parser.close()
            
            if parser.get_starttag_text() is None:
                self._docViewer_.document().setPlainText(data)
                
            else:
                self._docViewer_.document().setHtml(data)
            
            if data.find("<?xml version=") >= 0:
                self._highlighter_ = xmlutils.XmlSyntaxHighlighter(self._docViewer_.document())
            else:
                self._highlighter_ = None
                
        else:
            raise TypeError("Expecting a QTextDdocument or a str; got %s instead" % type(data).__name__)
        
        if kwargs.get("show", True):
            self.activateWindow()
        
    def clear(self):
        self._set_data_("")
    
    def saveAsFile(self):
        if self._docViewer_.document().isEmpty():
            #print("Nothing to save")
            return
        
        fileFilter = "All files (*.*);;Text files (*.txt);;OpenDocumentFormat text (*.odf);;HTML (*.html)"
        
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Document", filter=fileFilter)
        
        if len(filePath) > 0:
            writer = QtGui.QTextDocumentWriter(filePath)
            (name, extn) = os.path.splitext(filePath)
            
            if len(extn) == 0 or extn.lower() == "txt":
                writer.setFormat(QtCore.QByteArray(bytearray("plaintext", "utf-8"))) #FORCE text output
                
            elif extn.lower() == "odf":
                writer.setFormat(QtCore.QByteArray(bytearray("odf", "utf-8"))) #FORCE text output
                
            elif extn.lower() == "html":
                writer.setFormat(QtCore.QByteArray(bytearray("html", "utf-8"))) #FORCE text output
                
            else:
                writer.setFormat(QtCore.QByteArray(bytearray("plaintext", "utf-8"))) #FORCE text output
                
                
            if writer.write(self._docViewer_.document()):
                print("Document saved to ", filePath)
                        
            
            
