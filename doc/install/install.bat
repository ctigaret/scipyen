@echo off
REM in progress...
REM this is where scipyen repo has been cloned
set scipyendir=e:\scipyen
REM this is where you want the virtual environment to be created
set scipyenvroot=e:
REM this is the name of the environment
REM     NOTE: set it to something relevant e.g."scipyenv<python version>"
set scipyenvname=scipyen_3_10_10
REM full path to the environment (including the name)
set scipyenvpath=%scipyenvroot%\%scipyenvname%
REM things being done manually, you MUST EDIT the code here first:
REM 1. install latest stable version of Python (3.10.10 as of 2023-03-24 09:17:50)
REM 2. navigate to where you want the new environment to be e.g., E:\
REM     NOTE: this can be a partition (in this example is e:) or a directory
REM     inside it
REM 3. install (or upgrade) pip, then virtualenv:
python -m pip install --upgrade --user pip
python -m pip install --upgrade --user virtualenv
REM 4. create the virtual environment - use a static name, for now (i.e., scipyen + python version)
REM     NOTE: Unlike UNIX, you may want to avoid using dots, unless your file manager
REM     is configured to show file extensions
cd %scipyenroot%
python -m virtualenv %scipyenvname%
REM 5. Activate the environment (NOTE: you MUST use the full path)
e:\scipyenv_3_10_10/Scripts/activate
REM your prompt should now display the environment name
REM 6. install pip requirements
REM     NOTE: This assumes you have cloned Scipyen in the root of e: partition
REM     meaning you now have a e:\scipyen directory tree
python -m pip install -r e:\scipyen\doc\install\pip_requirements.txt


REM SETLOCAL ENABLEDELAYEDEXPANSION
