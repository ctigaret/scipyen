"""Various helpers for GUI
"""
from PyQt5 import (QtCore, QtWidgets)

def get_elided_text(s,w):
    fm = QtWidgets.QApplication.fontMetrics()
    return fm.elidedText(s, QtCore.Qt.ElideRight, w)

def get_text_width(s, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    fm = QtWidgets.QApplication.fontMetrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.width()
    
    
    
    
