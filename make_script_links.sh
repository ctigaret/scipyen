#!/bin/bash

if [ -z ${VIRTUAL_ENV} ] ; then
    echo "You must run this script while in a virtual python environment"
fi

realscript=`realpath $0`
scipyendir=`dirname $realscript`

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
    




