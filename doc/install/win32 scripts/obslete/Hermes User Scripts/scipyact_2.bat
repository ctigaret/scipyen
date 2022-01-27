@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
rem  CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
rem  SET "PROMPT=(x64) $P$G"
REM EDIT BELOW TO SET WHERE scipyenv HAS BEEN CREATED
CALL "c:\scipyenv2\Scripts\activate"
set "SDK=c:\scipyen_sdk"
set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\vigra;%SDK%\lib;%SDK%\lib64;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIB%"
set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIBPATH%"
set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%USERPROFILE%\AppData\Local\Programs\Python\Python39\include;%INCLUDE%"
set "PATH=%VIRTUAL_ENV%\bin;%VIRTUAL_ENV%\Scripts;%SDK%\bin;%USERPROFILE%\AppData\Local\Programs\Python\Python39\DLLs;%PATH%"
SET PYTHONSTARTUP=%SDK%\scipyen_startup.py
SET "PYTHONHOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
SET "PY_HOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
rem  "E:\scipyenv-msys64\bin\activate"
rem  SET "PROMPT=(x64 scipyenv) $P$G"
echo on
