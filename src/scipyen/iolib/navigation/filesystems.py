# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
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

def fileSystemType(path:str) -> FsType:
    netMounts = NetworkMounts.instance()
    if netMounts.isSlowPath(path, NetworkMountsType.SmbPaths):
        return FsType.Smb
    elif netMounts.isSlowPath(path, NetworkMountsType.NfsPaths):
        return FsType.Nfs
    else:
        return determineFileSystemType(path)
        
def fileSysteName(type:FsType) -> str:
    pass
    
