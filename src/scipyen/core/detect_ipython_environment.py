#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Created on Tue May  8 20:40:30 2018

@author: yanglei
https://gist.github.com/DIYer22/5cc015dcef53d62c16bdff0f8f345e96
"""
'''
# Detection Python Environment, Especially distinguish Spyder, Jupyter notebook, Qtconsole

As far as I know, Here has 3 kinds of ipython that used `ipykernel`

1. `ipython qtconsole` ("qtipython" for short)
2. IPython in spyder ("spyder" for short)
3. IPython in jupyter notebook ("jn" for short)


use `'spyder' in sys.modules` can distinguish spyder

but for qtipython and jn are hard to distinguish cause

they have same `sys.modules` and same IPython config:`get_ipython().config`

I find a different between qtipython and jn:

first run `os.getpid()` in IPython shell get the pid number

then run `ps -ef|grep [pid number]`

my qtipython pid is 8699
```
yanglei   8699  8693  4 20:31 ?        00:00:01 /home/yanglei/miniconda2/envs/py3/bin/python -m ipykernel_launcher -f /run/user/1000/jupyter/kernel-8693.json
```

my jn pid is 8832
```
yanglei   8832  9788 13 20:32 ?        00:00:01 /home/yanglei/miniconda2/bin/python -m ipykernel_launcher -f /run/user/1000/jupyter/kernel-ccb962ec-3cd3-4008-a4b7-805a79576b1b.json
```

the different of qtipython and jn is the ipython's json name, jn's json name are longer than qtipython's

so, we can auto detection all Python Environment by following code:
'''

import sys,os
pyv = sys.version_info.major
py3 = (pyv == 3)
py2 = (pyv == 2)

def jupyterNotebookOrQtConsole():
    #env = 'Unknow'
    # NOTE: 2021-01-15 17:08:28 cezar.tigaret@gmail.com
    # correct typo
    env = 'Unknown'
    cmd = 'ps -ef'
    try:
        with os.popen(cmd) as stream:
            if not py2:
                stream = stream._stream
            s = stream.read()
            
        #print("s", s)
        pid = os.getpid()
        #print("pid",pid)
        proclines = s.split("\n")
        
        procline = list(filter(lambda l: str(pid) in l, proclines))
        # print("process", procline)
        if len(procline) == 1:
            l = procline[0]
            import re
            pa = re.compile(r'kernel-([-a-z0-9]*)\.json')
            rs = pa.findall(l)
            # print("rs", rs)
            if len(rs):
                r = rs[0]
                if len(r)<12:
                    env = 'qtipython'
                else :
                    env = 'jn'
            
        
        #ls = list(filter(lambda l:'jupyter' in l and str(pid) in l.split(' '), s.split('\n')))
        #ls = list(filter(lambda l:'ipkernel_launcher' in l and str(pid) in l.split(' '), s.split('\n')))
        #ls = list(filter(lambda l:'ipkernel' in l and str(pid) in l, s.split('\n')))
        #ls = list(filter(lambda l:'ipkernel' in l and str(pid) in l, proclines))
        ##print(ls)
        #if len(ls) == 1:
            #l = ls[0]
            #import re
            #pa = re.compile(r'kernel-([-a-z0-9]*)\.json')
            #rs = pa.findall(l)
            #if len(rs):
                #r = rs[0]
                #if len(r)<12:
                    #env = 'qtipython'
                #else :
                    #env = 'jn'
        return env
    except:
        return env
    

class pyi():
    '''
    python info
    
    plt : Bool
        mean plt avaliable
    env :
        belong [cmd, cmdipython, qtipython, spyder, jn]
    '''
    pid = os.getpid()
    gui = 'ipykernel' in sys.modules
    cmdipython = 'IPython' in sys.modules and not gui
    ipython = cmdipython or gui
    spyder = 'spyder' in sys.modules
    if gui:
        env = 'spyder' if spyder else jupyterNotebookOrQtConsole()
    else:
        env = 'cmdipython' if ipython else 'cmd'
    
    cmd = not ipython
    qtipython = env == 'qtipython'
    jn = env == 'jn'
    
    plt = gui or 'DISPLAY' in os.environ 

#print('Python Envronment is %s'%pyi.env)
