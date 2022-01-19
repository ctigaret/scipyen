@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
rem  SET "PROMPT=(x64) $P$G"
REM EDIT BELOW TO SET WHERE scipyenv HAS BEEN CREATED
CALL "e:\scipyenv\Scripts\activate"
set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%USERPROFILE%\AppData\Local\Programs\Python\Python39;%USERPROFILE%\AppData\Local\Programs\Python\Python39\Lib;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIB%"
set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%USERPROFILE%\AppData\Local\Programs\Python\Python39;%USERPROFILE%\AppData\Local\Programs\Python\Python39\Lib;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIBPATH%"
set "INCLUDE=%VIRTUAL_ENV%\include;C:\Program Files (x86)\Microsoft SDKs\MPI\Include;%USERPROFILE%\AppData\Local\Programs\Python\Python39\include;%INCLUDE%"
set "PATH=%VIRTUAL_ENV%\bin;%VIRTUAL_ENV%\Scripts;C:\Program Files\Microsoft MPI\Bin;%VIRTUAL_ENV%\Boost.Build\bin;%USERPROFILE%\AppData\Local\Programs\Python\Python39\DLLs;%PATH%"
SET PYTHONSTARTUP=%VIRTUAL_ENV%\Scripts\scipyen_startup.py
rem  "E:\scipyenv-msys64\bin\activate"
SET "PROMPT=(x64 scipyenv) $P$G"
echo on
