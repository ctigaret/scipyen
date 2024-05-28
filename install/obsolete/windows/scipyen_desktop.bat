@echo off
REM EDIT BELOW THE PATH TO CLONED scipyen GIT REPOSITORY
SET scipyendir=e:\scipyen
REM EDIT BELOW PATH TO THE scipyenv ACTIVATION SCRIPT
CALL "e:\scipyenv\Scripts\activate"
REM EDIT BELOW PATH TO THE scipyenv_sdk DIRECTORY
set "SDK=e:\scipyen_sdk"
set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\vigra;%SDK%\lib;%SDK%\lib64;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIB%"
set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIBPATH%"
set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%USERPROFILE%\AppData\Local\Programs\Python\Python39\include;%INCLUDE%"
set "PATH=%VIRTUAL_ENV%\bin;%VIRTUAL_ENV%\Scripts;%SDK%\bin;%USERPROFILE%\AppData\Local\Programs\Python\Python39\DLLs;%PATH%"
SET PYTHONSTARTUP=%scipyendir%\scipyen_startup.py
SET "PYTHONHOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
SET "PY_HOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
echo "Using Python Virtual Environment in "%VIRTUAL_ENV%
cmd /C "python %scipyendir%\scipyen.py"
echo on
