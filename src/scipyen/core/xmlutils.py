# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


'''
Code for parsing and inspecting XML data.

Some code adapted from PyQt5 Simple DOM Model Example,
Copyright (C) 2013 Riverbank Computing Limited,
Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).

2016-08-13 09:29:11 - file created

NOTE: here are the values of the different node types in xml.dom:

xml.dom.Node.ELEMENT_NODE                   1

xml.dom.Node.ATTRIBUTE_NODE                 2

xml.dom.Node.TEXT_NODE                      3

xml.dom.Node.CDATA_SECTION_NODE             4

xml.dom.Node.ENTITY_REFERENCE_NODE          5

xml.dom.Node.ENTITY_NODE                    6

xml.dom.Node.PROCESSING_INSTRUCTION_NODE    7

xml.dom.Node.COMMENT_NODE                   8

xml.dom.Node.DOCUMENT_NODE                  9

xml.dom.Node.DOCUMENT_TYPE_NODE            10

xml.dom.Node.DOCUMENT_FRAGMENT_NODE        11

xml.dom.Node.NOTATION_NODE                 12


'''

# 2016-11-09 21:44:49
# use python3 xml module(s)
from __future__ import print_function

import sys, os, traceback, inspect, numbers
import typing
from collections import (namedtuple, OrderedDict, )

import xml.parsers.expat
import xml.etree
import xml.etree.ElementTree as ET # the default parsers in here are from xml.parsers.expat,
                                   # see documentation for xml.etree.ElementTree.XMLParser
import xml.dom
import xml.dom.minidom

from functools import singledispatch
#import abc

# 2016-09-25 21:28:37 
# add XMl text viewer, schema viewer and xquery editor

# 2016-08-16 09:30:07
# NOTE FIXME QtXml is not actively maintained anymore in Qt >= 5.5
from qtpy import (QtCore, QtWidgets, QtXml, QtGui, )
from qtpy.QtCore import (Signal, Slot, )
# NOTE: use Python re instead of QRegExp
import re

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
            
@singledispatch
def getChildren(element, eltype:int=1) -> typing.Generator:
    raise NotImplementedError(f"Fucntion does not support {type(element)} objects")

@getChildren.register(xml.dom.minidom.Element)
def _(element:xml.dom.minidom.Element, eltype:int=1) -> typing.Generator:
    """"""
    if eltype not in range(1,13):
        raise ValueError(f"'eltype' expected to be an int in the range 1⋯13; instead, got {eltype}")
    children = element.childNodes
    if len(children):
        yield from (c for c in children if c.nodeType == eltype)
    
@getChildren.register(ET.Element)
def _(element:ET.Element, eltype:int=None) -> typing.Generator:
    """"""
    yield from (c for c in element.iter())
        
        # return (c for c in children if c.nodeType == eltype)
    # chiter = element.iter()
    # return (c for c in next(chiter))
    
def elementToDict(node, eltype:int = 1):
    if eltype not in range(1,13):
        raise ValueError(f"'eltype' expected to be an int in the range 1⋯13; instead, got {eltype}")
    ret = dict()
    ret["__attributes__"] = attributesToDict(node)
    ret.update(dict(map(lambda x: (x.nodeName, elementToDict(x)), getChildren(node, eltype))))
    return ret

def attributesToDict(node):
    """Returns a dictionary with the attributes names/values
    """
    if node.attributes is None:
        return None
    
    #ret = OrderedDict()
    ret = dict()
    
    for v in node.attributes.values():
        try:
            val = eval(v.value)
        except:
            val = v.value
            
        ret[v.name] = val
        
    return ret

# def createXQuery(xmlstring, useXSLT=False):
#     ''' 
#     FIXME: when calling evaluateToString on the returned object, python crashes
#     -- why ?!?
#     
#     however, is does not crash when called inside testQuery function below
#     
#     Helper function to create an QXmlQuery (QtXmlPatterns XQuery) object on an XML document given as a string.
#     
#     Arguments:
#         
#             xmlstring = a string representation of an XML document;
#                         This string is bound to the XQuery variable $input
#                         
#             useXSLT = a boolean, optional (default: False) specifying the language
#                         the XQuery object (False: use XQuery 1.0; True: use XSLT 2.0)
#     
#     
#     Returns: an QXmlQuery object with the input XML document (as string) bound
#             to the internal variable $input,
#             
#             The language used is XQuery 1.0 (XPath), unless the useXSLT=True is passed
#             as argument.
#             
#             In either case, the XQuery uses a default (emty) namepool.
#             
#             The XQuery object has no query set, therefore is empty and invalid. 
#             
#             Before evaluating it, one must call one of the setQuery(...) methods.
#     
#     '''
#     device = QtCore.QBuffer()           # this is a QIOdevice
#     
#     device.setData(xmlstring.encode()) 
#     
#     device.open(QtCore.QIODevice.ReadOnly)
#     
#     if useXSLT:
#         xquery = QtXmlPatterns.QXmlQuery(QtXmlPatterns.QXmlQuery.XSLT20)
#     else:
#         xquery = QtXmlPatterns.QXmlQuery()
#     
#     xquery.bindVariable("input",device)
#     
#     device.close()
#     
#     return xquery
# 
# def testQuery(stringdata, querystring=None):
#     ''' test xquery on the OME XML metadata -- doesn't seem to work properly
#     '''
#     device = QtCore.QBuffer()           # this is a QIOdevice
#     
#     # pass the string to the device
#     # NOTE: support for creating a QByteArray from a Latin-1 encoded string is 
#     # deprecated in PyQt v5.4 and will be removed in v5.5
#     # therefore we call encode() function (by default uses utf-8 codec) to generate
#     # a QByteArray
#     device.setData(stringdata.encode()) 
#     
#     
#     # NOTE: alternatively:
#     #qba = QtCore.QByteArray()
#     #qba.append(stringdata.encode()) # see comment above
#     #device = QtCore.QBuffer(qba) # create the QIODevice in memory, on the QByteArray
#     
#     
#     # whichever way the QIODevice has been created, it MUST be open in ReadOnly mode
#     device.open(QtCore.QIODevice.ReadOnly)
#     
#     # create an XQuery object
#     xquery = QtXmlPatterns.QXmlQuery()
#     
#     # now we bind the xquery to the data stream from the "device"
#     xquery.bindVariable("input",device)
#     
#     # another option might be to set focus to the string data !?
#     #xquery.setFocus(stringdata)
#     
#     if querystring is None:
#         querystring = "doc($input)"
#     else:
#         querystring = "doc($input)" + querystring
#         
#     print("querystring: ", querystring)
# 
#     xquery.setQuery(querystring)
#     
#     #namePool = xquery.namePool()
#     
#     #print("namePool: ", namePool)
#     
#     #xquery.values()
#     
#     
#     if xquery.isValid():
#         xmlitems = QtXmlPatterns.QXmlResultItems()
#         xquery.evaluateTo(xmlitems)
#         
#         # without a querystring argument, the following returns a string 
#         # representation of the document node 
#         # a.k.a the root element in the OME XML metadata with its attributes and
#         # contents (i.e. children, if any) -- that is, it returns the part 
#         # of the stringdata between and including the OME start and end tags: 
#         # <OME> ... <OME/>; in other words, it skips the processing instructions header
#         # (<?xml ... ?>)
#         # 
#         # ret is basically the result of concatenating a QStringList (NOT present in PyQt5)
#         ret = xquery.evaluateToString() 
#         
#     else:
#         xmlitems = None
#         ret = None
#         print("invalid query")
#         
#     device.close()
#     
#     return ret, xmlitems
#     
#     #return (ret, xmlitems, xquery)

def testExpatParse(data, sep=None):
    def start_element(name, attrs):
        print('Element:', name, "\nAttributes: ", attrs)
        
    def end_element(name):
        print('End element:', name)
        
    def char_data(data):
        print('Character data:', repr(data))
        
    def xml_declaration(version, encoding, standalone):
        print("XML declaration version:", version, " encoding: ", encoding, " standalone: ", standalone)
        
    def start_dtd_handler(doctypeName, systemId, publicId, has_internal_subset):
        print("DocType decl: ", doctypeName, " systemId: ", systemId, "publicId: ", publicId, " has_internal_subset: ", has_internal_subset)
        
    def end_dtd_handler():
        print("done parsing element type declaration")
        
    def element_declaration(name, model):
        print("Element decl: ", name, " model: ", model)
        
    def process_instruction(target, dta):
        print("Instruction: ", target, "\ndata: ", dta)

    if sep is not None:
        p = xml.parsers.expat.ParserCreate(namespace_separator=sep)
    else:
        p = xml.parsers.expat.ParserCreate()
    
    p.ordered_attributes = 0 # default 0 => atributes parsed as a dictionary mapping names to values; 
                             # positive > 0 => attributes returned as list
    
    
    p.StartElementHandler = start_element
    #p.EndElementHandler = end_element
    p.CharacterDataHandler = char_data
    
    p.XmlDeclHandler = xml_declaration
    p.StartDoctypeDeclHandler = start_dtd_handler
    p.EndDoctypeDeclHandler = end_dtd_handler
    p.ElementDeclHandler = element_declaration
    
    p.ProcessingInstructionHandler = process_instruction
    
    p.Parse(data)
    
def testEtree(data):
    root = ET.XML(data)
    
    
    return root

def testMiniDom(data):
    domdoc  = xml.dom.minidom.parseString(data)
    
    return domdoc

# NOTE: 2016-11-10 11:02:27
# TODO: use this funtion to generate a DOM Node ONLY and return it
#       then, pass the results to a more flexible node parser
#       which should inspect attributes, child nodes, etc, get their values
#       (e.g. for text nodes/CDATA sections) and build up appropriate python objects
def parseMetadata(mdatastr):
    ''' parses OME metadata passed as string
    
        Arguments:
        
        metadatastr = string representation of an entire valid XML document
        
        returns a DOM Node (xml.dom.Node object)
    '''
    #FIXME: allow for passing string representation for element, comment, text/CDATA as well
    #       not just entire documents
    
    
    # NOTE: here are the values of the different node types in xml.dom:
    
    #xml.dom.Node.ELEMENT_NODE                   1
    
    #xml.dom.Node.ATTRIBUTE_NODE                 2
    
    #xml.dom.Node.TEXT_NODE                      3
    
    #xml.dom.Node.CDATA_SECTION_NODE             4
    
    #xml.dom.Node.ENTITY_REFERENCE_NODE          5
    
    #xml.dom.Node.ENTITY_NODE                    6
    
    #xml.dom.Node.PROCESSING_INSTRUCTION_NODE    7
    
    #xml.dom.Node.COMMENT_NODE                   8
    
    #xml.dom.Node.DOCUMENT_NODE                  9
    
    #xml.dom.Node.DOCUMENT_TYPE_NODE            10
    
    #xml.dom.Node.DOCUMENT_FRAGMENT_NODE        11
    
    #xml.dom.Node.NOTATION_NODE                 12
    
    
    # NOTE: this can be of any of the above types !!!
    domnode = xml.dom.minidom.parseString(mdata)
    
    #if domdoc.nodeType is not xml.dom.Node.DOCUMENT_TYPE:
        #print("Not an XML document")
        #return None
    
    
    
    return domnode # NOTE: for now (FIXME)

# TODO: revisit this!
def parseDOMNode(domnode):
    # NOTE: here are the values of the different node types in xml.dom:
    
    #xml.dom.Node.ELEMENT_NODE                   1
    
    #xml.dom.Node.ATTRIBUTE_NODE                 2
    
    #xml.dom.Node.TEXT_NODE                      3
    
    #xml.dom.Node.CDATA_SECTION_NODE             4
    
    #xml.dom.Node.ENTITY_REFERENCE_NODE          5
    
    #xml.dom.Node.ENTITY_NODE                    6
    
    #xml.dom.Node.PROCESSING_INSTRUCTION_NODE    7
    
    #xml.dom.Node.COMMENT_NODE                   8
    
    #xml.dom.Node.DOCUMENT_NODE                  9
    
    #xml.dom.Node.DOCUMENT_TYPE_NODE            10
    
    #xml.dom.Node.DOCUMENT_FRAGMENT_NODE        11
    
    #xml.dom.Node.NOTATION_NODE                 12
    
    
    if domnode.nodeType is xml.dom.Node.DOCUMENT_NODE:
        # the document node has only one element the root element
        # i.e. domnode.childNodes should return a list of one Element object
        # which can be retrieved by domnode.documentElement
        if not domnode.hasChildNodes():
            print("Empty XMl node!")
            return None

        domelement = domnode.documentElement # this is the root element of the document
    
    elif domnode.nodeType is xml.dom.Node.ELEMENT_NODE:
        # this is where the interesting things should take place
        
        # is this a root node?
        if domnode.parentNode.nodeType is xml.dom.Node.DOCUMENT_NODE:
            # yes, it is
            pass
        
def pythonDataToXMLElement(datakey, datavalue, parentDoc, parentNode, maxElements = 10):
    import quantities as pq
    import numpy as np
    import neo
    #from patchneo import neo
    from core.vigra_patches import vigra
    import datatypes  
    
    k_attribs = list()
    #print(datakey)
    #print(datavalue)
    vattr = parentDoc.createAttribute("value_type")
    vattr.value = str(datavalue.__class__).replace("<","").replace(">", "")
    
    if isinstance(datakey, (str, numbers.Integral)):
        #tagName = "%s" % str(datakey)
        tagName = "%s" % datakey.replace(" ", "_").replace("/","_")
        attr = parentDoc.createAttribute("key_type")
        attr.value = str(datakey.__class__).replace("<","").replace(">", "")
        #attr.value = type(datakey).__name__
        
        #print(attr.value)
        
        k_attribs.append(vattr)
        k_attribs.append(attr)
        
    else: # any  other hashable type
        k_name = ""
        if hasattr(datakey, "name"):
            k_name = datakey.name
        elif hasattr(datakey, "Name"):
            k_name = datakey.Name
        elif hasattr(datakey , "NAME"):
            k_name = datakey.NAME
        else:
            k_name = "%s object" % type(k).__name__
            
        tagName = k_name
        
        tattr = parentDoc.createAttribute("key_type")
        #tattr.value = type(datakey).__name__
        tattr.value = str(datakey.__class__).replace("<","").replace(">", "")
        
        iattr = parentDoc.createAttribute("id")
        iattr.value = id(datakey)
        
        k_attribs.append(tattr)
        k_attribs.append(iattr)
        
    #print(tagName)
        
    node = parentDoc.createElement(tagName)
    #print(node.nodeType)
    
    if len(k_attribs) > 0:
        for a in k_attribs:
            node.setAttributeNode(a)
        
    #print("to append: ", node.tagName)
    
    v_attrlist = list()
    v_tagName = type(datavalue).__name__
    v_typeattr = parentDoc.createAttribute("value_type")
    v_typeattr.value = str(datavalue.__class__).replace("<","").replace(">", "")
    v_attrlist.append(v_typeattr)
    
    if isinstance(datavalue, (str, bool, numbers.Number)):
        value_node = parentDoc.createTextNode(str(datavalue))
        node.appendChild(value_node)
        
    elif isinstance(datavalue, dict):
        for (k, v) in datavalue.items():
            pythonDataToXMLElement(k, v, parentDoc, node)
        #value_node = parentDoc.createElement(v_tagName)
        
    elif isinstance(datavalue, (tuple, list)):
        if len(datavalue) <= maxElements:
            for (k, e) in enumerate(datavalue):
                key = "%s_%d" % (type(e).__name__, k)
                pythonDataToXMLElement(key, e, parentDoc, node)
        else:
            txt = "list of %d elements" % len(datavalue)
            value_node = parentDoc.createTextNode(txt)
            node.appendChild(value_node)
        
    elif isinstance(datavalue, (vigra.filters.Kernel1D, pq.Quantity, np.ndarray)):
        if datavalue.size <= maxElements:
            value_node = parentDoc.createTextNode(datavalue.__str__())
            #value_node = parentDoc.createTextNode(str(datavalue))
            node.appendChild(value_node)
        else:
            value_node = parentDoc.createTextNode("%s%s" % (type(datavalue).__name__, str(datavalue.shape)))
            node.appendChild(value_node)
            
    else:
        value_node = parentDoc.createElement(v_tagName)
        node.appendChild(value_node)
        #for va in v_attrlist:
            #value_node.setAttributeNode(va)
    
    
    parentNode.appendChild(node)
    
    return node
        
def dictToXMLDocument(data, name=None, maxElements = 10):
    if not isinstance(data, dict):
        raise TypeError("Expecting a dict; got a %s instead" % (type(data).__name__))
    
    if name is None or not isinstance(name, str):
        cframe = inspect.getouterframes(inspect.currentframe())[1][0]
        try:
            for (k,v) in cframe.f_globals.items():
                if isinstance(v, dict):
                    if v is data and not k.startswith("_"):
                        name = k
        finally:
            del(cframe)
            
    if name is None or isinstance(name, str) and len(name.strip()) == 0:
        name = "root"
        
        
    domImpl = xml.dom.getDOMImplementation()
    
    doc = domImpl.createDocument(xml.dom.EMPTY_NAMESPACE, name, "")
    
    #print(doc.nodeType)
    #print("children: ", len(doc.childNodes))
    rootNode = doc.childNodes[0]
    #print(len(rootNode.childNodes))
    #print(rootNode.nodeType)
    
    for (k,v) in data.items():
        pythonDataToXMLElement(k, v, doc, rootNode, maxElements = maxElements)
        
    #print(len(rootNode.childNodes))
        
        
    return doc

def composeStringListForXMLElement(tagname, value):
    """Generates a list with the components of a string representation for an XML element
    
    Parameters:
    ===========
    
    tagname: str; the tag of the element
    
    value: any python data that can be represented as a str via its __repr__ function
    
    Returns:
    =======
    
    A list of string items of the following format:
    
    "<tagname>"
    "str(value)"
    "</tagname>"
    
    """
    if not isinstance(tagname, str):
        raise TypError("tagname must be a str; got %s instead" % type(tagname).__name__)
    
    ret = list()
    
    ret.append("<%s>"   % tagname )
    ret.append("%s"     % value)
    ret.append("</%s>"  % tagname)
    
    return ret
    
    
