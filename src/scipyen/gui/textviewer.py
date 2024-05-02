# -*- coding: utf-8 -*-

#### BEGIN core python modules
from __future__ import print_function
import os
#### END core python modules

#### BEGIN 3rd party modules
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot, QEnum, Property
# from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import Signal, Slot, QEnum, Q_FLAGS, Property
#### END 3rd party modules

#### BEGIN pict.core modules
import core.xmlutils as xmlutils
#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
# from . import icons_rc
#### END pict.gui modules

import iolib.pictio as pio

# NOTE: 2022-12-25 23:08:51
# needed for the new plugins framework
__scipyen_plugin__ = None


# TODO: 2019-11-10 13:12:40
# configure text syntax highlighting
class TextViewer(ScipyenViewer):
    """No-frills text viewer/editor with the simplest text editing functionality.
    • syntax highlighting (XML, HTML, Markdown)
    • support for ODF format (save only)
    • no formatting of characters or font
    • only save as
    • no drag'n drop
    """
    sig_activated = Signal(int)
    # closeMe  = Signal(int)
    # signal_window_will_close = Signal()
    sig_textChanged = Signal(name = "sig_textChanged")
    
    viewer_for_types = {str: 99, QtGui.QTextDocument: 99}
    # view_action_name = "Text"
    
    # FIXME/TODO: 2019-11-10 13:16:56
    # highlighter_types = ("plain", "xml", "html")
    
    def __init__(self, data: (object, type(None)) = None, parent: (QtWidgets.QMainWindow, type(None)) = None, ID:(int, type(None)) = None,win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None, edit:bool=False, markdown:bool=False, *args, **kwargs):
        self._readOnly = edit!=True
        self._markdown = markdown==True
        super().__init__(data=data, parent=parent, ID = ID, win_title=win_title, doc_title=doc_title, *args, **kwargs)
        # super(QMainWindow, self).__init__(parent)
        # self._wm_id_ = int(self.winId())
            
    def _configureUI_(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(QtGui.QIcon.fromTheme("document-open"), "&Open...", self.openFile, "Ctrl+Shift+O")
        self.fileMenu.addAction(QtGui.QIcon.fromTheme("document-save-as"), "&Save As...", self.saveAsFile, "Ctrl+Shift+S")
        self.fileMenu.addAction(QtGui.QIcon.fromTheme("document-export"), "Export to workspace...", self._slot_exportDataToWorkspace, "Ctrl+Shift+E")
        self.editMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(QtGui.QIcon.fromTheme("edit-undo"), "&Undo", self.undo, "Ctrl+z")
        self.editMenu.addAction(QtGui.QIcon.fromTheme("edit-redo"), "&Redo", self.undo, "Ctrl+Shift+z")
        
        self._docViewer_ = QtWidgets.QTextEdit(self)
        self._docViewer_.setReadOnly(self._readOnly)
        self._docViewer_.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        
        if not self._readOnly:
            self._docViewer_.textChanged.connect(self.sig_textChanged)
        
        self.setCentralWidget(self._docViewer_)
        
        #self._defaultCursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        
        self._docViewer_.setDocument(QtGui.QTextDocument())
        
    def _set_data_(self, data, *args, **kwargs):
        if isinstance(data, QtGui.QTextDocument):
            self._docViewer_.setDocument(data)
            
        elif isinstance(data, str):
            from html.parser import HTMLParser
            
            if self._markdown:
                self._docViewer_.document().setMarkdown(data)
                
            else:
            
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
            
    def text(self, plain:bool=False):
        if plain:
            return self._docViewer_.document().toPlainText()
        
        else:
            if self._markdown:
                return self._docViewer_.document().toMarkdown()
        
            return self._docViewer_.document().toHtml()
        
    def setText(self, data):
        self.setData(data) # inherited
    
    @property
    def isMarkdown(self):
        return self._markdown
    
    @isMarkdown.setter
    def isMarkdown(self, value:bool):
        self._markdown = value == True
        if self._markdown:
            data = self._docViewer_.document().toPlainText()
            self._docViewer_.document().clear()
            self._docViewer_.document().toMarkdown(data)
            self._highlighter_ = None
    
    def clear(self):
        self._set_data_("")
        self._docViewer_.document().clear()
        
    def openFile(self):
        fileFilter = "All files (*.*);;Text files (*.txt);;HTML (*.html, *.htm);;XML (*.xml);;Markdown (*.md)"
        
        filePath, flt = self.chooseFile(caption="Open document", 
                                  fileFilter = fileFilter, 
                                  single=True,save=False)
        if len(filePath) > 0:
            data = pio.loadTextFile(filePath, forceText=True)
            (name, extn) = os.path.splitext(filePath)
            
            if len(extn) == 0 or extn.lower() == "txt":
                self._docViewer_.document().clear()
                self._docViewer_.document().setPlainText(data)
                self._highlighter_ = None
                
            elif extn.lower() in ("html", "htm"):
                self._docViewer_.document().clear()
                self._docViewer_.document().setHtml(data)
                
            elif extn.lower() == "xml":
                self._docViewer_.document().clear()
                self._docViewer_.document().setHtml(data)
                self._highlighter_ = xmlutils.XmlSyntaxHighlighter(self._docViewer_.document())
         
            elif extn.lower() == "md":
                self._docViewer_.document().clear()
                self._docViewer_.document().setMarkdown(data)
                self._markdown = True
                self._highlighter_ = None
                
            else:
                self._docViewer_.document().clear()
                self._docViewer_.document().setPlainText(data)
                self._highlighter_ = None
                
    def undo(self):
        self._docViewer_.undo()
        
    def redo(self):
        self._docViewer_.redo()
    
    def saveAsFile(self):
        if self._docViewer_.document().isEmpty():
            #print("Nothing to save")
            return
        
        fileFilter = "All files (*.*);;Text files (*.txt);;OpenDocumentFormat text (*.odf);;HTML (*.html, *.htm);;XML (*.xml);;Markdown (*.md)"
        
        filePath, flt = self.chooseFile(caption="Save document", 
                                  fileFilter = fileFilter, 
                                  single=True,save=True)
        
        if len(filePath) > 0:
            writer = QtGui.QTextDocumentWriter(filePath)
            (name, extn) = os.path.splitext(filePath)
            
            if len(extn) == 0 or extn.lower() == "txt":
                writer.setFormat(QtCore.QByteArray(bytearray("plaintext", "utf-8"))) #FORCE text output
                
            elif extn.lower() == "odf":
                writer.setFormat(QtCore.QByteArray(bytearray("odf", "utf-8"))) #FORCE text output
                
            elif extn.lower() in ("html", "htm", "xml"):
                writer.setFormat(QtCore.QByteArray(bytearray("html", "utf-8"))) #FORCE text output
                
            elif extn.lower() == "md":
                writer.setFormat(QtCore.QByteArray(bytearray("markdown", "utf-8"))) #FORCE text output
                
            else:
                writer.setFormat(QtCore.QByteArray(bytearray("plaintext", "utf-8"))) #FORCE text output
                
            return writer.write(self._docViewer_.document())
                # print("Document saved to ", filePath)
                
    def lines(self):
        doc = self._docViewer_.document()
        ret = list()
        if not doc.isEmpty():
            tb = doc.begin()
            while tb.isValid():
                ret.append(tb.text())
                tb = tb.next()
                
                # NOTE: 2023-02-25 09:46:17
                # do not delete -> stub for more atomic code
    #             try:
    #                 layout = tb.layout()
    #                 for i in range(layout.lineCount()):
    #                     line = layout.lineAt(i)
    #                     lines.append(line)
    #                     
    #                 tb = tb.next()
    #             except:
    #                 continue
                
        return ret
            
    @Slot()
    def _slot_exportDataToWorkspace(self):
        if self._docViewer_.document().isEmpty():
            return
        
        lines = self.lines()
        
        if len(lines):
            textData = "\n".join(lines)
            
            self.exportDataToWorkspace(textData, "textdata")
        
        # doc = self._docViewer_.document()
        # lines = list()
            
        
        
        
