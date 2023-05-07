class BreadCrumb(QtWidgets.QWidget):
    navigate = pyqtSignal(str, name="navigate")
        
    def __init__(self, path:pathlib.Path, isBranch:bool=False, parentCrumb=None,parent:typing.Optional[QtWidgets.QWidget]=None):
        super().__init__(parent=parent)
        # if not path.is_absolute():
        path = path.resolve()
        # print(f"{self.__class__.__name__}.__init__ path = {path}")
        if not path.is_dir():
            path = path.parent

        self.path=path

        self.name = self.path.name
        
        self.parentCrumb = parentCrumb
        
        if len(self.name) == 0:
            self.name = self.path.parts[0]
            
        self._isBranch_ = isBranch
        self.subDirsMenu = None
        # NOTE: 2023-04-27 08:38:31
        # defines the following members: 
        # self.fileSystemModel, self.rootIndex, self.dirButton, self.branchButton
        # self.branchIcon, self.iconSize, self.subDirsMenu
        self._configureUI_()
        
    def _configureUI_(self):
        # print(f"{self.__class__.__name__}._configureUI_ path {self.path.as_posix()}")
        self.fileSystemModel = QtWidgets.QFileSystemModel(parent=self)
        # self.fileSystemModel.setOption(QtWidgets.QFileSystemModel.DontWatchForChanges, True)
        self.fileSystemModel.setReadOnly(True)
        self.fileSystemModel.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.CaseSensitive | QtCore.QDir.NoDotAndDotDot)
        self.fileSystemModel.setRootPath(self.path.as_posix())
        self.rootIndex = self.fileSystemModel.index(self.fileSystemModel.rootPath())

        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.setContentsMargins(0,0,0,0)
        self.hlayout.setSpacing(0)
        self.setLayout(self.hlayout)
        w,h = guiutils.get_text_width_and_height(self.name)
        self.dirButton = QtWidgets.QPushButton(self.name, self)
        isLeaf = not self._isBranch_
        # self.dirButton = NavigatorButton(self.name, isLeaf, self)
        self.dirButton.setFlat(True)
        self.dirButton.setMinimumSize(w,h)
        # self.dirButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        # self.dirButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed))
        self.dirButton.clicked.connect(self.dirButtonClicked)
        
        # self.branchIcon = QtGui.QIcon.fromTheme("go-next")
        # self.iconSize = self.branchIcon.actualSize(QtCore.QSize(16,h), state=QtGui.QIcon.On)
        
        # self.branchButton = QtWidgets.QPushButton(self.branchIcon, "", self)
        # self.branchButton = ArrowButton(self)
        self.branchButton = QtWidgets.QToolButton(self)
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        # self.branchButton.setFlat(True)
        self.branchButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        # self.branchButton.setMinimumSize(self.iconSize.width(), self.iconSize.height())
        # self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))
        self.branchButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed))
        self.branchButton.clicked.connect(self.branchButtonClicked)
        
        
        self.hlayout.addWidget(self.dirButton)
        self.hlayout.addWidget(self.branchButton)
        
        self.branchButton.setVisible(self.isBranch)

    @property
    def isBranch(self):
        return self._isBranch_
    
    @isBranch.setter
    def isBranch(self, value):
        self._isBranch_ = value == True
        self.branchButton.setVisible(self._isBranch_)
        
    @pyqtSlot()
    def dirButtonClicked(self):
        # print(f"{self.__class__.__name__}.dirButtonClicked on {self.name}")
        self.navigate.emit(self.path.as_posix())
        
    @pyqtSlot()
    def branchButtonClicked(self):
        if self.subDirsMenu is None:
            self.subDirsMenu = QtWidgets.QMenu("", self.branchButton)
            self.subDirsMenu.aboutToHide.connect(self.slot_menuHiding)
            
        self.subDirsMenu.clear()
        
        if self.fileSystemModel.hasChildren(self.rootIndex):
            subDirs = [self.fileSystemModel.data(self.fileSystemModel.index(row, 0, self.rootIndex)) for row in range(self.fileSystemModel.rowCount(self.rootIndex))]
            # print(f"rootIndex subDirs {subDirs}")
            if len(subDirs):
                for k, subDir in enumerate(subDirs):
                    # print(f"subDir {subDir}")
                    action = self.subDirsMenu.addAction(subDir)
                    action.setText(subDir)
                    action.triggered.connect(self.slot_subDirClick)
        
                self.branchButton.setMenu(self.subDirsMenu)
                
            self.branchButton.setArrowType(QtCore.Qt.DownArrow)
            self.branchButton.showMenu()
        
    @pyqtSlot()
    def slot_subDirClick(self):
        action = self.sender()
        ps = os.path.join(self.path.as_posix(), action.text())
        self.navigate.emit(ps)
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        
    @pyqtSlot()
    def slot_menuHiding(self):
        self.branchButton.setArrowType(QtCore.Qt.RightArrow)
        
        
class BreadCrumbsNavigator(QtWidgets.QWidget):
    sig_chDirString = pyqtSignal(str, name = "sig_chDirString")
    sig_switchToEditor = pyqtSignal(name = "sig_switchToEditor")
    # def __init__(self, url:QtCore.QUrl, parent:typing.Optional[QtWidgets.QWidget] = None):
    def __init__(self, path:pathlib.Path, parent:typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent=parent)
        if not path.is_dir():
            path = path.parent
        self._path_= path
        self.crumbs = list()
        self._configureUI_()
        self._setupCrumbs_()
        
    def _configureUI_(self):
        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.setContentsMargins(0,0,0,0)
        self.hlayout.setSpacing(0)
        self.setLayout(self.hlayout)
        
    def _setupCrumbs_(self):
        parts = self._path_.parts
        # print(f"{self.__class__.__name__}._setupCrumbs_ parts = {parts}")
        partPaths = [pathlib.Path(*parts[0:k]) for k in range(1, len(parts))] # avoid this dir dot
        nCrumbs = len(partPaths)

        # NOTE: 2023-04-28 21:52:31
        # when chaning the path it's easier to just remove all widgets and 
        # populate anew.
        if len(self.crumbs):
            self._clearCrumbs_()
                
        for k, p in enumerate(partPaths):
            if k > 0:
                # b = BreadCrumb(p, True, parentCrumb = self.crumbs[-1])#, parent=self)
                b = NavigatorButton(p, True)#, parentCrumb = self.crumbs[-1])
            else:
                # b = BreadCrumb(p, True)#, parent=self)
                b = NavigatorButton(p, True)#, parent=self)
                
            b.navigate.connect(self.slot_crumb_clicked)
            self.crumbs.append(b)
            
        # b = BreadCrumb(self._path_, False, parentCrumb=self.crumbs[-1]) # last dir in path = LEAF !!!
        b = NavigatorButton(self._path_, False)#, parentCrumb=self.crumbs[-1]) # last dir in path = LEAF !!!
        b.navigate.connect(self.slot_crumb_clicked)
        self.crumbs.append(b)
        
        for bc in self.crumbs:
            self.hlayout.addWidget(bc)
                
        self.navspot = QtWidgets.QPushButton("", self)
        self.navspot.setFlat(True)
        self.navspot.clicked.connect(self.slot_editPath_request)
        self.hlayout.addWidget(self.navspot)
            
    def _clearCrumbs_(self):
        """
        Removes all BreadCrumbs from this BreadCrumbsNavigator/.
        Leaves the last Pushbutton behind (for switching to path editor)
        """
        for k, b in enumerate(self.crumbs):
            b.hide()
            b.deleteLater()
            b = None
            
        self.crumbs.clear()
        
        self.navspot.destroy()
        self.navspot = None

    @pyqtSlot(str)
    def slot_crumb_clicked(self, path):
        self.sig_chDirString.emit(path)
        # print(f"{self.__class__.__name__}.slot_crumb_clicked {path}")
        
    @pyqtSlot()
    def slot_editPath_request(self):
        self.sig_switchToEditor.emit()
        # print("to switch to path editing mode")
        
    @property
    def path(self):
        return self._path_
    
    @path.setter
    def path(self, value:pathlib.Path):
        print(f"{self.__class__.__name__}.path = {value}")
        self._path_ = value
        self._setupCrumbs_()
        
        
class PathEditor(QtWidgets.QWidget):
    sig_chDirString = pyqtSignal(str, name = "sig_chDirString")
    sig_removeCurrentDirFromHistory = pyqtSignal(str, name = "sig_removeCurrentDirFromHistory")
    sig_clearRecentDirsList = pyqtSignal(str, name = "sig_clearRecentDirsList")
    sig_switchToNavigator = pyqtSignal(name="sig_switchToNavigator")
    
    def __init__(self, path:pathlib.Path, recentDirs:list = [], maxRecent:int=10, parent=None):
        super().__init__(parent=parent) 
        self._path_ = path.resolve()
        self._recentDirs_ = recentDirs
        self._maxRecent_ = maxRecent
        self._configureUI_()
       
    def _configureUI_(self):
        self.directoryComboBox = QtWidgets.QComboBox(parent=self)
        self.directoryComboBox.setEditable(True)
        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        self.directoryComboBox.lineEdit().undoAvailable = True
        self.directoryComboBox.lineEdit().redoAvailable = True
        
        for i in [self._path_.as_posix()] + self._recentDirs_:
            self.directoryComboBox.addItem(i)
            
        self.directoryComboBox.setCurrentIndex(0)
        
        self.directoryComboBox.activated[str].connect(self.slot_dirChange) 
       
        self.removeRecentDirFromListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("edit-delete"), \
                                                        "Remove this path from list", \
                                                        self.directoryComboBox.lineEdit())
        
        self.removeRecentDirFromListAction.setToolTip("Remove this path from history")
        
        self.removeRecentDirFromListAction.triggered.connect(self.slot_removeDirFromHistory)
        
        self.clearRecentDirListAction = QtWidgets.QAction(QtGui.QIcon.fromTheme("final_activity"), \
                                                        "Clear history of visited paths", \
                                                        self.directoryComboBox.lineEdit())
        
        self.clearRecentDirListAction.setToolTip("Clear history of visited paths")
        
        self.clearRecentDirListAction.triggered.connect(self.slot_clearRecentDirList)
        
        self.switchToBreadCrumbsAction=QtWidgets.QAction(QtGui.QIcon.fromTheme("checkbox"),
                                                         "Apply",
                                                         self.directoryComboBox.lineEdit())
        
        self.switchToBreadCrumbsAction.setToolTip("End editing and switch to navigation bar")
        self.switchToBreadCrumbsAction.triggered.connect(self.sig_switchToNavigator)
        
        self.directoryComboBox.lineEdit().addAction(self.switchToBreadCrumbsAction,
                                                   QtWidgets.QLineEdit.TrailingPosition)
        
        self.directoryComboBox.lineEdit().addAction(self.clearRecentDirListAction,
                                                    QtWidgets.QLineEdit.TrailingPosition)
        
        self.directoryComboBox.lineEdit().addAction(self.removeRecentDirFromListAction,
                                                    QtWidgets.QLineEdit.TrailingPosition)
       
        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.addWidget(self.directoryComboBox)
        
    @property
    def path(self):
        return self._path_
    
    @path.setter
    def path(self, value:pathlib.Path):
        oldp = self._path_.as_posix()
        if oldp not in self.history:
            self.history.insert(0, oldp)
        self._path_ = value.resolve()
        ps = self._path_.as_posix()
        
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        
        self.directoryComboBox.clear()
        
        for i in [ps] + self.history:
            self.directoryComboBox.addItem(i)
            
        self.directoryComboBox.setCurrentIndex(0)
        
    @property
    def history(self):
        return self._recentDirs_
    
    @history.setter
    def history(self, value:list=list()):
        sigBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        
        if len(value) > self._maxRecent_:
            value = value[0:self._maxRecent_]
            
        self._recentDirs_[:] = value
        
        if len(self._recentDirs_):
            self.directoryComboBox.clear()
            
            ps = self._path_.as_posix()
            for item in [ps] + self._recentDirs_:
                self.directoryComboBox.addItem(item)
                
        self.directoryComboBox.setCurrentIndex(0)
        
    @property
    def maxHistory(self):
        return self._maxRecent_
    
    @maxHistory.setter
    def maxHistory(self, value:int):
        self._maxRecent_ = value
        
        if len(self.history) > self._maxRecent_:
            self.history = self.history[0:self._maxRecent_]
        
    @pyqtSlot()
    def slot_removeDirFromHistory(self):
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        currentNdx = self.directoryComboBox.currentIndex()
        self.directoryComboBox.removeItem(currentNdx)
        self.directoryComboBox.lineEdit().setClearButtonEnabled(True)
        
    @pyqtSlot()
    def slot_clearRecentDirList(self):
        signalBlocker = QtCore.QSignalBlocker(self.directoryComboBox)
        self.history.clear()
        self.history = [self.path.as_posix()]
        self.directoryComboBox.clear()
        for i in self.history:
            self.directoryComboBox.addItem(i)
            
        self.directoryComboBox.setCurrentIndex(0)
        
    @pyqtSlot(str)
    def slot_dirChange(self, value):
        hh = self.history
        p = pathlib.Path(value).resolve().as_posix()
        
        if p not in hh:
            hh.insert(0, p)
            self.history = hh
            
        else:
            ndx = hh.index(p)
            del hh[ndx]
            hh.insert(0, p)
            self.history = hh

        self.sig_chDirString.emit(value)
        
