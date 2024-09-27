#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later


function request_miniforge ()
{
    read -e -p "Enter the miniforge directory (no spaces, please) or CTRL+C to cancel: "
#     echo "reply is $REPLY"
    miniforge_dir=$(printf %s "$REPLY" | envsubst)

    if test -d $miniforge_dir ; then
        my_conda=${miniforge_dir}/bin/conda
        eval "$($my_conda shell.bash hook)"
    else
        echo
        echo "You did not provide a valid path to Miniforge installation. Goodbye!"
        echo
        exit -1
    fi
}

function install_miniforge ()
{
    if [[ $(uname) -eq "Linux" ]]; then
#         echo "This is a Linux machine"
        wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
    else
#         echo "This is something else"
        curl -fsSLo Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-$(uname -m).sh"
    fi

    if [[ $? -ne 0 ]]; then
        echo
        echo "Could not download Miniforge installer. Goodbye!"
        echo
        exit -1
    fi

    bash Miniforge3.sh -b -p ${miniforge_dir}

    if [[ $? -ne 0 ]]; then
        echo
        echo "Could not install Miniforge. Goodbye!"
        echo
        exit -1
    else
        rm -fr Miniforge3.sh
        source "${miniforge_dir}/etc/profile.d/conda.sh"
        # For mamba support also run the following command
        source "${miniforge_dir}/etc/profile.d/mamba.sh"

        my_conda=${miniforge_dir}/bin/conda
        eval "$($my_conda shell.bash hook)"

        if [[ $? -ne 0 ]]; then
            echo
            echo "Could not activate conda. Goodbye!"
            echo
            exit -1
        fi
    fi
}

function complete_install ()
{
    echo
    echo "Installing additional pip packages"
    echo
    pip install -r "$scipyendir"/setup_env/conda_pip_reqs.txt
    cd "$scipyendir"/src/scipyen/gui/scipyen_console_styles
    pip install .
    echo
    echo "Installing breeze icons..."
    echo
    tar -x -f ${scipyendir}/payload/breeze_icons.tar.gz -C ${CONDA_PREFIX}/share/icons
    tar -x -f ${scipyendir}/payload/breeze-dark_icons.tar.gz -C ${CONDA_PREFIX}/share/icons
    echo
    echo "Done"
    echo
}

function make_launch_script_conda()
{
target_dir=${HOME}/bin
mkdir -p ${target_dir}

if [ -r ${target_dir}/scipyen ] ; then
    dt=`date '+%Y-%m-%d_%H-%M-%s'`
    mv ${target_dir}/scipyen ${target_dir}/scipyen.$dt
fi

shopt -s lastpipe

cat <<END > ${target_dir}/scipyen
#!/usr/bin/env bash
if [ -z \${CONDA_DEFAULT_ENV} ]; then
eval "\$(${miniforge_dir}/bin/conda shell.bash hook)"
fi
if [ \${CONDA_DEFAULT_ENV} = "base" ]; then
eval "\$(conda shell.bash hook)"
conda activate $env_name
elif [ \${CONDA_DEFAULT_ENV} != "${env_name}" ]; then
echo "You're in the wrong environment: ${CONDA_DEFAULT_ENV}  - goodbye!"
exit -1
fi
python -Xfrozen_modules=off "$scipyendir"/src/scipyen/scipyen.py "\$*"

END
shopt -u lastpipe
chmod +x ${target_dir}/scipyen

echo -e "Scipyen launch script created as ${target_dir}/scipyen \n"

}

# echo "Run this script from a directory OUTSIDE scipyen repo"
realscript=`realpath $0`
scipyendir=`dirname "$realscript"`
env_name="scipyenv"
miniforge_dir=$HOME/miniforge3
virtualenv_dir=$HOME/$env_name

if [[ $(pwd) == ${scipyendir} ]]; then
    echo
    echo "You must run this script from a directory OUTSIDE scipyen repo."
    echo "Goodbye!"
    echo
    exit -1
fi


if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Conda (Miniforge) does not appear to be available."
    PS3='Please enter your choice: '
    options=("Install Miniforge" "Miniforge is installed elsewhere" "Quit")
    select opt in "${options[@]}"
    do
        case $opt in
            "Miniforge is installed in a custom place")
                request_miniforge
                break
    #             echo "you chose choice 1"
                ;;
            "Install Miniforge")
                echo
                echo "Will install Miniforge in $HOME/miniforge3"
                echo
                install_miniforge
                break
                ;;
    #         "Option 3")
    #             echo "you chose choice $REPLY which is $opt"
    #             ;;
            "Quit")
                exit 0
                break
                ;;
            *) echo "invalid option $REPLY";;
        esac
    done

fi

if [ ${CONDA_DEFAULT_ENV} = "base" ]; then
    has_scipyenv=$(conda env list | grep $env_name)
    if [ "${has_scipyenv:-_}" == "_" ]; then
        echo "Creating ${env_name} environment"
        echo
        mamba create -y --name "$env_name" python=3.11 --file "$scipyendir"/setup_env/conda_reqs.txt
        mamba init
    fi
    echo
    echo "Activating $env_name environment"
    echo
    conda activate $env_name

    if [[ $? -ne 0 ]]; then
        echo "Could not activate $env_name - goodbye!"
        exit -1
    fi

elif [ ${CONDA_DEFAULT_ENV} -ne ${env_name} ]; then
    echo "You're in a wrong conda environment: $CONDA_DEFAULT_ENV  - goodbye!"
    exit -1
fi

echo "$env_name IS ACTIVE"
echo
complete_install

if [[ $? -ne 0 ]]; then
    echo "You must complete the installation manually"
    echo ""
    echo "1. Restart the shell (or, better, open a new shell)"
    echo "2. Activate the environment: "
    echo "  2.1 If conda and mamba are in your path, call:"
    echo "      \$  mamba activate $env_name"
    echo "  2.2 othwerwise, call:"
    echo "      \$ eval \"($miniforge_dir/bin/conda shell.bash hook)\" "
    echo "      \$ conda activate $env_name"
    echo "3. Call: "
    echo "      \$ pip install -r $scipyendir/setup_env/conda_pip_reqs.txt"
    echo "4. Change to directory $scipyendir/src/scipyen/gui/scipyen_console_styles :"
    echo "      \$ cd $scipyendir/src/scipyen/gui/scipyen_console_styles"
    echo "5. Call:"
    echo "      \$ pip install ."
    echo ""
    exit -1
fi

make_launch_script_conda


# the scipyenv is already created

