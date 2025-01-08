# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathlib, urllib, stat, traceback
import datetime
from enum import Enum, IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from core import strutils
from iolib.navigation.udsentry import UDSEntry
from . import utils, filesystems
from core import utilities
from core.multimeta import MultipleMeta
from core.prog import scipywarn
HAS_STATX = False
try:
    from . import statx
    HAS_STATX = True
except:
    pass

__module_path__ = os.path.abspath(os.path.dirname(__file__))

cachedStrings = dict()

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

_FI_ = typing.TypeVar("_FI_", bound = "_FileItem_")
FI = typing.TypeVar("FI", bound="FileItem")

class _FileItem_:
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
        # if isinstance(itemOrDirUrl, pathlib.Path):
        #     self._url_ = QtCore.QUrl(itemOrDirUrl.as_uri())
        # else:
        self._fileMode_:int = mode
        self._permissions_:int = permissions
        self._url_:QtCore.QUrl = itemOrDirUrl
        self._strName_:str = str()
        self._strText_:str = str()
        self._iconName_:str = str()
        self._strLowerCaseName:str = str()
        self._mimeType_:QtCore.QMimeType = QtCore.QMimeType()
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
        
        # print(f"{self.__class__.__name__}.__init__(entry with {entry.count()} fields)")
        if entry.count() != 0:
            self.readUDSEntry(urlIsDirectory)
        else:
            if not urlIsDirectory:
                self._strName_ = itemOrDirUrl.fileName()
                self._strText_ = self._strName_
        
    def readUDSEntry(self, urlIsDirectory:bool):
        print(f"{self.__class__.__name__}.readUDSEntry")
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
            
            try:
                if HAS_STATX:
                    buff = statx.stat(pPath, follow_symlinks=False)
                else:
                    buff = os.stat(pPath, follow_symlinks=False)
                    
                self._entry_.reserve(9)
                # self._entry_.reserve(10)
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
                    mode = (utils.IFMT_MASK - 1) | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                    # mode = (utils.IFMT_MASK - 1) | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                    
                # NOTE: 2025-01-08 21:48:48
                # this is the same as stat.S_IFMT(mode)
                file_type = mode & utils.IFMT_MASK # meaning regular, directory, block, ...
                
                self._entry_.replace(UDSEntry.UDS_SIZE, buff.st_size)
                self._entry_.replace(UDSEntry.UDS_FILE_TYPE, file_type)
                self._entry_.replace(UDSEntry.UDS_ACCESS, mode & 0o7777)
                
                if HAS_STATX:
                    self._entry_.replace(UDSEntry.UDS_MODIFICATION_TIME, buff.st_mtime)
                    self._entry_.replace(UDSEntry.UDS_ACCESS_TIME, buff.st_atime) 
                    self._entry_.replace(UDSEntry.UDS_CREATION_TIME, buff.st_birthtime) # thank you, py_datasource authors!
                else:
                    self._entry_.replace(UDSEntry.UDS_MODIFICATION_TIME, int(buff.st_mtime))
                    self._entry_.replace(UDSEntry.UDS_ACCESS_TIME, int(buff.st_atime))
                    self._entry_.replace(UDSEntry.UDS_CREATION_TIME, int(buff.st_ctime))
                    
                if sys.platform != "win32":
                    uid = buff.st_uid
                    gid = buff.st_gid
                    self._entry_.replace(UDSEntry.UDS_LOCAL_USER_ID, uid)
                    self._entry_.replace(UDSEntry.UDS_LOCAL_GROUP_ID, gid)
                    
                if self._fileMode_ == UnknownEnum.Unknown:
                    self._fileMode_ = file_type
                    
                if self._permissions_ == UnknownEnum.Unknown:
                    self._permissions_ = mode & 0o7777
            except PermissionError:
                pass
            
            except:
                traceback.print_exc()

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
    
    def setTime(self, mappedWhich:FileTimes, val:typing.Union[int, QtCore.QDateTime, datetime.datetime]):
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
            
    def printCompareDebug(self, item:type(_FI_)):
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
        
    def cmp(self, item:type[_FI_]) -> bool:
        # NOTE: 2025-01-06 16:59:14
        # similar to filecmp module...might want to check against it
        if item._bInitCalled_:
            self.ensureInitialized()
            
        if self._bInitCalled_:
            item.ensureInitialized()
            
        return all((self._strName_ == item._strName_, 
                   self._bIsLocalUrl_ == item._bIsLocalUrl_,
                   self._fileMode_ == item._fileMode_,
                   self._permissions_ == item._permissions_,
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
        # BUG: 2025-01-08 18:45:50 FIXME:
        # • why does this keep inserting the 't' bit?
        # • rw appears all over the place when it shouldn't'
        # • sticky bit appears when it shouldn't
        self.ensureInitialized()
        
        bfr = ["-"]*12
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
        
        if self._entry_.contains(UDSEntry.UDS_EXTENDED_ACL):
            bfr[10] = '+'
            bfr[11] = '-'
        else:
            bfr[10] = '-'
            
        return "".join(bfr)

    def isSlow(self) -> bool:
        if self._slow_ == self.SlowUnknown:
            path = self.localPath()
            if len(path):
                fsType = filesystems.fileSystemType(path)
                self._slow_ = self.Slow if fsType in (filesystems.FsType.Nfs, filesystems.FsType.Smb) else self.Fast
            else:
                self._slow_ = self.Slow
                
        return self._slow_ == self.Slow
                
    def determineMimeTypeHelper(self, url:QtCore.QUrl):
        db = QtCore.QMimeDatabase()
        
        if self._bSkipMimeTypeFromContent_ or self.isSlow():
            scheme = url.scheme()
            if scheme.startswith("http") or scheme == "mailto":
                self._mimeType_ = db.mimeTypeForName("application/octet-streaam")
            else:
                self._mimeType_ = db.mimeTypeForFile(url.path(), QtCore.QMimeDatabase.MatchExtension)
        else:
            self._mimeType_ = db.mimeTypeForUrl(url)
            
    def localPath(self) -> str:
        if self._bIsLocalUrl_:
            return self._url_.toLocalFile()
        
        self.ensureInitialized()
        return self._entry_.stringValue(UDSEntry.UDS_LOCAL_PATH)
        
class FileItem(metaclass=MultipleMeta):
    # FIXME: 2025-01-08 18:40:39
    # MultipleMeta has problems when an argument type is a subclass of what is 
    # given in annotations  - FIXME tweak the MeultipleMeta class in 
    # core.multimeta module
    # TODO: 2025-01-08 17:59:34 methods:
    # __eq__
    # __le__
    # __gt__
    # cmp
    # getStatusBarInfo
    
    
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
                 itemOrDirUrl:QtCore.QUrl,
                 delayedMimeTypes:bool,
                 urlIsDirectory:bool
                 ):
        self.__init__(entry, int(UnknownEnum.Unknown), int(UnknownEnum.Unknown),
                              itemOrDirUrl, urlIsDirectory, delayedMimeTypes,
                              MimeTypeDetermination.NormalMimeTypeDetermination)
        
    def __init__(self, url:QtCore.QUrl, mimeType:str, mode:int):
        self.__init__(UDSEntry(), mode, int(UnknownEnum.Unknown), url, 
                        False, False, MimeTypeDetermination.NormalMimeTypeDetermination)
        
        self._d_._bMimeTypeKnown_ = len(strutils.simplify(mimeType)) > 0 
        
        if self._d_._bMimeTypeKnown_:
            db = QtCore.QMimeDatabase()
            self._d_._mimeType_ = db.mimeTypeForName(mimeType)
            
    def __init__(self, path:pathlib.Path, mimeType:str, mode:int):
        self.__init__(UDSEntry(), mode, int(UnknownEnum.Unknown), path.absolute().as_uri(), 
                        False, False, MimeTypeDetermination.NormalMimeTypeDetermination)
        
        self._d_._bMimeTypeKnown_ = len(strutils.simplify(mimeType)) > 0 
        if self._d_._bMimeTypeKnown_:
            db = QtCore.QMimeDatabase()
            self._d_._mimeType_ = db.mimeTypeForName(mimeType)
            
    def __init__(self, url:QtCore.QUrl, mimeTypeDetermination:MimeTypeDetermination):
        self.__init__(UDSEntry(), int(UnknownEnum.Unknown), int(UnknownEnum.Unknown),
                    url, False, False, mimeTypeDetermination)
    
    def __init__(self, path:str,  mimeTypeDetermination:MimeTypeDetermination):
        pp = pathlib.Path(path).absolute()
        self.__init__(UDSEntry(), int(UnknownEnum.Unknown), int(UnknownEnum.Unknown),
                    QtCore.QUrl(pp.as_uri()), pp.is_dir(), False, mimeTypeDetermination)
    
    def __init__(self, path:str):
        pp = pathlib.Path(path).absolute()
        url = pp.as_uri()
        self.__init__(UDSEntry(), int(UnknownEnum.Unknown), int(UnknownEnum.Unknown),
                    QtCore.QUrl(pp.as_uri()), pp.is_dir(), False, MimeTypeDetermination.NormalMimeTypeDetermination)
    
    def __init__(self, url:QtCore.QUrl):
        self.__init__(UDSEntry(), int(UnknownEnum.Unknown), int(UnknownEnum.Unknown),
                    url, False, False, MimeTypeDetermination.NormalMimeTypeDetermination)
        
    def __init__(self):
        self._d_ = None
    
    def __init__(self, entry:UDSEntry, mode:int, permissions:int,
                 itemOrDirUrl:QtCore.QUrl, urlIsDirectory:bool,
                 delayedMimeTypes:bool, mimeTypeDetermination:MimeTypeDetermination):
        # ### BEGIN KFileItemPrivate
        print(f"{self.__class__.__name__}.__init__<common>:")
        print(f"entry: {entry.count()}, mode: {mode}, permissions: {permissions}, itemOrDirUrl: {itemOrDirUrl}, urlIsDirectory: {urlIsDirectory}, delayedMimeTypes: {delayedMimeTypes}, mimeTypeDetermination: {mimeTypeDetermination})")
        self._d_ = _FileItem_(entry, mode, permissions, itemOrDirUrl, urlIsDirectory, 
                         delayedMimeTypes, mimeTypeDetermination)
        # ### END KFileItemPrivate
        
    def refresh(self):
        if self._d_ is None:
            scipywarn("null item")
            return
        
        self._d_._fileMode_ = self.Unknown
        self._d_._permissions_ = self.Unknown
        self._d_._hidden_ = self.Auto
        self._d_._hiddenCache_ = self.HiddenUncached
        self.refreshMimeType()
        ####
        # TODO: 2025-01-08 14:00:19 addACL
        ####
        self._d_._entry_.clear()
        self._d_.init()
        
    def refreshMimeType(self):
        if self._d_ is None:
            return
        
        self._d_._mimeType_ = QtCore.QMimeType()
        self._d_._bMimeTypeKnown_ = False
        self._d_._iconName_ = str()
        
    def setDelayedMimeTypes(self, val:bool):
        if self._d_ is None:
            return
        self._d_._delayedMimeTypes_ = val == True
        
    def setUrl(self, val:QtCore.QUrl):
        self._url_ = val
        if self._d_ is None:
            scipywarn("null item")
            return
        self._d_._url_ = url
        self.setName(url.fileName())
    
    def url(self) -> QtCore.QUrl:
        if self._d_ is None:
            return QtCore.QUrl()
        return self._d_._url_

    def setLocalPath(self, val:str):
        if self._d_ is None:
            scipywarn("null item")
            return 
        self._d_._entry_.replace(UDSEntry.UDS_LOCAL_PATH, path)
        
    def setLocalPath(self, val:pathlib.Path):
        if self._d_ is None:
            scipywarn("null item")
            return 
        self._d_._entry_.replace(UDSEntry.UDS_LOCAL_PATH, path.as_posix())
        
    def localPath(self) -> str:
        if self._d_ is None:
            return str()
        
        return self_d_.localPath()
    
    def setName(self, val:str):
        if self._d_ is None:
            scipywan("null item")
            return
        
        self._d_.ensureInitialized()
        self._d_._name_ = val
        
        if len(self._d_._name_):
            self._d_._strText_ = self._d_._name_
            
        if self._d_._entry_.contains(UDSEntry.UDS_NAME):
            self._d_._entry_.replace(UDSEntry.UDS_NAME, self._d_._strName_)
            
        self._d_._hiddenCache_ = self.HiddenUncached
        
    def name(self, lowerCase:bool=False) -> str:
        if self._d_ is None:
            return str()
        
        self._d_.ensureInitialized()
        
        if not lowerCase:
            return self._d_._strName_
        
        elif len(self._d_._strLowerCaseName_) == 0:
            self._d_._strLowerCaseName = self._d_._strName_.lower()
            
        return self._d_._strLowerCaseName
    
    def user(self) -> str:
        import pwd
        if self._d_ is None:
            return str()
        
        if self.entry().contains(UDSEntry.UDS_USER):
            return self.entry().stringValue(UDSEntry.UDS_USER)
        else:
            if sys.platform != "win32":
                uid = self.entry().numberValue(UDSEntry.UDS_LOCAL_USER_ID, -1)
                if uid != -1:
                    try:
                        return pwd.getpwuid(uid).pw_name
                    except:
                        traceback.print_exc()
                    return str()
                
            return str()
        
    def userId(self) -> int:
        if self._d_ is None:
            return -1
        
        return self.entry().numberValue(UDSEntry.UDS_LOCAL_USER_ID, -1)
    
    def group(self) -> str:
        import grp
        if self._d_ is None:
            return str()
        
        if self.entry().contains(UDSEntry.UDS_GROUP):
            return self.entry().numberValue(UDSEntry.UDS_GROUP)
        else:
            if sys.platform != "win32":
                gid = self.entry().numberValue(UDSEntry.UDS_LOCAL_GROUP_ID, -1)
                if gid != -1:
                    if gid not in cachedStrings:
                        try:
                            groupName = grp.getgrgid(gid).gr_name
                            cachedStrings[gid] = groupName
                        except:
                            return str()
                        
                    return cachedStrings[gid]
                
        return str()
    
    def groupId(self) -> int:
        if self._d_ is None:
            return -1
        
        return self.entry().numberValue(UDSEntry.UDS_LOCAL_GROUP_ID, -1)
    
    def isLink(self) -> bool:
        if self._d_ is None:
            return False
        self._d_.ensureInitialized()
        return self._d_._bLink_
    
    def isDir(self) -> bool:
        if self._d_ is None:
            return False
        
        if self._d_._fileMode_ != self.Unknown:
            return utils.isDirMask(self._d_._fileMode_)
        
        if self._d_._bMimeTypeKnown_ and self._d_._mimeType_.isValid():
            return self._d_._mimeType_.inherits("inode/directory")
        
        if self._d_._bSkipMimeTypeFromContent_:
            return False
        
        self._d_.ensureInitialized()
        if self._d_._fileMode_ == self.Unknown:
            return False
        
        return utils.isDirMask(self._d_._fileMode_)
    
    def isFile(self) -> bool:
        if self._d_ is None:
            return False
        return not self.isDir()
        
    def isReadable(self) -> bool:
        if self._d_ is None:
            return False
        
        self._d_.ensureInitialized()
        
        if self._d_._permissions_ != self.Unknown:
            readMask = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            
            if self._d_._permissions_ & readMask == 0:
                return False
            
            if self._d_._permissions_ & readMask == readMask:
                return True
            
            if sys.platform != "win32":
                uidOfItem = self.userId()
                if uidOfItem != -1:
                    currentUser = os.getuid()
                    if uidOfItem == currentUser:
                        return stat.S_IRUSR & self._d_._permissions_ > 0
                    gidOfItem = self.groupId()
                    if gidOfItem != -1:
                        groups = os.getgroupslist(os.getlogin(), os.getgid())
                        if gidOfItem in groups:
                            return stat.S_IRGRP & self._d_._permissions_ > 0
                        
                        return stat.S_IROTH & self._d_._permissions_ > 0
                        
            else:
                return stat.S_IRUSR & self._d_._permissions_ > 0
        else:
            if self._d_._bIsLocalUrl_ and not QtCore.QFileInfo(self._d_._url_.toLocalFile()).isReadable():
                return False
            
            return True
            
    def isHidden(self) -> bool:
        if self._d_ is None:
            return False
        if self._d_._hidden_ != self.Auto:
            return self._d_._hidden_ == self.Hidden
        if self._d_._hiddenCache_ != self.HiddenUncached:
            return self._d_._hidden_ == self.HiddenUncached
        
        fileName = self._d_._url_.fileName()
        if len(fileName) == 0:
            fileName = self._d_._strName_
        
        self._d_._hiddenCache_ = self.HiddenCached if len(fileName) > 1 and fileName.startswith('.') else self.ShownCached
        return self._d_._hiddenCache_ == self.HiddenCached
    
    def setHidden(self):
        if self._d_ is not None:
            self._d_._hidden_ = self.Hidden
        
    def isSlow(self) -> bool:
        if self._d_ is None:
            return False
        
        return self._d_.isSlow()
    
    def isDesktopFile(self) -> bool:
        return checkDesktopFile(self, True)
        
    def linkDest(self) -> str:
        if self._d_ is None:
            return str()
        
        self._d_.ensureInitialized()
        if not self._d_._bLink_:
            return str()
        
        linkStr = self._d_._entry_.stringValue(UDSEntry.UDS_LINK_DEST)
        if len(linkStr):
            return linkstr
        
        if self._d_._bIsLocalUrl_:
            if sys.platform == "win32":
                return QtCore.QFile.symLinkTarget(self._d_._url_.adjusted(QtCore.QUrl.StripTrailingSlash).toLocalFile())
            else:
                path = self._d_._url_.adjusted(QtCore.QUrl.StripTrailingSlash).toLocalFile()
                return pathlib.Path(path).readlink() # or resolve()?
        return str()
    
    def targetUrl(self) -> QtCore.QUrl:
        if self._d_ is None:
            return QtCore.QUrl()
        
        targetUrlStr = self._d_._entry_.stringValue(UDSEntry.UDS_TARGET_URL)
        if len(targetUrlStr):
            return QtCore.QUrl(targetUrlStr)
        return self.url()
    
    def isLocalFile(self) -> bool:
        if self._d_ is None:
            return False
        return self._d_._bIsLocalUrl_
    
    def text(self) -> str:
        if self._d_ is None:
            return str()
        return self._d_._strText_
        
    def isWritable(self) -> bool:
        import grp
        if self._d_ is None:
            return False
        
        self._d_.ensureInitialized()
        
        if self._d_._permissions_ != self.Unknown:
            if self._d_._permissions_ & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH) == 0:
                return False
            
            if sys.platform != "win32":
                uidOfItem = self.userId()
                if uidOfItem != -1:
                    currentUser = og.getuid()
                    if uidOfItem == currentUser:
                        return stat.S_IWUSR & self._d_._permissions_ > 0
                    
                    gidOfItem = self.groupId()
                    if gidOfItem != -1:
                        groups = os.getgroupslist(os.getlogin(), os.getgid())
                        if gidOfItem in groups:
                            return stat.S_IWGRP & self._d_._permissions_ > 0
                        
                        if stat.S_IWOTH * self._d_._permissions_ > 0:
                            return True
            else:
                return stat.S_IWUSR & self._d_._permissions_ > 0
            
        else:
            if self._d_._bIsLocalUrl_:
                return QtCore.QFileInfo(self._s_._url_.toLocalFile()).isWritable()
            else:
                return False # FIXME 2025-01-08 18:13:54 TODO 
                             # return KProtocolManager::supportsWriting(d->m_url);
                    
    def mimetype(self) -> str:
        if self._d_ is None:
            return str()
        
        return self.determineMimeType().name()
    
    def determineMimeType(self) -> QtCore.QMimeType:
        if self._d_ is None:
            return QtCore.QMimeType()
        
        if not self._d_._mimeType_.isValid() or not self._d_._bMimeTypeKnown_:
            db = QtCore.QMimeDatabase()
            if self.isDir():
                self._d_._mimeType_ = db.mimeTypeForName("inode/directory")
            else:
                url, isLocalUrl = self.isMostLocalUrl() # TODO
                self._d_.determineMimeTypeHelper(url)
                assert self._d_._mimeType_.isValid(), "Invalid mime type"
                
            self._d_._bMimeTypeKnown_ = True
            
        if self._d_._delayedMimeTypes_:
            self._d_._delayedMimeTypes_ = False
            self._d_._useIconNameCache_ = False
            self.iconName() # TODO
            
        return self._d_._mimeType_
    
    def isMostLocalUrl(self) -> tuple:
        # NOTE: MostLocalUrlResult is a tuple, here!
        if self._d_ is None:
            return QtCore.QUrl(), False
        
        localPath = self.localPath()
        if len(localPath):
            return QtCore.QUrl.fromLocalFile(localPath), True
        else:
            return self._d_._url_, self._d_._bIsLocalUrl_
        
    def mostLocalUrl(self, local:bool) -> tuple:
        if self._d_ is None:
            return tuple()
        
        _u, _l = self.isMostLocalUrl()
        if local:
            local = _l
            
        return _u, local
    
    def currentMimeType(self) -> QtCore.QMimeType:
        if self._d_ is None or self._d_._url_.isEmpty():
            return QtCore.QMimeType()
        
        if not self._d_._mimeType_.isValid():
            db = QtCore.QMimeDatabase()
            if self.isDir():
                self._d_._mimeType_ = db.mimeTypeForName("inode/directory")
                return self._d_._mimeType_
            
            _url, _lurl = self.mostLocalUrl()
            if self._d_._delayedMimeTypes_:
                mimeTypes = db.mimeTypesForFileName(_url.path())
                if len(mimeTypes) == 0:
                    self._d_._mimeType_ = db.mimeTypeForName("application/octet-stream")
                    self._d_._bMimeTypeKnown_ = False
                else:
                    self._d_._mimeType_ = mimeTypes[0]
                    self._d_._bMimeTypeKnown_ = len(mimeTypes) == 1
            else:
                self._d_.determineMimeTypeHelper(_url)
                self._d_._bMimeTypeKnown_ = True
        
        return self._d_._mimeType_
            
    def isFinalIconKnown(self) -> bool:
        if self._d_ is None:
            return False
        return self._d_._bMimeTypeKnown_ and not self._d_._delayedMimeTypes_
    
    def isMimeTypeKnown(self) -> bool:
        if self._d_ is None:
            return False
        return self._d_._bMimeTypeKnown_ and len(self._d_._guessedMimeType)==0 # ?!? TODO check this
    
    def comment(self) -> str:
        if self._d_ is None:
            return str()
        
        return self._d_._entry_.stringValue(UDSEntry.UDS_COMMENT)
    
    def overlays(self) -> list:
        if self._d_ is None:
            return list()
        
        self._d_.ensureInitialized()
        names = self._d_._entry_.stringValue(UDSEntry.UDS_ICON_OVERLAY_NAMES)
        namesList = list(map(lambda x: x.strip(), names.split(",")))
        
        if self._d_._bLink_:
            namesList.append("emblem-symbolic-link")
            
        if not self.isReadable():
            names.append("emblem-locked")
            
        if checkDesktopFile(self, False):
            # TODO: 
            # KDesktopFile cfg(localPath());
            # const KConfigGroup group = cfg.desktopGroup();
            # 
            # // Add a warning emblem if this is an executable desktop file
            # // which is untrusted.
            # if (group.hasKey("Exec") && !KDesktopFile::isAuthorizedDesktopFile(localPath())) {
            #     names.append(QStringLiteral("emblem-important"));
            # }
            pass
        
        if self.isHidden():
            names.append("hidden")
            
        if sys.platform != "win32":
            if self.isDir():
                url, mlu = self.isMostLocalUrl()
                if mlu:
                    path = url.toLocalFile()
                    # TODO:
                    # if (KSambaShare::instance()->isDirectoryShared(path) || KNFSShare::instance()->isDirectoryShared(path)) {
                    #     names.append(QStringLiteral("emblem-shared"));
                    # }
        return names
    
    def mimeComment(self) -> str:#TODO
        return self._mimeComment_
    
    # @property
    def iconName(self) -> str:
        return self._iconName_
    
    # # @iconName.setter
    # def iconName(self, val:str):
    #     self._iconName_ = val
        
    # @property
    def overlays(self) -> list[str]:
        return self._overlays_
    
    # # @overlays.setter
    # # def overlays(self, val:typing.List[str]):
    # def overlays(self, val:list):
    #     self._overlays_ = val
        
    # @property
    def comment(self) -> str:
        return self._comment_
    
    # # @comment.setter
    # def comment(self, val:str):
    #     self._comment_ = val
        
    # @property
    def isRegularFile(self) -> bool:
        if self._d_ is None:
            return False
        self._d_.ensureInitialized()
        return utils.isRegFileMask(self._d_._fileMode_)
    
    # # @isRegularFile.setter
    # def isRegularFile(self, val:bool):
    #     self._isRegularFile_ = val == True
    
    def permissionString(self) -> str:
        if self._d_ is None:
            return str()
        
        self._d_.ensureInitialized()
        
        if len(self._d_._access_) == 0 and self._d_._permissions_ != self.Unknown:
            self._d_._access_ = self._d_.parsePermissions(self._d_._permissions_)
            
        return self._d_._access_
        
    
    def permissions(self) -> int:
        if self._d_ is None:
            return 0
        self._d_.ensureInitialized()
        return self._d_._permissions_
        
    def mode(self) -> int:
        if self._d_ is None:
            return 0
        self._d_.ensureInitialized()
        return self._d_._fileMode_
    
    def suffix(self) -> str:
        if self._d_ is None or self.isDir():
            return str()
        
        pp = pathlib.Path(self._d_._strText_)
        return pp.suffix() # TODO check if right

    def size(self) -> int:
        if self._d_ is None:
            return 0
        return self._d_.recursiveSize()
    
    def recursiveSize(self) -> int:
        if self._d_ is None:
            return 0
        
        return self._d_.recursiveSize()
    
    def hasExtendedACL(self) -> bool:
        if self._d_ is None:
            return False
        return self.entry().contains(UDSEntry.UDS_EXTENDED_ACL)
    
    def ACL(self):
        # FIXME: 2025-01-08 17:51:03 TODO
        scipywarn("Access Control lists not yet imlemented")
        return None
    
    def defaultACL(self):
        # FIXME: 2025-01-08 17:51:03 TODO
        scipywarn("Access Control lists not yet imlemented")
        return None
    
    def entry(self) -> UDSEntry:
        if self._d_ is None:
            return UDSEntry()
        self._d_.ensureInitialized()
        return self._d_._entry_
    
    def isNull(self) -> bool:
        return self._d_ is None
    
    def exists(self) -> bool:
        if self._d_ is None:
            return False
        
        if not self._d_._bInitCalled_:
            scipywarn(f"FileItem: exists called when not initialized ({self._d_._url_})")
            return False
        
        return self._d_._fileMode_ != self.Unknown
    
    def isExecutable(self) -> bool:
        if self._d_ is None: 
            return False
        
        self._d_.ensureInitialized()
        
        if self._d_._permissions_ == self.Unknown:
            return False
        
        executableMask = stat.S_IXGRP | stat.S_IXUSR | stat.S_IXOTH
        if self._d_._permissions_ & executableMask == 0:
            return False
        
        if sys.platform == "win32":
            return stat.S_IXUSR & self._d_._permissions_ > 0
        else:
            uid = self.userId()
            if uid != -1:
                if uid == og.getuid():
                    return stat.S_IXUSR & self._d_._permissions_ > 0
                
                gid = self.groupId()
                if gid != -1:
                    groups = os.getgroupslist(os.getlogin(), os.getgid())
                    if gid in groups:
                        return stat.S_IXGRP & self._d_._permissions_ > 0
                    return stat.S_IXOTH & self._d_._permissions_ > 0
            else:
                return False

def checkDesktopFile(item:FileItem, detMimeType:bool):
    if not item.isMostLocalUrl().local:
        return False
    
    if not item.isRegularFile():
        return False
    
    if not item.isReadable():
        return False
    
    mime = item.determineMimeType() if detMimeType else item.currentMimeType()
    
    return mime.inherits("application/x-xdesktop")
