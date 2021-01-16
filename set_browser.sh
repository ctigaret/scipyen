#!/bin/bash
realscript=`realpath $0`
scipyendir=`dirname $realscript`
scipyenvdir=`dirname $scipyendir`

if [ -z $1 ]; then
    echo "Resetting BROWSER to default"
    unset BROWSER
fi

echo "export BROWSER=$1" > $scipyenvdir/bin/browser


