Build 263 (next build)
- player to player TP - Add inter-dimensional TP (1.8+) api
  Community Input enhancement proxy mode

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
- really having problems getting XMLHttpRequest to return valid JSON
 data back to the client (running webpage).  We are also using (seem forced to)
 deprecated Synchronous XMLHttpRequest (setting False to third argument in
 `XMLHttpRequest.open()`  Tried to use True a few different ways, but it still
 breaks our ability to get a good textResponse from XMLHttpRequest.

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
