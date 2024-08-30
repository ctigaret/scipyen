# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

$myWindowsID=[System.Security.Principal.WindowsIdentity]::GetCurrent()
$myWindowsPrincipal=new-object System.Security.Principal.WindowsPrincipal($myWindowsID)

# Get the security principal for the Administrator role
$adminRole=[System.Security.Principal.WindowsBuiltInRole]::Administrator

# if ($myWindowsPrincipal.IsInRole($adminRole))
# {
#     $desktop=$shell.SpecialFolders.Item("AllUsersDesktop")
#     $wdir=$shell.SpecialFolders.Item("AllUsersDesktop")
# }
# else
# {
#     $desktop=$shell.SpecialFolders.Item("Desktop")
#     $wdir=Join-Path -Path $Home -ChildPath "Documents"
# }

$srcdir=Split-Path -Path $MyInvocation.InvocationName -Parent
$myDrive=Split-Path -Path $MyInvocation.InvocationName -Qualifier
# find out where is this repository located
$p=$srcdir
while ( !(Test-Path -Path (Join-Path -Path $p -ChildPath ".git")))
{
    $p = Split-Path -Path $p
}
$repodir=$p

$myScipyenLaunchScript=Join-Path -Path $repodir -ChildPath "src\scipyen\scipyen.py"
$myCondaEnv=$Env:CONDA_PREFIX
$myAnaconda=$Env:CONDA_PREFIX_1
$myActivate=Join-Path -Path $myAnaconda -ChildPath "Scripts\activate.bat"
$program="cmd.exe"
$activateArgs1= "$myActivate $myAnaconda"
$activateArgs2= "conda activate $myCondaEnv"

$launchArgs="python -Xfrozen_modules=off $myScipyenLaunchScript"

$activateScriptContent = @"
@echo off
echo Activating python virtual environment (mamba) in $myCondaEnv
$activateArgs1 && $activateArgs2
"@


$launchScriptContent = @"
@echo off
echo Activating python virtual environment (mamba) in $myCondaEnv
$activateArgs1 && $activateArgs2 && $launchArgs
"@

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


