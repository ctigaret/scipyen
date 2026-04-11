# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

r"""Capture & redirect output from 3rd party C/C++ libraries

Inspired from code by Eli Bendersky

https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/#id1
"""
import typing, traceback
from contextlib import contextmanager
import ctypes
import io
import os, sys
import tempfile

libc = ctypes.CDLL(None)
c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

@contextmanager
def stdout_redirector(stream):
    r"""FIXME: 2021-11-30 15:04:24
    Subsequent error messages from Python code(via sys.stderr) do not show up 
    anymore until after Scipyen has been closed. 
    """
    libc = ctypes.CDLL(None)
    c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
    #c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stdout_fd = sys.stdout.fileno()

    def _redirect_(to_fd):
        r"""Redirect stdout to the given file descriptor."""
        # Flush the C-level buffer stdout
        libc.fflush(c_stdout)
        # Flush and close sys.stdout - also closes the file descriptor (fd)
        sys.stdout.close()
        # Make original_stdout_fd point to the same file as to_fd
        os.dup2(to_fd, original_stdout_fd)
        # Create a new sys.stdout that points to the redirected fd
        sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, 'wb'))

    # Save a copy of the original stdout fd in saved_stdout_fd
    saved_stdout_fd = os.dup(original_stdout_fd)
    try:
        # Create a temporary file and redirect stdout to it
        tfile = tempfile.TemporaryFile(mode='w+b')
        _redirect_(tfile.fileno())
        # Yield to caller, then redirect stdout back to the saved fd
        yield
        _redirect_(saved_stdout_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read().decode())
    finally:
        tfile.close()
        os.close(saved_stdout_fd)
        
@contextmanager
def stderr_redirector(stream):
    #libc = ctypes.CDLL(None)
    #c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
    #c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

    print(type(sys.stderr))
    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stderr_fd = sys.stderr.fileno()
    #print("original", original_stderr_fd)
    #system_stderr_fd = sys.stderr.fileno() # also save this

    def _redirect_(to_fd):
        r"""Redirect stderr to the given file descriptor."""
        # Flush the C-level buffer stderr
        libc.fflush(c_stderr)
        
        # Flush and close sys.stderr - also closes the file descriptor (fd)
        sys.stderr.close()
        
        # Make original_stderr_fd point to the same file as to_fd:
        # duplicate to_fd to original_stderr_fd;
        #print(f"in _redirect_ before dup2: to_fd: {to_fd}, original_stderr_fd, {original_stderr_fd}")
        os.dup2(to_fd, original_stderr_fd)
        #print(f"in _redirect_ after dup2: to_fd: {to_fd}, original_stderr_fd, {original_stderr_fd}")
        # now 'original_stderr_fd' is a duplicate of 'to_fd'
        
        # Create a new sys.stderr that points to the redirected fd
        sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, 'wb'))
        
        #original_stderr= os.fdopen(original_stderr_fd, 'wb')
        #print(type(original_stderr))
        #sys.stderr = io.TextIOWrapper(original_stderr)
        #original_stderr.flush()
        #print(type(original_stderr.fileno()))
        #os.fsync(original_stderr_fd)

    # Save a copy of the original stderr fd in saved_stderr_fd
    saved_stderr_fd = os.dup(original_stderr_fd)
    #print("saved", saved_stderr_fd)
    try:
        # Create a temporary file and redirect stderr to it
        tfile = tempfile.TemporaryFile(mode='w+b')
        # this call duplictes tfile's fd to original_stderr_fd and replaces
        # sys.stderr with a new stream fdopen-ed on tfile's fd
        _redirect_(tfile.fileno())
        # Yield to caller, then redirect stderr back to the saved fd
        yield
        # next: duplicates saved_stderr_fd to original_stderr_fd; replaces
        # sys.stderr with a new one fdopen-ed on saved_stderr_fd
        _redirect_(saved_stderr_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        #sys.stderr.write(tfile.read().decode())
        stream.write(tfile.read().decode())
    #except: # NOTE: 2021-11-30 14:48:20
        #traceback.print_exc()
        #_redirect_(saved_stderr_fd)
        ## Copy contents of temporary file to the given stream
        #tfile.flush()
        #tfile.seek(0, io.SEEK_SET)
        #sys.stderr.write(tfile.read().decode())
        ##stream.write(tfile.read().decode())
    finally:
        #print("finally: saved", saved_stderr_fd)
        #print("finally: original", original_stderr_fd)
        #print(saved_stderr_fd is original_stderr_fd)
        tfile.close()
        os.close(saved_stderr_fd)
        sys.stderr = sys.__stderr__
        #os.fsync(original_stderr_fd) # invalid argument!
        #original_stderr_fd = os.dup(saved_stderr_fd)
        #sys.stderr = io.TextIOWrapper(os.fdopen(system_stderr_fd, 'wb'))
        
        
