@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
rem  CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
rem  SET "PROMPT=(x64) $P$G"
REM EDIT BELW TO SET WHERE scipyenv HAS BEEN CREATED
CALL "F:\Users\Public\scipyenv\Scripts\activate"
set LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%LIB%
set LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%LIBPATH%
set INCLUDE=%VIRTUAL_ENV%\include;%INCLUDE%
set PATH=%VIRTUAL_ENV%\bin;%PATH%
SET PYTHONSTARTUP=%VIRTUAL_ENV%\Scripts\scipyen_startup.py
rem  "E:\scipyenv-msys64\bin\activate"
rem  SET "PROMPT=(x64 scipyenv) $P$G"
echo on
