#!python
import pathlib, subprocess
# import os, sys


resourcesdir = pathlib.Path('./gui/resources')
iconsdir = resourcesdir / 'icons'
iconsthemesdir = [d for d in list(iconsdir.glob('*')) if d.is_dir() and d.joinpath("index.theme").is_file() ]

rc_files = list()

for d in iconsthemesdir:
    pfx = d.name
    subdirs = [sd for sd in d.iterdir() if sd.is_dir()]
    index_file = pathlib.Path(*["icons", d.name, "index.theme"])
    # print(f"index_file = {index_file}")
    qrc_icontheme_name = "".join([d.name, ".qrc"])
    # print(f"qrc_icontheme_name = {qrc_icontheme_name}")
    qrc_icontheme_path = iconsdir.parent / qrc_icontheme_name
    # print(f"qrc_icontheme_path = {qrc_icontheme_path}")
    rc_icontheme_name = "_".join([d.name, "rc.py"])
    rc_icontheme_path = iconsdir.parent / rc_icontheme_name
    rc_icontheme_py = str(rc_icontheme_path).replace("-", "_")
    local_parts = [p for p in d.parts if p not in resourcesdir.parts]
    # print(f"local_parts = {local_parts}")
    local_theme_file_for_qrc = pathlib.Path(*local_parts) / index_file
    # print(f"local_theme_file_for_qrc = {local_theme_file_for_qrc}")
    with open(str(qrc_icontheme_path), mode="w") as qrc_icontheme_file:
        qrc_icontheme_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
        qrc_icontheme_file.write("\t<qresource>\n")
        qrc_icontheme_file.write(f"\t\t<file>{str(index_file)}</file>\n")
        qrc_icontheme_file.write("\t</qresource>\n")
        qrc_icontheme_file.write("</RCC>\n")
        
    subprocess.run(["pyrcc5", "-threshold", "70", "-compress", "90", "-o", rc_icontheme_py, str(qrc_icontheme_path)], shell=False)
    # rc_files.append(rc_icontheme_path)
    rc_files.append(pathlib.Path(rc_icontheme_py))
    
    for k, sd in enumerate(subdirs):
        qrc_name = "_".join([pfx, sd.name, ".qrc"])
        qrc_path = iconsdir.parent / qrc_name
        rc_name = "_".join([pfx, sd.name, "rc.py"]).replace("-", "_")
        rc_path = iconsdir.parent / rc_name
        with open(str(qrc_path), mode="w") as qrc_file:
            # d_parts = [p for p in d.parts if p not in resourcesdir.parts]
            # local_d = pathlib.Path(*d_parts)
            # prefix = "".join(["/", str(local_d)])
            qrc_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
            # qrc_file.write(f"<qresource prefix=\"{prefix}\">\n")
            # qrc_file.write("<qresource prefix=\"/\">\n")
            # qrc_file.write(f"<qresource prefix=\"{str(iconsdir.parent)}\">\n")
            qrc_file.write("\t<qresource>\n")
            # qrc_write(f"<file>{index_file.name}</file>\n")
            for f in sd.glob("**/*.svg"):
                parts = [p for p in f.parts if p not in resourcesdir.parts]
                local_f = pathlib.Path(*parts)
                f_name = str(local_f)
                if f.is_symlink():
                    # continue
                    link = f.readlink()
                    original = f.parent / link
                    o_parts = [p for p in original.parts if p not in resourcesdir.parts]
                    local_o = pathlib.Path(*o_parts)
                    original_name = str(local_o)
                    # qrc_file.write(f"\t\t<file alias=\"{original_name}\">{f_name}</file>\n")
                    qrc_file.write(f"\t\t<file alias=\"{f_name}\">{original_name}</file>\n")
                else:
                    qrc_file.write(f"\t\t<file>{f_name}</file>\n")
                    
            qrc_file.write("\t</qresource>\n")
            qrc_file.write("</RCC>\n") 
            
        subprocess.run(["pyrcc5", "-threshold", "70", "-compress", "90", "-o", str(rc_path), str(qrc_path)], shell=False)
        rc_files.append(rc_path)

imagesdir = resourcesdir / 'images'

imagespng = list(imagesdir.glob('*.png'))
imagessvg = list(imagesdir.glob('*.svg'))
imagesfiles = imagespng + imagessvg

# qrc_images_path = resourcesdir.parent / 'images.qrc'
qrc_images_path = resourcesdir / 'images.qrc'
rc_images_path  = resourcesdir.parent / 'images_rc.py'

# print(f"qrc_images_path: {qrc_images_path}")
# print(f"rc_images_path: {rc_images_path}")

# for f in imagespng:
#     local_f = pathlib.Path(imagesdir.name, f.name)
#     print(f"{f} ↦ {local_f} ↦ <file>{str(local_f)}</file>")


with open(str(qrc_images_path), mode="w") as qrc_images_file:
    qrc_images_file.write(f"<!DOCTYPE RCC><RCC version=\"1.0\">\n")
    qrc_images_file.write("\t<qresource>\n")
    for f in imagesfiles:
        # local_f = pathlib.Path(resourcesdir.name, imagesdir.name, f.name)
        local_f = pathlib.Path(imagesdir.name, f.name)
        qrc_images_file.write(f"\t\t<file>{str(local_f)}</file>\n")
    qrc_images_file.write("\t</qresource>\n")
    qrc_images_file.write("</RCC>\n")
    
subprocess.run(["pyrcc5", "-threshold", "70", "-compress", "90", "-o", str(rc_images_path), str(qrc_images_path)], shell=False)

# rc_files.append(rc_images_path)

# with open("gui/icons_rc.py", mode="w") as icons_rc_file:
with open("gui/resources_rc.py", mode="w") as resources_file:
    for f in rc_files:
        local_f = pathlib.Path(*[p for p in f.parts if p not in resourcesdir.parts])
        resources_file.write(f"from .resources import {f.stem}\n")
        
    resources_file.write(f"from . import {rc_images_path.stem}\n")
