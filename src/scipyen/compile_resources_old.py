#!python
import pathlib, subprocess
# import os, sys

mydir = pathlib.Path('./gui/resources')
breeze_qrc = pathlib.Path('./breeze_resources.qrc')
breeze_rc = pathlib.Path('./gui/breeze_resources_rc.py')
breezesvgs = mydir.glob('icons/breeze/**/*.svg')

breeze_dark_qrc = pathlib.Path('./breeze_dark_resources.qrc')
breeze_dark_rc = pathlib.Path('./gui/breeze_dark_resources_rc.py')
breezedarksvgs = mydir.glob('icons/breeze-dark/**/*.svg')

qrc = pathlib.Path('./resources.qrc')
rc = pathlib.Path('./gui/resources_rc.py')
images = list(mydir.glob('images/**/*.svg')) + list(mydir.glob('images/**/*.png'))

with open(str(breeze_qrc), mode="w") as qrc_file:
    qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
    qrc_file.write("<qresource prefix=\"/\">\n")

    for svgfile in breezesvgs:
        qrc_file.write(f"<file>{str(svgfile)}</file>\n")

    qrc_file.write("</qresource>")
    qrc_file.write("</RCC>") 
    
subprocess.run(["pyrcc5","-o", str(breeze_rc), str(breeze_qrc)], shell=False)

with open(str(breeze_dark_qrc), mode="w") as qrc_file:
    qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
    qrc_file.write("<qresource prefix=\"/\">\n")

    for svgfile in breezedarksvgs:
        qrc_file.write(f"<file>{str(svgfile)}</file>\n")
        
    qrc_file.write("</qresource>")
    qrc_file.write("</RCC>") 
    
subprocess.run(["pyrcc5","-o", str(breeze_dark_rc), str(breeze_dark_qrc)], shell=False)

with open(str(qrc), mode="w") as qrc_file:
    qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
    qrc_file.write("<qresource prefix=\"/\">\n")
        
    for imgfile in images:
        qrc_file.write(f"<file>{str(imgfile)}</file>\n")

    qrc_file.write("</qresource>")
    qrc_file.write("</RCC>") 
    
subprocess.run(["pyrcc5","-o", str(rc), str(qrc)], shell=False)

    

    

# echo "<!DOCTYPE RCC><RCC version=\"1.0\">" > breeze-resources.qrc
# echo -e "\t<qresource prefix='/'>" >> breeze-resources.qrc
# ls -1 -R icons/breeze/*.svg images/*.png | sed "s/^/\t\t\<file\>/" - | sed "s/$/\<\/file\>/" - >> resources.qrc
# echo -e "\t</qresource>" >> resources.qrc
# echo "</RCC>" >> resources.qrc




