#!/bin/sh 
echo "<!DOCTYPE RCC><RCC version=\"1.0\">" > resources.qrc
echo -e "\t<qresource>" >> resources.qrc
ls -1 images/*.svg images/*.png | sed "s/^/\t\t\<file\>/" - | sed "s/$/\<\/file\>/" - >> resources.qrc
echo -e "\t</qresource>" >> resources.qrc
echo "</RCC>" >> resources.qrc




