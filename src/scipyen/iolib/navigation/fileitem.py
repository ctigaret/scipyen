# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathlib, urllib, stat
import datetime
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from iolib.navigation.udsentry import UDSEntry
from . import utils, filesystem
from core import utilities
from core.prog import scipywarn
HAS_STATX = False
try:
    from . import statx
    HAS_STATX = True
except:
    pass

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class UnknownEnum(IntEnum):
    Unknown = -1
    
class FileTimes(IntEnum):pass
    # ModificationTime = 0
    # AccessTime = 1
    # CreationTime = 2
    # ChangeTime = 3
    
FileTimes = IntEnum("FileTimes", ["ModificationTime", "AccessTime", "CreationTime", "ChangeTime"])
class MimeTypeDetermination(IntEnum):pass
    # NormalMimeTypeDetermination = 0
    # SkipMimeTypeFromContent = 1
    
MimeTypeDetermination = IntEnum("MimeTypeDetermination", ["NormalMimeTypeDetermination", "SkipMimeTypeFromContent"])
    
class HiddenEnum:pass
HiddenEnum = IntEnum("HiddenEnum", ["Auto", "Hidden", "Shown"])

class HiddenCacheEnum:pass
HiddenCacheEnum = IntEnum("HiddenCacheEnum", ["HiddenUncached", "HiddenCached", "ShownCached"])

class SlowEnum:pass
SlowEnum = IntEnum("SlowEnum", ["SlowUnknown", "Fast", "Slow"])

class _FileItem_():
    Unknown         = UnknownEnum.Unknown
    
    Auto            = HiddenEnum.Auto
    Hidden          = HiddenEnum.Hidden
    Shown           = HiddenEnum.Shown
    
    HiddenUncached  = HiddenCacheEnum.HiddenUncached
    HiddenCached    = HiddenCacheEnum.HiddenCached
    ShownCached     = HiddenCacheEnum.ShownCached
    
    SlowUnknown     = SlowEnum.SlowUnknown
    Fast            = SlowEnum.Fast
    Slow            = SlowEnum.Slow
    
    def __init__(self, entry:UDSEntry, 
                 mode:int, 
                 permissions:int,
                 itemOrDirUrl:QtCore.QUrl, 
                 urlIsDirectory:bool,
                 delayedMimeTypes:bool, 
                 mimeTypeDetermination:MimeTypeDetermination):
        self._entry_:UDSEntry = entry
        self._url_:QtCore.QUrl = itemOrDirUrl
        self._strName_:str = str()
        self._strText_:str = str()
        self._iconName_:str = str()
        self._mimeType_:QtCore.QMimeType = QtCore.QMimeType()
        self._fileMode_:int = mode
        self._permissions_:int = permissions
        self._addACL_:bool = False
        self._bLink_:bool = False
        self._bIsLocalUrl_:bool = itemOrDirUrl.isLocalFile()
        self._bMimeTypeKnown_:bool = False
        self._guessedMimeType:str = str()
        self._delayedMimeTypes_:bool = bool(delayedMimeTypes)
        self._useIconNameCache_:bool = False
        self._hidden_:int = self.Auto
        self._hiddenCache_:int = self.HiddenCached
        self._slow_:int = self.SlowUnknown
        self._bSkipMimeTypeFromContent_ = mimeTypeDetermination == MimeTypeDetermination.SkipMimeTypeFromContent
        self._bInitCalled_:bool = False
        self._access_:str = str()
        
        if entry.count() != 0:
            self.readUDSEntry(not urlIsDirectory)
        else:
            if not urlIsDirectory:
                self._strName_ = itemOrDirUrl.fileName()
                self._strText_ = self._strName_
        
    def readUDSEntry(self, urlIsDirectory:bool):
        self._fileMode_ = self._entry_.numberValue(UDSEntry.UDS_FILE_TYPE, self.Unknown)
        self._permissions_ = self._entry_.numberValue(UDSEntry.UDS_ACCESS, self.Unknown)
        self._strName_ = self._entry_.stringValue(UDSEntry.UDS_NAME)
        displayName = self._entry_.stringValue(UDSEntry.UDS_DISPLAY_NAME)
        if len(displayName):
            self._strText_ = displayName
        else:
            # NOTE: 2025-01-06 00:16:58
            # here and in other places, KIO calls decodeFileName (global.h/global.cpp)
            # which is a noop
            self._strText_ = self._strName_ 
            
        urlStr = self._entry_.stringValue(UDSEntry.UDS_URL)
        uds_url_seen = len(urlStr) > 0
        if uds_url_seen:
            self._url_ = QtCore.QUrl(urlStr)
            
            # NOTE: 2025-01-06 00:14:27
            # this below is not the same as
            # `self._bIsLocalUrl_ = self._url_.isLocalFile()`
            # i.e., it does nothing when self._url_.isLocalFile() is False, given
            # that self._bIsLocalUrl_ was already assigned to, earlier in the c'tor
            if self._url_.isLocalFile():
                self._bIsLocalUrl_ = True
                
        db = QtCore.QMimeDatabase()
        mimeTypeStr = self._entry_.stringValue(UDSEntry.UDS_MIME_TYPE)
        self._bMimeTypeKnown_ = len(mimeTypeStr) > 0
        if self._bMimeTypeKnown_:
            self._mimeType_ = db.mimeTypeForName(mimeTypeStr)
            
        self._guessedMimeType = self._entry_.stringValue(UDSEntry.UDS_GUESSED_MIME_TYPE)
        self._bLink_ = len(self._entry_.stringValue(UDSEntry.UDS_LINK_DEST)) > 0
        
        hiddenVal = self._entry_.numberValue(UDSEntry.UDS_HIDDEN, -1)
        self._hidden_ = self.Hidden if hiddenVal == 1 else self.Shown if hiddenVal == 1 else self.Auto
        self._hiddenCache_ = self.HiddenUncached
        
        if urlIsDirectory and not uds_url_seen and len(self._strName_) > 0 and self._strName_ != ".":
            path = self._url_.path()
            if len(path) == 0:
                self._utl_.setPath((pathlib.Path(path) / self._strName_).as_posix())
                # path = "/" # FIXME: 2025-01-06 00:35:48 ?!? hmmm... should not it be os.path.sep?
            
        self._iconName_ = str()
        if self._fileMode_ != self.Unknown:
            self._bInitCalled_ =  True
            
    def ensureInitialized(self):
        if not self._bInitCalled_:
            self.init()
            
    def init(self):
        self._access_ = str()
        
        shouldStat = self._fileMode_ == UnknownEnum.Unknown or self._permissions_ == UnknownEnum.Unknown or (self._entry_.count() == 0 and self._url_.isLocalFile())
        
        if shouldStat:
            path = self._url_.adjusted(QtCore.QUrl.StripTrailingSlash).toLocalFile()
            # pathBA = QtCore.QFile.encodeName(path)
            pPath = pathlib.Path(path)
            
            if HAS_STATX:
                buff = statx.stat(pPath, follow_symlinks=False)
            else:
                buff = os.stat(pPath, follow_symlinks=False)
                
            self._entry_.reserve(10)
            self._entry_.replace(UDSEntry.UDS_DEVICE_ID, buff.st_dev)
            self._entry_.replace(UDSEntry.UDS_INODE, buff.st_ino)
            
            mode = buff.st_mode
            
            if utils.isLinkMask(mode):
                self._bLink_ = True
                
                if HAS_STATX:
                    buff = statx.stat(pPath, follow_symlinks=True)
                else:
                    buff = stat.stat(pPath, follow_symlinks=True)
                    
                mode = buff.st_mode
                
            else:
                mode = (utils.STAT_MASK - 1) | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                
            file_type = mode & utils.STAT_MASK # meaning regular, directory, block, ...
            
            self._entry_.replace(UDSEntry.UDS_SIZE, buff.st_size)
            self._entry_.replace(UDSEntry.UDS_FILE_TYPE, file_type)
            self._entry_.replace(UDSEntry.UDS_ACCESS, mode & 0o7777)
            
            if HAS_STATX:
                self._entry_.replace(UDS_MODIFICATION_TIME, buff.st_mtime)
                self._entry_.replace(UDS_ACCESS_TIME, buff.st_atime) 
                self._entry_.replace(UDS_CREATION_TIME, buff.st_birthtime) # thank you, py_datasource authors!
            else:
                self._entry_.replace(UDS_MODIFICATION_TIME, int(buff.st_mtime))
                self._entry_.replace(UDS_ACCESS_TIME, int(buff.st_atime))
                self._entry_.replace(UDS_CREATION_TIME, int(buff.st_ctime))
                
            if sys.platform != "win32":
                uid = buff.st_uid
                gid = buff.st_gid
                self._entry_.replace(UDSEntry.UDS_LOCAL_USER_ID, uid)
                self._entry_.replace(UDSEntry.UDS_LOCAL_GROUP_ID, gid)
                
            if self._fileMode_ == UnknownEnum.Unknown:
                self._fileMode_ = file_type
                
            if self._permissions_ == UnknownEnum.Unknown:
                self._permissions_ = mode & 0o7777
                
        self._bInitCalled_ = True

    def size(self) -> int:
        self.ensureInitialized()
        
        fieldVal = self._entry_.numberValue(UDSEntry.UDS_SIZE, -1)
        
        if fieldVal != -1:
            return fieldVal
        
        if self._bIsLocalUrl_:
            return QtCore.QFileInfo(self._url_.toLocalFile()).size()
        
        return 0

    def recursiveSize(self) -> int:
        fieldVal = self._entry_.numberValue(UDSEntry.UDS_RECURSIVE_SIZE, -1)
        if fieldVal != -1:
            return fieldVal
        return 0
    
    @staticmethod
    def udsFieldForTime(mappedWhich:FileTimes) -> int:
        match mappedWhich:
            case FileTimes.ModificationTime:
                return UDSEntry.UDS_MODIFICATION_TIME
            case FileTimes.AccessTime:
                return UDSEntry.UDS_ACCESS_TIME
            case FileTimes.CreationTime:
                return UDSEntry.UDS_CREATION_TIME
            case _:
                return 0
            
        return 0
    
    def setTime(self, mappedWhich:FileTimes, 
                val:typing.Union[int, QtCore.QDateTime, datetime.datetime]):
        """val: int (seconds), QDateTime, datetime.datetime"""
        if isinstance(val, int):
            self._entry_.replace(self.udsFieldForTime(mappedWhich), val)
            
        elif isinstance(val, QtCore.QDateTime):
            dt = QtCore.QDateTime(val.toLocalTime())
            self._entry_.replace(self.udsFieldForTime(mappedWhich), dt.toSecsSinceEpoch())
            
        elif isinstance(val, datetime.datetime):
            self._entry_.replace(self.udsFieldForTime(mappedWhich), int(utilities.posixUTC(val)))
            
        else:
            scipywarn(f"Expecting an int (UTC time stamp), QDateTime or datetime.datetime; instead, got {type(val).__name__}")
            
    def time(self, mapedWhich:FileTimes) -> QtCore.QDateTime:
        """Use core.utilities.datetimeFromQt to convert to datetime.datetime
        """
        self.ensureInitialized()
        uds = self.udsFieldForTime(mappedWhich)
        if uds > 0:
            fieldVal = self._entry_.numberValue(uds, -1)
            if fieldVal != -1:
                return QtCore.QDateTime.fromsSecsSinceEpoch(fieldVal) # converts to local time, so no this should NOT be the one below?!?
                # return QtCore.QDateTime.fromsSecsSinceEpoch(fieldVal, QtCore.Qt.TimeSpec(1))
                # # which is same as
                # return QtCore.QDateTime.fromsSecsSinceEpoch(fieldVal, QtCore.Qt.UTC)
                
        return QtCore.QDateTime() # null date time
            
    def printCompareDebug(self, item:_FileItem_):
        otherEntry = item._entry_
        msg = list()
        msg.append(f"Comparing {self._url_} and {item._url_}")
        msg.append(f" name {self._strName_ == item._strName_}")
        msg.append(f" local {self._bIsLocalUrl_ == item._bIsLocalUrl_}")

        msg.append(f" mode {self._fileMode_ == item._fileMode_}")
        msg.append(f" perm {self._permissions_ == item._permissions_}")
        msg.append(f" group {self._entry_.stringValue(UDSEntry.UDS_GROUP) == otherEntry.stringValue(UDSEntry.UDS_GROUP)}")
        msg.append(f" user {self._entry_.stringValue(UDSEntry.UDS_USER) == otherEntry.stringValue(UDSEntry.UDS_USER)}")

        # TODO 2025-01-06 16:36:42
        # add support for ACL — check PyACL ?!?
        # msg.append(f" UDS_EXTENDED_ACL {self._entry_.stringValue(UDSEntry.UDS_EXTENDED_ACL) == otherEntry.stringValue(UDSEntry.UDS_EXTENDED_ACL)}")
        # msg.append(f" UDS_ACL_STRING {self._entry_.stringValue(UDSEntry.UDS_ACL_STRING) == otherEntry.stringValue(UDSEntry.UDS_ACL_STRING)}")
        # msg.append(f" UDS_DEFAULT_ACL_STRING {(self._entry_.stringValue(UDSEntry.UDS_DEFAULT_ACL_STRING) == otherEntry.stringValue(UDSEntry.UDS_DEFAULT_ACL_STRING)}")

        msg.append(f" link {self._bLink_ == item.self._bLink_}")
        msg.append(f" hidden {self._hidden_ == item._hidden_}")

        msg.append(f" size {self.size() == item.size()}")

        msg.append(f" ModificationTime {self._entry_.numberValue(UDSEntry.UDS_MODIFICATION_TIME) == otherEntry.numberValue(UDSEntry.UDS_MODIFICATION_TIME)}")

        msg.append(f" UDS_ICON_NAME {self._entry_.stringValue(UDSEntry.UDS_ICON_NAME) == otherEntry.stringValue(UDSEntry.UDS_ICON_NAME)}")
        
        QtCore.qDebug("\n".join(msg))
        
    def cmp(self, item:_FileItem_) -> bool:
        # NOTE: 2025-01-06 16:59:14
        # similar to filecmp module...might want to check against it
        if item._bInitCalled_:
            self.ensureInitialized()
            
        if self._bInitCalled_:
            item.ensureInitialized()
            
        return all((self._strName_ == item._strName_, 
                   self._bIsLocalUrl_ == item._bIsLocalUrl_,
                   self._fileMode_ == item._fileMode_,
                   self._persmissions_ == item._persmissions_,
                   self._entry_.stringValue(UDSEntry.UDS_GROUP) == item._entry_.stringValue(UDSEntry.UDS_GROUP),
                   self._entry_.stringValue(UDSEntry.UDS_USER) == item._entry_.stringValue(UDSEntry.UDS_USER),
                   self._entry_.stringValue(UDSEntry.UDS_EXTENDED_ACL) == item._entry_.stringValue(UDSEntry.UDS_EXTENDED_ACL),
                   self._entry_.stringValue(UDSEntry.UDS_ACL_STRING) == item._entry_.stringValue(UDSEntry.UDS_ACL_STRING),
                   self._entry_.stringValue(UDSEntry.UDS_DEFAULT_ACL_STRING) == item._entry_.stringValue(UDSEntry.UDS_DEFAULT_ACL_STRING),
                   self._bLink_ == item._bLink_,
                   self._hidden_ == item._hidden_,
                   self.size() == item.size(),
                   self._entry_.numberValue(UDSEntry.UDS_MODIFICATION_TIME) == item._entry_.numberValue(UDSEntry.UDS_MODIFICATION_TIME),
                   self._entry_.stringValue(UDSEntry.UDS_ICON_NAME) == item._entry_.stringValue(UDSEntry.UDS_ICON_NAME),
                   self. _entry_.stringValue(UDSEntry.UDS_TARGET_URL) == item._entry_.stringValue(UDSEntry.UDS_TARGET_URL),
                   self._entry_.stringValue(UDSEntry.UDS_LOCAL_PATH) == item._entry_.stringValue(UDSEntry.UDS_LOCAL_PATH)))
        
    def parsePermissions(self, perm:int) -> str:
        # TODO: 2025-01-06 17:07:40 check against result from stat.filemode(mode)
        self.ensureInitialized()
        
        bfr = ["_"]*12
        uxbit = "-"
        gxbit = "-"
        oxbit = "-"
        
        if ((perm & (stat.S_IXUSR | stat.S_ISUID)) == (stat.S_IXUSR | stat.S_ISUID)):
            uxbit = 's'
        elif ((perm & (stat.S_IXUSR | stat.S_ISUID)) == stat.S_ISUID):
            uxbit = 'S'
        elif ((perm & (stat.S_IXUSR | stat.S_ISUID)) == stat.S_IXUSR):
            uxbit = 'x'
        else:
            uxbit = '-'

        if ((perm & (stat.S_IXGRP | stat.S_ISGID)) == (stat.S_IXGRP | stat.S_ISGID)):
            gxbit = 's'
        elif ((perm & (stat.S_IXGRP | stat.S_ISGID)) == stat.S_ISGID):
            gxbit = 'S'
        elif ((perm & (stat.S_IXGRP | stat.S_ISGID)) == stat.S_IXGRP):
            gxbit = 'x'
        else:
            gxbit = '-'

        if ((perm & (stat.S_IXOTH | stat.S_ISVTX)) == (stat.S_IXOTH | stat.S_ISVTX)):
            oxbit = 't'
        elif ((perm & (stat.S_IXOTH | stat.S_ISVTX)) == stat.S_ISVTX):
            oxbit = 'T'
        elif ((perm & (stat.S_IXOTH | stat.S_ISVTX)) == stat.S_IXOTH):
            oxbit = 'x'
        else:
            oxbit = '-'
        
        if self._bLink_:
            bfr[0]="l"
        elif self._fileMode_ != self.Unknown:
            if utils.isDirMask(self._fileMode_):
                bfr[0] = "d"
            elif sys.platform != "win32":
                if stat.S_ISSOCK(self._fileMode_):
                    bfr[0] = "s"
                elif stat.S_ISCHR(self._fileMode_):
                    bfr[0] = "c"
                elif stat.S_ISBLK(self._fileMode_):
                    bfr[0] = "b"
                elif stat.S_ISFIFO(self._fileMode_):
                    bfr[0] = "p"
                else:
                    bfr[0] = "-"
            else:
                bfr[0] = "-"
        else:
            bfr[0] = "-"
            
        bfr[1] = "r" if (perm & stat.S_IRUSR) == stat.S_IRUSR else "-"
        bfr[2] = "w" if (perm & stat.S_IWUSR) == stat.S_IWUSR else "-"
        bfr[3] = uxbit
        bfr[4] = "r" if (perm & stat.S_IRGRP) == stat.S_IRGRP else "-"
        bfr[5] = "w" if (perm & stat.S_IWGRP) == stat.S_IWGRP else "-"
        bfr[6] = gxbit
        bfr[7] = "r" if (perm & stat.S_IROTH) == stat.S_IROTH else "-"
        bfr[8] = "w" if (perm & stat.S_IWOTH) == stat.S_IWOTH else "-"
        bfr[9] = oxbit
        
        if self.m_entry.contains(UDSEntry.UDS_EXTENDED_ACL):
            bfr[10] = '+'
            bfr[11] = 0
        else:
            bfr[10] = 0
            
        return "".join(bfr)

    def isSlow(self) -> bool:
        if self._slow_ == self.SlowUnknown:
            path = self.localPath()
            if len(path):
                # TODO: 2025-01-06 17:41:31
                # study https://api.kde.org/frameworks/kcoreaddons/html/kfilesystemtype_8cpp_source.html
                # and https://api.kde.org/frameworks/kcoreaddons/html/namespaceKFileSystemType.html
                pass
                
        
    def determineMimeTypeHelper(self, url:QtCore.QUrl):
        db = QtCore.QMimeDatabase()
        
        if self._bSkipMimeTypeFromContent_ or self.isSlow():
            pass # TODO
        
        
        
class FileItem(_FileItem_):
    # NOTE: 2025-01-04 12:47:20
    # should use a pathlib.Path as backend
    # NOTE: 2025-01-04 15:07:39
    # doesn't use Qt Signals/Slots so no need to inherit from QObject
    # By keeping it in the Python world I guess also removes the need to inherit 
    # from QSharedData (KFileItemPrivate)
    
    def __init__(self, entry:UDSEntry, mode:int, permissions:int,
                 itemOrDirUrl:QtCore.QUrl, urlIsDirectory:bool,
                 delayedMimeTypes:bool, mimeTypeDetermination:MimeTypeDetermination):
        # ### BEGIN KFileItemPrivate
        super().__init__(entry, mode, itemOrDirUrl, urlIsDirectory, 
                         delayedMimeTypes, mimeTypeDetermination)
        # ### END KFileItemPrivate
        
        self._user_:str = str()
        self._group_:str = str()
        self._isLink_:bool = False
        self._isDir_:bool = False
        self._isFile_:bool = False
        self._isReadable_:bool = False
        self._isWritable_:bool = False
        self._isHidden_:bool = False
        self._isSlow_:bool = False
        self._isDesktopFile_:bool = False
        self._linkDest_:str = str()
        self._targetUrl_:QtCore.QUrl = QtCore.QUrl()
        self._localPath_:str = str()
        self._isLocalFile_:bool = False
        self._text_:str = str()
        self._name_:str = str()
        self._determineMimeType_:QtCore.QMimeType = QtCore.QMimeType()
        self._currentMimeType_:QtCore.QMimeType = QtCore.QMimeType()
        self._isFinalIconKnown_:bool = False
        self._isMimeTypeKnown_:bool = False
        self._mimeComment_:str = str()
        self._overlays_:list[str] = list()
        self._comment_:str = str()
        self._statusBarInfo_:str = str()
        self._isRegularFile_:bool = False

    @property
    def url(self) -> QtCore.QUrl:
        return self._url_
    
    @url.setter
    def url(self, val:QtCore.QUrl):
        self._url_ = val

    @property
    def user(self) -> str:
        return self._user_
    
    @user.setter
    def user(self, val:str):
        self._user_ = val
        
    @property
    def group(self) -> str:
        return self._group_
    
    @group.setter
    def group(self, val:str):
        self._group_ = val
        
    @property
    def isLink(self) -> bool:
        return self._isLink_
    
    @isLink.setter
    def isLink(self, val:bool):
        self._isLink_ = val == True
        
    @property
    def isDir(self) -> bool:
        return self._isDir_
    
    @isDir.setter
    def isDir(self, val:bool):
        self._isDir_ = val == True
        
    @property
    def isFile(self) -> bool:
        return self._isFile_
    
    @isFile.setter
    def isFile(self, val:bool):
        self._isFile_ = val == True
        
    @property
    def isReadable(self) -> bool:
        return self._isReadable_
    
    @isReadable.setter
    def isReadable(self, val:bool):
        self._isReadable_ = val == True
        
    @property
    def isWritable(self) -> bool:
        return self._isWritable_
    
    @isWritable.setter
    def isWritable(self, val:bool):
        self._isWritable_ = val == True
        
    @property
    def isHidden(self) -> bool:
        return self._isHidden_
    
    @isHidden.setter
    def isHidden(self, val:bool):
        self._isHidden_ = val == True
        
    @property
    def isSlow(self) -> bool:
        return self._isSlow_
    
    @isSlow.setter
    def isSlow(self, val:bool):
        self._isSlow_ = val == True
        
    @property
    def isDesktopFile(self) -> bool:
        return self._isDesktopFile_
    
    @isDesktopFile.setter
    def isDesktopFile(self, val:bool):
        self._isDesktopFile_ = val == True
        
    @property
    def linkDest(self) -> str:
        return self._linkDest_
    
    @linkDest.setter
    def linkDest(self, val:str):
        self._linkDest_ = val
        
    @property
    def targetUrl(self) -> QtCore.QUrl:
        return self._targetUrl_
    
    @targetUrl.setter
    def targetUrl(self, val:QtCore.QUrl):
        self._targetUrl_ = val

    @property
    def localPath(self) -> str:
        return self._localPath_
    
    @localPath.setter
    def localPath(self, val:str):
        self._localPath_ = val
        
    @property
    def isLocalFile(self) -> bool:
        return self._isLocalFile_
    
    @isLocalFile.setter
    def isLocalFile(self, val:bool):
        self._isLocalFile_ = val == True
        
    @property
    def text(self) -> str:
        return self._text_
        
    @text.setter
    def text(self, val:str):
        self._text_ = val
        
    @property
    def name(self) -> str:
        return self._name_
    
    @name.setter
    def name(self, val:str):
        self._name_ = val
        
    @property
    def mimetype(self) -> str:
        return self._mimetype_
    
    @mimetype.setter
    def mimetype(self, val:str):
        self._mimetype_ = val
        
    @property
    def determineMimeType(self) -> QtCore.QMimeType:
        return self._determineMimeType_
    
    @determineMimeType.setter
    def determineMimeType(self, val:QtCore.QMimeType):
        self._determineMimeType_ = val
        
    @property
    def currentMimeType(self) -> QtCore.QMimeType:
        return self._currentMimeType_
    
    @currentMimeType.setter
    def currentMimeType(self, val:QtCore.QMimeType):
        self._currentMimeType_ = val
        
    @property
    def isFinalIconKnown(self) -> bool:
        return self._isFinalIconKnown_
    
    @isFinalIconKnown.setter
    def isFinalIconKnown(self, val:bool):
        self._isFinalIconKnown_ = val == True
        
    @property
    def isMimeTypeKnown(self) -> bool:
        return self._isMimeTypeKnown_
    
    @isMimeTypeKnown.setter
    def isMimeTypeKnown(self, val:bool):
        self._isMimeTypeKnown_ = val == True
        
    @property
    def mimeComment(self) -> str:
        return self._mimeComment_
    
    @mimeComment.setter
    def mimeComment(self, val:str):
        self._mimeComment_ = val
    
    @property
    def iconName(self) -> str:
        return self._iconName_
    
    @iconName.setter
    def iconName(self, val:str):
        self._iconName_ = val
        
    @property
    def overlays(self) -> list[str]:
        return self._overlays_
    
    @overlays.setter
    def overlays(self, val:list[str]):
        self._overlays_ = val
        
    @property
    def comment(self) -> str:
        return self._comment_
    
    @comment.setter
    def comment(self, val:str):
        self._comment_ = val
        
    @property
    def statusBarInfo(self) -> str:
        return self._statusBarInfo_
    
    @statusBarInfo.setter
    def statusBarInfo(self, val:str):
        self._statusBarInfo_ = val
        
    @property
    def isRegularFile(self) -> bool:
        return self._isRegularFile_
    
    @isRegularFile.setter
    def isRegularFile(self, val:bool):
        self._isRegularFile_ = val == True

    # ### BEGIN KFileItemPrivate methods
    # ### END KFileItemPrivate methods
