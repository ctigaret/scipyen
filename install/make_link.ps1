# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# echo $myInvocation.MyCommand.Definition
# echo $myInvocation.MyCommand.Path
# see https://learn.microsoft.com/en-us/archive/blogs/virtual_pc_guy/a-self-elevating-powershell-script
# Get the ID and security principal of the current user account
$myWindowsID=[System.Security.Principal.WindowsIdentity]::GetCurrent()
$myWindowsPrincipal=new-object System.Security.Principal.WindowsPrincipal($myWindowsID)

# Get the security principal for the Administrator role
$adminRole=[System.Security.Principal.WindowsBuiltInRole]::Administrator

$shell = New-Object -ComObject WScript.Shell
# Check to see if we are currently running "as Administrator"
if ($myWindowsPrincipal.IsInRole($adminRole))
{
    $desktop=$shell.SpecialFolders.Item("AllUsersDesktop")
    $wdir=$shell.SpecialFolders.Item("AllUsersDesktop")
}
else
{
    $desktop=$shell.SpecialFolders.Item("Desktop")
    $wdir=Join-Path -Path $Home -ChildPath "Documents"
}
# # Run your code that needs to be elevated here
$srcdir=Split-Path -Path $MyInvocation.InvocationName -Parent
$myDrive=Split-Path -Path $MyInvocation.InvocationName -Qualifier
# find out where is this repository located
$p=$srcdir
while ( !(Test-Path -Path (Join-Path -Path $p -ChildPath ".git")))
{
    $p = Split-Path -Path $p
}
$repodir=$p
# echo $repodir

$myScipyenLaunchScript=Join-Path -Path $repodir -ChildPath "src\scipyen\scipyen.py"
$myCondaEnv=$Env:CONDA_PREFIX
$myAnaconda=$Env:CONDA_PREFIX_1
$myActivate=Join-Path -Path $myAnaconda -ChildPath "Scripts\activate.bat"
$targetPath="cmd.exe"
$args = "/K $myActivate $myAnaconda && conda activate $myCondaEnv && python -Xfrozen_modules=off $myScipyenLaunchScript"
$linkPath=Join-Path -Path $desktop -ChildPath "Scipyen (git).lnk"
$iconPath=Join-Path -Path $srcdir -ChildPath "pythonbackend.ico"
# Create desktop shortcut
$shortcut=$shell.CreateShortcut($linkPath)
# $shortcut | Get-Member
$shortcut.TargetPath=$targetPath
$shortcut.Arguments=$args
$shortcut.IconLocation=$iconPath
$shortcut.Workingdirectory=$wdir
$shortcut.Save()
# create start menu shortcut - doesn't work ?!?'
# $startPath = Join-Path -Path $shell.SpecialFolders.Item("Startup") -ChildPath "Scipyen.lnk"
# $startshortcut=$shell.CreateShortcut($startPath)
# $startshortcut.TargetPath=$targetPath
# $startshortcut.Arguments=$args
# $startshortcut.IconLocation=$iconPath
# $startshortcut.Workingdirectory=$wdir
# $startshortcut.Save()
