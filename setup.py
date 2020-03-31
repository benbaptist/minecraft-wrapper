# from distutils.core import setup
from setuptools import find_packages, setup, Command

from wrapper.__version__ import __version__

setup(
    name='Wrapper.py',
    version=__version__,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    license='???',
    long_description=open('README.md').read(),
    scripts=["bin/wrapper-lite"]
)
