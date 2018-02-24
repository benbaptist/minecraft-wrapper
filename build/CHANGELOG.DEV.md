Build 8  [1.0b8]
- Improve web to get player.message() - see build 1.0b4, third bullet point.
- Console readouts are redirected to the player who ran the command (benefits Web).
- Improve Web Chat and Console layouts.
- Allow login page to capture a unique username for the WebAdmin.


Build 7  [1.0b7]
- Whitelist online/offline also converts player data uuid files to their correct type, so converting
 the server between online and offline will not hurt players inventory (provided you restart promptly).
- Code staged so that name changes can incorporate the same abilities to transfer UUID information


Build 6  [1.0b6]
FIX Whitelisting!  #314
- whitelist add/remove both also 'reload'... because everybody forgets that part!
- whitelist adds players using offline uuids while in proxy mode.
- two new commands added:
    - /whitelist online - convert all whitelist names to online uuids (to set server to online mode)
    - /whitelist offline -  convert all whitelist names to offline uuids (to set server to offline/proxy mode)
- uuid changes are "cosmetic" and do not affect player inventory, etc.  HOWEVER; changing a servers online mode WILL.


Build 5  [1.0b5]
- [#519](https://github.com/benbaptist/minecraft-wrapper/issues/519) - delay server backups during idle periods.


Build 4 [1.0b4]
- upgrade consoleuser.py for use with new player.message()
- add its 'execute()' method.
- create support for alternate output streams besides the console.
- more proxy fixes as I prepare to fix whitelisting issues:
    - Made disconnects work better and staged ability to allow proxy client
     to ignore proxy server disconnects (later on for lobby/multiserver ops)
    - Disconnect messages use minecraft translate and work in all client states.
    - Added way to substitute coloration and augmented text for commands wrapper
     modifies (in this case, 'op') - parse_cb.py.
    - added a 'client_notify()' function to let server request a client's
     disconnection.  Client will have the abilty to ignore this request! :D
- install vanilla whitelist commands into 'commands.py' -off, on, add, remove, list, reload
- Manually Save server before a restart (spigot plugins mess with save states).
- Fix bug in commands.command_op that would op "False" player if name is left blank.


Build 3 [1.0b3]
- Fix in-game "wrapper update" command (was broken with new version format)


Build 2 [1.0b2]
- Ensure server auto-restarts don't happen during a backup cycle.
- added some API.backups functions to test backup status.
- Fix [#521](https://github.com/benbaptist/minecraft-wrapper/issues/521)
   using a config item in Misc: "trap-ctrl-z"
- reverted "properly implement Ctrl-z as a wrapper/server 'freeze'." in favor of the above solution.
- removed option to disable wrapper passphrase.
- fixed player.message broken with regards to '&' usages.  Also works for
  all json again, including "translate".
- Player.message takes second argument for position of message (0,1,2)


Build 266 / Build 1 [1.0.0  beta]
- properly implement Ctrl-z as a wrapper/server 'freeze' (does not work).
- restage version.py and make buildscript.py comply with 5 part format.
- build numbers are now unique only to major version and release type (X.x.x, 'a','b', 'rc', 'final')


Build 265 [0.16.1]
- remove PyCrypto dependency!  PyCrypto is no longer maintained.
 PyCrypto was not pip installing properly anymore on recent Python3
 systems.  This was the straw that broke the camel's back.  It has
 fork that is being maintained (pycryptodome), but we already have a good
 crypto package requirement in use for wrapper encryption (cryptography),
 so I chose to leverage that instead to minimize the number of
 package dependencies:
- wrapper dependencies are only `requests`, `cryptography` and `bcrypt`:
 `package_resources` is part of normal setuptools on any recent pip version these days.
- added file "requirements.txt" to be useful for `pip install -r requirements.txt`

Build 264 [0.16.0] The web version.
- Web console commands pass through wrappers console parsing, so that wrapper
 commands can be run in Web.
- Add Wrapper memory usage items to Web.
- touch-up server.properties layout.
- fix player chat in Web mode.
- remove debug code console logs from web code.
- Py3 fixes for Web mode.

Build 263b [0.16.0] The web version.  (not pulled to benBaptist Dev)
- documentation touch-ups
- change check_password and hash_password (new functions) to checkPassword and
 hashPassword for API consistency.
- clean up management/html/request.js code up.
- Fixed key/session-key/sessionKey components throughout web.py, login.html, and admin.html.
- Fixed admin.html tick and statsCallback functions to get web page data to refresh properly
- Fixed up logins code some more to ensure
- Repair various stats in code.  Added free disk space stat (only works for py3).
- Move "server.consoleMessage" event code out of javaserver.py and into wrapper.py.
- make server 'restart' call start if server is stopped (versus telling user to run /start...
- Move ServerVitals class out of javaserver.py into it's own module servervitals.py
 because I keep forgetting where the class is...
- make wrapper override console /kick command because, if proxymode, it must be done with
 client.disconnect, not the console kick (which will leave the client hanging
 until it times out and will not display the kick message).
- Fix Web components:
    - Console
    - Files - New Directory working
    - Server properties - can be saved and reloaded.
    - plugins - can be disabled.  If all plugins are disabled, all disabled plugins can be reloaded.
    - Kick and ban options in player list fixed and work properly, depending on proxy mode.
    - playercounts read (x / n) (i.e. 5/20 or 1/20, etc) not "undefined/undefined"
 Only things left now to get a full working web mode:
  - [ ] get chat panel working
  - [ ] OP and DeOP buttons in playerlist (should "op" be there?)

Build 263
- Finally repaired logins; fixed isAuthed() components of login.html and admin.html
- tested OK with firefox and chrome browsers.
- Fixed bug that prevented browsing into directories with periods (like com.banbaptist.some.plugin)
- retaining the feature for using 'safe-ips'.
- Moved out alot of cruft that probably was/is experimental, unused, or meant for the new
 management.py interface.  Proposed items for removal are in `/management/html/html_deprecate`. Extra
 js, css, and junk... just lots of clutter to confuse us.

Build 262
- First working Web module, with important changes:
    - Best results with Firefox.
    - Password login is NOT WORKING
    - only connections from localhost are allowed by default.
    - To access web from another network (IP), in the config:
        1) Add the ip to "Web" config item 'safe-ips"
        2) Set item 'use_safe_ips' to true.
    - Basic buttons work (reload plugins, halt wrapper, start/stop/restart/kill server)
    - file operations fully functional (in Firefox only)!
    - Chat and console "send" things, but don't "receive" responses
__Future__
 We are also using (seem forced to) deprecated Synchronous XMLHttpRequest
 (setting False to third argument in `XMLHttpRequest.open()`  Tried to
 use True a few different ways, but it still breaks our ability to get
 a good textResponse from XMLHttpRequest.

 Right now, though, it is functional enough to do some nice RC stuff, like
 renaming and deleting files!  So, I am making it an official build for
 development!

Build 261
- Add api.base item sendEmail( message, recipients, subject, group="wrapper") to api.
- Make alerts have a threaded interface to allow non-blocking alert processing.
- Built-in alerts for wrapper startup, shutdown, and crashes.

Build 260
- Finish alerts API.  Alerts allow wrapper to send emails:
    - api.base - sendAlerts(self, message, group="wrapper")
    - New wrapper.properties.json section:
    ```json

    ...
    {
      "Alerts": {
        "enabled": false, <-- don't enable this until after a correct password has been entered.
        "password-plaintext": false, <-- 1) Enter a password in place of false... start wrapper and it will be encrypted and placed in "password"
        "password": "", <-- 2) cut this and paste it below in "encrypted-password"
        "servers": [
          {
            "group": "wrapper",
            "subject": "Wrapper.py Alert",
            "address": "smtp-mail.outlook.com",
            "encrypted-password": "Copy and Paste from 'password' (above) after wrapper encrypts it.",
            "login-name": "myliveaccount@live.com", <-- This is the email account that will send the emails.
            "port": 587,
            "recipients": [
              "someone@gmail.com",
              "someone-else@yahoo.com"
            ],
            "type": "email"
          }
        ]
      }
    }
    ...
    ```
- Correct concern with Wrapper console echoing commands when setting passwords.
 the echoed and logged password is in plain text as the user typed it. [#513](https://github.com/benbaptist/minecraft-wrapper/issues/513)
- Web mode still broken.

Build 259 (and 258)
- first crack at getting web.py working (i.e., at least getting into the admin page).
- Web mode changed for now to only permit bindings to 127.0.0.1 because:
- password checking is disabled in admin.html (function isAuthed()).
- Warning messages in wrapper startup.
- Warning messages in Login.html.

Build 257
- Add countdown timers of 45, 30, 15 and then 5-1 seconds to the reboot timers broadcasts
- Add a backups summary text.

Build 256 [0.15.1]
- fix spigot bug where nicknamed players producing chat results in
 an invalid playerobject being generated with a player.message event
 because the nickname is not a logged on player.
- will wait for first release candidate to reset build numbers..
- A few documentation updates/corrections.
- update change logs (not done properly since 0.7.7)

Starting with:
Build 255 [0.15.0] - Developement branch update
