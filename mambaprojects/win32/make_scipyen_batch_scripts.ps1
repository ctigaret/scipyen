# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

$myWindowsID=[System.Security.Principal.WindowsIdentity]::GetCurrent()
$myWindowsPrincipal=new-object System.Security.Principal.WindowsPrincipal($myWindowsID)

# Get the security principal for the Administrator role
$adminRole=[System.Security.Principal.WindowsBuiltInRole]::Administrator

$topdir=Split-Path -Path $MyInvocation.InvocationName -Parent
$srcdir=Split-Path -Path $topdir -Parent
echo $srcdir
$myDrive=Split-Path -Path $MyInvocation.InvocationName -Qualifier
echo $myDrive
# find out where is this repository located
# $p=$srcdir
#while ( !(Test-Path -Path (Join-Path -Path $p -ChildPath ".git")))
# {
#     $p = Split-Path -Path $p
# }
# $repodir=$srcdir

$myScipyenLaunchScript=Join-Path -Path $srcdir -ChildPath "src\scipyen\scipyen.py"
echo $Env
$myCondaEnv=$Env:CONDA_PREFIX
echo $myCondaEnv
# NO NEED for these, just make sure you have called conda init from Miniforge prompt right after having installed miniforge3
# $myAnaconda="c:\ProgramData\miniforge3"
# echo $myAnaconda
# $myActivate=Join-Path -Path $myAnaconda -ChildPath "Scripts\activate.bat"
$program="cmd.exe"
$setQTAPI=@"
set QT_API=pyside6
set PYQTGRAPH_QT_LIB=PySide6
set FORCE_QT_API=1
"@

# $activateArgs1= "$myActivate $myAnaconda"
# $activateArgs2= "conda activate $myCondaEnv"
$activateArgs2= "mamba activate $myCondaEnv"

$launchArgs="python -Xfrozen_modules=off $myScipyenLaunchScript"

$activateScriptContent = @"
@echo off
echo Activating python virtual environment (mamba) in $myCondaEnv
$activateArgs2
"@
# $activateArgs1 && $activateArgs2


$launchScriptContent = @"
@echo off
echo Activating python virtual environment (mamba) in $myCondaEnv
$activateArgs2
$setQTAPI
$launchArgs
"@
# $setATAPI && <#$#>activateArgs1 && $activateArgs2 && $launchArgs

# Create Scripts directory in user's home
$myScriptsDir=Join-Path -Path $HOME -ChildPath "Scripts"
if (-Not (Test-Path -Path $myScriptsDir))
{
New-Item -Path $myScriptsDir -ItemType Directory
Write-host "'$myScriptsDir' directory created"
}
# Check that Scripts directory is in PATH
$hasScriptsInPath=$Env:PATH -split ";" -contains $myScriptsDir
if (-Not $hasScriptsInPath)
{
$Env:PATH += ";$myScriptsDir"
Write-host "'$myScriptsDir' was added to your PATH"
}

$activateScript=Join-Path -Path $myScriptsDir -ChildPath "scipyact.bat"
Set-Content -Path $activateScript -Value $activateScriptContent
Write-host "To activate scipyen's environment call $activateScript"
$launchScript=Join-Path -Path $myScriptsDir -ChildPath "scipyen.bat"
Set-content -Path $launchScript -Value $launchScriptContent
Write-host "To launch scipyen from local git clone call $launchScript"


