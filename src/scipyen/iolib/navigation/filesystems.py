# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""
"""
import os, sys, pathlib, traceback, typing, types, stat, datetime # noqa
import dataclasses
import psutil
from functools import (singledispatch, singledispatchmethod) # noqa
from enum import Enum, IntEnum # noqa
import qtpy
from qtpy import (QtCore, QtGui, QtWidgets, QtXml, QtSvg, QtNetwork, ) # noqa
from qtpy.QtCore import (Signal, Slot, Property,) # noqa
__has_PySide6__ = False
__has_PyQt6__ = False
__has_sip__ = False
if os.environ["QT_API"] == "pyside6":
    __has_PySide6__ = True
    import PySide6
    from PySide6 import Shiboken
    # from PySide6.QtCore import (Signal, Slot, Property,)
    from PySide6.QtUiTools import loadUiType # -- A-HA!
    QAction = QtGui.QAction
    QActionGroup = QtGui.QActionGroup
    QShortcut = QtGui.QShortcut
else:
    if os.environ["QT_API"] == "pyqt6":
        __has_PyQt6__ = True

    from qtpy import sip
    from qtpy.uic import loadUiType
    QAction = QtWidgets.QAction
    QActionGroup = QtWidgets.QActionGroup
    QShortcut = QtWidgets.QShortcut
    __has_sip__ = True

# from gui.itemmodels.filesystemmodel import FileSystemModel
# from . import networkmounts
# from iolib.navigation.networkmounts import (NetworkMounts, NetworkMountsType)

# NOTE: 2026-01-23 14:45:04
# "standard" file system item operations for the file system viewer - single item selected
#
#                               Shown for   Enabled if:                                         Acts on:
#                               item type   item permissions        parent item permissions
#                                           ReadOwner|WriteOwner|   ReadOwner|WriteOwner|ReadGroup|WriteGroup
#                                           ReadGroup|WriteGroup
# ---------------------------------------------------------------------------------------------------------
# Create New -> submenu         directory                                                       item
# Cut                           all                                 WriteOwner|WriteGroup       item
# Copy                          all                                                             item
# Copy location                 all                                                             item
# Paste Clipboard Contents      directory                                                       item
# Duplicate here                all         ReadOwner|WriteOwner    WriteOwner|WriteGroup       parent item
# Rename                        all                                 WriteOwner|WriteGroup       parent item, item
# Move to Trash                 all                                 WriteOwner|WriteGroup       parent item
# Delete                        all                                 WriteOwner|WriteGroup       parent item
# ----------------------------------------------------------------------------------------------------------
#
#                                                                   NOTE: when parent item (always a directory)
#                                                                   is not readable the tree should collapse and hide its contents
#                                                                   thjerefore, ReadOwner is implied to be True, in this column

# class FileSystemItemData:
#     def __init__(self, value):
#         self.value = value
#
# FileSystemItemDataType = QtCore.QMetaType.registerType(FileSystemItemData, "FileSystemItemData")

class FsType(IntEnum):pass
FsType = IntEnum("FsType",
                 ["Unknown",
                   "Nfs",          # NFS or other full-featured networked filesystems (autofs, subfs, cachefs, sshfs)
                   "Smb",          # SMB/CIFS mount (networked but with some FAT-like behavior)
                   "Fat",          # FAT or similar (msdos, FAT, VFAT)
                   "Ramfs",        # RAMDISK mount
                   "Other",        # Ext3, Ext4, ReiserFs, and so on. "Normal" local filesystems.
                   "Ntfs",         # NTFS filesystem
                   "Exfat",        # ExFat filesystem
                   "Fuse"          # FUSE (Filesystem in USErspace), this is used for a variety of underlying file systems
                 ])


@dataclasses.dataclass
class FsInfo:
    type:FsType = dataclasses.field(default = FsType.Unknown)
    name:str = dataclasses.field(default_factory = str)

fsMap = [
        FsInfo(FsType.Nfs, "nfs"),
        FsInfo(FsType.Nfs, "nfs4"),
        FsInfo(FsType.Smb, "smb"),
        FsInfo(FsType.Fat, "fat"),
        FsInfo(FsType.Ramfs, "ramfs"),
        FsInfo(FsType.Other, "other"),
        FsInfo(FsType.Ntfs, "ntfs"),
        FsInfo(FsType.Ntfs, "ntfs3"),
        FsInfo(FsType.Exfat, "exfat"),
        FsInfo(FsType.Unknown, "unknown"),
        FsInfo(FsType.Nfs, "autofs"),
        FsInfo(FsType.Nfs, "cachefs"),
        FsInfo(FsType.Nfs, "fuse.sshfs"),
        FsInfo(FsType.Nfs, "xtreemfs@"), # #178678
        FsInfo(FsType.Smb, "smbfs"),
        FsInfo(FsType.Smb, "cifs"),
        FsInfo(FsType.Fat, "vfat"),
        FsInfo(FsType.Fat, "msdos"),
        FsInfo(FsType.Fuse, "fuseblk"),
    ]

class FileOperationJob(QtCore.QObject):
    sig_finished = Signal(name="sig_finished") # noqa
    def __init__(self, parent:typing.Optional[QtCore.QObject]=None):
        self.loopControl:dict = {"break": False}
        self.progressCounter:int = 0

        QtCore.QObject.__init__(self, parent=parent)

    @Slot(object)
    def workerReady(self, obj):
        self.loopControl["break"] = False
        self.sig_finished.emit()

    def run(self, source: typing.Sequence[pathlib.Path],
                 destination: typing.Sequence[pathlib.Path],
                 jobType:str = "copy"):
        from core.strutils import pluralize
        from gui import pictgui as pgui
        self.progressCounter = 0

        nFiles = len(source)

        subDirs = list(filter(lambda p: p.is_dir(), source))

        for subDir in subDirs:
            nFiles += self._countEntries_(QtCore.QDir(subDir.as_posix()))

        if not isinstance(jobType, str) or len(jobType.strip()) == 0 or jobType.lower() not in ("copy","move", "trash", "delete"):
            raise ValueError(f"Unknown transfer job type {jobType}; allowed values are 'copy', 'move', 'trash', 'delete'")

        transferName = "Moving" if jobType=="move" else "Copying"
        progressDlg = QtWidgets.QProgressDialog(f"{transferName} {nFiles} {pluralize('File', nFiles)}...",
                                                "Abort", 0, nFiles, parent=self.parent())
        progressDlg.setMinimumDuration(1000)
        progressDlg.canceled.connect(self._slot_breakLoop)
        kw = {"source": source, "destination": destination, "jobType": jobType,
              "loopControl": self.loopControl} # noqa
        workerThread = pgui.LoopWorkerThread(self, self._operateFile_, **kw)
        workerThread.signals.signal_Progress[int].connect(progressDlg.setValue)
        workerThread.signals.signal_Result[object].connect(self.workerReady)
        workerThread.signals.signal_Finished.connect(progressDlg.reset)
        workerThread.start()

    @Slot()
    def _slot_breakLoop(self):
        r"""To be connected to the `canceled` signal of a progress dialog.
        Modifies the loopControl variable to interrupt a worker loop gracefully.
        """
        self.loopControl["break"] = True

    def _countEntries_(self, directory:QtCore.QDir) -> int:
        if not directory.exists():
            return 0

        count = len(directory.entryList(QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllEntries))

        for subDir in directory.entryList(QtCore.QDir.NoDotAndDotDot|QtCore.QDir.Dirs):
            count += self._countEntries_(QtCore.QDir(directory.filePath(subDir)))

        return count

    def _operateFile_(self, **kwargs) -> bool:
        from core.prog import scipywarn
        # print(f"{self.__class__.__name__}._operateFile_: kwargs = {kwargs}")
        jobType: str = kwargs.pop("jobType", "copy")
        source: typing.optional[typing.Sequence[pathlib.Path]] = kwargs.pop("source", list())
        destination: typing.Optional[typing.Sequence[pathlib.Path]] = kwargs.pop("destination", list())
        loopControl = kwargs.pop("loopControl", None) # noqa
        progressSignal = kwargs.pop("progressSignal", None) # noqa
        canceledSignal = kwargs.pop("canceledSignal", None) # noqa

        # print(f"{self.__class__.__name__}._operateFile_: jobType = {jobType}")
        if len(source) == 0:
            return

        if len(source) != len(destination) and jobType not in ("trash", "delete"): # noqa
            scipywarn(f"Mismatch between number of source ({len(source)}) and destination files ({destination})")
            return

        self.progressCounter = 0

        OK = True

        canceled = False # noqa

        if jobType == "trash": # noqa
            for src in source:
                srcFile = QtCore.QFile(src.as_posix())
                result = srcFile.moveToTrash()
                OK &= result
                if result:
                    self.progressCounter += 1

        elif jobType == "delete":
            for src in source:
                if src.is_file():
                    srcFile = QtCore.QFile(src.as_posix())
                    result = srcFile.remove()
                    OK &= result
                    if result:
                        self.progressCounter += 1
                elif src.is_dir():
                    srcDir = QtCore.QDir(src.as_posix())
                    result = srcDir.removeRecursively()
                    OK &= result
                    if result:
                        self.progressCounter += 1

        else:
            for k, src in enumerate(source):
                try:
                    s = src.as_posix()
                    d = destination[k].as_posix()
                    if src.is_file():
                        result = self._copyFile_(s,d)
                        if jobType == "move" and result:
                            srcFile = QtCore.QFile(src.as_posix())
                            result = srcFile.remove()
                    elif src.is_dir():
                        result = self._copyDirectory_(QtCore.QDir(s), QtCore.QDir(d))
                        if jobType == "move" and result:
                            srcDir = QtCore.QDir(src.as_posix())
                            result = srcDir.removeRecursively()

                    OK &= result

                    if OK and isinstance(progressSignal, QtCore.SignalInstance):
                        progressSignal.emit(self.progressCounter)
                except:
                    traceback.print_exc()
                    continue

                if isinstance(loopControl, dict) and loopControl.get("break", None) == True:
                    if isinstance(canceledSignal, QtCore.SignalInstance):
                        canceledSignal.emit()
                    break

        return OK

    def _copyFile_(self, src:str, dest:str) -> bool:
        self.progressCounter += 1
        if not QtCore.QFile.exists(src):
            scipywarn(f"Source file {src} does not exist")
            return False

        if QtCore.QFile.exists(dest):
            # remove destination first
            if not QtCore.QFile.remove(dest):
                scipywarn(f"Could not remove existing destination file {dest}")
                return False
        if not QtCore.QFile.copy(src, dest):
            scipywarn(f"Could not copy {src} to {dest}")
            return False

        return True

    def _copyDirectory_(self, src:QtCore.QDir, dest:QtCore.QDir) -> bool:
        self.progressCounter += 1
        if not src.exists():
            scipywarn(f"Source directory {src.fileName()} does not exist")
            return False

        if not dest.exists():
            dest.mkpath(".")

        entryInfoList = src.entryInfoList(QtCore.QDir.AllEntries | QtCore.QDir.NoDotAndDotDot)

        for entry in entryInfoList:
            newDestPath = dest.filePath(entry.fileName())
            if entry.isDir():
                if not self._copyDirectory_(entry.filePath(), newDestPath):
                    return False
            else:
                if not QtCore.QFile.copy(entry.filePath(), newDestPath):
                    scipywarn(f"Failed to copy {entry.filePath()} to {newDestPath}")
                    return False

        return True

def typeFromName(name:str):
    from core.prog import scipywarn
    found = list(filter(lambda x: x.name == name, fsMap))
    if len(found):
        if len(found) > 1:
            scipywarn(f"Ambiguous file system type detection for '{name}'")
        return found[0].type

    return FsType.Other

def determineFileSystemType(path:str) -> FsType:
    if sys.platform.startswith("win32"):
        return FsType.Unknown
    else:
        partitions = psutil.disk_partitions(True)
        ppath = pathlib.Path(path).absolute() # wrap in a pathlib.Path for the code below
                                             # and ensure this is absolute

        # NOTE: 2025-01-07 19:34:21
        # get the mount point for the partition where this path is located
        # • check that the mount point of the partitions reported by psutil is
        #   among the parents of the path (this is why path has to be wrapped in a pathlib.Path)
        #
        #   ∘ NOTE: In UNIX, this may return more than one mount point for a regular path
        #       (either file or directory). This is because ALL partitions are mounted
        #       in the root partition, which itself is mounted at the '/' mount point
        #
        #       A common example is that of a file in the user's home directory (that is '/home/<user_name>')
        #       physically located on a disk partition that is different from
        #       the one containing the root file system (not the 'root' user!):
        #
        #       This user home partition will be mounted in the root file system at
        #       some mount point (usually '/home'). Because the root file system is
        #       already mounted at the '/' mount point, psutils will report TWO disk
        #       partitions as residence for this file, with mount points, respectively,
        #       of '/' and '/home'. Bpth of these mount points are 'parents' of the file
        #       represented by 'path', with '/home' being obviously a descendant of '/'.
        #
        #       In the (unusual) case where a partition on an externaldisk (e.g.
        #       a hotplugged USB disk or 'key') is manually mounted by the user in
        #       their own home directory, there will be yet another mount point,
        #       in effect a descendant of '/home'.
        #
        #      Therefore the partition of interest here (the one corresponding to
        #      the physical place where the file resides) is the partition with
        #      the longest mount point naame (in characters)  i.e. the deepest nested
        #      "child path"
        #
        #   ∘ the next line returns to tuples:
        #       ▷ the first (mpl) has the length of the string representation of the mount point
        #       ▷ the second (mpp) is the partition on which the path exists
        mpl, mpp = zip(*list(map(lambda x: (len(x.mountpoint), x), filter(lambda x: x.mountpoint in map(lambda p: p.as_posix(), ppath.parents), partitions))))
        # (WARNING: not checking for the unlikely case here none of the mount points are among the path's parents)

        pathPartition = mpp[mpl.index(max(mpl))] # that is usually the last element in the list
        return typeFromName(pathPartition.fstype)

    pass

def fileSystemType(path:str) -> FsType:
    # netMounts = NetworkMounts.instance()
    # if netMounts.isSlowPath(path, NetworkMountsType.SmbPaths):
    #     return FsType.Smb
    # elif netMounts.isSlowPath(path, NetworkMountsType.NfsPaths):
    #     return FsType.Nfs
    # else:
    #     return determineFileSystemType(path)
    return determineFileSystemType(path)

def fileSystemName(ftype:FsType) -> str:
    # TODO 2025-01-07 19:03:57
    # figure out translations - what context here?
    match ftype:
        case FsType.Nfs:
            return "NFS"
            # return QCoreApplication::translate("KFileSystemType", "NFS");
        case FsType.Smb:
            return "SMB"
            # return QCoreApplication::translate("KFileSystemType", "SMB");
        case FsType.Fat:
            return "FAT"
            # return QCoreApplication::translate("KFileSystemType", "FAT");
        case FsType.Ramfs:
            return "RAMFS"
            # return QCoreApplication::translate("KFileSystemType", "RAMFS");
        case FsType.Other:
            return "Other"
            # return QCoreApplication::translate("KFileSystemType", "Other");
        case FsType.Ntfs:
            return "NTFS"
            # return QCoreApplication::translate("KFileSystemType", "NTFS");
        case FsType.Exfat:
            return "ExFAT"
            # return QCoreApplication::translate("KFileSystemType", "ExFAT");
        case FsType.Fuse:
            return "FUSE"
            # return QCoreApplication::translate("KFileSystemType", "FUSE");
        case FsType.Unknown:
            return "Unknown"
            # return QCoreApplication::translate("KFileSystemType", "Unknown");
        case _:
            return "Unknown"

def pathLen(x:pathlib.Path) -> int:
    return len(x.parts)

@singledispatch
def pathStrLen(x:typing.Any) -> int:
    raise NotImplementedError(f"Method is not implemented for objects of type {type(x).__name__}")

@pathStrLen.register(pathlib.Path)
def _(x:pathlib.Path) -> int:
    return len(x.absolute().as_posix())

@pathStrLen.register(str)
def _(x:str) -> int:
    s = x[x.index("://")+3:] # remove schema
    return len(s)

@pathStrLen.register(QtCore.QUrl)
def _(x:QtCore.QUrl) -> int:
    return len(x.path())

@singledispatch
def urlToPath(x:typing.Any) -> pathlib.Path | None:
    raise NotImplementedError(f"Method is not implemented for objects of type {type(x).__name__}")

@urlToPath.register(str)
def _(x:str) -> pathlib.Path | None:
    if "://" in x:
        s = x[x.index("://")+3:] # remove schema
    return pathlib.Path(x).absolute()

@urlToPath.register(QtCore.QUrl)
def _(x:QtCore.QUrl) -> pathlib.Path | None:
    # print(f"filesystems.urlToPath({x})\n\t scheme: {x.scheme()},\n\t path: {x.path()}")
    if x.scheme() != "file":
        return

    pathStr = x.path()

    if len(pathStr.strip()) == 0:
        return

    if sys.platform.startswith("win32"):
        if pathStr.startswith("/"):
            pathStr = pathStr[1:]
            path = pathlib.Path(pathStr)
            if pathLen(path) == 1: # figure out and path for windows drive
                if path.as_posix().endswith(":/"):
                    path = pathlib.Path(path.as_posix()[:-1])
                    return path

                if path.as_posix().endswith(":"):
                # this looks like a Windows drive string
                    return path

    return pathlib.Path(pathStr).absolute()

def pathToQUrl(x:pathlib.Path) -> QtCore.QUrl:
    drive = x.drive
    if len(drive) > 1 and drive.endswith(":"): # Windows path
        ppath = x.as_posix()[len(drive):]
        upath = f"file:///{drive}/{ppath}"
        return QtCore.QUrl(upath)
    else:
        return QtCore.QUrl(x)

def get_windows_drive_letters() -> list[str] | None:
    r"""Lists available drives in Windows"""
    # NOTE 2025-02-25 10:59:57
    # Thans to https://stackoverflow.com/questions/827371/is-there-a-way-to-list-all-the-available-windows-drives
    # (RichieHindle)

    isWin=sys.platform.startswith("win32")
    if isWin:
        try:
            from ctypes import windll
            import string
            isWin=True
        except:
            isWin=False
            pass

    if not isWin:
        # scipywarn("get_windows_drives() function is not supported on non-Windows platforms")
        return get_disk_partitions()

    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()

    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives

def get_disk_partitions(physical_only:bool=False, fixed_only:bool=False) -> list:
    partitions = psutil.disk_partitions(all=not physical_only)


    if sys.platform.startswith("win32"):
        if fixed_only:
            partitions = list(filter(lambda x: "fixed" in x.opts, paritions))
        return list(filter(lambda x: len(x.fstype) > 0, partitions))

    return partitions

def mountpoints(physical_only:bool=False, fixed_only:bool=False) -> list:
    p = get_disk_partitions(physical_only, fixed_only)

    return list(map(lambda x: x.mountpoint, p))

def deviceNames(physical_only:bool=False, fixed_only:bool=False) -> list:
    return list(map(lambda x: x.device, get_disk_partitions(physical_only, fixed_only)))

def networkFolders():
    p = get_disk_partitions(False)

    if sys.platform.startswith("win32"):
        return list(filter(lambda x: "remote" in x.opts, p))

    scipywarn("networkFolders function is not supported on non-Windows platforms")
    return p

def fsTypes():
    from core.utilities import unique
    return sorted(unique(list(map(lambda x: x.fstype, get_disk_partitions(False)))))

def getFileCreationDateTime(
    s: typing.Union[str, pathlib.Path],
    followSymLink: bool = False,
    ) -> datetime.datetime | None:
    if isinstance(s, str):
        s = pathlib.Path(s)

    elif not isinstance(s, pathlib.Path):
        raise TypeError(f"Expecting a string or a pathlib.Path object; got {type(s).__name__} instead")

    if s.exists():
        fs = s.lstat() if (s.is_symlink() and followSymLink) else s.stat()
        if hasattr(fs, "st_birthtime"):
            return datetime.datetime.fromtimestamp(fs.st_birthtime)
        else:
            return datetime.datetime.fromtimestamp(fs.st_ctime)






