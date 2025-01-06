# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
import sys, os, stat
"""

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

