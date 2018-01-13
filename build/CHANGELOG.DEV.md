Build 261 (next build)
- player to player TP - Add inter-dimensional TP (1.8+) api
  Community Input enhancement proxy mode

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
