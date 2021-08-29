"""Various helpers for GUI
"""
import typing, warnings
from PyQt5 import (QtCore, QtWidgets, QtGui)
from gui.painting_shared import (FontStyleType, standardQtFontStyles, 
                                 FontWeightType, standardQtFontWeights)

def get_elided_text(s,w):
    fm = QtWidgets.QApplication.fontMetrics()
    return fm.elidedText(s, QtCore.Qt.ElideRight, w)

def get_text_width(s, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    fm = QtWidgets.QApplication.fontMetrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.width()

def get_font_style(val:typing.Union[str, FontStyleType]) -> typing.Union[int, QtGui.QFont.Style]:
    """Returns an int or a QtGui.QFont.Style enum value
    
    Always returns QtGui.QFont.StyleNormal if val has wrong type or value.
    
    Parameter:
    ==========
    
    val: int (0,1,2)
    
         str = a font style name (case-sensitive), one of :
            StyleNormal
            StyleItalic
            StyleOblique
            
        QtGui.QFont.Style enum value (see Qt documentation for details)
    
    """
    
    if isinstance(val, str) and len(val.strip()):
        ret = standardQtFontStyles.get(val, None) # --> int or None if not found
        if ret is None:
            return QtGui.QFont.StyleNormal
        
        return ret # --> int
        
    elif isinstance(val, int):
        if val not in standardQtFontStyles.values():
            # NOTE: 2021-08-29 10:25:46
            # this os different from Qt behavioru where if font.setTyle() is 
            # passed an int val < 0 or > 2 it assigns the largest Style value 
            # (oblique)
            return QtGui.QFont.StyleNormal
        
        return val # OK to feed an int to font.setStyle()
        
    elif isinstance(val, QtGui.QFont.Style):
        return val
    
    else:
        return QtGui.QFont.StyleNormal
    
            
def get_font_weight(val:typing.Union[str, FontWeightType]) -> typing.Union[int, QtGui.QFont.Weight]:
    """Returns an int or a QtGui.QFont.Weight eunm value
    
    Always returns QtGui.QFont.Normal if val has wrong type or value
    """
    
    if isinstance(val, str) and len(val.strip()):
        ret = standardQtFontWeights.get(val, None)
        if ret is None:
            return QtGui.QFont.Normal
        
        return ret
    
    elif isinstance(val, int):
        if val not in standardQtFontWeights.values():
            return QtGui.QFont.Normal
        
        return val
    
    elif isinstance(val, QtGui.QFont.Weight):
        return val
    
    else:
        return QtGui.QFont.Normal
    
    
