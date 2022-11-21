"""Various helpers for GUI
"""
import typing, warnings, math
from core.utilities import get_least_pwr10
from PyQt5 import (QtCore, QtWidgets, QtGui)
from gui.painting_shared import (FontStyleType, standardQtFontStyles, 
                                 FontWeightType, standardQtFontWeights)

import quantities as pq
from gui.pyqtgraph_patch import pyqtgraph as pg

class UnitsStringValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        super(UnitsStringValidator, self).__init__(parent)
        
    def validate(self, s, pos):
        try:
            u = eval("1*%s" % (s[0:pos]), pq.__dict__)
            return QtGui.QValidator.Acceptable
        
        except:
            return QtGui.QValidator.Invalid
        
def getPlotItemDataBoundaries(item:pg.PlotItem):
    """Calculates actual data bounds (data domain, `X`, and data range, `Y`)
    NOTE: 2022-11-21 16:11:36
    Unless there is data plotted, this does not rely on PlotItem.viewRange()  
    because this extends outside of the data domain and data range.
    """
    plotDataItems = [i for i in item.listDataItems() if isinstance(i, pg.PlotDataItem)]
    if len(plotDataItems) == 0: # no data plotted
        [[xmin, xmax], [ymin,ymax]] = item.viewRange()
    else:
        mfun = lambda x: -np.inf if x is None else x
        pfun = lambda x: np.inf if x is None else x
        
        xmin = min(map(mfun, [min(p.xData) for p in plotDataItems]))
        xmax = max(map(pfun, [max(p.xData) for p in plotDataItems]))
                
        ymin = min(map(mfun, [min(p.yData) for p in plotDataItems]))
        ymax = max(map(pfun, [max(p.yData) for p in plotDataItems]))
            
    return [[xmin, xmax], [ymin, ymax]]
    
        
def get_QDoubleSpinBox_params(x:typing.Sequence):
    """Return stepSize and decimals for a QDoubleSpinBox given x.

    x is a sequence of numbers
    """
    dd = get_least_pwr10(x)
    if dd < 0:
        return (abs(dd), 10**dd)
    return (0, 1)
    
def csqueeze(s:str, w:int):
    """Returns text elided to the right
    """
    if len(s) > w and w > 3:
        part = (w-3)/2
        return s[0:part] + "get_QDoubleSpinBox_params..."
    return s

def rsqueeze(s:str, w:int):
    """Returns text elided to the right
    """
    if len(s) > w:
        part = w - 3
        return s[0:part] + "..."
    return s

def lsqueeze(s:str, w:int):
    """Returns text elided to the left
    """
    if len(s) > w:
        part = w - 3
        return "..." + s[part:]
    return s
        
def get_elided_text(s:str, w:int):
    fm = QtWidgets.QApplication.fontMetrics()
    return fm.elidedText(s, QtCore.Qt.ElideRight, w)

def get_text_width(s:str, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    fm = QtWidgets.QApplication.fontMetrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.width()

def get_text_height(s:str, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    fm = QtWidgets.QApplication.fontMetrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.height()

def get_text_width_and_height(s:str, flags=QtCore.Qt.TextSingleLine, tabStops = 0, tabArray=None):
    fm = QtWidgets.QApplication.fontMetrics()
    sz = fm.size(flags, s, tabStops=tabStops, tabArray=tabArray)
    return sz.width(), sz.height()

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
    
    
