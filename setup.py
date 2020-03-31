from setuptools import find_packages, setup, Command

with open("wrapper/__version__.py", "r") as f:
    exec(f.read())

setup(
    name='Wrapper.py',
    version=__version__,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    license='???',
    long_description=open('README.md').read(),
    scripts=["bin/wrapper-lite"]
)
