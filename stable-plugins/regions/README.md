# Overview #

Regions is the back end implementation that takes care of the 'low-level'
implementation of the regions package; stuff like creation and 
maintenance of region data.  Regions also implements the actual process
of protecting the region from unauthorized player activity.

Regions Manager is the front-end command interface for the Regions
protection plugin and can be used to create, administer, and maintain
regions.  It also does some basic world edit functions.  It is not very 
user friendly and is intended for operation by an admin/staff member.
Regions Manager can itself be used as a back end for a higher level 
player-friendly land claim system

# Set up #

## permissions ## 

After installing the regions plugin files, you need to set up
some permissions so that you (or designated people) can use the 
command interface.  The permissions below can be manually given using wrapper's 
`/permission` command (e.g., `/perms users <username> set region.player True`),
but let's do it the easier way:

Use the GroupsManager plugin:<br>
set your permission to use it (level 10 Superops [./superops.txt] don't
 need to do this):<br>
`/perms users <username> set groupsmanager.auth True`


In the `/wrapper-data/plugins/groupsmanager` directory, create the 
group manager files.  First, create the group definitions file:<br><br>
_"groups.txt"_
```
owner
admin
trusted
```


Authorized players (let's call them group 'trusted') get these permissions
by creating a trusted.txt file:<br><br>
_"trusted.txt"_
```
region.player
# region.home  (optional, if you want to give players this command)
```

Admin Staff (group 'admin") need these permissions to administer 
regions(claims) for others:<br><br>
_"admin.txt"_
```
region.wand
region.delete
region.define
region.protect
region.adjust
region.setowner
SurestTexas0
# own more than one region (optional, not needed for admin duties)
region.multiple

# inherit trusted
trusted
```

Optionally, you can set a higher "owner" level to give more (dangerous) 
 commands:<br><br>
_"owner.txt"_
```
# You can do a lot of damage if you misuse these three!
region.copy
region.replace
region.fill

region.dumps

# inherit admin (which will inherit trusted)
admin
```

run the following command to load the files into the wrapper permission
system:<br><br>
```
/loadgr
```

Easy!, now just give yourself the appropriate group permission:<br><br>
admin/staff - `/perms user <username> group admin`<br>
player - `/perms user <player> group trusted`<br>

# Using Regions #

## create a region ##

 1) get the wand:  `//wand`.
 2) Using the wand, right click and left click on two opposing blocks
  (_note: you can also manually select the positions by standing in a location
   and using the `//pos1` and `//pos2` commands_).
 3) Once the corners are selected, decide on a name for the region and type (I'll use
  'myproperty' here):<br> `//rg define myproperty`<br>
 4) now select the region for further edits:<br>`//rg use myproperty`<br>
 5) You must now define the height and depth of the region (I'll use 5 and 256):<br>
  `//rg floor 5`<br>
  `//rg roof 256`<br>
 6) The region is now created!  The next step is to activate protection:<br>
  `rg protect on`
