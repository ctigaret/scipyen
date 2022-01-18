@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%LIB%"
set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%LIBPATH%"
set "INCLUDE=%VIRTUAL_ENV%\include;C:\Program Files (x86)\Microsoft SDKs\MPI\Include;%INCLUDE%"
set "PATH=%VIRTUAL_ENV%\bin;C:\Program Files\Microsoft MPI\Bin;%PATH%"
SET "PROMPT=(x64) $P$G"
rem  "E:\scipyenv\Scripts\activate"
rem  "E:\scipyenv-msys64\bin\activate"
rem  SET "PROMPT=(x64 scipyenv) $P$G"
echo on
