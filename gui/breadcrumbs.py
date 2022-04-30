import typing, pathlib
from urllib.parse import urlparse, urlsplit
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
            elements = urlsplit(url)
            if len(elements.scheme):
                self._url = QtCore.QUrl(url)
            else:
                p = pathlib.Path(elements.path)
                if not p.is_absolute():
                    self._url = QtCore.QUrl(pathlib.Path((os.sep,) + p.parts[1:]).as_uri())
                else:
                    self._url = QtCore.QUrl(p.as_uri())
                    
        else:
            self._url = QtCore.QUrl()
            
        self._setupComponents()
        
        
    def _setupComponents(self):
        is self._url.isEmpty():
            return
        
        urlpath = pathlib.Path(self._url.path())
        
        user_places = desktoputils.get_user_places()
        
        file_system_user_places = dict((k,v) for k,v in user_places.items() if urlsplit(v["url"]).scheme == "file" and v["app"] is None)
        
        candidate_places = [(len(urlsplit(v["url"]).path), k) for k,v in file_system_user_places.items() if str(urlpath).startswith(urlsplit(v["url"]).path)]
        
        longest_match = max(i[0] for i in candidate_places)
        
        place = [i[1] for i in candidate_places if i[0] == longest_match]
        
        if len(place):
            place = place[0]
            
        else:
            place = ""
            
        
    
