#Overview#
Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying the server jar file.

</br></br>It also comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used to create Bukkit-like plugins on vanilla.

[![Join the chat at https://gitter.im/benbaptist/minecraft-wrapper](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/benbaptist/minecraft-wrapper?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

NOTICE: Wrapper will Accept the minecraft server EULA on your behalf.  Using wrapper means you also accept the EULA, which
will be set to true in the eula.txt file in your server folder.
[Mojang EULA](https://account.mojang.com/documents/minecraft_eula)


#Installation#
Wrapper.py doesn't require any special modules for most of the basic features to work, but web mode and proxy mode require `requests` and `pycrypto`, and `pkg_resources`.

You will also need `tar` installed if you need backups. Most Linux distros have this pre-installed, but you may need to install it manually on Windows: http://gnuwin32.sourceforge.net/packages/gtar.htm

You only need to download Wrapper.py, the src folder is just the extracted version of Wrapper.py.</br>


**LINUX Installation**
You can run the following command to download the stable Wrapper.py (if you have wget installed):

```wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py```

or the following to download the unstable, development version of Wrapper.py:

```wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/Wrapper.py```

To install dependencies, use pip (note: you may need to use sudo in some cases):

```pip install requests pycrypto```

Make sure Python's setuptools is also installed. On Debian-based systems, run the following:

```sudo apt-get install python-setuptools```

Place the wrapper.py file in your minecraft folder and then run `python Wrapper.py` to start.


**Windows Installation**


You may need to get [python 2.7.x](https://www.python.org/downloads/) as it does not come with Windows.
for best results, ensure the add python.exe to path is installed during the setup


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

Download the wrapper.py file and place it in your minecraft folder, then create a batch file to run the wrapper, or start it from the command prompt:
`python wrapper.py`



**Start Up**


Run `python Wrapper.py` to start. On first start, it'll create a wrapper.properties file for you to configure and exit. Set it to boot the jar file of your choice, and then start Wrapper.py again.

Wrapper.py is a Python-executable zipped-up folder, rather than a plain text file. If you want to view the source code, open it with a zip file viewer OR download the src folder.</br>

On first run, it'll create the configuration file 'wrapper.properties' and exit. Tune this file to your needs, and then run `python Wrapper.py` again.  It will also create a logging.json file to configure log handlers (you should not need to modify this file, unless you have a special logging need).</br>

Type /help to see a list of Wrapper.py commands.  In cases where a Wrapper and minecraft command are identical, precede the command with a '/' to specify Wrapper's command. To completely shutdown the wrapper, type /halt.</br>

If you run into any bugs, please report them!

Wrapper.py is made to work with 1.7.2 and later, but it will work on 1.6.4 and earlier if you don't use proxy mode and you turn on pre-1.7-mode in wrapper.properties.

#Features#
Wrapper.py supports the following features:
- Plugin system for adding Bukkit-like features to a vanilla server
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

#API#
The documentation for Wrapper.py is not complete, but you can find a reference on the plugin API here:
</br><a href="https://github.com/benbaptist/minecraft-wrapper/wiki/Plugin-API">wrapper wiki</a>

Wrapper continues to be a work in progress and changes often happen faster than they get documented, but this should help give you an idea of the methods that can be used. below is a list of plugin events that can be registered in your plugins:</br></br>
<b>List of events</b>: https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing</br>

</br></br>Check the 'example-plugins' folder to see some example plugins.
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
            "level": "INFO" <-- Set to DEBUG or TRACE
        },
...
```
  Debug is a normal debugging setting.  TRACE allows detailed information, such as parsing of packets, etc.  If you want TRACE to be logged, find the item "trace" and change it's "level" to "TRACE" (set to "ERROR" by default)
