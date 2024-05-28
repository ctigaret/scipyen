#!/bin/bash

function show_help ()
{
    echo -e "\n***                                                         ***"
    echo -e "* Bash script for building a Scipyen executable (frozen Scipyen app *\n"
    echo -e "*  including its virtual python environment) using PyInstaller.              *\n"
    echo -e "***                                                         ***\n"
    echo -e "(C) 2023 Cezar M. Tigaret "
    echo -e "<cezar tigaret at gmail com> , <tigaretc at cardiff ac uk>"
    echo -e "\nInstructions:"
    echo -e "============\n"
    echo -e "In a terminal, cd to the directory containing the local clone of \n"
    echo -e "Scipyen's git repository and run 'sh build_app.sh'.\n"
    echo -e "\n"
    echo -e "By default, the frozen app will be built as a directory inside ${HOME}\scipyen_app\dist \n"
    echo -e " but this can be changed using the option below\n"
    echo -e "\n"
    echo -e "Options:"
    echo -e "========\n"
    echo -e "--install_dir=DIR\tSpecify the top directory where the frozen Scipyen will be built (default is ${HOME}\scipyen_app)\n"
    echo -e "\n"
    echo -e "Prerequisites:\n"
    echo -e "============== \n"
    echo -e "A python virtual environment for scipyen must have been built; \n"
    echo -e "\tthis will include installing an activation script for the environmment \n"
}

if [ -z ${VIRTUAL_ENV} ]; then

    if [ -a $HOME/.scipyenrc ] ; then
        source $HOME/.scipyenrc && scipyact
    else
    echo "Cannot activate a python virtual environment for Scipyen"
    exit 1
    fi
fi

destination=${HOME}/scipyen_app 

for i in "$@" ; do
    case $i in 
        --install_dir)
        destination="${i#*=}"
        shift
        ;;
        -h|-?|--help)
        show_help
        exit 0
        shift
        ;;
        -*|--*)
        echo -e "Unknown option $i"
        show_help
        shift
        exit 0
        ;;
        *)
        ;;
    esac
done

if [ -d ${destination} ] ; then
    mkdir $destination
fi

workdir=${destination}/build
distdir=${destination}/dist

pyinstaller --distpath ${distdir} --workpath ${workdir} --clean --noconfirm ./scipyen.spec

if [[ $? -ne 0 ]] ; then
echo -e "Compilation of frozen Scipyen application failed"
exit 1
fi

echo -e "Creating a desktop file for Scipyen_app\n"

# tmpfiledir=$(mktemp -d)
# tmpfile=${tmpfiledir}/cezartigaret-Scipyen.desktop
# tmpfile=${tmpfiledir}/Scipyen_app.desktop
desktopfile=${workdir}/Scipyen_app.desktop

# cat<<END > ${tmpfile}
cat<<END > ${desktopfile}
[Desktop Entry]
Type=Application
Name[en_GB]=Scipyen app
Name=Scipyen app
Comment[en_GB]=Scientific Python Environment for Neurophysiology - PyInstaller frozen application
Comment=Scientific Python Environment for Neurophysiology - PyInstaller frozen application
GenericName[en_GB]=Scipyen application 
GenericName=Scipyen application 
Icon=pythonbackend
Categories=Science;Utilities;
Exec=${distdir}/Scipyen_app
MimeType=
Path=
StartupNotify=true
Terminal=true
TerminalOptions=\s
X-DBUS-ServiceName=
X-DBUS-StartupType=
X-KDE-SubstituteUID=false
X-KDE-Username=
END

