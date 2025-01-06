# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import dataclasses
from enum import Enum, IntEnum

class Type(IntEnum):pass

Type = IntEnum("Type", ["Unknown", 
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
    type:Type = dataclasses.field(default = Type.Unknown)
    name:str = dataclasses.field(default_factory = str)
    
