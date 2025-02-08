# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathlib, urllib, warnings, subprocess, traceback
import inspect, platform, collections
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy import QtXml # not sure which one is more suitable: this or xml.dom.minidom?
# QtXml is more Qt-ish (so probably better to port from KBookmarks framework)
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from enum import Enum, IntEnum
from xml.dom import minidom
from functools import (singledispatch, singledispatchmethod)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

def metaDataKDEOwner() -> str:
    return "http://www.kde.org"

def metaDataOwner() -> str:
    return "https://github.com/ctigaret/scipyen"

def metaDataFreedesktopOwner() -> str:
    return "http://freedesktop.org"

def metaDataMimeOwner() -> str:
    return "http://www.freedesktop.org/standards/shared-mime-info"

def xbelMimetype() -> str:
    return "application/x-xbel"

# ### BEGIN NOTE: 2025-02-08 22:42:02 Not sure I really need all this
# # ### BEGIN NOTE 2025-02-08 22:36:25 TODO
# # revisit this if willing to implement for xml.dom.mindom API as well
# # @singledispatch
# # def cd(node:typing.Any, name:str, create:bool, qxml:bool=False):
# #     raise NotImplementedError()
# # 
# # @cd.register(minidom.Node)
# # def _(node:minidom.Node, name:str, create:bool, qxml:bool=False):
# #     raise NotImplementedError()
# #     
# # @cd.register(QtXml.QDomNode)
# # def _(node:QtXml.QDomNode, name:str, create:bool, qxml:bool=True):
# # ### END   NOTE 2025-02-08 22:36:25 TODO
# 
# def cd(node:QtXml.QDomNode, name:str, create:bool) -> QtXml.QDomNode:
#     subnode = node.namedItem(name)
#     if create and subnode.isNull():
#         subnode = node.ownerDocument().createElement(name)
#         node.appendChild(subnode)
#         
#     return subnode
# 
# def cd_or_create(node:QtXml.QDomNode, name:str) -> QtXml.QDomNode:
#     return cd(node, name, True)
# 
# def get_or_create_text(node: QtXml.QDomNode) -> QtXml.QDomText:
#     subnode = node.firstChild()
#     if subnode.isNull():
#         subnode = node.ownerDocument()
    
# ### END   NOTE: 2025-02-08 22:42:02 Not sure I really need all this

class BookmarkGroup:pass

class Bookmark(QtCore.QObject):
    def __init__(self, element:typing.Optional[typing.Union[minidom.Element, QtXml.QDomElement]=None):
        super().__init__(self)
        self._element_ = element
        
        
    
