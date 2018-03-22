
**< class API(object) >**

    The API (base) class contains methods for basic plugin functionality,
    such as handling events, registering commands, and more. Most
    methods aren't related to gameplay, aside from commands and
    events, but for core stuff. See the Minecraft class (accessible
    at self.api.minecraft) for gameplay-related methods.

        :Plugin Names, Events and such..: Most of the Wrapper plugin
         api is implemented with the java/javascript mixedCamelCase
         convention. (BenBaptist's first programming language being
         javascript...)  Not very Pythonic, but we have good reason
         to retain this convention.

    backups was one of the newer api modules and some thought was given
    to making the those methods snake_case when it was first being written.

    However, PEP-8 acknowledges that 'mixedCase [... is allowed
    ...] in contexts where that's already the prevailing style
    (e.g. threading.py), to retain backwards compatibility.'

    This is the case with the wrapper plugin API.  Even though
    there has been no 'official' release candidate before 1.0.0,
    Wrapper.py has been around for a while now and converting
    the entire plugin API to snake_case will break lots of people's
    plugins.

    To maintain a consitent'look and feel' within wrapper's plugin
    API, we have elected to retain this convention *in the*
    *public Plugin API only*!

    Wrapper's internals will follow standard PEP-8 conventions.

    :sample Plugin snippet:

        .. code:: python

            class Main:
                def __init__(self, api, log):
                    self.api = api

                def onEnable(self):
                    self.api.minecraft.registerHelp(
                        "Home", "Commands from the Home plugin",
                        [("/sethome", "Save curremt position as home", None),
                         ("/home",
                          "Teleports you to your home set by /sethome",
                          None),])
        ..

    

-  registerCommand(self, command, callback, permission=None)

        This registers a command that, when entered by the Minecraft
        client, will execute `callback(player, args)`. permission is
        an optional attribute if you want your command to only be
        executable if the player has a specified permission node.

        :Args:
            :command:  The command the client enters (without the
             slash).  using a slash will mean two slashes will have
             to be typed (e.g. "/region" means the user must type "//region".

            :callback:  The plugin method you want to call when the
             command is typed. Expected arguments that will be returned
             to your function will be: 1) the player  object, 2) a list
             of the arguments (words after the command, stripped of
             whitespace).

            :permission:  A string item of your choosing, such as
             "essentials.home".  Can be (type) None to require no
             permission.  (See also `api.registerPermission` for another
             way to set permission defaults.)

        :sample usage:

            .. code:: python

                self.api.registerCommand("home", self._home, None)
            ..

        :returns:  None/Nothing

        

-  registerEvent(self, eventname, callback)

        Register an event and a callback function. See
         https://github.com/benbaptist/minecraft-wrapper/blob/development/documentation/events.rst
         for a list of events.

        :Args:
            :eventname:  A text name from the list of built-in events,
             for example, "player.place".
            :callback: the plugin method you want to be called when the
             event occurs. The contents of the payload that is passed
             back to your method varies between events.

        :returns:  None/Nothing

        

-  registerPermission(self, permission=None, value=False)

        Used to set a default for a specific permission node.

        Note: *You do not need to run this function unless you want*
        *certain permission nodes to be granted by default.*
        *i.e., 'essentials.list' should be on by default, so players*
        *can run /list without having any permissions*

        :Args:
            :permission:  String argument for the permission node; e.g.
             "essentials.list"
            :value:  Set to True to make a permission default to True.

        :returns:  None/Nothing

        

-  registerHelp(self, groupname, summary, commands)

        Used to create a help group for the /help command.

        :Args:
            :groupname: The name of the help group (usually the plugin
             name). The groupname is the name you'll see in the list
             when you run '/help'.

            :summary: The text that you'll see next next to the help
             group's name.

            :commands: a list of tuples in the following example format;

                .. code:: python

                    [("/command <argument>, [optional_argument]", "description", "permission.node"),
                    ("/summon <EntityName> [x] [y] [z]", "Summons an entity", None),
                    ("/suicide", "Kills you - beware of losing your stuff!", "essentials.suicide")]
                ..

        :returns:  None/Nothing

        

-  blockForEvent(self, eventtype)

        Blocks until the specified event is called.
        

-  callEvent(self, event, payload)

        Invokes the specific event. Payload is extra information
        relating to the event. Errors may occur if you don't specify
        the right payload information.
        

-  getPluginContext(self, plugin_id)

        Returns the instance (content) of another running wrapper
        plugin with the specified ID.

        :arg plugin_id:  The `ID` of the plugin from the plugin's header.
         if no `ID` was specified by the plugin, then the file name
         (without the .py extension) is used as the `ID`.

        :sample usage:

            .. code:: python

                essentials_id = "com.benbaptist.plugins.essentials"
                running_essentials = api.getPluginContext(essentials_id)
                warps = running_essentials.data["warps"]
                print("Warps data currently being used by essentials: \n %s" %
                      warps)
            ..

        :returns:  Raises exception if the specified plugin does not exist.

        

-  getStorage(self, name, world=False, formatting="pickle")

        Returns a storage object manager.  The manager contains the
        storage object, 'Data' (a dictionary). 'Data' contains the
        data your plugin will remember across reboots.

        :NOTE: This method is somewhat different from previous Wrapper
         versions prior to 0.10.1 (build 182).  The storage object is
         no longer a data object itself; It is a manager used for
         controlling the saving of the object data.  The actual data
         is contained in Dictionary subitem 'Data'

        ___

        :Args:
            :name:  The name of the storage (on disk).
            :world:
                :False: set the storage's location to
                 '/wrapper-data/plugins'.
                :True: set the storage path to
                 '<serverpath>/<worldname>/plugins'.

            :formatting="pickle":  Pickle formatting is the default. pickling is
             less strict than json formats and leverages binary storage.
             Use of json (or future implemented formats) can result in
             errors if your keys or data do not conform to json standards
             (like use of string keys).  However, pickle is not generally
             human-readable, whereas json is human readable. If you need
             a human-readable copy (for debugging), consider using
             self.api.helpers.putjsonfile(<yourDictionary>) to write a
             copy to disk in Json.  if you do so, check the return status
             of `putjsonfile` to make sure it was written.

        ___

        :sample methods:

            The new method:

            .. code:: python

                # to start a storage:
                self.homes = self.api.getStorage("homes", True)

                # access the data:
                for player in self.homes.Data:  # note upper case `D`
                    print("player %s has a home at: %s" % (
                        player, self.homes.Data[player]))

                # to save (storages also do periodic saves every minute):
                self.homes.save()

                # to close (and save):
                def onDisable(self):
                    self.homes.close()
            ..

            the key difference is here (under the old Storage API):

            .. code:: python

                # This used to work under the former API
                # however, this will produce an exception
                # because "self.homes" is no longer an
                # iterable data set:
                for player in self.homes:  <= Exception!
                    print("player %s has a home at: %s" % (
                        player, self.homes[player]))
            ..

            **tip**
            *to make the transition easier for existing code, redefine
            your the storage statements above like this to re-write as
            few lines as possible (and avoid problems with other
            plugins that might link to your plugin's data)*:

            .. code:: python

                # change your storage setup from:
                self.homes = self.api.getStorage("homes", True)

                # to:
                self.homestorage = self.api.getStorage("homes", True)
                self.homes = homestorage.Data

                # Now the only other change you need to make is to any
                # .save() or .close() statements:
                def onDisable(self):
                    # self.homes.close()  # change to -
                    self.homestorage.close()
            ..

        

-  wrapperHalt(self)

        Shuts wrapper down entirely.  To use this as a wrapper-restart
        method, use some code like this in a shell file to start
        wrapper (Linux example).  This code will restart wrapper
        after every shutdown until the console user ends it with CTRL-C.

        .. caution::
            (using CTRL-C will allow Wrapper.py to close gracefully,
            saving it's Storages, and shutting down plugins. Don't use
            CTRL-Z unless absolutely necessary!)
        ..

        :./start.sh:


            .. code:: bash

                    #! bin/bash
                    function finish() {
                      echo "Stopped startup script!"
                      read -p "Press [Enter] key to continue..."
                      exit
                    }

                    trap finish SIGINT SIGTERM SIGQUIT

                    while true; do
                      cd "/home/wrapper/"
                      python Wrapper.py
                      sleep 1
                    done
            ..

        

-  createGroup(self, groupname)

        Used to create a permission group.

        :Args:
            :groupname: The name of the permission group.


        :returns:  string message indicating the outcome

        

-  deleteGroup(self, groupname)

        Used to delete a permission group.

        :Args:
            :groupname: The name of the permission group.


        :returns:  string message indicating the outcome

        

-  addGroupPerm(self, groupname, permissionnode, value=True)

        Used to add a permission node to a group.

        :Args:
            :groupname: The name of the permission group.

            :permissionnode: The permission node to add to the group.
             The node can be another group!  Nested permissions must be
             enabled (see player api "hasPermission").

            :value: value of the node.  normally True to allow the
             permission, but can be false to deny the permission. For
             instance, you want a "badplayer" group to be denied some
             command that would normally be permitted.

        :returns:  string message indicating the outcome

        

-  deleteGroupPerm(self, groupname, permissionnode)

        Used to remove a permission node to a group.

        :Args:
            :groupname: The name of the permission group.

            :permissionnode: The permission node to remove.

        :returns:  string message indicating the outcome

        

-  resetGroups(self)

        resets group data (removes all permission groups).

        :returns:  nothing

        

-  resetUsers(self)

        resets all user data (removes all permissions from all users).

        :returns:  nothing

        

-  hash_password(self, password)
 Bcrypt-based password encryption.  Takes a raw string password
        returns a string representation of the binary hash.

        Bcrypt functions are to be used where ever you are storing a user's
        password, but do not ever want to be able to "know" their password
        directly.  We only need to know if the password they supplied is
        correct or not.

        :Args:
            :password: The raw string password to be encrypted.

        :returns: a string representation of the encrypted data.  Returns
         False if bcrypt is not installed on the system.

        

-  check_password(self, password, hashed_password)
 Bcrypt-based password checker.  Takes a raw string password and
        compares it to the hash of a previously hashed password, returning True
        if the passwords match, or False if not.

        Bcrypt functions are to be used where ever you are storing a user's
        password, but do not ever want to be able to "know" their password
        directly.  We only need to know if the password they supplied is
        correct or not.

        :Args:
            :password: The raw string password to be checked.
            :hashed_password: a previously stored hash.

        :returns: Boolean result of the comparison.  Returns
         False if bcrypt is not installed on the system.
        
