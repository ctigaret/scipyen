"""Capture & redirect output from 3rd party C/C++ libraries

Inspired from code by Eli Bendersky

https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/#id1
"""
import typing, traceback
from contextlib import contextmanager
import ctypes
import io
import os, sys
import tempfile

#libc = ctypes.CDLL(None)
#c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
#c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

#@contextmanager
#def output_stream_redirector(stream, 
                             #what:typing.Optional[typing.Union[io.TextIOWrapper, str, int]]=sys.stdout):
    #if isinstance(what, str):
        #if what.lower() not in ("out", "stdout", "err", "stderr"):
            #p_stream = sys.stdout
            #c_stream = c_stdout
            ##raise ValueError(f"Incorrect output stream specification; expecting 'out' or 'err' got {what}")
        #else:
            ## NOTE: this is the python stream
            #p_stream = sys.stderr if what.lower() in ("err", "stderr") else sys.stdout
            #c_stream = c_stderr if what.lower() in ("err", "stderr") else c_stdout
        
    #elif isinstance(what, int):
        #if what not in (1,2):
            #p_stream = sys.stdout
            #c_stream = c_stdout
            ##raise ValueError(f"Incorrect output stream descriptor; expecting one of 1, 2; got {what}")
        #else:
            #p_stream = sys.stderr if what == 2 else sys.stdout
            #c_stream = c_stderr if what == 2 else c_stdout
        
        ##original_fd = what
            
    #elif what in (sys.stdout, sys.stderr):
        #p_stream = what
        #c_stream = c_stderr if what is sys.stderr else c_stdout
        
    #else:
        #p_stream = sys.stdout
        #c_stream = c_stdout
        ##raise TypeError(f"Expecting an one of sys.stdout or sys.stderr; got {type(what).__name__}")
        
    #original_fd = p_stream.fileno()
    
    ## NOTE: 2021-11-30 12:36:29
    ## The original fd points to. On POSIX systems this is isually 1 for stdout
    ## and 2 for stderr
    ##original_stdout_fd = sys.stdout.fileno()

    #def _redirect_(ostr, to_fd):
        #"""Redirect stdout to the given file descriptor."""
        ## Flush the C-level buffer stdout
        #libc.fflush(c_stream)
        ## Flush and close sys.stdout - also closes the file descriptor (fd)
        #ostr.close()
        ## Make original_stdout_fd point to the same file as to_fd
        #os.dup2(to_fd, original_fd)
        ## Create a new sys.stdout that points to the redirected fd
        #ostr = io.TextIOWrapper(os.fdopen(original_fd, 'wb'))
        #return ostr

    ## Save a copy of the original stdout fd in saved_stdout_fd
    #saved_fd = os.dup(original_fd)
    
    #try:
        ## Create a temporary file and redirect stdout to it
        #tfile = tempfile.TemporaryFile(mode='w+b')
        #p_stream = _redirect_(p_stream, tfile.fileno())
        ## Yield to caller, then redirect stdout back to the saved fd
        #yield
        #p_stream = _redirect_(p_stream, saved_fd)
        ## Copy contents of temporary file to the given stream
        #tfile.flush()
        #tfile.seek(0, io.SEEK_SET)
        #stream.write(tfile.read().decode())
    #finally:
        #tfile.close()
        #os.close(saved_fd)
        
@contextmanager
def stdout_redirector(stream):
    """FIXME: 2021-11-30 15:04:24
    Subsequent error messages from Python code(via sys.stderr) do not show up 
    anymore until after Scipyen has been closed. 
    """
    libc = ctypes.CDLL(None)
    c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
    #c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stdout_fd = sys.stdout.fileno()

    def _redirect_(to_fd):
        """Redirect stdout to the given file descriptor."""
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
    libc = ctypes.CDLL(None)
    #c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
    c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stderr_fd = sys.stderr.fileno()
    print("original", original_stderr_fd)
    #system_stderr_fd = sys.stderr.fileno() # also save this

    def _redirect_(to_fd):
        """Redirect stderr to the given file descriptor."""
        # Flush the C-level buffer stderr
        libc.fflush(c_stderr)
        # Flush and close sys.stderr - also closes the file descriptor (fd)
        sys.stderr.close()
        # Make original_stderr_fd point to the same file as to_fd:
        # duplicate to_fd to original_stderr_fd;
        print(f"in _redirect_ before dup2: to_fd: {to_fd}, original_stderr_fd, {original_stderr_fd}")
        os.dup2(to_fd, original_stderr_fd)
        print(f"in _redirect_ after dup2: to_fd: {to_fd}, original_stderr_fd, {original_stderr_fd}")
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
    print("saved", saved_stderr_fd)
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
        print("finally: saved", saved_stderr_fd)
        print("finally: original", original_stderr_fd)
        #print(saved_stderr_fd is original_stderr_fd)
        tfile.close()
        os.close(saved_stderr_fd)
        #os.fsync(original_stderr_fd) # invalid argument!
        #original_stderr_fd = os.dup(saved_stderr_fd)
        #sys.stderr = io.TextIOWrapper(os.fdopen(system_stderr_fd, 'wb'))
        
        
