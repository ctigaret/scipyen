from setuptools import setup #, find_packages
from pathlib import Path
import subprocess

def getUnbuiltVersion(path:Path) -> str:
    proc = subprocess.run([sys.executable, "-m", "setuptools_scm"], capture_output=True, cwd=path.as_posix())
    if proc.returncode == 0:
        return proc.stdout.decode().replace("\n", "")

def checkGitRepo(path:Path) -> bool:
    gitTest = subprocess.run(["git", "-C", path.as_posix(), "status", "--short", "--branch"], capture_output=True)
    return gitTest.returncode == 0

def getVersion():
    src = Path("src")
    repoDir = src.parent
    if checkGitRepo(repoDir):
        ret = getUnbuiltVersion(repoDir)
    else:
        ret = Path('src/scipyen/VERSION').read_text(encoding="utf-8").strip("\n").strip()
    return ret

VERSION = getVersion()

setup(
    name='Scipyen',
    # version='0.0.1',
    version=VERSION,
    install_requires=[
        'importlib-metadata; python_version>="3.11"',
    ],
    # package_dir = {"": "src"},
    # packages=find_packages(
    #     # All keyword arguments below are optional:
    #     where='src',  # '.' by default
    #     include=['scipyen*'],  # ['*'] by default
    #     exclude=[],  # empty by default
    # ),
    # install_requires=[
    #     'requests',
    #     'importlib-metadata; python_version<"3.10"',
    # ],
)
