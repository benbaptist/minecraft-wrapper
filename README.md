#Overview#
Wrapper.py is a simple Minecraft server wrapper for implementing various functions into the server without the need for bukkit. 

#Usage#
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
- Minecraft 1.7 and later support (uses tellraw!)