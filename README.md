#Overview#
Wrapper.py is an easy to use Minecraft server wrapper for adding extra functionality into the server without modifying the server jar file.
</br></br>It also comes with a relatively simple and straight-forward - yet powerful - plugin API that can be used to create Bukkit-like plugins with no server modding.  The API works best when operated in proxy mode. (If you are using a modded server system like bukkit, forge, sponge, etc, wrapper should __not__ be run in proxy mode!)

#Installation#
Wrapper.py doesn't require any special modules for most of the basic features to work, but web mode and proxy mode require `requests` and `pycrypto`, and `pkg_resources`.

You will also need `tar` installed if you need backups. Most Linux distros have this pre-installed, but you may need to install it manually on Windows: http://gnuwin32.sourceforge.net/packages/gtar.htm

You only need to download Wrapper.py, the src folder is just the extracted version of Wrapper.py.</br>

*Wrapper is presently written for Python 2.7, but we are progressing towards python 3.  Only python 3.4 and later will be supported*

**LINUX Installation**

You can run the following command to download the stable Wrapper.py (if you have wget installed):

`wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py`

or the following to download the unstable, development version of Wrapper.py:

`wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/Wrapper.py`

To install dependencies, use pip:

`pip install requests pkg_resources pycrypto`

Place the wrapper.py file in your minecraft folder and then run `python Wrapper.py` to start.


**Windows Installation**

You may need to get [python](https://www.python.org/downloads/) as it does not normally come with Windows.<br>
For best results, make sure the location of the python.exe file is in your system 'path' variable.


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

Download the wrapper.py file and place it in your minecraft folder, then create a batch file to run the wrapper, or start it from the command prompt.


**Start Up**

Run `python Wrapper.py` to start. On first start, it'll create a wrapper.properties file for you to configure and exit. Set it to boot the jar file of your choice, and then start Wrapper.py again.

_An alternative method of running wrapper is to run the source package directly.  To do this, clone the repo, copy the folder 'wrapper' to the desired location (usually in your server folder), and run it thusly:_<br>
`python /path/to/server/wrapper`


Wrapper.py is a Python-executable zipped-up folder, rather than a plain text file.


On first run, it'll create the configuration file 'wrapper.properties' and exit. Tune this file to your needs, and then run `python Wrapper.py` again.


Any console command beginning with a slash (/) will be interpreted as a Wrapper.py command.<br>
Type /help to see a list of Wrapper.py commands.<br>
To completely shutdown the wrapper, type /halt.</br>
If you run into any bugs, please report them!

The master branch will run all versions of minecraft if you don't use proxy mode. If you're using 1.6 and earlier, please turn on pre-1.7-mode in wrapper.properties.  If you want to use proxy mode in 1.9 or later versions, you must switch to the development branch (again, only for vanilla type unmodded servers!)

#Features#
Wrapper.py supports the following features:
- Plugin system for adding Bukkit-like features to a vanilla server
  - Proxy mode allows you to add extra functionality to plugins, such as real /commands
  - Permissions system with group support
  - Jump to different servers without reconnecting (extremely experimental, possibly broken on the development branch)
- Automatic Backups
  - Automatically delete the oldest backups once you reach amount of backups
  - Specify which folders and files get backed up
- IRC bridge
  - Controlling server from IRC
  - Achievements, deaths, and whatnot appear on IRC
  - Chat between Minecraft server and IRC channels
- Scheduled reboots
- Web remote for controlling the server and the wrapper through your web browser
- Shell scripts (Linux) that are called upon certain events (similar to plugin events, but quicker and easier)
- Minecraft 1.7 and later support (uses tellraw!)

#API#
The doucmentation for Wrapper.py is not complete, but you can find a quick reference on the plugin API here:
</br><a href="http://wrapper.benbaptist.com/docs/api.html">http://wrapper.benbaptist.com/docs/api.html</a>

It isn't finished, nor is it pretty, but it should help give you an idea of the methods that can be used. More documentation will be released for working with the plugin API, but for now, here's a few things.</br></br>

<b>List of events</b>: https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing</br>

</br></br>Check the 'example-plugins' folder to see some example plugins.
<ul>
<li>template.py does nothing - it is just the shell of a plugin to work off of.</li>
<li>example.py contains some actual functions. </li>
<li>zombie.py is a fun test plugin that leaves behind undead versions of people when killed by undead mobs.</li>
<li>speedboost.py gives everyone a speedboost when someone dies - similar to survival games.</li>
<li>poll.py allows players to vote for certain things on the server. It isn't very up-to-date at the moment, however. </li>
</ul>
</br>Tip: Set debug=True in wrapper.properties if you want to see more error messages and other useful messages while developing plugins.
