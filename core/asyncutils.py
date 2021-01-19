# -*- coding: utf-8 -*-
"""Coroutines and tasks
"""

import asyncio, subprocess, signal, sys, os
from subprocess import (PIPE, Popen,)
from notebook import notebookapp as nbapp

async def asyncstart_jupyter_notebook():
    nbapp.launch_new_instance()

def launch_jupyter_notebook_test1():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncstart_jupyter_notebook())
    loop.close()
    
#def test_run():
    ## invalid syntax
    #return await nbapp.launch_new_instance()
    ##await asyncstart_jupyter_notebook()
    
def launch_jupyter_notebook(browser:str="firefox", redirect=False):
    """Launch jupter notebook server as a separate process as if from a shell.
    """
    # ATTENTION: 2021-01-19 21:56:34
    # all code versions below are syntactically correct; all up to and excluding
    # NOTE: 2021-01-19 21:57:54  achieve the same thing; differences are explained
    # in NOTE comments
    
    # NOTE: 2021-01-19 21:30:27
    # OK but it is blocking; 
    # stderr and std are NOT redirected: they are sent to the process that 
    # started scipyen; if that is a shell (terminal), they will be displayed 
    # there; if that is systemd (on Linux);they appear in the system's logs 
    # 
    # returns once the server has quit normally
    #return subprocess.run(("jupyter", "notebook", "--browser", "firefox"))
    
    # NOTE: 2021-01-19 21:34:10 
    # Same effect as above; shell True means that args is now one string with
    # the complete command line as if input in a shell and the proces is launched
    # via the OS shell.
    #return subprocess.run(args=("jupyter notebook --browser=firefox"), shell=True)
    #return subprocess.run(args="jupyter notebook --browser=google-chrome", shell=True)
    #return subprocess.run("jupyter notebook --browser=firefox", shell=True)

    # NOTE 2021-01-19 21:54:23
    #return subprocess.run(("jupyter", "notebook", "--browser", browser))
    
    # NOTE: 2021-01-19 21:54:28
    #return subprocess.run(("jupyter", "notebook", "--browser", browser), start_new_session=True)

    # NOTE: 2021-01-19 21:57:54 below, stdout and stderr are captures in the 
    # returned CompletedProcess attributes 'stdout' and 'stderr', respectively.
    #return subprocess.run(("jupyter", "notebook", "--browser", browser), stdout = PIPE)
    
    if redirect:
        return subprocess.run(("jupyter", "notebook", "--browser", browser), 
                            stdout = PIPE, stderr = PIPE)
    
    else:
        return subprocess.run(("jupyter", "notebook", "--browser", browser))
    



def popen_jupyter_notebook(browser:str="firefox", redirect=False):
    """Launch jupter notebook server as a separate process as if from a shell.
    """
    # NOTE: 2021-01-19 22:08:23
    # Does NOT block; the Popen object is returned immediately.
    #return Popen(("jupyter", "notebook", "--browser", browser))
    
    # NOTE: 2021-01-19 22:11:57
    # Allow communication with the process via Popen.communicate() method.
    # all standard streams are redirected so that we can read this process output
    # and we can shut it down via Control-C
    
    # ATTENTION: p.communicate() actually blocks! you won;t get anything until
    # the process has been shutdown, and then you only get one change to retrieve
    # its (stdout, strderr) tuple
    if redirect:
        return Popen(("jupyter", "notebook", "--browser", browser),
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
    else:
        return Popen(("jupyter", "notebook", "--browser", browser))
    
def shutdown_jupyter_notebook_popen(p):
    """NOTE: REDUNDANT: Can also use p.terminate() to send SIGTERM on all platforms
    """
    if os.name == "nt":
        os.kill(p.pid, signal.CTRL_C_EVENT)
    else:
        os.kill(p.pid, signal.SIGTERM) # interrupt from keyboard
        #os.kill(p.pid, signal.SIGINT) # interrupt from keyboard

def kill_process_gracefully(p, sig=None):
    """ Run man 7 signal for what signals are there in Unix
    """
    if not sig:
        if os.name == "nt":
            os.kill(p.pid, signal.CTRL_C_EVENT)
        else:
            os.kill(p.pid, signal.SIGINT) # interrupt from keyboard
            
    else:
        os.kill(p.pid, sig) # interrupt from keyboard
        
    
    
    
