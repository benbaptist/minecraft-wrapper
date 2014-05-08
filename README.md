#Overview#
Wrapper.py is a simple Minecraft server wrapper for implementing various functions into the server without the need for bukkit.

</br></br>It also comes with a relatively simple and straight-forward plugin API that can be used to create small Bukkit-like plugins on vanilla. 

#Usage#
You only need to download Wrapper.py, the src folder is just the extracted version of Wrapper.py.
Run `python Wrapper.py` to start. Wrapper.py is a Python-executable zipped-up folder, so you won't need to unzip it. 
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
- Minecraft 1.7 and later support (uses tellraw!)

#API#
More documentation will be released for working with the plugin API, but for now, here's a few things.</br></br>

<b>List of events</b>: https://docs.google.com/spreadsheet/ccc?key=0AoWx24EFSt80dDRiSGVxcW1xQkVLb2dWTUN4WE5aNmc&usp=sharing</br>
Check the 'plugins' folder to see some example plugins. template.py literally does nothing - it is just the shell of a plugin to work off of.
example.py contains some actual functions. 