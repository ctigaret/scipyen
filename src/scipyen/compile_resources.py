#!python
import pathlib, subprocess
# import os, sys


resourcesdir = pathlib.Path('./gui/resources')
iconsdir = resourcesdir / 'icons'
# iconsdir = pathlib.Path('./gui/resources/icons')
iconsthemesdir = [d for d in list(iconsdir.glob('*')) if d.is_dir() and d.joinpath("index.theme").is_file() ]

rc_files = list()

for d in iconsthemesdir:
    pfx = d.name
    subdirs = [sd for sd in d.iterdir() if sd.is_dir()]
    for k, sd in enumerate(subdirs):
        # if k > 0:
        #     break
        qrc_name = "_".join([pfx, sd.name, ".qrc"])
        qrc_path = iconsdir.parent / qrc_name
        rc_name = "_".join([pfx, sd.name, "rc.py"])
        rc_path = iconsdir.parent / rc_name
        with open(str(qrc_path), mode="w") as qrc_file:
            # prefix = "".join(["/", str(iconsdir)])
            d_parts = [p for p in d.parts if p not in resourcesdir.parts]
            local_d = pathlib.Path(*d_parts)
            prefix = "".join(["/", str(local_d)])
            # prefix = "".join(["/", str(d)])
            qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
            # qrc_file.write(f"<qresource prefix=\"{prefix}\">\n")
            # qrc_file.write("<qresource prefix=\"/\">\n")
            # qrc_file.write(f"<qresource prefix=\"{str(iconsdir.parent)}\">\n")
            qrc_file.write("<qresource>\n")
            for f in sd.glob("**/*.svg"):
                # f_name = "".join(["./", str(f)])
                # parts = [p for p in f.parts if p not in sd.parts]
                parts = [p for p in f.parts if p not in resourcesdir.parts]
                local_f = pathlib.Path(*parts)
                f_name = str(local_f)
                if f.is_symlink():
                    continue
                    link = f.readlink()
                    original = f.parent / link
                    # o_parts = [p for p in original.parts if p not in sd.parts]
                    o_parts = [p for p in original.parts if p not in resourcesdir.parts]
                    local_o = pathlib.Path(*o_parts)
                    # original_name = "".join(["./", str(original)])
                    original_name = str(local_o)
                    # original_name = str(original)
                    qrc_file.write(f"<file alias=\"{original_name}\">{f_name}</file>\n")
                    # qrc_file.write(f"<file alias=\"{f_name}\">{original_name}</file>\n")
                else:
                    qrc_file.write(f"<file>{f_name}</file>\n")
                    
            qrc_file.write("</qresource>\n")
            qrc_file.write("</RCC>\n") 
            
        subprocess.run(["pyrcc5", "-threshold", "70", "-compress", "90", "-o", str(rc_path), str(qrc_path)], shell=False)
        rc_files.append(rc_path)
        
with open("gui/icons_rc.py", mode="w") as icons_rc_file:
    for f in rc_files:
        local_f = pathlib.Path(*[p for p in f.parts if p not in resourcesdir.parts])
        # rc_file_name = pathlib.Path("resources", str)
        icons_rc_file.write(f"from gui.resources import {str(local_f)}\n")

# breeze_qrc = pathlib.Path('./breeze_resources.qrc')
# breeze_rc = pathlib.Path('./gui/breeze_resources_rc.py')
# breezesvgs = mydir.glob('icons/breeze/**/*.svg')
# 
# breeze_dark_qrc = pathlib.Path('./breeze_dark_resources.qrc')
# breeze_dark_rc = pathlib.Path('./gui/breeze_dark_resources_rc.py')
# breezedarksvgs = mydir.glob('icons/breeze-dark/**/*.svg')
# 
# qrc = pathlib.Path('./resources.qrc')
# rc = pathlib.Path('./gui/resources_rc.py')
# images = list(mydir.glob('images/**/*.svg')) + list(mydir.glob('images/**/*.png'))

# with open(str(breeze_qrc), mode="w") as qrc_file:
#     qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
#     qrc_file.write("<qresource prefix=\"/\">\n")
# 
#     for svgfile in breezesvgs:
#         qrc_file.write(f"<file>{str(svgfile)}</file>\n")
# 
#     qrc_file.write("</qresource>")
#     qrc_file.write("</RCC>") 
#     
# subprocess.run(["pyrcc5","-o", str(breeze_rc), str(breeze_qrc)], shell=False)
# 
# with open(str(breeze_dark_qrc), mode="w") as qrc_file:
#     qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
#     qrc_file.write("<qresource prefix=\"/\">\n")
# 
#     for svgfile in breezedarksvgs:
#         qrc_file.write(f"<file>{str(svgfile)}</file>\n")
#         
#     qrc_file.write("</qresource>")
#     qrc_file.write("</RCC>") 
#     
# subprocess.run(["pyrcc5","-o", str(breeze_dark_rc), str(breeze_dark_qrc)], shell=False)
# 
# with open(str(qrc), mode="w") as qrc_file:
#     qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
#     qrc_file.write("<qresource prefix=\"/\">\n")
#         
#     for imgfile in images:
#         qrc_file.write(f"<file>{str(imgfile)}</file>\n")
# 
#     qrc_file.write("</qresource>")
#     qrc_file.write("</RCC>") 
#     
# subprocess.run(["pyrcc5","-o", str(rc), str(qrc)], shell=False)

    

    

# echo "<!DOCTYPE RCC><RCC version=\"1.0\">" > breeze-resources.qrc
# echo -e "\t<qresource prefix='/'>" >> breeze-resources.qrc
# ls -1 -R icons/breeze/*.svg images/*.png | sed "s/^/\t\t\<file\>/" - | sed "s/$/\<\/file\>/" - >> resources.qrc
# echo -e "\t</qresource>" >> resources.qrc
# echo "</RCC>" >> resources.qrc




