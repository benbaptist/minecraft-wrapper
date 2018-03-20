# Overview #

Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying 
the server jar file.

It also comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used
 to create Bukkit-like plugins with no server modding.  The API works best when operated in proxy mode.


We also have a gitter channel: [![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

NOTICE: Wrapper will Accept the minecraft server EULA on your behalf.  Using wrapper means you also accept the EULA, which
will be set to true in the eula.txt file in your server folder.
[Mojang EULA](https://account.mojang.com/documents/minecraft_eula)


# Installation #

###  **Python Versions**
Python 3.5 or higher is the recommended Python version to use with Wrapper.

*Wrapper is only designed to be compatible with Python 3.4+ and python 2.7+ versions (Using a python 2.7 version below 2.7.11 is also _not_ recommended)

*It may run under python 2.6, but this is untested and may cause errors.  Certain Linux distros with Python 2.7 also have known issues with the requests module.*


###  **Dependencies**
You must have a pip version > 9.0.1 to ensure wrapper's dependencies will install correctly. Bcrypt and cryptography
 may not install correctly if your pip version is not at least 9.0.1.
To ensure you have the correct pip version:

 `pip install --upgrade pip>=9.0.1`

Wrapper.py requires the following packages: </br>
- `requests` - Extensively used by Wrapper to handle internet data requests.
- `cryptography` - required for Proxy mode and internal wrapper password handling.
- `bcrypt` - Only required for the plugin API functions 'hashPassword' and 'checkPassword'
- `setuptools` - Most python libraries already have this now.  Used by the Web interface.

It is recommended that you install the requirements by using the requirements.txt
 file from the repo.  Save it to your hard drive.  Then from the same folder, you
 can type `pip install -r requirements.txt` in the console.  This will ensure you
 have these packages and their dependencies, with the proper versions.

If needed, install any older missing dependencies in older distros (using a current pip version and setuptools will usually avoid this):
```
pip install pkg_resources
```

If you have issues with bcrypt, please go to the bcrypt website on pypi for installation of bcrypt (depending on
your system, additional dependencies may be required):
[pypi.python.org](https://pypi.python.org/pypi/bcrypt/3.1.4).
Bcrypt is not critical to wrapper.  It is used in the plugin API.  It may be removed at a future date, depending on how useful (or not useful) it ends up being.

</br> Please do not submit issues regarding installing dependencies.  These are beyond
 the scope of this document or the author's expertise (in general); please research
 the solution applicable to your platform.  Some variants of the pip installation
 that can help if you are having permission problems:
 1) Use sudo with the -H flag (this example for Ubuntu type systems):
    `sudo -H pip install --upgrade pip>=9.0.1`: Only do this if you want the packages system-wide and you also _possibly_ risk breaking your packaging system or some other dependency.
 2) Better solution - use the --user flag for pip:
    `pip install --user --upgrade pip>=9.0.1`

You will also need "tar" installed if you need backups. Most Linux distros have this pre-installed, but you may need to
 install it manually on Windows: http://gnuwin32.sourceforge.net/packages/gtar.htm


###  **Wrapper.py Versions**

You only need to download Wrapper.py.  The 'wrapper' folder is the source code and is just the extracted version
 of Wrapper.py.  Wrapper.py is a Python-executable archive folder containing the sourcecode.</br>

The old stable branch "master", version 0.7.6, build 83 has now been archived in the ["Original"](https://github.com/benbaptist/minecraft-wrapper/tree/Original) branch. The original
version only supports minecraft versions up to 1.8.

[Master branch "stable"](https://github.com/benbaptist/minecraft-wrapper/tree/master):  Stable branch that is only updated with serious bug fixes and major releases

[Development branch "dev"](https://github.com/benbaptist/minecraft-wrapper/tree/development):  Development branch with newer features.

<br>

[SurestTexas Development branch "dev"](https://github.com/suresttexas00/minecraft-wrapper/tree/development):  SurestTexas00's development fork.  Might have bleeding edge stuff.


### **LINUX download and setup**

if you have wget installed, You can  use it to get Wrapper.py and its dependency lists.

For the stable Wrapper.py:

```
wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py
wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/requirements.txt
```

Or for the development version of Wrapper.py:
```
wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/Wrapper.py
wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/requirements.txt
```

To install dependencies, [See dependencies section](#dependencies)


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


###  **Start Up**

- Run `python Wrapper.py [--passphrase 'passphrase']` to start (passphrase must be 8 or more characters in length).


# Overview #
Tracer branch is a special wrapper fork that is co-opted for
use as a packet tracer.

Tracer wrapper will log all packets, clientbound and serverbound,
using text names of the packets instead of just numbers.

This first branch is built on Protocol 340, Minecraft 1.12.2.

I am hoping to keep this branch "compatible enough" with our
other branches to allow keeping tracer up to date with development/master.