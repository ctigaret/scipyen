@echo off
if not defined %VIRTUAL_ENV% CALL scipyact.bat

rem  set script=%~f0
rem  echo %script%

rem  for /f %%i in (powershell.exe -command "(Get-Item %script%).Target" ) do echo [%%i]

rem  echo %link_target%
rem  SET scipyendir=%~dp0
SET scipyendir=e:\scipyen

python %scipyendir%\scipyen.py
echo on
cmd /k
