###  **Dependencies**
--------------------------------------------
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
