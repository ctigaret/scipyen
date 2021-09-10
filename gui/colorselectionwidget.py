import os, typing
from itertools import (cycle, repeat)

from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty)
from PyQt5.uic import loadUiType as __loadUiType__

from .colorwidgets import (ColorComboBox, ColorPushButton,)
from .scipyen_colormaps import(paletteQColor, standardQColor, standardPalette,)
from . import quickdialog

from .stylewidgets import PenComboBox

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class ColorSelectionWidget(QtWidgets.QWidget):
    """Combines a ColorComboBox and a ColorPushButton in the same widget
    """
    colorChanged = pyqtSignal(QtGui.QColor, name="colorChanged")
    
    def __init__(self, color:typing.Optional[QtGui.QColor]=None,
                 defaultColor:typing.Optional[QtGui.QColor]=None,
                 palette:typing.Optional[typing.Union[dict,list, tuple, str]]=None,
                 useDefaultColor:bool=True,
                 alphaChannelEnabled:bool = True, 
                 transparentPixmap:typing.Optional[QtGui.QPixmap]=None,
                 keepAlphaOnDropPaste:bool=False,
                 parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._color = color

        self._colorPushButton = ColorPushButton(color=color, 
                                                defaultColor=defaultColor,
                                                alphaChannelEnabled=alphaChannelEnabled,
                                                useDefaultColor=useDefaultColor,
                                                keepAlphaOnDropPaste=keepAlphaOnDropPaste,
                                                transparentPixmap=transparentPixmap,
                                                parent=self)
        
        self._colorComboBox = ColorComboBox(color,
                                            palette=palette,
                                            alphaChannelEnabled=alphaChannelEnabled,
                                            transparentPixmap=transparentPixmap,
                                            parent=self)
        
        self._configureUI_()
        
    def _configureUI_(self):
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(2)
        for w in (self._colorComboBox, self._colorPushButton):
            self._layout.addWidget(w)
            
        # NOTE: required when self._color is None
        if not self._color:
            sigblock = QtCore.QSignalBlocker(self._colorPushButton)
            self._colorPushButton.color = self._colorComboBox.color
            self._color = self._colorComboBox.color

        self._colorComboBox.activated.connect(self._colorPushButton.slot_setColor)
        self._colorComboBox.activated.connect(self.colorChanged)
        self._colorPushButton.changedColor.connect(self._colorComboBox.slot_setColor)
        self._colorPushButton.changedColor.connect(self.colorChanged)
            
        
    @pyqtSlot(QtGui.QColor)
    def slot_setColor(self, color):
        self._color = QtGui.QColor(color)
        sigblock = QCore.QSignalBlocker(self._colorPushButton)
        self._colorPushButton.color = color
        self._colorComboBox._setCustomColor(color)
        
        
    @property
    def color(self):
        return QtGui.QColor(self._color)
    
    @color.setter
    def color(self, value:QtGui.QColor):
        if isinstance(value, QtGui.QColor) and value.isValid():
            self._color = color
            sigblock = QCore.QSignalBlocker(self._colorPushButton)
            self._colorPushButton.color = color
            self._colorComboBox._setCustomColor(color)
            self.colorChanged.emit(self._color)
            
    @property
    def palette(self):
        return self._colorComboBox.colors
    
    @palette.setter
    def palette(self, value):
        self._colorComboBox.colors = palette
        
    def validate(self):
        return True
        
def quickColorDialog(parent:typing.Optional[QtWidgets.QWidget]=None, 
                     title:typing.Optional[str]=None,
                     labels:typing.Optional[typing.Union[dict, typing.List[str]]]=None,
                     colors:typing.Optional[typing.List[typing.Union[str, QtGui.QColor]]] = None) -> dict:
    
    dlg = quickdialog.QuickDialog(parent=parent, title=title)
    
    if isinstance(labels, (tuple, list)):
        if len(labels) == 0:
            if isinstance(colors, (tuple, list)) and len(colors):
                lbl_col = dict(("Color%i" % k, color) for k, color in enumerate(colors))
                
            else:
                lbl_col = {"Select color": QtGui.QColor()}
                
        else:
            if isinstance(colors, (tuple, list)) and len(colors):
                if  len(labels) < len(colors):
                    lbl = list(labels)
                    lbl.extend("color%i" % k for k in range(len(labels), len(colors)))
                    lbl_col = dict(zip(lbl, colors))
                elif len(labels) > len(colors):
                    clr = list(colors)
                    cc = cycle(cl)
                    clr.extend(next(cc) for k in range(len(colors), len(labels)))
                    lbl_col = dict(zip(labels, clr))
                else:
                    lbl_col = dict(zip(labels, colors))
                    
            else:
                lbl_col = dict(zip(labels, repeat(QtGui.QColor(), len(labels))))
                
    elif isinstance(labels, dict):
        lbl_col = labels
        
    else:
        lbl_col = {"Select color": QtGui.QColor()}
    
    group = quickdialog.HDialogGroup(dlg)
        
    colorselwidgets = dict()
    
    for label, color in lbl_col.items():
        vgroup = quickdialog.VDialogGroup(group)
        colorselwidgets[label] = ColorSelectionWidget(color=color, parent=vgroup)
        vgroup.addWidget(colorselwidgets[label])
        group.addWidget(vgroup)
        
    dlg.addWidget(group)
    
    dlg.resize(-1, -1)
        
    dlgret = dlg.exec()
    
    ret = dict()
    
    if dlgret:
        ret = dict((lbl, w.color) for lbl, w in colorselwidgets.items())
        
    return ret
        
    
