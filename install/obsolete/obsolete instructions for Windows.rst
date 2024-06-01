## MPICH
Download from [here](https://www.microsoft.com/en-us/download/confirmation.aspx?id=57467):
* msmpisetup.exe <- run this first
* msmpisdk.msi

    If you choose to install these, then edit
    scipyact.bat, vs64.bat and scipyact_vs64.bat
    to append:
    C:\Program Files (x86)\Microsoft SDKs\MPI\Include to %INCLUDE%
    C:\Program Files (x86)\Microsoft SDKs\MPI\Lib to %LIB% and %LIBPATH%
    C:\Program Files\Microsoft MPI\Bin to %PATH%

## Ruby - to build Qt locally - not needed anymore
Download installer + devkit from [here](https://rubyinstaller.org/downloads/)
I used rubyinstaller-devkit-3.0.2-1-x64.exe

## StrawberryPerl - to build Qt locally - not needed anymore
Get strawberry-perl-5.32.1.1-64bit.msi from [here](https://strawberryperl.com/)

## flex and bison - required to build neuron - not needed anymore
Download from [here](https://sourceforge.net/projects/winflexbison/)
I use the win_flex_bison-latest.zip
Extract win_bison.exe and win_flex.exe to %USERPROFILE%\Scripts

## msys2-64bit - required for radline & termcap, see below - not needed anymore
Download installer from [here](https://www.msys2.org/)
Run the installer, follow the instruction [here](https://www.msys2.org/)
* make sure you run it after first installation ("Run MSYS2 Now")
* you may want to choose another drive (it will easily eat uo a few GiB of your
disk space)

## readline & termcap - required for building NEURON; supplied via msys2-mingw-w64-x86_64 - not needed anymore
* start MSYS2-MinGW64 from the Start menu
* run pacman -Su
* see below under NEURON heading for details

NOTE: Readline and termcap libraries are in XXX:\msys64\mingw64\include, lib, etc.
where XX si the drive where you installed MSYS2
