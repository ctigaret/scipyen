# -*- coding: utf-8 -*-
"""Viewer for XML documents
"""
#### BEGIN core python modules
from __future__ import print_function
import sys, os, traceback, inspect, numbers

from collections import namedtuple,OrderedDict

# NOTE: use Python's re instead of QRegExp
import re

import xml.parsers.expat
import xml.etree
import xml.etree.ElementTree as ET # the default parsers in here are from xml.parsers.expat,
                                   # see documentation for xml.etree.ElementTree.XMLParser
import xml.dom
import xml.dom.minidom
#import abc
#### END core python modules

#### BEGIN 3rd party modules
# 2016-09-25 21:28:37 
# add XMl text viewer, schema viewer and xquery editor

# 2016-08-16 09:30:07
# NOTE FIXME QtXml is not actively maintained anymore in Qt >= 5.5
from PyQt5 import QtCore, QtWidgets, QtXmlPatterns, QtXml, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUiType as __loadUiType__


#### END 3rd party modules

#### BEGIN pict.core modules
import core.xmlutils as xmlutils

#from core.datatypes import DataBag

#### END pict.core modules

#### BEGIN pict.gui modules
from .scipyenviewer import ScipyenViewer #, ScipyenFrameViewer
from . import quickdialog
from . import resources_rc
#### END pict.gui modules



HighlightingRule = namedtuple('HighlightingRule', ['pattern', 'format'])

class XmlSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    '''
    '''
    def __init__(self, parent = None):
        ''' Constructor
        
        Argument:
        
        parent = QtGui.QTextDocument; optional (default is None)
        
        '''
        super().__init__(parent)
        
        self.highlightingRules = list()
        
        self.tagFormat = QtGui.QTextCharFormat()
        self.tagFormat.setForeground(QtCore.Qt.darkBlue)
        self.tagFormat.setFontWeight(QtGui.QFont.Bold)

        # Tag format
        
        #rule = HighlightingRule(pattern=QtCore.QRegExp("(<[a-zA-Z:]+\\b|<\\?[a-zA-Z:]+\\b|\\?>|>|/>|</[a-zA-Z:]+>)"), format=self.tagFormat)
        #rule = HighlightingRule(pattern="(<[a-zA-Z:]+\\b|<\\?[a-zA-Z:]+\\b|\\?>|>|/>|</[a-zA-Z:]+>)", format=self.tagFormat)
        rule = HighlightingRule(pattern=re.compile("(<[a-zA-Z:]+\\b|<\\?[a-zA-Z:]+\\b|\\?>|>|/>|</[a-zA-Z:]+>)"), format=self.tagFormat)
        self.highlightingRules.append(rule)
        
        
        # Attribute format
        self.attributeFormat = QtGui.QTextCharFormat()
        self.attributeFormat.setForeground(QtCore.Qt.darkGreen)
        
        #rule = HighlightingRule(pattern=QtCore.QRegExp("[a-zA-Z:]+="), format=self.attributeFormat)
        #rule = HighlightingRule(pattern="[a-zA-Z:]+=", format=self.attributeFormat)
        rule = HighlightingRule(pattern=re.compile("[a-zA-Z:]+="), format=self.attributeFormat)
        self.highlightingRules.append(rule)
        
        # Attribute content format
        self.attributeContentFormat = QtGui.QTextCharFormat()
        self.attributeContentFormat.setForeground(QtCore.Qt.red)
        
        #rule = HighlightingRule(pattern=QtCore.QRegExp("(\"[^\"]*\"|'[^']*')"), format=self.attributeContentFormat)
        #rule = HighlightingRule(pattern="(\"[^\"]*\"|'[^']*')", format=self.attributeContentFormat)
        rule = HighlightingRule(pattern=re.compile("(\"[^\"]*\"|'[^']*')"), format=self.attributeContentFormat)
        self.highlightingRules.append(rule)
        
        # Comment format -- NOT appended to the list of highlighting rules
        self.commentFormat = QtGui.QTextCharFormat()
        self.commentFormat.setForeground(QtCore.Qt.lightGray)
        self.commentFormat.setFontItalic(True)
        
        #self.commentStartExpression = QtCore.QRegExp("<!--")
        #self.commentEndExpression = QtCore.QRegExp("-->")
        
        #self.commentStartExpression = "<!--"
        #self.commentEndExpression = "-->"
        
        self.commentStartExpression = re.compile("<!--")
        self.commentEndExpression = re.compile("-->")
        
        #self._defaultCursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        
    def highlightBlock(self, text):
        ''' Applies highlighting rule to text block
        '''
        for rule in self.highlightingRules:
            startIndex = 0
            
            while startIndex < len(text):
                match = rule.pattern.search(text, startIndex)
                if match:
                    span = match.span()
                    self.setFormat(span[0], span[1]-span[0], rule.format)
                    startIndex = span[1]
                else:
                    break

        self.setCurrentBlockState(0)
        
        startIndex = -1
        endIndex = -1
        commentLength = 0
        
        # check if we have a comment to highlight --  if so, then apply comment
        # format highlighting
        if self.previousBlockState() != -1:
            match = self.commentStartExpression.search(text)
            if match:
                startIndex = match.start()
                
        while startIndex >= 0:
            match = self.commentEndExpression.search(text, startIndex)
            if match:
                endIndex = match.start()
            
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                endNdx = match.end()
                commentLength = endNdx - startIndex
            
            self.setFormat(startIndex, commentLength, commentFormat)
            
            match = self.commentStartExpression.search(text, startIndex + commentLength)
            
            if match:
                startIndex = match.start()
            else:
                break
            
# 2016-08-16 23:55:53
class DomItem(object):
    '''Wraps a QDomNode 
    WARNING: This is based on a DEPRECATED Qt module
    '''
    def __init__(self, node: (QtXml.QDomNode, QtXml.QDomDocument), row: int, parent: (QtXml.QDomNode, type(None)) = None):
        ''' DomItem constructor
        
        Arguments:
        
        node -- an QtXml.QDomNode or  QtXml.QDomDocument, wrapped by this instance
        
        row -- int > = 0; when 0 this is a root node
        
        parent -- the parent node; can be None if 'node' is a root        
        '''
        #print("in DomItem constructor:")
        #print("node is ", type(node))
        #print("parent is ", type(parent))
        
        #if (node is not QtXml.QDomNode) and (node is not QtXml.QDomDocument):
            #raise TypeError("Wrong type for 'node' argument: must be a QtXml.QDomNode")
        
        if row < 0:
            raise ValueError("row must be >= 0")
        
        self._domNode_ = node #  the actual QDomNode wrapped by this instance
        self._rowNumber_ = row # the row of this DomNode, in the (tree) data model
        
        self._parent_ = parent
        
        # NOTE: 2016-09-25 14:14:48 QDomDocument inherits QDomNode!
        
        if parent is not None:
            #if row <= 0:
                #raise ValueError("node with row 0 (root) cannot have a parent")
            if parent is QtXml.QDomNode:
                self._parent_ = DomItem(parent, row-1) 
        
        # a dictionary of DomItem objects that wrap the cildren of this 'node',
        # keyed on the row index
        self._children_ = OrderedDict()

    def child(self, rowIndex):
        ''' Returns the child DOM node (item) of this item, given its "row" index.
        
        If row Index is a valid key in the dict of children ITEMS, then return the 
        corresponding child node.
        
        Else, if it is a valid index i.e. less than the number of NODE children of
        the wrapped DOM NODE then wrap the corresponding child NODE in an ITEM,
        add it to the dictionary, and return it.
        
        Otherwise return 0!
        
        Arguments:
        rowIndex -- int >= 0
        
        Returns:
        
        The child DOM Node (QDomNode) at index rowIndex as a DomItem object, 
        or None if rowIndex is not valid.
        
        '''
        if rowIndex in self._children_:
            return self._children_[rowIndex]
        
        if rowIndex >=0 and rowIndex < self._domNode_.childNodes().count():
            childNode = self._domNode_.childNodes().item(rowIndex)
            childItem = DomItem(childNode, rowIndex, self)
            self._children_[rowIndex] = childItem
            return childItem
        
        return None
        
        # BEGIN alternate code for debugging
        
        #print("in DomItem.child")
        
        #print("this DomItem nodeName: ", self._domNode_.nodeName())
        ## this is the local name of the current node a.k.a the parent of the child at
        ## rowIndex
        #print("this DomItem localName:", self._domNode_.localName())
        
        #print("rowIndex: ", rowIndex) # row Index is relative to this node !!!
        
        
        ## if rowIndex found as a key in the _children_ dictionary then return 
        ## the corresponding DomItem
        #if rowIndex in self._children_:
            #childItem = self._children_[rowIndex]
            ##return self._children_[rowIndex] # returned cached wrapper if it exists
        
        ## if rowIndex is positive AND the wrapped QDomNode 'node' reports to have at least
        ## 'rowIndex+1' children (indices are 0-based !!!) then wrap the child of the wrapped 
        ## node at the given rowIndex in a DomItem, add it to the _children_ cache, and 
        ## then return it
        ## NOTE: this CANNOT overwrite any existing child at rowIndex because
        ## NOTE: if there was one it would have been returned by now
        #elif rowIndex >= 0 and rowIndex < self._domNode_.childNodes().count():
            #childNode = self._domNode_.childNodes().item(rowIndex) #  get the child node of the wrapped QDomNode 'node', at index 'rowIndex'
            #childItem = DomItem(childNode, rowIndex, self) # wrap that childNode in a DomItem
            #self._children_[rowIndex] = childItem # then add it to the cache
            ##return childItem # and then return it.
        #else:
            #childItem = None
            ##return None
            
        #if childItem is not None:
            #print("childItem nodeName: ", childItem._domNode_.nodeName())
            #print("childItem localName: ", childItem._domNode_.nodeName())

        #return childItem
    
        # END alternate code for debugging
    
    
    def parent(self):
        return self._parent_

    def node(self):
        ''' Returns the wrapped QtXml.QDomNode
        '''
        return self._domNode_

    def row(self):
        return self._rowNumber_

# 2016-08-16 23:56:21
# NOTE: QAbstractItemModel has nothing to do with XML; it just creates
# a data mode for the underling QDomDocument
# TODO: replace QDomDocument with QXmlStreamReader (QtCore)
class GenericDomModel(QtCore.QAbstractItemModel):
    '''Read-only DOM model
    
    Inherits QtCore.QAbstractItemModel
    
    WARNING: This uses classes from QtXml which is being DEPRECATED
    
    '''
    def __init__(self, document: (QtXml.QDomDocument, type(None)) = None, parent=None):
        ''' Constructor for GenericDomModel
        
        Arguments:
        
        document -- QtXml.QDomDocument; the actual DOM document that becomes the 
                    root item of this model -- can be empty (i.e. a default constructed
                    QtXml.QDomDocument); optional, default is None, which means in effect
                    the instance will contain an empty QtXml.QDomDocument
                    
        parent   -- QtCore.QObject parent object (optional, default is None)
        '''
        super().__init__(parent)
        
        if document is None:
            document = QtXml.QDomDocument()

        self.domDocument = document
        
        # also set the root item as the DOM document (which, again, it might be empty)
        self.rootItem = DomItem(self.domDocument, 0) # row is 0 because root has no siblings
        
    def data(self, index, role):
        '''
        Arguments:
        
        index -- QtCore.QModelIndex 
        role  -- int
        
        Returns a str or None
        
        '''
        
        if not index.isValid():
            return None # in C++ this is a QVariant()
        
        if role != QtCore.Qt.DisplayRole:
            return None # in C++ this is a QVariant()
        
        item = index.internalPointer()
        
        node = item.node() # in C+ this is a QtXml.QDomNode
        
        #print("in GenericDomModel.data:")
        #print("node name: ", node.nodeName())
        #print("node local name: ", node.localName())
        #print("node attributes count: ", node.attributes().count())
        
        attributes = list() # in C++ this is a QStringList
        
        attributeMap = node.attributes()
        
        if index.column() == 0:
            return node.nodeName()
        
        elif index.column() == 1:
            for i in range(attributeMap.count()):
                attribute = attributeMap.item(i)
                attributes.append(''.join((attribute.nodeName(), '="', attribute.nodeValue(), '"')))
                
            return ' '.join(attributes)
        
        elif index.column() == 2:
            return ' '.join(node.nodeValue().split('\n'))
            #return ' '.join(node.nodeValue().splitlines(False))
        
        else:
            return None # in C++ this is a QVariant()
    
    def flags(self, index):
        '''
        Arguments:
        index  -- QtCore.QModelIndex (C++ const reference)
        
        Returns QtCore.Qt.ItemFlags
        '''
        
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
            #return 0 
        
        # 2016-08-14 17:39:30
        # NOTE: here, the simpledommodel.py in PyQt5 returns:
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
    
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        ''' Provides a horizontal header, as the model is intended for use in a 
        tree view. 
        
        Column headers are:
        
        Column:     Column Name:    Meaning:
        ------------------------------------
        0           Name            name of the node (element)
        1           Attributes      element attributes
        2           Value           node values
        
        Arguments:
        section     -- int -- effectively, the column number
        orientation -- QtCore.Qt.Orientation
        role        -- int (optional, default is QtCore.Qt.DiplayRole)
        
        Returns a string (when section is 0..2) or None
        '''
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Name"
            
            elif section == 1:
                return "Attributes"
            
            elif section == 2:
                return "Value"
            
            else:
                return None # in C++ this is a QtCore.QVariant()
            
        return None # in C++ this is a QtCore.QVariant()
    
    def index(self, row, column, parent=QtCore.QModelIndex()):
        ''' Returns the QModelIndex for the item with the given row, column and 
        parent in the model.
        
        Arguments:
        row    -- int
        column -- int
        parent -- QtCore.QModelIndex (optional, gets a default constructed value)
       
        Returns a QtCore.QModelIndex
        '''
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer() # isn't this a sip.voidptr?
            
        childItem = parentItem.child(row)
        
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()
    
    def parent(self, child):
        ''' Returns the parent QModelIndex of the child QModelIndex.
        
        Arguments:
        child -- QtCore.QModelIndex
        
        Returns a QtCore.QModelIndex
        '''
        
        if not child.isValid():
            return QtCore.QModelIndex()
        
        childItem = child.internalPointer()
        
        parentItem = childItem.parent()
        
        if not parentItem or parentItem == self.rootItem:
            return QtCore.QModelIndex()
        
        return self.createIndex(parentItem.row(), 0, parentItem)
    
    def rowCount(self, parent=QtCore.QModelIndex()):
        ''' Returns the row count of this or its parent model index.
        
        Arguments:
        parent -- QtCore.QModelIndex (optional, gets a default constructed value)
        
        Returns an int
        '''
        
        if parent.column() > 0:
            return 0
        
        if not parent.isValid():
            parentItem = self.rootItem
            
        else:
            parentItem = parent.internalPointer()
            
        #return parentItem.rowCount()
        return parentItem.node().childNodes().count()
            
    def columnCount(self, parent=QtCore.QModelIndex()):
        ''' Returns the column count of this or its parent model index.
        
        Arguments:
        parent -- QtCore.QModelIndex (optional, gets a default constructed value)
        
        Returns an int
        '''
        
        return 3 # TODO revisit this !!! find out how many columns are there -- should there be only three?
    
class XMLViewer(ScipyenViewer):
    '''WARNING: This uses classes from QtXml which is being DEPRECATED
     2016-09-29 12:14:25 TODO FIXME: 
     problems with converting utf-8 characters => when saving document to file
     results in invalid XML 
    '''
    sig_activated = pyqtSignal(int)
    closeMe  = pyqtSignal(int)
    supported_types = (xmlutils.xml.dom.minidom.Document, xmlutils.xml.etree.ElementTree.Element, QtXml.QDomNode, QtXml.QDomDocument, str)
    view_action_name = "XML Object"
        
    def __init__(self, data: (xml.etree.ElementTree.Element, xml.dom.minidom.Document, QtXml.QDomNode, QtXml.QDomDocument, str, type(None)) = None, 
                 parent: (QtWidgets.QMainWindow, type(None)) = None, 
                 pWin: (QtWidgets.QMainWindow, type(None))= None, ID:(int, type(None)) = None,
                 win_title: (str, type(None)) = None, doc_title: (str, type(None)) = None,
                 processNameSpaces=True, *args, **kwargs) -> None:
        ''' Constructor for XMLViewer
        
        Arguments:  
            data -- a well formed XML string, a QtXml.QDomDocument, or QtXml.QDomNode, or None
                            (optional, default is None)
                            
            processNameSpaces -- boolean, optional (default is True) -- only used when xmltext
                            is a string and indicates to the underlying DOM document whether to
                            process namespaces (True) or not (False)
        '''
        super().__init__(data=data, parent=parent, pWin=pWin, ID = ID, win_title=win_title, doc_title=doc_title, *args, **kwargs)

        self.processNS = processNameSpaces
        
    def _configureGUI_(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction("&Save As...", self.saveAsFile, "Ctrl+Shift+S")
        
        # contruct a tree view
        self._docViewer_ = QtWidgets.QTreeView(self)
        
        ## construct a generic DOM _docModel_ on an empty DOM document
        #self._docModel_ = GenericDomModel(QtXml.QDomDocument(), self)
        ## and bind it to the generic DOM _docModel_ (essentially, a tree data _docModel_)
        #self._docViewer_.setModel(self._docModel_)

        self.setCentralWidget(self._docViewer_)
        
    def _set_doc_(self, data: (QtXml.QDomNode, QtXml.QDomDocument)):
        ''' Sets the DOM document 'data' as the XML document to be shown
        '''
        # construct a new generic DOM _docModel_ on this document
        newModel = GenericDomModel(data, self)
        
        # then set this newly constructed DOM _docModel_ as the underlying _docModel_
        # in the tree viewer
        self._docViewer_.setModel(newModel)
        
        # also assign this _docModel_ to the instance variable
        self._docModel_ = newModel
        
    def _set_data_(self, data: (xml.etree.ElementTree.Element, xml.dom.minidom.Document, QtXml.QDomNode, QtXml.QDomDocument, str, type(None)),
                   *args, **kwargs):
        ''' Set the xml document 'data' as the DOM document of the underlying DOM _docModel_
            associated with the tree view
        
        '''
        try:
            if isinstance(data, str):
                document = QtXml.QDomDocument() # Create an empty DOM document
                                                # the populate it with the string data.
                                                # At this point, 'data' must be a string
                                                # representation of an XML document
                                                # otherwise setContent will return False.
                                                # NOTE: this does not check whether 'data'
                                                # contains a well-formed XML document -- I think...
                                                
                if document.setContent(data, self.processNS):
                    self._set_doc_(document)    # if the DOM document has been successfully
                                                # populated by the data str, then set it as 
                                                # the document to be shown
                                                
                    self._data_ = data
                    
            elif isinstance(data, QtXml.QDomDocument) and not data.isNull():
                self._set_doc_(data)
                self._data_ = data
                    
            elif isinstance(data, QtXml.QDomNode) and not data.isNull():
                if data.isDocument():
                    self._set_doc_(data.toDocument())
                    
                else: # deep import of a non-document QDomNode
                    document =  QtXml.QDomDocument()
                    document.importNode(data, True)
                    self._set_doc_(document)
                    
                self._data_ = data
                
            elif isinstance(data, xml.dom.minidom.Document):
                document = QtXml.QDomDocument()
                if document.setContent(data.toprettyxml(), self.processNS):
                    self._set_doc_(document)
                    self._data_ = data
                
            elif isinstance(data, xml.etree.ElementTree.Element):
                document = QtXml.QDomDocument()
                docString= ET.tostring(data, encoding="unicode")
                if document.setContent(docString, self.processNS):
                    self._set_doc_(document)
                    self._data = data
                #print(docString)
                #self._set_data_(docString)
                
        except Exception as e:
            traceback.print_exc()
            
        if kwargs.get("show", True):
            self.activateWindow()
            
    def saveAsFile(self):
        if self._docModel_.domDocument.isNull():
            return
        
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save XML Document", filter="XML files (*.xml)")
        
        #print("filePath: ", filePath)
        #print("filePath is None: ", filePath is None)
        #if filePath is not None:
            #print("filePath is empty: ", len(filePath) == 0)
            
        if len(filePath) > 0:
            outputXmlFile = QtCore.QFile(filePath)
            if outputXmlFile.open(QtCore.QFile.WriteOnly | QtCore.QFile.Truncate):
                out = QtCore.QTextStream(outputXmlFile)
                self._docModel_.domDocument.save(out,4, QtXml.QDomNode.EncodingFromDocument)
                
