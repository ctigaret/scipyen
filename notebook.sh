#!/bin/bash
realscript=`realpath $0`
scipyendir=`dirname $realscript`
scipyenvdir=`dirname $scipyendir`
if [ -z $BROWSER ]; then
    source $scipyenvdir/bin/browser
fi
jupyter notebook &

