# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import os, sys, pathlib
import dataclasses
import psutil
from enum import Enum, IntEnum
from . import networkmounts
from iolib.navigation.networkmounts import (NetworkMounts, NetworkMountsType)

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

def typeFromName(name:str):
    from core.prog import scipywarn
    found = list(filter(lambda x: x.name == name, fsMap))
    if len(found):
        if len(found) > 1:
            scipywarn(f"Ambiguous file system type detection for '{name}'")
        return found[0].type
    
    return FsType.Other

def determineFileSystemType(path:str) -> FsType:
    if sys.platform == "win32":
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
    netMounts = NetworkMounts.instance()
    if netMounts.isSlowPath(path, NetworkMountsType.SmbPaths):
        return FsType.Smb
    elif netMounts.isSlowPath(path, NetworkMountsType.NfsPaths):
        return FsType.Nfs
    else:
        return determineFileSystemType(path)
        
def fileSysteName(ftype:FsType) -> str:
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

    
