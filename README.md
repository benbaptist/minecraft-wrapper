# Overview #
Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying 
the server jar file.
</br></br>It also comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used
 to create Bukkit-like plugins with no server modding.  The API works best when operated in proxy mode.


We also have a gitter channel: [![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

NOTICE: Wrapper will Accept the minecraft server EULA on your behalf.  Using wrapper means you also accept the EULA, which
will be set to true in the eula.txt file in your server folder.
[Mojang EULA](https://account.mojang.com/documents/minecraft_eula)


# Installation #

###  **Dependencies**

Wrapper.py doesn't require any special modules for most of the basic features to work, but web mode and proxy mode
 require `requests` and `pycrypto`, and `pkg_resources`.  Some systems may also need `readline` (which is usually standard).

You will also need "tar" installed if you need backups. Most Linux distros have this pre-installed, but you may need to
 install it manually on Windows: http://gnuwin32.sourceforge.net/packages/gtar.htm



###  **Wrapper.py Versions**

You only need to download Wrapper.py, the 'wrapper' folder is the source code and is just the extracted version
 of Wrapper.py.  Wrapper.py is a Python-executable zipped-up folder, rather than a plain text file.


The original stable branch "master" is build (version 0.7.6).  This version is considered to be the working 
standard version.  However, it is quite old at this point and the development version has far outpaced it.

The current "development" branch version (0.9.x) is now at a point where it is probably a much better choice to use.

- If you are running proxymode with a 1.9 or newer server, you _must_ use the development version.
- The master version 0.7.6 may be a better choice if you require web mode and possibly IRC, as those have not been tested on development.
- If you experience serious errors with IRC or web mode in the master branch, you should switch to development (unless you are able to create a pull request to fix the master).
- The features/advantages of the 0.9.x version are presently too numerous to list.



###  **Python Versions**

*Wrapper is only designed to be compatible with Python 2.7+ and python 3.4+ versions

*It may run under 2.6, but this may cause problems with some dependencies.*



**LINUX download and setup**

if you have wget installed, You can run the following command to download the stable Wrapper.py (0.7.6):

`wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py`

or the following to download the development version (0.9.x) of Wrapper.py:

`wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/Wrapper.py`

To install dependencies, use pip.  Many modern distros will actually have most of wrapper's dependencies installed by default.
These three are commonly missing from older distros:

`pip install requests pkg_resources pycrypto`



**Windows Download and setup**

You may need to get [python](https://www.python.org/downloads/) as it does not normally come with Windows.<br>
For best results, make sure the location of the python.exe file is in your system 'path' variable.

Windows installations of Python are mostly beyond the scope of this document.  If you get errors; investigate,
Google it, Stack Overflow it, and read any error messages carefully to find out what additional pieces of Windows-ware
you will need to get it working.  For convenience, these Python 2.7 instructions were made when I first started using
wrapper with Windows.  They may not be completely accurate or up to date any more:


Python 2.7 should already have pip and setuptools installed, however they will be old versions.  You should manually remove them and install the updated versions from the command prompt (need to be administrator to do this):
```
pip uninstall setuptools
pip install pip
pip install setuptools
```

Before installing requests and pycrypto, you will need to install the [Microsoft Visual C++ Compiler for Python 2.7](http://www.microsoft.com/en-us/download/details.aspx?id=44266).

Then from the command prompt:
```
pip install requests
pip install pycrypto
```

Download the Wrapper.py file and place it in the desired folder.



###  **Start Up**

Run `python Wrapper.py` to start.

_An alternative method of running wrapper is to run the source package directly.  To do this, clone the repo, copy the
folder 'wrapper' to the desired location and run it thusly:_<br>
`python /path/to/wrapperfolder/wrapper`


 - You will see the following output at first run, as it creates the logging file, a wrapper.properties 
 file (wrapper.properties.json after wrapper 0.8.x), and then exits.:
```
[12:58:31] [root/WARNING]: Unable to locate logging.json -- Creating default logging configuration
[12:58:31] [Config/WARNING]: Updated wrapper.properties.json file - check and edit configuration if needed and start again.
```

- Open the wrapper properties file, set the `["General"]["command"]` item to boot the jar file and java start
 options of your choice.
 
- Wrapper supports having a separate server and wrapper folder.  This is also recommended, although you can simply put
 Wrapper in the same directory with your server.  Examples (item `["General"]["server-directory"]` in the config file):

     - setting `../server` - will set the server folder to a sister directory.
     - or you can use an absolute path: `/home/user/minecraft/server`.
     - use the default `'.'` to run wrapper inside your server folder.

Tune the file to your remaining preferences, and then run wrapper again.

If the server is new (only a server.jar file in the server directory) You will see output similar
 to the following as Wrapper boots the server and sets up the Eula:

```
[13:42:34] [root/INFO]: Logging configuration file (logging.json) located and loaded, logging configuration set!
[13:42:34] [Wrapper.py/INFO]: Wrapper.py started - Version [0, 9, 12] (development build #174)
[13:42:34] [requests.packages.urllib3.connectionpool/INFO]: Starting new HTTP connection (1): minecraft-ids.grahamedgecombe.com
[13:42:34] [Wrapper.py/WARNING]: File 'server.properties' not found.
[13:42:34] [Wrapper.py/INFO]: Loading plugins...
[13:42:34] [Wrapper.py/INFO]: Starting server...
[13:42:34] [Wrapper.py/WARNING]: File 'server.properties' not found.
[13:42:43] [Server thread/INFO]: Starting minecraft server version 1.11.2
[13:42:43] [Server thread/INFO]: Loading properties
[13:42:43] [Server thread/WARN]: server.properties does not exist
[13:42:43] [Server thread/INFO]: Generating new properties file
[13:42:43] [Server thread/WARN]: Failed to load eula.txt
[13:42:43] [Server thread/INFO]: You need to agree to the EULA in order to run the server. Go to eula.txt for more info.
[13:42:43] [Server thread/INFO]: Stopping server
[13:42:43] [Wrapper.py/INFO]: Starting server...
[13:42:43] [Wrapper.py/WARNING]: File 'server.properties' not found.
[13:42:43] [Wrapper.py/WARNING]: EULA agreement was not accepted, accepting on your behalf...
[13:42:52] [Server thread/INFO]: Starting minecraft server version 1.11.2
[13:42:52] [Server thread/INFO]: Loading properties
[13:42:52] [Server thread/INFO]: Default game type: SURVIVAL
```


Any console command beginning with a slash (/) will be interpreted as a Wrapper.py command.<br>
Type /help to see a list of Wrapper.py commands.<br>
To completely shutdown the wrapper, type /halt.</br>

Please read our [wiki](https://github.com/benbaptist/minecraft-wrapper/wiki) for additional information and review the issues page before submitting bug reports.<br>
If you run into any bugs, please _do_ report them!

# Features #
Wrapper.py supports the following features:
  - [Plugin system](/documentation/index.md) for adding Bukkit-like features to a vanilla server
  - Proxy mode allows you to add extra functionality to plugins, such as real /commands
  - Permissions system with group support
  - Jump to different servers without reconnecting (extremely experimental, can be used by calling api.minecraft.connect(ip, port) )
- Automatic Backups
  - Automatically delete the oldest backups once you reach amount of backups
  - Specify which folders and files get backed up
- IRC bridge
  - Controlling server from IRC
  - Achievements, deaths, and whatnot appear on IRC
  - Chat between Minecraft server and IRC channels
- Scheduled reboots
- Web remote for controlling the server and the wrapper through your web browser
- Shell scripts that are called upon certain events (similar to plugin events, but quicker and easier)
- Minecraft 1.7 and later support (uses tellraw!)
- Colorized console output.

# API #
The documentation for Wrapper.py is not complete, but you can find a reference on the plugin API here:
[Wrapper.py Plugin API](/documentation/index.md)


Wrapper continues to be a work in progress and changes often happen faster than they get documented, but this should help give you an idea of the methods that can be used. below is a list of plugin events that can be registered in your plugins:</br></br>
<b>Original list of events</b>: https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing</br>

Here is a list of updates to the events:
[Wrapper events](https://docs.google.com/spreadsheets/d/1Sxli0mpN3Aib-aejjX7VRlcN2HZkak_wIqPFJ6mtVIk/edit?usp=sharing)


</br></br>Check the 'example-plugins' folder to see some example plugins.  These are very useful for seeing hwo the API functions.
<ul>
<li>template.py does nothing - it is just the shell of a plugin to work off of.</li>
<li>example.py contains some actual functions. </li>
<li>zombie.py is a fun test plugin that leaves behind undead versions of people when killed by undead mobs.</li>
<li>speedboost.py gives everyone a speedboost when someone dies - similar to survival games.</li>
<li>poll.py allows players to vote for certain things on the server. It isn't very up-to-date at the moment, however. </li>
</ul>
</br>Tip:  
If you want to see more error messages and other useful messages while developing plugins or debugging wrapper,
look for the logging.json file and make changes to the "console" section:  

```json
...
        "console": {
            "stream": "ext://sys.stdout",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "filters": [
                "plugin"
            ],
            "level": "INFO" <-- Set to DEBUG for more detailed output
        },
...
```
