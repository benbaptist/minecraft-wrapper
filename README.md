#Overview#
Wrapper.py is a simple Minecraft server wrapper for implementing various functions into the server without the need for bukkit.

</br></br>It also comes with a relatively simple and straight-forward plugin API that can be used to create small Bukkit-like plugins on vanilla. 

#Usage#
You only need to download Wrapper.py, the src folder is just the extracted version of Wrapper.py.</br>
Run the following command to download Wrapper.py:</br>
`curl https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py`
</br>Run `python Wrapper.py` to start. Wrapper.py is a Python-executable zipped-up folder, hence why viewing it results in garbled text. If you want to view the source code, open it
with a zip file viewer OR download the src folder. 
</br>On first run, it'll create the configuration file 'wrapper.properties' and exit. Tune this file to your needs, and then run `python Wrapper.py` again.
</br>Any console command beginning with a slash (/) will be interpreted as a Wrapper.py command. 
Type /help to see a list of Wrapper.py commands. To completely shutdown the wrapper, type /halt.
</br>If you run into any bugs, please report them!

#Features#
Wrapper.py supports the following features:
- Automatic Backups
- IRC bridge
<ul>
<li> Controlling server from IRC</li>
<li> Achievements, deaths, and whatnot appear on IRC</li>
<li> Chat between Minecraft server and IRC channels</li>
</ul>
- Plugin system for modifying the Wrapper or adding Bukkit-like features to a vanilla server
<ul>
<li> Proxy mode allows you to add extra functionality to plugins, such as real /commands</li>
</ul>
- Minecraft 1.7 and later support (uses tellraw!)

#API#
More documentation will be released for working with the plugin API, but for now, here's a few things.</br></br>

<b>List of events</b>: https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing</br>
</br></br>Check the 'plugins' folder to see some example plugins. (note: plugins are supposed to go into the wrapper-plugins folder on your Wrapper.py installation)
<ul> 
<li>template.py literally does nothing - it is just the shell of a plugin to work off of.</li>
<li>example.py contains some actual functions. </li>
<li>zombie.py is a fun test plugin that leaves behind undead versions of people when killed by undead mobs.</li>
</ul>
</br>Tip: Open config.py and change debug to True in the 'Config' class if you want to see more error messages and other useful messages 
while developing plugins.
