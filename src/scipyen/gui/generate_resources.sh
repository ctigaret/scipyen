#!/bin/sh 
# NOTE: add your pyrcc5 version here; on openSUSE Leap 15.0
# this is one of pyrcc5-2.7  pyrcc5-3.6 
# for pict we use PyQt5 and python3 (pyrcc5-3.6)
# pyrcc5 resources/resources.qrc > resources_rc.py

pyrcc5-3.6 resources/resources.qrc > resources_rc.py

