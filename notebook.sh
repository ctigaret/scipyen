#!/bin/bash
realscript=`realpath $0`
scipyendir=`dirname $realscript`
scipyenvdir=`dirname $scipyendir`

if [ -z $VIRTUAL_ENV ]; then
    source $scipyenvdir/bin/activate
fi

if [ -z $BROWSER ]; then
    if [ -a $scipyenvdir/bin/broswer ]; then
        source $scipyenvdir/bin/browser
    fi
fi

jupyter notebook &

