@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
REM Edit this location to point to the source code of Qt
SET _ROOT=%VIRTUAL_ENV%\src\qt5
SET PATH=%_ROOT%\qtbase\bin;%_ROOT%\gnuwin32\bin;%PATH%
REM Uncomment the below line when using a git checkout of the source repository
SET PATH=%_ROOT%\qtrepotools\bin;%PATH%
REM Uncomment the below line when building with OpenSSL enabled. 
REM If so, make sure the directory points to the correct location (binaries for OpenSSL).
REM SET PATH=C:\OpenSSL-Win32\bin;%PATH%
rem NOTE: try to use the built openssl
rem  SET PATH=C:\Program Files\OpenSSL-Win64\bin;%PATH%
REM When compiling with ICU, uncomment the lines below and change <icupath> appropriately:
REM NOTE: try to use built icu
rem  SET INCLUDE=C:\icu\dist\include;%INCLUDE%
rem  SET LIB=C:\icu\dist\lib;%LIB%
rem  SET PATH=C:\icu\dist\lib;%PATH%
REM Add path to jom.exe -already in %VIRTUAL_ENV%\bin
rem  SET PATH=C:\jom;%PATH%
REM Contrary to earlier recommendations, do NOT set QMAKESPEC.
SET _ROOT=
REM Keeps the command line open when this script is run.
cmd /k
