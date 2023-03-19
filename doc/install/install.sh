#!/bin/bash

# Installation script stub for scipyen 23c19

upgrade_pip="N"
virtual_env="scipyenv"
ve_path=$HOME

function pipup
{
    echo "Upgrading pip locally..."
#     pip install --user --upgrade virtualenv
}

function makevirtenv
{
    read -e -p "Name of virtual environment [$virtual_env]: " virtual_env
    if [[ $? -ne 0 ]] ; then
        echo -e "Goodbye!\n"
        exit 1
    fi
    read -e p "Location of virtual environment [$HOME]: " ve_path
    
    if [[ $? -ne 0 ]] ; then
        echo -e "Goodbye!\n"
        exit 1
    fi
    virtual_env=$ve_path"/"$virtual_env
}

# read -e -t 5 -p "Upgrade pip locally? [y/$upgrade_pip]" upgrade_pip # timeout 5 s
read -e -p "Upgrade pip locally? [y/$upgrade_pip]: " upgrade_pip # no timeout

if [[ $? -ne 0 ]] ; then
    echo -e "Goodbye!\n"
    exit 1
fi

if [[ ($upgrade_pip == "y") || ($upgrade_pip == "Y") || ($upgrade_pip == "Yes") || ($upgrade_pip == "YES") || ($upgrade_pip == "yes")]] ; then
# echo $upgrade_pip
    pipup

    if [[ $? -ne 0 ]] ; then
        echo -e "\nError upgrading pip. Goodbye!\n"
        exit 1
    fi

    makevirtenv
# else
#     echo -e "Goodbye! \n"
#     exit 
fi


echo $virtual_env

# virtualenv scipyenv_23c19
# source scipyenv_23c19/bin/activate
# pip install -r ~/scipyen/doc/install/pip_requirements.txt

