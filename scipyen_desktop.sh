#!/bin/bash
realscript=`realpath $0`
scipyendir=`dirname $realscript`
source $HOME/scipyenv3.10/bin/activate
$scipyendir/scipyen

# scipyendir=$HOME/scipyen
# if [ -z $VIRTUAL_ENV ]; then
# #     source $scipyenvdir/bin/activate
#     echo "You must run this script while in a virtual python environment"
# fi
# 
# if [ -z $BROWSER ]; then
#     if [ -a $VIRTUAL_ENV/bin/browser ]; then
#         source $VIRTUAL_ENV/bin/browser
#     fi
# fi
# 
# # NOTE: 2021-02-04 18:00:07
# # On linux, override KDE or other DEs theming from overriding the resources 
# # (colors etc) in the InterViews GUI
# a=`which xrdb` # do we have xrdb to read the X11 resources? (on Unix almost surely yes)
# if [ $0 == 0 ] ; then
#     if [ -r $scipyendir/neuron_python/app-defaults/nrniv ] ; then
#         xrdb -merge $scipyendir/neuron_python/app-defaults/nrniv
#     fi
# fi
# python3 $scipyendir/scipyen.py



