# Repository is currently not active #
If you are interested in helping to bring wrapper up to date and maintain it, please respond using the issues tab.  An open issue exists to [request a new wrapper developer](https://github.com/benbaptist/minecraft-wrapper/issues/622).

# Overview #
-------------------------------------------
Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying 
the server jar file.  It also comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used
to create Bukkit-like plugins with no server modding.  The API works best when operated in proxy mode.

We also have a gitter channel: [![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

###  **Wrapper.py Versions**

 - [Master branch "stable"](https://github.com/benbaptist/minecraft-wrapper/tree/master):  Stable branch that is only updated with serious bug fixes and major releases. <sup id="a1">[1](#f1)</sup>
 - [Development branch "dev"](https://github.com/benbaptist/minecraft-wrapper/tree/development):  Development branch with newer features.

NOTICE: Wrapper will Accept the minecraft server EULA on your behalf. <sup id="a2">[2](#f2)</sup>


# Features #
-------------------------------------------
Wrapper.py supports the following features:
- [Plugin system](/documentation/plugin_api.md) for adding extra features to a vanilla server.
- Permissions system with group support.
- Proxy mode operation allows you to add extra bukkit-like functionality to plugins:
  - Real `/` command interface.
  - Built in hub worlds / multi-server support!
    - Use the built-in /hub functionality with world configurations set up in the wrapper config, __or__
    - Implement your own customized version with the plugin API by calling the player.connect() method.
  - Limit entity breeding / spawning with entity controls.
  - Monitor, Modify, and change:
    - player chat.
    - player block /digging/placement.
    - player inventory.
    - .. and More!
- Automatic Backups
  - Automatically delete the oldest backups once you reach a specified number of backups
  - Specify which folders and files get backed up
- IRC bridge
  - Controlling server from IRC
  - Achievements, deaths, and whatnot appear on IRC
  - Chat between Minecraft server and IRC channels
- Scheduled reboots
- Web remote for controlling the server and the wrapper through your web browser
- Shell scripts that are called upon certain events (similar to plugin events, but quicker and easier)
- Minecraft 1.7 and later support
- Colorized console logging.


# Installation #

###  **Python Versions**

Python 3.5 + is suggested,
***[However...](/documentation/pyversions.md)***

###  **Dependencies**

Wrapper.py requires the following packages: </br>
- Python packages: `pip, requests, cryptography, bcrypt, setuptools, pkg_resources`
- Tar is required for backups.
 - ***[More...](/documentation/depends.md)***


#### [**LINUX download and setup**](/documentation/linux.md)

#### [**Windows Download and setup**](/documentation/windows.md)

###  **Start Up**

You only need to download Wrapper.py.  The '\wrapper' folder is the source code and is just the extracted version
 of Wrapper.py.  Wrapper.py is a Python-executable archive folder containing the sourcecode.</br>

To start Wrapper, open a console where the `Wrapper.py` or `/wrapper` sourcecode are
located and type the following into the console to start:

 `python Wrapper.py|/wrapper [--passphrase 'passphrase']` <sup>The passphrase must be 8 or more characters in length!</sup>

#### [Starting Wrapper.py for the first time...](/documentation/first_start.md)

Once wrapper has started:
- Open the wrapper.properties.json file and tune the file to your remaining preferences.
- Tune and setup your server and server.properties accordingly.
- Restart wrapper.

    ```
    [15:28:08] [Server thread/INFO]: Starting minecraft server version 1.12.2
    [15:28:08] [Server thread/INFO]: Loading properties
     ...
    [15:28:16] [Server thread/INFO]: Preparing spawn area: 94%
    [15:28:17] [Server thread/INFO]: Done (7.956s)! For help, type "help" or "?"
    [15:28:17] [Wrapper.py/INFO]: Server started
    [15:28:17] [Wrapper.py/INFO]: Proxy listening on *:25566
    ```

### Operating wrapper ###

- Any console command beginning with a slash (/) will be interpreted firstly as a Wrapper.py command.<br>
- Type /help to see a list of Wrapper.py commands.<br>
- To completely shutdown the wrapper, type /halt.</br>

- To enter passwords into the wrapper.properties.config file, use the `/password` console command to enter the applicable password:
    `/password Web web-password <new password>`

Please read our [Doc page](/documentation/readme.md) for additional information and review the issues page before submitting bug reports.<br>
If you run into any bugs, please _do_ report them!

If you have questions, please use our [Gitter page](https://gitter.im/benbaptist/minecraft-wrapper) instead of creating an issue.


# API #
The references for the wrapper plugin API are here:
[Wrapper.py Plugin API](/documentation/plugin_api.md)

#### New Permissions System ####

A file in the wrapper root directory "superOPs.txt" now augments the "Ops.json" file.  Operators in the ops.json file can be assigned a higher (wrapper) OP level.  The contents of the file are laid out just like server.properties (lines of \<something\>=\<value\>).

Sample `superops.txt`:
```
Suresttexas00=5
BenBaptist=9
```

Higher op levels are required to run sensitive wrapper commands like `/perms`.

#### Plugins ####

The modern event list is updated with each build: [Wrapper events](/documentation/events.rst) <sup id="a3">[3](#f3)</sup>

Check the 'example-plugins' and 'stable-plugins' folders to see some example plugins.  These are very useful for seeing how the API functions.

- TEMPLATE.py and EXAMPLE.py are mostly just shells of a plugin to work off of.  They contain useful tutorial comments.
- zombie.py is a fun test plugin that leaves behind undead versions of people when killed by undead mobs.
- speedboost.py gives everyone a speedboost when someone dies - similar to survival games.
- poll.py allows players to vote for certain things on the server. It isn't very up-to-date at the moment, however.
- Essentials is a plugin loosely based off of Essentials for Bukkit.
- WorldEdit - is a plugin loosely based on the WorldEdit for Bukkit by sk89q
- SmallBrother is a lightweight logging plugin based on the old Bukkit plugin, BigBrother
- Open.py is a plugin that opens a window with nothing.  This plugin was probably just a test plugin and may not work, but contains example code for accessing packets from the player api.

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
<br><br>
<sup><b id="f1">1</b></sup> - The old stable branch "master", version 0.7.6, build 83 has now been archived in the ["Original"](https://github.com/benbaptist/minecraft-wrapper/tree/Original) branch. The original
version only supports minecraft versions up to 1.8.    [↩](#a1)

<sup><b id="f2">2</b></sup> - Using wrapper means you also accept the EULA, which will be set to true in the eula.txt file in your server folder. [Mojang EULA](https://account.mojang.com/documents/minecraft_eula)   [↩](#a2)

<sup><b id="f3">3</b></sup> - The original Event list (Wrapper version 0.7.6) - [0.7.6 Wrapper list of events](https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing)   [↩](#a3)

