#!/bin/sh 
echo "<!DOCTYPE RCC><RCC version=\"1.0\">" > breeze-resources.qrc
echo -e "\t<qresource prefix='/'>" >> breeze-resources.qrc
ls -1 -R icons/breeze/*.svg images/*.png | sed "s/^/\t\t\<file\>/" - | sed "s/$/\<\/file\>/" - >> resources.qrc
echo -e "\t</qresource>" >> resources.qrc
echo "</RCC>" >> resources.qrc




