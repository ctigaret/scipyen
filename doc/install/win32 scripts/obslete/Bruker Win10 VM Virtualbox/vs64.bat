@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
set "LIB=C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIB%"
set "LIBPATH=C:\Program Files (x86)\Microsoft SDKs\MPI\Lib;%USERPROFILE%\AppData\Local\Programs\Python\Python39\libs;%LIBPATH%"
set "INCLUDE=C:\Program Files (x86)\Microsoft SDKs\MPI\Include;%USERPROFILE%\AppData\Local\Programs\Python\Python39\include;%INCLUDE%"
set "PATH=C:\Program Files\Microsoft MPI\Bin;%PATH%"
SET "PROMPT=(x64) $P$G"
SET "PYTHONHOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
SET "PY_HOME=%USERPROFILE%\AppData\Local\Programs\Python\Python39\"
rem  "E:\scipyenv\Scripts\activate"
rem  "E:\scipyenv-msys64\bin\activate"
rem  SET "PROMPT=(x64 scipyenv) $P$G"
echo on
