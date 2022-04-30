import typing, pathlib
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType

from core import desktoputils


class BreadCrumbsWidget(QtWidgets.QWidget):
    
    def __init__(self, url:typing.Optional[typing.Union[str, pathlib.Path, QtCore.QUrl]]=None, 
                 parent:typing.optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0,0,0,0)
        
        if isinstance(url, QtCore.QUrl):
            if url.isLocalFile():
                self._url = url
            else:
                self._url = QtCore.QUrl() # only local files are supported
            
        elif isinstance(url, pathlib.Path):
            self._url = QtCore.QUrl(url.as_uri())
            
        elif isinstance(url, str):
            # check for sanity
            p = pathlib.Path(url)
            if not p.is_absolute():
                if p.parts[0].endswith(":"):
                    # this is the url schema
                    self._url = QtCore.QUrl(url)
                else:
                    self._url = QtCore.QUrl(pathlib.Path((os.sep,) + p.parts[1:]).as_uri())
            else:
                self._url = QtCore.QUrl(p.as_uri())
            
        else:
            self._url = QtCore.QUrl()
            
        self._setupComponents()
        
        
    def _setupComponents(self):
        is self._url.isEmpty():
            return
        
        urlpath = self._url.path()
        
        user_places = desktoputils.get_user_places()
        
        file_system_user_places = dict((k,v) for k,v in user_places.items() if v["url"].startswith("file"))
        
        
        
        
    
