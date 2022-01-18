#!/bin/bash

realscript=`realpath $0`
scipyendir=`dirname $realscript`

if ! [ -r ${HOME}/bin/pyenv ] ; then
    ln -s $scipyendir/doc/install/Python/Unix/pyenv ${HOME}/bin
fi
    
echo "Initial pyenv script was linked to $HOME/bin/pyenv"
echo "You must now make an alias in your .bashrc ."
echo "See $scipyendir/docs/installation/Python/Unix/README for details"

if [ -z ${VIRTUAL_ENV} ] ; then
    
    echo "You must run this script while in a virtual python environment"
    echo "in order to install other scripts"
    exit 
fi

if [ -z $BROWSER ]; then
    if [ -a $VIRTUAL_ENV/bin/browser ]; then
        source $VIRTUAL_ENV/bin/browser
    fi
fi

ln -s $scipyendir/scipyen ${VIRTUAL_ENV}/bin/scipyen
ln -s $scipyendir/noteboook.sh ${VIRTUAL_ENV}/bin/notebook
ln -s $scipyendir/jupyterlab.sh ${VIRTUAL_ENV}/bin/jupyterlab
ln -s $scipyendir/set_browser.sh ${VIRTUAL_ENV}/bin/set_browser

if [ -d $scipyendir/nrnipython ] ; then
    ln -s $scipyendir/nrnipython/nrnipython ${VIRTUAL_ENV}/bin/nrnipython
    ln -s $scipyendir/nrnipython/nrnipython ${VIRTUAL_ENV}/bin/nrnpython
    ln -s $scipyendir/nrnipython/nrnipython ${VIRTUAL_ENV}/bin/nrnpy
fi





