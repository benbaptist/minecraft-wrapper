### **Windows Download and setup**

You may need to get [python](https://www.python.org/downloads/) as it does not normally come with Windows. For
 best results, make sure the location of the python.exe file is in your system 'path' variable.

Windows installations of Python are mostly beyond the scope of this document.  If you get errors; investigate,
 Google it, Stack Overflow it, and read any error messages carefully to find out what additional pieces of Windows-ware
 you will need to get it working.  For convenience, these Python 2.7 instructions were made when I first started using
 wrapper with Windows (2014).  They are not completely accurate or up to date any more:


Python 2.7 should already have pip and setuptools installed, however they will be old versions.  You should manually remove them and install the updated versions from the command prompt (need to be administrator to do this):
```
pip uninstall setuptools
pip install pip
pip install setuptools
```

Before installing requests, you will need to install the [Microsoft Visual C++ Compiler for Python 2.7](http://www.microsoft.com/en-us/download/details.aspx?id=44266).

Then from the command prompt:
```
pip install requests
pip install cryptography
pip install bcrypt
```

Download the Wrapper.py file and place it in the desired folder.

