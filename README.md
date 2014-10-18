#Overview#
Wrapper.py is a simple Minecraft server wrapper for implementing various functions into the server without the need for bukkit.

</br></br>It also comes with a relatively simple and straight-forward plugin API that can be used to create small Bukkit-like plugins on vanilla. 

#Usage#
Wrapper.py doesn't require any special modules for most of the basic features to work, but web mode and proxy mode require the following: `pkg_resources`, `requests`, and `pycrypto`. 

</br></br>
You only need to download Wrapper.py, the src folder is just the extracted version of Wrapper.py.</br>  
On Linux, you can run the following command to download the stable Wrapper.py (if you have wget installed):</br></br>  
```

wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/master/Wrapper.py
```  
or the following to download the unstable, development version of Wrapper.py:
```

wget https://raw.githubusercontent.com/benbaptist/minecraft-wrapper/development/Wrapper.py
```
Run `python Wrapper.py` to start. On first start, it'll create a wrapper.properties file for you to configure and exit. Set it to boot the jar file of your choice, and then start Wrapper.py again. 

Wrapper.py is a Python-executable zipped-up folder, rather than a plain text file. If you want to view the source code, open it
with a zip file viewer OR download the src folder.</br>   
On first run, it'll create the configuration file 'wrapper.properties' and exit. Tune this file to your needs, and then run `python Wrapper.py` again.</br>  
Any console command beginning with a slash (/) will be interpreted as a Wrapper.py command. 
Type /help to see a list of Wrapper.py commands. To completely shutdown the wrapper, type /halt.</br>  
If you run into any bugs, please report them!

#Features#
Wrapper.py supports the following features:
- Plugin system for adding Bukkit-like features to a vanilla server
<ul>
<li> Proxy mode allows you to add extra functionality to plugins, such as real /commands</li>
<li> Permissions system with group support </li>
<li> Jump to different servers without reconnecting (extremely experimental, can be used by calling api.minecraft.connect(ip, port) )</li>
</ul>
- Automatic Backups
<ul>
<li>Automatically delete the oldest backups once you reach amount of backups</li>
<li>Specify precisely what folders and files get backed up</li>
</ul>
- IRC bridge
<ul>
<li> Controlling server from IRC</li>
<li> Achievements, deaths, and whatnot appear on IRC</li>
<li> Chat between Minecraft server and IRC channels</li>
</ul>
- Shell scripts that are called upon certain events (similar to plugin events, but quicker and easier)
- Minecraft 1.7 and later support (uses tellraw!)

#API#
The doucmentation for Wrapper.py is not complete, but you can find a quick reference on the plugin API here:
</br><a href="http://wrapper.benbaptist.com/docs/api.html">http://wrapper.benbaptist.com/docs/api.html</a>

It isn't finished, nor is it pretty, but it should help give you an idea of the methods that can be used. More documentation will be released 
for working with the plugin API, but for now, here's a few things.</br></br>

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
