Build 2 (next build)
- consider temporal and timed backup hydrid system.
- interdimensional TP (vanilla servers only):
    ```
        I tested this and IT WORKS!

            ...gamemode 3 player1...
            otherperson = self.api.minecraft.getPlayer("some player2 in other dimension")
            otheruuid = otherperson.offlineUuid
            player.getClient().server_connection.packet.sendpkt(0x1b, [16,], (otheruuid,))
            ...gamemode 0 player1...
    This does underscore the need for a public api for sending packets to the server and client... and SOON.

    I think this might find application with getting players to respawn properly in HUBs too.
    ```

Build 266 / Build 1 [1.0.0  rc]
- properly implement Ctrl-z as a wrapper/server 'freeze'.
- restage version.py and make buildscript.py comply with 5 part format.
- build numbers are now unique only to major version and release type (X.x.x, 'a','b', 'rc', 'final')

  (Goals)
implement bug fixes and improvements:
- player.message broken with regards to '&' usages.  I broke this a several versions ago.
- whitelist needs a long overdue overhaul: #314
    - jspanos71 @jspanos71 Feb 04 17:28
     I'm having an issue when i try to turn on proxy mode for a whitelist server... the
     existing whitelist entries don't register as valid and doing /whitelist add at the
     console doesn't work either... is there something i'm missing? running the latest
     beta build within a couple of minor builds
- verify units and update docs if needed for adjustBackupInterval(self, desired_interval) (may have units of minutes now, not seconds...)
- When name changes occur, add option to convert local player name by changing the name and the offline filenames in serverFolder/world/playerdata/<uuid>.dat and serverFolder/world/stats/<uuid>.json
- Also re-implement the server conversion option to convert online player files to offline (and vs-vs?)


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
