#! /bin/sh 
compiler=`which pyrcc5`
if [ -n ${compiler} ] ; then
cd gui/resources
echo "<!DOCTYPE RCC><RCC version=\"1.0\">" > resources.qrc
echo -e "\t<qresource>" >> resources.qrc
ls -1 images/*.svg images/*.png | sed "s/^/\t\t\<file\>/" - | sed "s/$/\<\/file\>/" - >> resources.qrc
echo -e "\t</qresource>" >> resources.qrc
echo "</RCC>" >> resources.qrc
# sh generate_resources_qrc.sh
cd ../..
${compiler} gui/resources/resources.qrc > gui/resources_rc.py
else
echo -e "Cannot find a Qt5 resource compiler. Goodbye!\n"
fi
