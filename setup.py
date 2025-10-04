from setuptools import setup #, find_packages
from pathlib import Path

VERSION = Path('src/scipyen/VERSION').read_text(encoding="utf-8").strip("\n").strip()

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
