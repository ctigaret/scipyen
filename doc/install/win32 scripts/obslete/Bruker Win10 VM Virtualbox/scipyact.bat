@echo off
REM NOTE: Below, edit activation_script and SDK
REM NOTE: ATTENTION: VIRTUAL_ENV is created by the activation script
set activation_script="z:\scipyenv\Scripts\activate"
CALL %activation_script%
set "SDK=z:\scipyen_sdk"

set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\vigra;%SDK%\lib;%SDK%\lib64;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%LIB%"
set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%LIBPATH%"
set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%USERPROFILE%\AppData\Local\Programs\Python\Python39\include;C:\Program Files (x86)\Microsoft SDKs\MPI\Include;%INCLUDE%"
set "PATH=%VIRTUAL_ENV%\bin;%VIRTUAL_ENV%\Scripts;%SDK%\bin;%USERPROFILE%\AppData\Local\Programs\Python\Python39\DLLs;C:\Program Files\Microsoft MPI\Bin;%PATH%"
SET PYTHONSTARTUP=%VIRTUAL_ENV%\Scripts\scipyen_startup.py
SET "PYTHONHOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
SET "PY_HOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"

echo on
