  ### **Running Wrapper for the first time**
  ---------------------------------------------

    To start wrapper using your passphrase:</br>
    `python Wrapper.py --passphrase "my special passphrase - keep this a secret!"`

    If a passphrase is not supplied, Wrapper will prompt for one:
    ```
    please input a master passphrase for Wrapper.  This passphrase will be used to encrypt
     all passwords in Wrapper.
    >
    ```


 - When you first run Wrapper, you will see the following output as it creates the logging file, a wrapper.properties.json
 file, and then exits.:
    ```
    [15:19:18] [root/WARNING]: Unable to locate logging.json -- Creating default logging configuration
    please input a master passphrase for Wrapper.  This passphrase will be used to encrypt all passwords in Wrapper.  Please use a fairly long phrase (minimum is 8 characters).  You can change the pass-phrase later with /passphrase <new phrase>
    >
    [15:19:30] [Config/WARNING]: Updated wrapper.properties.json file - check and edit configuration if needed and start again.

    ```

- Open the wrapper properties file, set the `["General"]["command"]` item to boot the jar file and java start
 options of your choice.

- Wrapper supports having a separate server and wrapper folder.  This is also recommended, although you can simply put
 Wrapper in the same directory with your server.  Examples (item `["General"]["server-directory"]` in the config file):

     - setting `"../server"` - will set the server folder to a sister directory.
     - or you can use an absolute path: `"/home/user/minecraft/server"`.
     - use the default `"."` to run wrapper inside your server folder.

- Tune the file to your remaining preferences, and then run wrapper again.

- If the server is new (only a server.jar file in the server directory) You will see output similar
 to this:
    ```
    [15:24:10] [root/INFO]: Logging configuration file (logging.json) located and loaded, logging configuration set!
    please input a master passphrase for Wrapper.  This passphrase will be used to encrypt all passwords in Wrapper.  Please use a fairly long phrase (minimum is 8 characters).  You can change the pass-phrase later with /passphrase <new phrase>
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
     ...
    [15:28:16] [Server thread/INFO]: Preparing spawn area: 94%
    [15:28:17] [Server thread/INFO]: Done (7.956s)! For help, type "help" or "?"
    [15:28:17] [Wrapper.py/INFO]: Server started
    [15:28:17] [Wrapper.py/INFO]: Proxy listening on *:25566
    ```

Wrapper.py is now full up and running!
