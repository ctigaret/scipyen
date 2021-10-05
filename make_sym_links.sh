#!/bin/bash
realscript=`realpath $0`
scipyendir=`dirname $realscript`
# envdir=`dirname $scipyendir`


if [ -z ${VIRTUAL_ENV+_} ] ; then
    echo "This script must be run from a virtual Python environment"
fi

setup_browser () {
    # try falkon, then firefox, then chromium, then chrome in this order
}
