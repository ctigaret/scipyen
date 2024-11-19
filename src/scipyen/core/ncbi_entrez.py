# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import os, sys, traceback, typing
from iolib import pictio as pio

_home = os.environ["USERPROFILE"] if sys.platform == "win32" else os.environ["HOME"]

api_key_file = os.path.join(_home, "NCBI_API_key")

if os.path.isfile(api_key_file):
    api_key = pio.loadTextFile(api_key_file)
else:
    api_key = None
    

hasBiopythonEntrez = False
try:
    from Bio import Entrez
    hasBiopythonEntrez = True
    
    if isinstance(api_key, str) and len(api_key.strip()):
        Entrez.api_key = api_key
    
except:
    scipywarn(f"The module {__name__} requires BioPython")

def list_databases() -> list:
    if not hasBiopythonEntrez:
        return list()
    
    with Entrez.einfo() as stream:
        record = Entrez.read(stream)
        
    return record["DbList"]
    

def get_database_info(db:str) -> dict:
    if not hasBiopythonEntrez:
        return dict()
    with Entrez.einfo(db=db) as stream:
        record = Entrez.read(stream)
    return record["DbInfo"]



