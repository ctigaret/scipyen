"""Implementation of breadcrumbs navigation

Under development !!!
"""
from enum import Enum
import typing

#### BEGIN PyQt5 modules
from PyQt5 import (QtCore, QtGui, QtWidgets, QtXmlPatterns, QtXml, QtSvg,)
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ENUMS, Q_FLAGS, pyqtProperty,)
from PyQt5.uic import loadUiType
#### END PyQt5 modules

class BreadcrumbTarget(Enum):
    MakeBreadcrumbSelectionInOther = enum.auto()
    MakeBreadcrumbSelectionInSelf = enum.auto()
    
class AdditionalRoles(Enum):
    UrlRole = 0x069CD12B #, /// @see url(). roleName is "url".
    HiddenRole = 0x0741CAAC #, /// @see isHidden(). roleName is "isHidden".
    SetupNeededRole = 0x059A935D #, /// @see setupNeeded(). roleName is "isSetupNeeded".
    FixedDeviceRole = 0x332896C1 #, /// Whether the place is a fixed device (neither hotpluggable nor removable). roleName is "isFixedDevice".
    CapacityBarRecommendedRole = 0x1548C5C4 #, /// Whether the place should have its free space displayed in a capacity bar. roleName is "isCapacityBarRecommended".
    GroupRole = 0x0a5b64ee #, ///< The name of the group, for example "Remote" or "Devices". @since 5.40. roleName is "group".
    IconNameRole = 0x00a45c00 #, ///< @since 5.41 @see icon(). roleName is "iconName".
    GroupHiddenRole = 0x21a4b936 #, ///< @since 5.42 @see isGroupHidden(). roleName is "isGroupHidden".
    TeardownAllowedRole = 0x02533364 #, ///< @since 5.91 @see isTeardownAllowed(). roleName is "isTeardownAllowed".
    
class GroupType(Enum):
    PlacesType = enum.auto()
    RemoteType = enum.auto()
    RecentlySavedType = enum.auto()
    SearchForType = enum.auto()
    DevicesType = enum.auto()
    RemovableDevicesType = enum.auto()
    UnknownType = enum.auto()
    TagsType = enum.auto()
    
    
class BreadcrumbSelectionModel(QtCore.QItemSelectionModel):
    # NOTE: 2022-04-01 23:39:02 
    # NOT used by kurlnavigator !?!
    def __init__(self, selectionModel:QtCore.QItemSelectionModel, 
                 direction:BreadcrumbTarget = BreadcrumbTarget.MakeBreadcrumbSelectionInSelf,
                 parent:typing.Optional[QtCore.QObject] = None):
        
        # these below are from KBreadcrumbSelectionModelPrivate
        self.m_includeActualSelection = True
        self.m_showHiddenAscendantData = False
        self.m_ignoreCurrentChanged = False
        self.m_selectionDepth= -1
        self.m_direction = direction
        self.m_selectionModel = selectionModel
        
        if self.m_direction != BreadcrumbTarget.MakeBreadcrumbSelectionInSelf:
            self.m_selectionModel.selectionChanged.connect(self.sourceSelectionChanged)
            
        self.m_selectionModel.model().layoutChanged.connect(self.syncBreadcrumbs)
        self.m_selectionModel.model().modelReset.connect(self.syncBreadcrumbs)
        self.m_selectionModel.model().rowsMoved.connect(self.syncBreadcrumbs)
        
        super().__init__(m_selectionModel.model(), parent)
    
    # TODO: 2022-04-01 22:00:33
    # reimplement using single dispatch
    def getBreadcrumbSelection(self, index:typing.Union[QtCore.QModelIndex, QtCore.QItemSelection]) -> QtCore.QItemSelection:
        breadcrumbSelection = QtCore.QItemSelection() # empty selection
        
        if isinstance(index, QtCore.QModelIndex):
            if self.m_includeActualSelection:
                breadcrumbSelection.append(QtCore.QItemSelectionRange(index))
                
            parent = index.parent()
            
            sumBreadcrumbs = 0
            
            includeAll = self.m_selectionDepth < 0
            
            while(parent.isValid() and (includeAll || sumBreadcrumbs < self.m_selectionDepth)):
                breadcrumbSelection.append(QtCore.QItemSelectionRange(parent))
                parent = parent.parent()
                
        elif isinstance(index, QtCore.QItemSelection):
            if self.m_includeActualSelection:
                breadcrumbSelection = index
                
            for item in index:
                parent = item.parent()
                if breadcrumbSelection.contains(parent):
                    continue
                sumBreadcrumbs = 0
                includeAll = self.m_selectionDepth < 0
                
                while(parent.isValid() and (includeAll || sumBreadcrumbs < self.m_selectionDepth)):
                    breadcrumbSelection.append(QtCore.QItemSelectionRange(parent))
                    parent = parent.parent()
                    
                    if breadcrumbSelection.contains(parent):
                        break
                    
                    sumBreadcrumbs += 1
                    
        else:
            raise TypeError(f"Expecting a QModelIndex or QItemSelection; got {type(index).__name__} instead")
            

        return breadcrumbSelection
    
    
    @pyqtSlot
    def sourceSelectionChanged(self, selected:QtCore.QItemSelection, deselected:QtCore.QItemSelection):
        deselectedCrumbs = self.getBreadcrumbSelection(deselected)
        selectedCrumbs = self.getBreadcrumbSelection(selected)
        
        removed = deselectedCrumbs
        
        for rng in selectedCrumbs:
            removed.removeAll(rng)
            
        added = selectedCrumbs
        
        for rng in deselectedCrumbs:
            added.removeAll(rng)
            
        if not removed.isEmpty():
            self.select(removed, QtCore.QItemSelectionModel.Deselect)
            
        if not added.isEmpty():
            self.select(added, QtCore.QItemSelectionModel.Select)
        
    def syncBreadcrumbs(self):
        self.select(self.m_selectionModel.selection(), QtCore.QItemSelectionModel.ClearAndSelect)
    
    # make property - but propagate in user classes
    def isActualSelectionIncluded(self) -> bool:
        return self.m_includeActualSelection
        
    
    # make property settery - but propagate in user classes
    def setActualSelectionIncluded(self, val:bool):
        self.m_includeActualSelection = val is True
    
    # TODO: 2022-04-01 22:15:32
    # reimplement using single dispatch
    def select(self, index_selection:typing.Union[QtCore.QModelIndex, QtCore.QItemSelection], 
               command:QtCore.QItemSelectionModel.Selectionflags):
        
        if isinstance(index_selection, QtCore.QModelIndex):
            if self.m_ignoreCurrentChanged:
                self.m_ignoreCurrentChanged = False
                return
            if self.m_direction == BreadcrumbTarget.MakeBreadcrumbSelectionInOther:
                self.m_selectionModel.select(self.getBreadcrumbSelection(index_selection), command)
                super().select(index_selection, command)
            else:
                self.m_selectionModel.select(index_selection, command)
                super().select(self.getBreadcrumbSelection(index_selection), command)
                
        elif isinstance(index_selection, QtCore.QItemSelection):
            bcc = self.getBreadcrumbSelection(index_selection)
            if self.m_direction == BreadcrumbTarget.MakeBreadcrumbSelectionInOther:
                self.m_selectionModel.select(index_selection, command)
                super().select(bcc, command)
            else:
                self.m_selectionModel.select(bcc, command)
                super().select(index_selection, commad)
        else: 
            raise TypeError(f"Expecting a QModelIndex or QItemSelection; got {type(index_selection).__name__} instead")
    
    # make property - but propagate in user classes
    def breadcrumbLength(self) -> int:
        return self.m_selectionDepth
    
    # make property setter - but propagate in user classes
    def setBreadcrumbLength(self, val:int):
        self.m_selectionDepth = val
        
class FilePlacesModel(QtCore.QAbstractItemModel):
    def __init__(self, alternativeApplicationname:typing.Optional[str] = None,
                 parent:typing.Optionak[QtCore.QObject] = None):
    pass
    
class UrlNavigator(QtWidgets.QWidget):
    """Port of KDE's KUrlNavigator
     TODO: 2022-04-01 23:42:57
     Consider implementing dolphinurlnavigator code
     FIXME: How to deal with KDE's solid classes (i.e. devices) and KBookmark?
     TODO: Perhaps this required detecting if running under a KDE desktop
     which will fail under windows.
    """
    def __init__(self, parent:QtWidgets.QWidget):
        pass
    
    def url(self, index:QtCore.QModelIndex) -> QtCore.QUrl:
        pass
    
    def setupNeeded(self, index:QtCore.QModelIndex) -> bool:
        pass
    
    def isTearDownAllowed(self, index:QtCore.QModelIndex) -> bool:
        pass
        
    def icon(self, index:QtCore.QModelIndex) -> QtGui.QIcon:
        pass
    
    def text(self, index:QtCore.QModelIndex) -> str:
        pass
    
    def isHidden(self, index:QtCore.QModelIndex) -> bool:
        pass
    
    def isGroupHidden(self, type:typing.Union[GroupType, QtCore.QModelIndex]) -> bool:
        pass
    
    def isDevice(self, index:QtCore.QModelIndex) -> bool:
        pass
    
    def deviceForIndex(self, index:QtCore.QModelIndex) -> bool:
        raise NotImplementedError
    
    def bookmarkForIndex(self, index:QtCore.QModelIndex) -> bool:
        raise NotImplementedError
    
    def bookmarkForUrl(self, searchUrl:QtCore.QUrl) -> bool:
        raise NotImplementedError
    
    def groupType(self, index:QtCore.QModelIndex) -> GroupType:
        pass
    
    
    
