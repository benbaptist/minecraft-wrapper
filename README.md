# Overview #

Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying 
the server jar file.

</br></br>It also comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used
 to create Bukkit-like plugins with no server modding.  The API works best when operated in proxy mode. </br>


We also have a gitter channel: [![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

NOTICE: Wrapper will Accept the minecraft server EULA on your behalf.  Using wrapper means you also accept the EULA, which
will be set to true in the eula.txt file in your server folder.
[Mojang EULA](https://account.mojang.com/documents/minecraft_eula)


# Installation #

###  **Dependencies**

Wrapper.py usually doesn't require any special modules for most of the basic features to work.  However: </br>

- Some systems may also need `readline` (which is usually standard).

- Web mode and proxy mode require `requests`, `pycrypto`, and `pkg_resources`. </br>

- `bcrypt` and `cryptography` are required if you want to securely encrypt
    passwords used in Wrapper.  If you don't satisfy these imports, all
    passwords will be stored in plain text in the wrapper.properties.json.

- Make sure your pip version is up-to-date when installing bcrypt in particular:</br>
   `[sudo -H] pip install --upgrade pip`

You will also need "tar" installed if you need backups. Most Linux distros have this pre-installed, but you may need to
 install it manually on Windows: http://gnuwin32.sourceforge.net/packages/gtar.htm

</br> Please do not submit issues regarding installing dependencies.  These are beyond the scope of this document or the author's expertise (in general); please research the solution applicable to your platform.

###  **Wrapper.py Versions**

You only need to download Wrapper.py.  The 'wrapper' folder is the source code and is just the extracted version
 of Wrapper.py.  Wrapper.py is a Python-executable archive folder containing the sourcecode.</br>

The old stable branch "master", version 0.7.6, build 83 has now been archived in the "Original" branch. The original
version only supports minecraft versions prior to 1.9.

- If you are running proxymode with a Minecraft version 1.9 or newer server, you _must_ use the modern versions.
- The old version 0.7.6 may be a better choice if you require web mode (which is currently broken at this point).


###  **Python Versions**

*Wrapper is only designed to be compatible with Python 2.7+ and python 3.4+ versions

*It may run under 2.6, but this may cause problems with some dependencies.  Certain Linux distros with Python 2.7 also have known issues with the requests module.  Whether that affects wrapper or not is uncertain*


### **LINUX download and setup**

if you have wget installed, You can run the following command to download the stable Wrapper.py:

`wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py`

or the following to download the development version of Wrapper.py:

`wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/Wrapper.py`

To install dependencies, use pip.  Many modern distros will actually have most of wrapper's dependencies installed by default.
These three are commonly missing from older distros:

```
pip install requests
pip install pycrypto
pip install pkg_resources

pip install bcrypt
pip install cryptography
```

`bcrypt` and `cryptography` are newer additions to Wrapper that are also not in the standard library at this time.


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

Before installing requests and pycrypto, you will need to install the [Microsoft Visual C++ Compiler for Python 2.7](http://www.microsoft.com/en-us/download/details.aspx?id=44266).

Then from the command prompt:
```
pip install requests
pip install pycrypto
 ...
```

Download the Wrapper.py file and place it in the desired folder.


###  **Start Up**

Run `python Wrapper.py` to start.


_An alternative method of running wrapper is to run the source package directly.  To do this, clone the repo, copy the
folder 'wrapper' to the desired location and run it thusly:_<br>
`python /path/to/wrapperfolder/wrapper`


Wrapper also takes the following optional arguments:

```
  -h, --help           show this help message and exit
  --encoding, -e       Specify an encoding (other than utf-8)
  --betterconsole, -b  Use "better console" feature to anchor your imput at
                       the bottom of the console (anti- scroll-away feature)
  --passphrase, -p     Passphrase used to encrypt all passwords in Wrapper.
                       Please use as fairly long phrase (minimum is 8
                       characters). If not specified, or incorrectly supplied,
                       Wrapper will prompt for a new passphrase before
                       starting! Use "--passphrase none" to start wrapper with
                       passwords disabled.
```

To start wrapper using your passphrase:
`python Wrapper.py --passphrase "my special passphrase - keep this a secret!"`

To disable password encryption with bcrypt, use "none" for the passphrase:
`python Wrapper.py --passphrase none`

If bcrypt and cryptography are not installed or the start up passphrase is
disabled by specifying "none", Wrapper.py will handle all passwords in plain
text and will not prompt the user for a password. Otherwise, if a passphrase
is not supplied, Wrapper will prompt for one:

```
please input a master passphrase for Wrapper.  This passphrase willbe used to encrypt
 all passwords in Wrapper.
>
```


 - When you first run Wrapper, you will see the following output as it creates the logging file, a wrapper.properties.json
 file, and then exits.:
```
[15:19:18] [root/WARNING]: Unable to locate logging.json -- Creating default logging configuration
please input a master passphrase for Wrapper.  This passphrase willbe used to encrypt all passwords in Wrapper.  Please use a fairly long phrase (minimum is 8 characters).  You can change the pass-phrase later with /passphrase <new phrase>
>
[15:19:30] [Config/WARNING]: Updated wrapper.properties.json file - check and edit configuration if needed and start again.

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
 to this:
```
[15:24:10] [root/INFO]: Logging configuration file (logging.json) located and loaded, logging configuration set!
please input a master passphrase for Wrapper.  This passphrase willbe used to encrypt all passwords in Wrapper.  Please use a fairly long phrase (minimum is 8 characters).  You can change the pass-phrase later with /passphrase <new phrase>
>
[15:24:16] [Wrapper.py/INFO]: Wrapper.py started - Version [0, 14, 1] (development build #245)
[15:24:16] [Wrapper.py/WARNING]: NOTE: Server was in 'STOP' state last time  Wrapper.py was running. To start the server, run /start.
[15:24:16] [Wrapper.py/WARNING]: File 'server.properties' not found.
[15:24:16] [Wrapper.py/INFO]: Loading plugins...

```

To continue, you will need to enter `/start` to continue running (if you are using proxy mode, be aware that this must be done within 2 minutes or proxy mode will be disabled).

The server will start and accept the Eula for you:
```
/start
[15:28:02] [Wrapper.py/INFO]: Starting server...
[15:28:02] [Wrapper.py/WARNING]: File 'server.properties' not found.
[15:28:05] [Server thread/INFO]: Starting minecraft server version 1.12.2
[15:28:05] [Server thread/INFO]: Loading properties
[15:28:05] [Server thread/WARN]: server.properties does not exist
[15:28:05] [Server thread/INFO]: Generating new properties file
[15:28:05] [Server thread/WARN]: Failed to load eula.txt
[15:28:05] [Server thread/INFO]: You need to agree to the EULA in order to run the server. Go to eula.txt for more info.
[15:28:05] [Server thread/INFO]: Stopping server
[15:28:05] [Server Shutdown Thread/INFO]: Stopping server
[15:28:06] [Wrapper.py/INFO]: Starting server...
[15:28:06] [Wrapper.py/WARNING]: File 'server.properties' not found.
[15:28:06] [Wrapper.py/WARNING]: EULA agreement was not accepted, accepting on your behalf...
[15:28:08] [Server thread/INFO]: Starting minecraft server version 1.12.2
[15:28:08] [Server thread/INFO]: Loading properties
[15:28:08] [Server thread/INFO]: Default game type: SURVIVAL
[15:28:08] [Server thread/INFO]: Generating keypair
[15:28:09] [Server thread/INFO]: Starting Minecraft server on *:25565
[15:28:09] [Server thread/INFO]: Using epoll channel type
[15:28:09] [Server thread/INFO]: Preparing level "world"
[15:28:09] [Server thread/INFO]: Loaded 488 advancements
[15:28:09] [Server thread/INFO]: Preparing start region for level 0
[15:28:10] [Server thread/INFO]: Preparing spawn area: 9%
[15:28:11] [Server thread/INFO]: Preparing spawn area: 18%
[15:28:12] [Server thread/INFO]: Preparing spawn area: 30%
[15:28:13] [Server thread/INFO]: Preparing spawn area: 45%
[15:28:14] [Server thread/INFO]: Preparing spawn area: 60%
[15:28:15] [Server thread/INFO]: Preparing spawn area: 77%
[15:28:16] [Server thread/INFO]: Preparing spawn area: 94%
[15:28:17] [Server thread/INFO]: Done (7.956s)! For help, type "help" or "?"
[15:28:17] [Wrapper.py/INFO]: Server started
[15:28:17] [Wrapper.py/INFO]: Proxy listening on *:25566

```


Any console command beginning with a slash (/) will be interpreted as a Wrapper.py command.<br>
Type /help to see a list of Wrapper.py commands.<br>
To completely shutdown the wrapper, type /halt.</br>

Please read our [wiki](https://github.com/benbaptist/minecraft-wrapper/wiki) for additional information and review the issues page before submitting bug reports.<br>
If you run into any bugs, please _do_ report them!

# Features #
Wrapper.py supports the following features:
  - [Plugin system](/documentation/readme.md) for adding Bukkit-like features to a vanilla server
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
- (NOT WORKING) Web remote for controlling the server and the wrapper through your web browser
- Shell scripts that are called upon certain events (similar to plugin events, but quicker and easier)
- Minecraft 1.7 and later support
- Colorized console output.

# API #
The documentation for Wrapper.py is not complete, but you can find a reference on the wrapper plugin API here:
[Wrapper.py Plugin API](/documentation/readme.md)

####New Permissions System####

A file in the wrapper root directory "superOPs.txt" now augments the "Ops.json" file.  Operators in the ops.json file can be assigned a higher (wrapper) OP level.  The contents of the file are laid out just like server.properties (lines of \<something\>=\<value\>).

Sample `superops.txt`:
```
Suresttexas00=5
BenBaptist=9
```
Higher op levels are required to run sensitive wrapper commands like `/perms`.

####Plugins####

Wrapper continues to be a work in progress and changes often happen faster than they
 get documented, but this should help give you an idea of the methods that can be used.
 below is a list of plugin events that can be registered in your plugins:

[Original list of events](https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing)

Here is an updated list of the events:
[Wrapper events](https://docs.google.com/spreadsheets/d/1Sxli0mpN3Aib-aejjX7VRlcN2HZkak_wIqPFJ6mtVIk/edit?usp=sharing)

Check the 'example-plugins' and 'stable-plugins' folders to see some example plugins.  These are very useful for seeing how the API functions.

- template.py does nothing - it is just the shell of a plugin to work off of.
- example.py contains some more example functions.
- zombie.py is a fun test plugin that leaves behind undead versions of people when killed by undead mobs.
- speedboost.py gives everyone a speedboost when someone dies - similar to survival games.
- poll.py allows players to vote for certain things on the server. It isn't very up-to-date at the moment, however.


__Tip__:

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
