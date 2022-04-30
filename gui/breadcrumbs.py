import typing, pathlib
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType


class BreadCrumbsWidget(QtWidgets.QWidget):
    
    def __init__(self, directory:typing.Optional[typing.Union[str, pathlib.Path]]=None, 
                 parent:typing.optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0,0,0,0)
        
        
        #if 
    
