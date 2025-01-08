# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
#define QT_STAT_MASK            S_IFMT
#define QT_STAT_REG             S_IFREG
#define QT_STAT_DIR             S_IFDIR
#define QT_STAT_LNK             S_IFLNK
# ### BEGIN python library stat.py
# S_IFMT() -> mask is 0o170000  # NOTE: flag is NOT available in stat module, but proided below as STAT_MASK
# S_IMODE() -> mask is 0o7777   # NOTE: stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO == 0o0777
#                               # therefore (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO | stat.S_ISVTX) & 0o7777 == 1023
# S_IFDIR  = 0o040000  # directory
# S_IFCHR  = 0o020000  # character device
# S_IFBLK  = 0o060000  # block device
# S_IFREG  = 0o100000  # regular file
# S_IFIFO  = 0o010000  # fifo (named pipe)
# S_IFLNK  = 0o120000  # symbolic link
# S_IFSOCK = 0o140000  # socket file
#
# # Fallbacks for uncommon platform-specific constants
# S_IFDOOR = 0
# S_IFPORT = 0
# S_IFWHT = 0
#
# # Names for permission bits - NOTE: all these below are available in stat module
# 
# S_ISUID = 0o4000  # set UID bit
# S_ISGID = 0o2000  # set GID bit
# S_ENFMT = S_ISGID # file locking enforcement
# S_ISVTX = 0o1000  # sticky bit
# S_IREAD = 0o0400  # Unix V7 synonym for S_IRUSR
# S_IWRITE = 0o0200 # Unix V7 synonym for S_IWUSR
# S_IEXEC = 0o0100  # Unix V7 synonym for S_IXUSR
# S_IRWXU = 0o0700  # mask for owner permissions
# S_IRUSR = 0o0400  # read by owner
# S_IWUSR = 0o0200  # write by owner
# S_IXUSR = 0o0100  # execute by owner
# S_IRWXG = 0o0070  # mask for group permissions
# S_IRGRP = 0o0040  # read by group
# S_IWGRP = 0o0020  # write by group
# S_IXGRP = 0o0010  # execute by group
# S_IRWXO = 0o0007  # mask for others (not in group) permissions
# S_IROTH = 0o0004  # read by others
# S_IWOTH = 0o0002  # write by others
# S_IXOTH = 0o0001  # execute by others
# 
# # Names for file flags
# UF_SETTABLE  = 0x0000ffff  # owner settable flags
# UF_NODUMP    = 0x00000001  # do not dump file
# UF_IMMUTABLE = 0x00000002  # file may not be changed
# UF_APPEND    = 0x00000004  # file may only be appended to
# UF_OPAQUE    = 0x00000008  # directory is opaque when viewed through a union stack
# UF_NOUNLINK  = 0x00000010  # file may not be renamed or deleted
# UF_COMPRESSED = 0x00000020 # macOS: file is compressed
# UF_TRACKED   = 0x00000040  # macOS: used for handling document IDs
# UF_DATAVAULT = 0x00000080  # macOS: entitlement needed for I/O
# UF_HIDDEN    = 0x00008000  # macOS: file should not be displayed
# SF_SETTABLE  = 0xffff0000  # superuser settable flags
# SF_ARCHIVED  = 0x00010000  # file may be archived
# SF_IMMUTABLE = 0x00020000  # file may not be changed
# SF_APPEND    = 0x00040000  # file may only be appended to
# SF_RESTRICTED = 0x00080000 # macOS: entitlement needed for writing
# SF_NOUNLINK  = 0x00100000  # file may not be renamed or deleted
# SF_SNAPSHOT  = 0x00200000  # file is a snapshot file
# SF_FIRMLINK  = 0x00800000  # macOS: file is a firmlink
# SF_DATALESS  = 0x40000000  # macOS: file is a dataless object
# ### END python library stat.py
#
#                       file owner                  group                       permissions for
#                       permissions                 permissions                 others (not in group)
#  S_IFMT               (Read/Write/Exec User)      (Read/Write/Exec Group)     (Read/Write/Exec Others)
# (QT_STAT_MASK - 1)  | S_IRWXU                 |   S_IRWXG                 |   S_IRWXO

import sys, os, stat, pathlib
from enum import IntEnum

STAT_MASK = 0o170000

class StatDetail(IntEnum):
    # /// No field returned, useful to check if a file exists
    StatNoDetails = 0x0
    # /// Filename, access, type, size, linkdest
    StatBasic = 0x1 # mask |= STATX_SIZE | STATX_TYPE; in stat_unix.h
    # /// uid, gid
    StatUser = 0x2
    # /// atime, mtime, btime
    StatTime = 0x4
    # /// Resolve symlinks
    StatResolveSymlink = 0x8
    # /// ACL data
    StatAcl = 0x10
    # /// dev, inode
    StatInode = 0x20
    # /// Recursive size
    # /// @since 5.70
    StatRecursiveSize = 0x40
    # /// MIME type
    # /// @since 5.82
    StatMimeType = 0x80

    # /// Default StatDetail flag when creating a @c StatJob.
    # /// Equivalent to setting <tt>StatBasic | StatUser | StatTime | StatAcl | StatResolveSymlink</tt>
    StatDefaultDetails = StatBasic | StatUser | StatTime | StatAcl | StatResolveSymlink
    
def getLstat(path:pathlib.Path, details:StatDetail): # not sure I really need this in Python
    pass
    
    
def isRegFileMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a regular file"""
    return stat.S_ISREG(mode) > 0

def isDirMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a directory"""
    return stat.S_ISDIR(mode) > 0

def isLinkMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a symbolic link"""
    return stat.S_ISLNK(mode) > 0

def isBlockMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a block special device file.
    A block device is randomly accessible (buffered) a disk partition or volume, 
    peripheral device etc; see also character device
    """
    return stats.S_ISBLK(mode) > 0

def isChrMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a character special device file.
    A character device provide only a serial stream of input or accept a serial 
    stream of outputs e.g., a terminal, disk partition, "raw" hardware device
    """
    return stat.S_ISCHR(mode) > 0

def isSockMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a socket.
    A socket allows bi-directional point-to-point inter-process communication.
    E.g., a network device.
    """
    return stat.S_ISSOCK(mode) > 0

def isDoorMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a Solaris door"""
    return stat.S_ISDOOR(mode) > 0

def isFifoMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a FIFO (named pipe).
    Named pipes allow unidirectional inter-process communication.
    Examples: lyxpipe.in, lyxpipe.out:
    prw------- 1 cezar users      0 Jan  5 22:41 lyxpipe.in
    prw------- 1 cezar users      0 Jan  5 22:41 lyxpipe.out
    
    """
    return stat.S_ISFIFO(mode) > 0

def isPortMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from an event port"""
    return stat.S_ISPORT(mode) > 0

def isWhtMask(mode:int)->bool:
    """Returns True if the st_mode 'mode' is from a whiteout.
    See 
https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html#whiteouts-and-opaque-directories
    """
    return stat.S_ISWHT(mode) > 0

